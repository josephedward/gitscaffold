import click
from . import __version__

import os
from pathlib import Path
from dotenv import load_dotenv, set_key
from github import Github, GithubException

from .parser import parse_roadmap
from .validator import validate_roadmap
from .github import GitHubClient
from .ai import extract_issues_from_markdown, enrich_issue_description

@click.group()
@click.version_option(version=__version__, prog_name="gitscaffold")
def cli():
    """Scaffold – Convert roadmaps to GitHub issues."""
    pass


def get_github_token():
    """
    Retrieves the GitHub token from .env file or prompts the user if not found.
    Saves the token to .env if newly provided.
    """
    load_dotenv()
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        click.echo("GitHub PAT not found in environment or .env file.")
        token = click.prompt('Please enter your GitHub Personal Access Token (PAT)', hide_input=True)
        # Ensure .env file exists for set_key
        env_path = Path('.env')
        env_path.touch(exist_ok=True)
        set_key(str(env_path), 'GITHUB_TOKEN', token)
        click.echo("GitHub PAT saved to .env file. Please re-run the command.")
        # It's often better to ask the user to re-run so all parts of the app pick up the new env var.
        # Or, for immediate use, ensure os.environ is updated:
        os.environ['GITHUB_TOKEN'] = token
    return token


def _populate_repo_from_roadmap(
    gh_client: GitHubClient,
    roadmap_data,
    dry_run: bool,
    ai_enrich: bool,
    context_text: str,
    roadmap_file_path: Path # For context if needed, though context_text is passed
):
    """Helper function to populate a repository with milestones and issues from roadmap data."""
    click.echo(f"Processing roadmap '{roadmap_data.name}' for repository '{gh_client.repo.full_name}'.")
    click.echo(f"Found {len(roadmap_data.milestones)} milestones and {len(roadmap_data.features)} features.")

    # Process milestones
    for m in roadmap_data.milestones:
        if dry_run:
            click.echo(f"[dry-run] Would create or fetch milestone: {m.name} (due: {m.due_date})")
        else:
            gh_client.create_milestone(name=m.name, due_on=m.due_date)
            click.echo(f"Milestone created or exists: {m.name}")

    # Process features and tasks
    for feat in roadmap_data.features:
        body = feat.description or ''
        if ai_enrich:
            if dry_run:
                click.echo(f"[dry-run] Would AI-enrich feature: {feat.title}")
            else:
                click.echo(f"AI-enriching feature: {feat.title}...")
                body = enrich_issue_description(feat.title, body, context_text)
        
        if dry_run:
            click.echo(f"[dry-run] Would create or fetch feature issue: {feat.title}")
            feat_issue_number = 'N/A (dry-run)'
            feat_issue_obj = None # In dry-run, we don't have a real issue object
        else:
            feat_issue = gh_client.create_issue(
                title=feat.title,
                body=body,
                assignees=feat.assignees,
                labels=feat.labels,
                milestone=feat.milestone
            )
            click.echo(f"Issue created or exists: #{feat_issue.number} {feat.title}")
            feat_issue_number = feat_issue.number
            feat_issue_obj = feat_issue

        for task in feat.tasks:
            t_body = task.description or ''
            if ai_enrich:
                if dry_run:
                    click.echo(f"[dry-run] Would AI-enrich sub-task: {task.title}")
                else:
                    click.echo(f"AI-enriching sub-task: {task.title}...")
                    t_body = enrich_issue_description(task.title, t_body, context_text)
            
            if dry_run:
                parent_info = f"(parent: #{feat_issue_number})"
                click.echo(f"[dry-run] Would create sub-task: {task.title} {parent_info}")
            else:
                content = t_body
                if feat_issue_obj: # Check if feat_issue_obj is not None
                    content = f"{t_body}\n\nParent issue: #{feat_issue_obj.number}".strip()
                gh_client.create_issue(
                    title=task.title,
                    body=content,
                    assignees=task.assignees,
                    labels=task.labels,
                    milestone=feat.milestone # Tasks usually inherit milestone from feature
                )
                click.echo(f"Sub-task created or exists: {task.title}")


