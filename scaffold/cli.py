import click
from . import __version__

import os
import sys
import subprocess
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
    load_dotenv()  # Load .env file at the start of CLI execution
    pass


def get_github_token():
    """
    Retrieves the GitHub token from .env file or prompts the user if not found.
    Saves the token to .env if newly provided.
    Assumes load_dotenv() has already been called.
    """
    # load_dotenv() # Moved to cli()
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


def get_openai_api_key():
    """
    Retrieves the OpenAI API key from .env file or environment.
    Assumes load_dotenv() has already been called.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        # Unlike GitHub token, we won't prompt for OpenAI key for now,
        # as it's usually less interactive and more of a setup step.
        # We also won't save it back to .env from here.
        click.echo(
            "Error: OPENAI_API_KEY not found. Please set it in your environment or .env file. "
            "Ensure the .env file is in the directory where you are running gitscaffold.",
            err=True
        )
        return None
    return api_key


def _populate_repo_from_roadmap(
    gh_client: GitHubClient,
    roadmap_data,
    dry_run: bool,
    ai_enrich: bool,
    openai_api_key: str, # Added openai_api_key
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
            elif openai_api_key: # Only enrich if key is available
                click.echo(f"AI-enriching feature: {feat.title}...")
                body = enrich_issue_description(feat.title, body, openai_api_key, context_text)
        
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
                elif openai_api_key: # Only enrich if key is available
                    click.echo(f"AI-enriching sub-task: {task.title}...")
                    t_body = enrich_issue_description(task.title, t_body, openai_api_key, context_text)
            
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

    openai_api_key_for_ai = None
    if ai_extract or ai_enrich:
        openai_api_key_for_ai = get_openai_api_key()
        if not openai_api_key_for_ai:
            # get_openai_api_key already printed an error, so just return
            return 1 # Indicate error

    if ai_extract:
        if suffix not in ('.md', '.markdown'):
            raise click.UsageError('--ai-extract only supported for Markdown files')
        click.echo(f"AI-extracting issues from {roadmap_file}...")
        features = extract_issues_from_markdown(roadmap_file, api_key=openai_api_key_for_ai)
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
        openai_api_key=openai_api_key_for_ai,
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

    openai_api_key_for_ai = None
    if ai_extract or ai_enrich:
        openai_api_key_for_ai = get_openai_api_key()
        if not openai_api_key_for_ai:
            return 1

    if ai_extract:
        if suffix not in ('.md', '.markdown'):
            raise click.UsageError('--ai-extract only supported for Markdown files')
        click.echo(f"AI-extracting issues from {roadmap_file}...")
        features = extract_issues_from_markdown(roadmap_file, api_key=openai_api_key_for_ai)
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
        openai_api_key=openai_api_key_for_ai,
        context_text=context_text,
        roadmap_file_path=path
    )


def _sync_issues_from_roadmap(
    gh_client: GitHubClient,
    roadmap_data,
    existing_issue_titles: set[str],
    dry_run: bool,
    ai_enrich: bool,
    openai_api_key: str, # Added openai_api_key
    context_text: str
):
    """Helper function to sync roadmap items to GitHub, creating missing ones after prompt."""
    click.echo(f"Syncing roadmap '{roadmap_data.name}' with repository '{gh_client.repo.full_name}'.")
    click.echo(f"Found {len(existing_issue_titles)} existing issue titles in the repository.")

    # 1. Ensure Milestones exist
    for m_data in roadmap_data.milestones:
        milestone_name = m_data.name
        existing_milestone = gh_client._find_milestone(milestone_name)
        if dry_run:
            if existing_milestone:
                click.echo(f"[dry-run] Milestone '{milestone_name}' already exists. No action.")
            else:
                click.echo(f"[dry-run] Milestone '{milestone_name}' not found. Would create (Due: {m_data.due_date}).")
        else:
            if existing_milestone:
                click.echo(f"Milestone '{existing_milestone.title}' already exists.")
            else:
                click.echo(f"Milestone '{milestone_name}' not found. Creating...")
                new_milestone = gh_client.create_milestone(name=milestone_name, due_on=m_data.due_date)
                click.echo(f"Milestone created: {new_milestone.title}")

    # 2. Process features and tasks
    for feat in roadmap_data.features:
        feature_exists = feat.title in existing_issue_titles
        feat_issue_obj = None # Stores created/found feature issue for parent linking

        if not feature_exists:
            if dry_run:
                click.echo(f"[dry-run] Feature '{feat.title}' not found. Would prompt to create.")
            elif click.confirm(f"Feature '{feat.title}' not found in GitHub issues. Create it?", default=False):
                body = feat.description or ''
                if ai_enrich and openai_api_key: # Only enrich if key is available
                    click.echo(f"AI-enriching new feature: {feat.title}...")
                    body = enrich_issue_description(feat.title, body, openai_api_key, context_text)
                
                click.echo(f"Creating feature issue: {feat.title}")
                feat_issue_obj = gh_client.create_issue(
                    title=feat.title,
                    body=body,
                    assignees=feat.assignees,
                    labels=feat.labels,
                    milestone=feat.milestone
                )
                click.echo(f"Feature issue created: #{feat_issue_obj.number} {feat.title}")
                existing_issue_titles.add(feat.title) # Add to set to avoid re-prompting
            else:
                click.echo(f"Skipping feature: {feat.title}")
        else:
            click.echo(f"Feature '{feat.title}' already exists in GitHub issues. Checking its tasks...")
            # Try to get the existing feature object for potential parent linking of new tasks
            feat_issue_obj = gh_client._find_issue(feat.title)

        # Process tasks for this feature
        for task in feat.tasks:
            task_exists = task.title in existing_issue_titles
            if not task_exists:
                if dry_run:
                    click.echo(f"[dry-run] Task '{task.title}' (for feature '{feat.title}') not found. Would prompt to create.")
                elif click.confirm(f"Task '{task.title}' (for feature '{feat.title}') not found in GitHub issues. Create it?", default=False):
                    t_body = task.description or ''
                    if ai_enrich and openai_api_key: # Only enrich if key is available
                        click.echo(f"AI-enriching new task: {task.title}...")
                        t_body = enrich_issue_description(task.title, t_body, openai_api_key, context_text)
                    
                    content = t_body
                    # Attempt to link to parent feature if it was just created or already existed
                    parent_issue_for_linking = feat_issue_obj
                    if not parent_issue_for_linking and feature_exists: # If feature existed but obj not fetched yet
                        parent_issue_for_linking = gh_client._find_issue(feat.title)

                    if parent_issue_for_linking:
                        content = f"{t_body}\n\nParent issue: #{parent_issue_for_linking.number}".strip()
                    
                    click.echo(f"Creating task issue: {task.title}")
                    new_task_issue = gh_client.create_issue(
                        title=task.title,
                        body=content,
                        assignees=task.assignees,
                        labels=task.labels,
                        milestone=feat.milestone # Tasks inherit milestone from feature
                    )
                    click.echo(f"Task issue created: #{new_task_issue.number} {task.title}")
                    existing_issue_titles.add(task.title) # Add to set
                else:
                    click.echo(f"Skipping task: {task.title}")
            else:
                click.echo(f"Task '{task.title}' (for feature '{feat.title}') already exists in GitHub issues.")
    click.echo("Roadmap sync processing finished.")


@cli.command()
@click.argument('roadmap_file', type=click.Path(exists=True))
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env if not provided)')
@click.option('--repo', help='GitHub repository (owner/repo)', required=True)
@click.option('--dry-run', is_flag=True, help='Simulate and show what would be created without making changes')
@click.option('--ai-extract', is_flag=True, help='Use AI to extract issues from Markdown (if roadmap is Markdown)')
@click.option('--ai-enrich', is_flag=True, help='Use AI to enrich descriptions of new issues')
def sync(roadmap_file, token, repo, dry_run, ai_extract, ai_enrich):
    """Compare roadmap with an existing GitHub repository and prompt to create missing issues."""
    actual_token = token if token else get_github_token()
    if not actual_token:
        return

    path = Path(roadmap_file)
    suffix = path.suffix.lower()

    openai_api_key_for_ai = None
    if ai_extract or ai_enrich:
        openai_api_key_for_ai = get_openai_api_key()
        if not openai_api_key_for_ai:
            return 1

    if ai_extract:
        if suffix not in ('.md', '.markdown'):
            raise click.UsageError('--ai-extract only supported for Markdown files')
        click.echo(f"AI-extracting issues from {roadmap_file}...")
        features = extract_issues_from_markdown(roadmap_file, api_key=openai_api_key_for_ai)
        raw_roadmap_data = {'name': path.stem, 'description': 'Roadmap extracted by AI.', 'milestones': [], 'features': features}
    else:
        raw_roadmap_data = parse_roadmap(roadmap_file)

    validated_roadmap = validate_roadmap(raw_roadmap_data)
    
    gh_client = GitHubClient(actual_token, repo)

    click.echo(f"Fetching existing issue titles from repository '{repo}'...")
    existing_issue_titles = gh_client.get_all_issue_titles()
    
    context_text = ''
    if ai_enrich:
        if suffix in ('.md', '.markdown'):
            context_text = path.read_text(encoding='utf-8')
        elif validated_roadmap.description: # Use roadmap description as context for structured files
            context_text = validated_roadmap.description
    
    _sync_issues_from_roadmap(
        gh_client=gh_client,
        roadmap_data=validated_roadmap,
        existing_issue_titles=existing_issue_titles,
        dry_run=dry_run,
        ai_enrich=ai_enrich,
        openai_api_key=openai_api_key_for_ai,
        context_text=context_text
    )
    click.echo("Sync command finished.")


@cli.command(name='delete-closed')
@click.option('--repo', help='GitHub repository (owner/repo)', required=True)
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env if not provided)')
@click.option('--dry-run', is_flag=True, help='List closed issues that would be deleted, without actually deleting them')
@click.confirmation_option(prompt='Are you absolutely sure you want to delete closed issues? This action is irreversible. Type "yes" to confirm.')
def delete_closed_issues_command(repo, token, dry_run, yes): # 'yes' is injected by confirmation_option
    """Permanently delete all closed issues in a repository. Requires confirmation."""
    if not yes and not dry_run: # Check if confirmation was given, unless it's a dry run
        click.echo("Confirmation not received. Aborting.")
        return

    actual_token = token if token else get_github_token()
    if not actual_token:
        return

    gh_client = GitHubClient(actual_token, repo)
    click.echo(f"Fetching closed issues from '{repo}'...")
    
    closed_issues = gh_client.get_closed_issues_for_deletion()

    if not closed_issues:
        click.echo("No closed issues found to delete.")
        return

    click.echo(f"Found {len(closed_issues)} closed issues:")
    for issue in closed_issues:
        click.echo(f"  - #{issue['number']}: {issue['title']} (Node ID: {issue['id']})")

    if dry_run:
        click.echo("\n[dry-run] No issues were deleted.")
        return

    # Double-check confirmation, as click.confirmation_option might not be enough for such a destructive action
    # The `yes` parameter from `confirmation_option` already handles the initial prompt.
    # If we reach here and it's not a dry_run, 'yes' must have been true.
    # An additional, more specific prompt can be added if desired:
    # specific_confirmation = click.prompt(f"To confirm deletion of {len(closed_issues)} issues from '{repo}', please type the repository name ('{repo}')")
    # if specific_confirmation != repo:
    #     click.echo("Repository name not matched. Aborting deletion.")
    #     return
    
    click.echo("\nProceeding with deletion...")
    deleted_count = 0
    failed_count = 0
    for issue in closed_issues:
        click.echo(f"Deleting issue #{issue['number']}: {issue['title']}...")
        if gh_client.delete_issue_by_node_id(issue['id']):
            click.echo(f"  Successfully deleted #{issue['number']}.")
            deleted_count += 1
        else:
            click.echo(f"  Failed to delete #{issue['number']}.")
            failed_count += 1
    
    click.echo("\nDeletion process finished.")
    click.echo(f"Successfully deleted: {deleted_count} issues.")
    if failed_count > 0:
        click.echo(f"Failed to delete: {failed_count} issues. Check logs for errors.", err=True)


@cli.command(name='import-md')
@click.argument('repo_full_name', metavar='REPO')
@click.argument('markdown_file', type=click.Path(exists=True), metavar='MARKDOWN_FILE')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var if not provided)')
@click.option('--openai-key', envvar='OPENAI_API_KEY', help='OpenAI API key (reads from .env or OPENAI_API_KEY env var if not provided)')
@click.option('--dry-run', is_flag=True, help='List issues without creating them')
@click.option('--verbose', '-v', is_flag=True, help='Show progress logs')
@click.option('--heading-level', 'heading_level', type=int, default=1, show_default=True,
                   help='Markdown heading level to split issues (1 for "#", 2 for "##"). Passed as --heading to the underlying script.')
# Options from scripts/import_md.py that might be useful to expose: --model, --temperature, --max-tokens
# For now, keeping it simple and letting the script use its defaults or env vars for those.
def import_md_command(repo_full_name, markdown_file, token, openai_key, dry_run, verbose, heading_level):
    """Import issues from an unstructured markdown file, enriching via OpenAI LLM.
    
    This command calls the scripts/import_md.py script.
    """
    actual_token = token if token else os.getenv('GITHUB_TOKEN')
    if not actual_token:
        # get_github_token() prompts and might save, but scripts/import_md.py needs it directly.
        # For simplicity, we'll rely on it being set or provided.
        click.echo("Error: GitHub token required. Set GITHUB_TOKEN env var or use --token.", err=True)
        # Could call get_github_token() here if we want to prompt.
        # However, scripts/import_md.py also checks for GITHUB_TOKEN.
        return 1 # Indicate error

    actual_openai_key = openai_key if openai_key else os.getenv('OPENAI_API_KEY')
    if not actual_openai_key:
        click.echo("Error: OpenAI API key required. Set OPENAI_API_KEY env var or use --openai-key.", err=True)
        return 1 # Indicate error

    script_path = Path(__file__).parent / 'scripts' / 'import_md.py'
    if not script_path.exists():
        click.echo(f"Error: The script import_md.py was not found at {script_path}", err=True)
        return 1

    cmd = [sys.executable, str(script_path), repo_full_name, markdown_file]

    if dry_run:
        cmd.append('--dry-run')
    if verbose:
        cmd.append('--verbose')
    
    # Pass token and openai_key to the script if provided, otherwise script will use env vars
    if token: # Pass explicitly if given via CLI option to this command
        cmd.extend(['--token', actual_token])
    if openai_key: # Pass explicitly if given via CLI option to this command
        cmd.extend(['--openai-key', actual_openai_key])

    if heading_level is not None: # scripts/import_md.py has a default, so always pass.
        cmd.extend(['--heading', str(heading_level)])

    try:
        # It's important to set the working directory or ensure script paths if scripts/import_md.py
        # relies on relative paths for its own imports or resources, though it seems self-contained.
        # For now, assume scripts/import_md.py handles its own dependencies.
        # Pass GITHUB_TOKEN and OPENAI_API_KEY in environment for the subprocess,
        # ensuring the script can pick them up if not passed directly as args.
        env = os.environ.copy()
        env['GITHUB_TOKEN'] = actual_token
        env['OPENAI_API_KEY'] = actual_openai_key
        
        click.echo(f"Running import script: {script_path.name}")
        process = subprocess.run(cmd, check=False, env=env)
        return process.returncode
    except Exception as e:
        click.echo(f"Failed to execute {script_path.name}: {e}", err=True)