@cli.command()
@click.argument('roadmap_file', type=click.Path(exists=True))
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env if not provided)')
@click.option('--repo', help='GitHub repository (owner/repo)', required=True)
@click.option('--dry-run', is_flag=True, help='Validate without creating issues')
@click.option('--ai-extract', is_flag=True, help='Use AI to extract issues from Markdown')
@click.option('--ai-enrich', is_flag=True, help='Use AI to enrich issue descriptions')
def create(roadmap_file, token, repo, dry_run, ai_extract, ai_enrich):
    """Populate an EXISTING GitHub repository with issues from a roadmap file."""
    actual_token = token if token else get_github_token()
    if not actual_token: # get_github_token might prompt and exit or ask to re-run
        return

    path = Path(roadmap_file)
    suffix = path.suffix.lower()

    if ai_extract:
        if suffix not in ('.md', '.markdown'):
            raise click.UsageError('--ai-extract only supported for Markdown files')
        click.echo(f"AI-extracting issues from {roadmap_file}...")
        features = extract_issues_from_markdown(roadmap_file)
        # TODO: AI extraction might need to provide milestones too, or a default one.
        # For now, assuming it primarily extracts features/tasks.
        raw_roadmap_data = {'name': path.stem, 'description': 'Roadmap extracted by AI.', 'milestones': [], 'features': features}
    else:
        raw_roadmap_data = parse_roadmap(roadmap_file)

    validated_roadmap = validate_roadmap(raw_roadmap_data)
    
    gh_client = GitHubClient(actual_token, repo)

    context_text = ''
    if ai_enrich and suffix in ('.md', '.markdown'): # Context from original MD
        context_text = path.read_text(encoding='utf-8')
    elif ai_enrich: # Context from structured roadmap (e.g. YAML)
        # This might be too verbose or not ideal. Consider if context is needed for non-MD.
        # For now, let's use the roadmap's own description.
        context_text = validated_roadmap.description or ''


    _populate_repo_from_roadmap(
        gh_client=gh_client,
        roadmap_data=validated_roadmap,
        dry_run=dry_run,
        ai_enrich=ai_enrich,
        context_text=context_text,
        roadmap_file_path=path
    )


@cli.command(name="setup-repository")
@click.argument('roadmap_file', type=click.Path(exists=True))
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env if not provided)')
@click.option('--repo-name', help='Name for the new GitHub repository (default: derived from roadmap name)')
@click.option('--org', help='GitHub organization to create the repository in (default: user account)')
@click.option('--private', is_flag=True, help='Create a private repository')
@click.option('--dry-run', is_flag=True, help='Simulate repository creation and issue population')
@click.option('--ai-extract', is_flag=True, help='Use AI to extract issues from Markdown (if roadmap is Markdown)')
@click.option('--ai-enrich', is_flag=True, help='Use AI to enrich issue descriptions')
def setup_repository(roadmap_file, token, repo_name, org, private, dry_run, ai_extract, ai_enrich):
    """Create a new GitHub repository from a roadmap file and populate it with issues."""
    actual_token = token if token else get_github_token()
    if not actual_token:
        return

    path = Path(roadmap_file)
    suffix = path.suffix.lower()

    if ai_extract:
        if suffix not in ('.md', '.markdown'):
            raise click.UsageError('--ai-extract only supported for Markdown files')
        click.echo(f"AI-extracting issues from {roadmap_file}...")
        features = extract_issues_from_markdown(roadmap_file)
        raw_roadmap_data = {'name': path.stem, 'description': f'Repository for {path.stem}', 'milestones': [], 'features': features}
    else:
        raw_roadmap_data = parse_roadmap(roadmap_file)

    validated_roadmap = validate_roadmap(raw_roadmap_data)
    
    actual_repo_name = repo_name if repo_name else validated_roadmap.name.lower().replace(' ', '-')
    repo_description = validated_roadmap.description or f"Repository for {validated_roadmap.name}"

    full_new_repo_name = ""

    if dry_run:
        owner_name = org if org else "current_user (dry_run)"
        full_new_repo_name = f"{owner_name}/{actual_repo_name}"
        click.echo(f"[dry-run] Would create GitHub repository: {full_new_repo_name}")
        click.echo(f"[dry-run] Description: {repo_description}")
        click.echo(f"[dry-run] Private: {private}")
        # For dry run of population, we need a dummy GitHubClient
        # It won't make calls, but _populate_repo_from_roadmap expects one.
        # We can initialize it with a dummy token and repo name for the dry run.
        gh_client_for_dry_run_population = GitHubClient("dummy_token_dry_run", full_new_repo_name)
    else:
        g = Github(actual_token)
        try:
            if org:
                entity = g.get_organization(org)
            else:
                entity = g.get_user()
            
            click.echo(f"Creating repository '{actual_repo_name}' under '{entity.login}'...")
            new_gh_repo = entity.create_repo(
                name=actual_repo_name,
                description=repo_description,
                private=private
            )
            full_new_repo_name = new_gh_repo.full_name
            click.echo(f"Repository '{full_new_repo_name}' created successfully.")
            gh_client_for_dry_run_population = GitHubClient(actual_token, full_new_repo_name)
        except GithubException as e:
            click.echo(f"Error creating repository: {e}", err=True)
            return
        except Exception as e: # Catch other potential errors like org not found
            click.echo(f"An unexpected error occurred during repository creation: {e}", err=True)
            return


    # Proceed to populate, using gh_client_for_dry_run_population which is correctly set up
    # for both dry-run and actual run scenarios for the population part.
    context_text = ''
    if ai_enrich and suffix in ('.md', '.markdown'):
        context_text = path.read_text(encoding='utf-8')
    elif ai_enrich:
        context_text = validated_roadmap.description or ''

    _populate_repo_from_roadmap(
        gh_client=gh_client_for_dry_run_population, # This client is real if not dry_run for repo creation
        roadmap_data=validated_roadmap,
        dry_run=dry_run, # This dry_run flag controls population behavior
        ai_enrich=ai_enrich,
        context_text=context_text,
        roadmap_file_path=path
    )
