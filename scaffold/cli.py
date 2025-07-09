import click
from . import __version__

import os
import sys
import subprocess
import logging
import shlex
from pathlib import Path
from dotenv import load_dotenv, set_key
from github import Github, GithubException

from .parser import parse_markdown
from .validator import validate_roadmap
from .github import GitHubClient
from .ai import enrich_issue_description
from datetime import date
import re
import random
import webbrowser
import time
import difflib
import openai
from collections import defaultdict

from rich.console import Console
from rich.table import Table


def run_repl(ctx):
    """Runs the interactive REPL shell."""
    click.secho("Entering interactive mode. Type 'exit' or 'quit' to leave.", fg='yellow')
    while True:
        try:
            command_line = input('gitscaffold> ')
            if command_line.lower() in ['exit', 'quit']:
                break
            
            # Use shlex to handle quoted arguments
            args = shlex.split(command_line)
            if not args:
                continue

            # Handle `help` command explicitly.
            if args[0] == 'help':
                if len(args) == 1:
                    # `help`
                    click.echo(ctx.get_help())
                elif args[1] in cli.commands:
                    # `help <command>`
                    cmd_obj = cli.commands[args[1]]
                    with cmd_obj.make_context(args[1], ['--help']) as sub_ctx:
                        click.echo(sub_ctx.get_help())
                else:
                    # `help <unknown-command>`
                    click.secho(f"Error: Unknown command '{args[1]}'", fg='red')
                continue

            cmd_name = args[0]
            if cmd_name not in cli.commands:
                click.secho(f"Error: Unknown command '{cmd_name}'", fg='red')
                continue

            cmd_obj = cli.commands[cmd_name]
            
            try:
                # `standalone_mode=False` prevents sys.exit on error.
                # This will also handle `--help` on subcommands by raising PrintHelpMessage.
                cmd_obj.main(args=args[1:], prog_name=cmd_name, standalone_mode=False)
            except click.exceptions.ClickException as e:
                e.show()
            except Exception as e:
                # Catch other exceptions to keep REPL alive
                click.secho(f"An unexpected error occurred: {e}", fg="red")
                logging.error(f"REPL error: {e}", exc_info=True)

        except (EOFError, KeyboardInterrupt):
            # Ctrl+D or Ctrl+C
            break
        except Exception as e:
            # Catch errors in the REPL loop itself
            click.secho(f"REPL error: {e}", fg='red')

    click.secho("Exiting interactive mode.", fg='yellow')


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="gitscaffold")
@click.option('--interactive', is_flag=True, help='Enter an interactive REPL to run multiple commands.')
@click.pass_context
def cli(ctx, interactive):
    """Scaffold – Convert roadmaps to GitHub issues."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    load_dotenv()  # Load .env file at the start of CLI execution
    logging.info("CLI execution started.")

    # If --interactive is passed, we want to enter the REPL.
    # We should not proceed to execute any subcommand that might have been passed.
    if interactive:
        run_repl(ctx)
        # Prevent further execution of a subcommand if one was passed, e.g., `gitscaffold --interactive init`
        ctx.exit()

    # If no subcommand is invoked and not in interactive mode, show help.
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


def get_github_token():
    """
    Retrieves the GitHub token from .env file or prompts the user if not found.
    Saves the token to .env if newly provided.
    Assumes load_dotenv() has already been called.
    """
    # load_dotenv() # Moved to cli()
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        logging.warning("GitHub PAT not found in environment or .env file.")
        click.echo("GitHub PAT not found in environment or .env file.")
        token = click.prompt('Please enter your GitHub Personal Access Token (PAT)', hide_input=True)
        # Ensure .env file exists for set_key
        env_path = Path('.env')
        env_path.touch(exist_ok=True)
        set_key(str(env_path), 'GITHUB_TOKEN', token)
        logging.info("GitHub PAT saved to .env file.")
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
        logging.error("OPENAI_API_KEY not found in environment or .env file.")
        click.echo(
            "Error: OPENAI_API_KEY not found. Please set it in your environment or .env file. "
            "Ensure the .env file is in the directory where you are running gitscaffold.",
            err=True
        )
        return None
    return api_key


def get_repo_from_git_config():
    """Retrieves the 'owner/repo' from the git config."""
    logging.info("Attempting to get repository from git config.")
    try:
        url = subprocess.check_output(
            ['git', 'config', '--get', 'remote.origin.url'],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        logging.info(f"Found git remote URL: {url}")

        # Handle SSH URLs: git@github.com:owner/repo.git
        ssh_match = re.search(r'github\.com:([^/]+/[^/]+?)(\.git)?$', url)
        if ssh_match:
            repo = ssh_match.group(1)
            logging.info(f"Parsed repository '{repo}' from SSH URL.")
            return repo

        # Handle HTTPS URLs: https://github.com/owner/repo.git
        https_match = re.search(r'github\.com/([^/]+/[^/]+?)(\.git)?$', url)
        if https_match:
            repo = https_match.group(1)
            logging.info(f"Parsed repository '{repo}' from HTTPS URL.")
            return repo

        logging.warning(f"Could not parse repository from git remote URL: {url}")
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.warning("Could not get repo from git config. Not a git repository or git is not installed.")
        return None


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
    logging.info(f"Populating repo '{gh_client.repo.full_name}' from roadmap '{roadmap_data.name}'. Dry run: {dry_run}")
    click.echo(f"Processing roadmap '{roadmap_data.name}' for repository '{gh_client.repo.full_name}'.")
    click.echo(f"Found {len(roadmap_data.milestones)} milestones and {len(roadmap_data.features)} features.")
    logging.info(f"Found {len(roadmap_data.milestones)} milestones and {len(roadmap_data.features)} features.")

    # Process milestones
    for m in roadmap_data.milestones:
        if dry_run:
            msg = f"Would create or fetch milestone: {m.name} (due: {m.due_date})"
            logging.info(f"[dry-run] {msg}")
            click.echo(f"[dry-run] {msg}")
        else:
            gh_client.create_milestone(name=m.name, due_on=m.due_date)
            click.echo(f"Milestone created or exists: {m.name}")

    # Process features and tasks
    for feat in roadmap_data.features:
        body = feat.description or ''
        if ai_enrich:
            if dry_run:
                msg = f"Would AI-enrich feature: {feat.title}"
                logging.info(f"[dry-run] {msg}")
                click.echo(f"[dry-run] {msg}")
            elif openai_api_key: # Only enrich if key is available
                logging.info(f"AI-enriching feature: {feat.title}...")
                click.echo(f"AI-enriching feature: {feat.title}...")
                body = enrich_issue_description(feat.title, body, openai_api_key, context_text)
        
        if dry_run:
            msg = f"Would create or fetch feature issue: {feat.title.strip()}"
            logging.info(f"[dry-run] {msg}")
            click.echo(f"[dry-run] {msg}")
            feat_issue_number = 'N/A (dry-run)'
            feat_issue_obj = None # In dry-run, we don't have a real issue object
        else:
            feat_issue = gh_client.create_issue(
                title=feat.title.strip(),
                body=body,
                assignees=feat.assignees,
                labels=feat.labels,
                milestone=feat.milestone
            )
            msg = f"Issue created or exists: #{feat_issue.number} {feat.title}"
            logging.info(msg)
            click.echo(msg)
            feat_issue_number = feat_issue.number
            feat_issue_obj = feat_issue

        for task in feat.tasks:
            t_body = task.description or ''
            if ai_enrich:
                if dry_run:
                    msg = f"Would AI-enrich sub-task: {task.title}"
                    logging.info(f"[dry-run] {msg}")
                    click.echo(f"[dry-run] {msg}")
                elif openai_api_key: # Only enrich if key is available
                    logging.info(f"AI-enriching sub-task: {task.title}...")
                    click.echo(f"AI-enriching sub-task: {task.title}...")
                    t_body = enrich_issue_description(task.title, t_body, openai_api_key, context_text)
            
            if dry_run:
                parent_info = f"(parent: #{feat_issue_number})"
                msg = f"Would create sub-task: {task.title.strip()} {parent_info}"
                logging.info(f"[dry-run] {msg}")
                click.echo(f"[dry-run] {msg}")
            else:
                content = t_body
                if feat_issue_obj: # Check if feat_issue_obj is not None
                    content = f"{t_body}\n\nParent issue: #{feat_issue_obj.number}".strip()
                gh_client.create_issue(
                    title=task.title.strip(),
                    body=content,
                    assignees=task.assignees,
                    labels=task.labels,
                    milestone=feat.milestone # Tasks usually inherit milestone from feature
                )
                msg = f"Sub-task created or exists: {task.title}"
                logging.info(msg)
                click.echo(msg)



@click.argument('roadmap_file', type=click.Path(exists=True), metavar='ROADMAP_FILE')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to git origin.')
@click.option('--dry-run', is_flag=True, help='Simulate the process without creating any issues on GitHub.')
@click.option('--ai-extract', is_flag=True, help='Use AI to parse issues from an unstructured Markdown file.')
@click.option('--ai-enrich', is_flag=True, help='Use AI to enrich issue descriptions with more details.')
def create(roadmap_file, token, repo, dry_run, ai_extract, ai_enrich):
    """Populate an EXISTING GitHub repository with issues from a roadmap file."""
    actual_token = token if token else get_github_token()
    if not actual_token:
        return
    # Determine repository: use --repo or infer from local git
    if not repo:
        repo = get_repo_from_git_config()
        if not repo:
            click.echo("Could not determine repository from git config. Please use --repo.", err=True)
            return
        click.echo(f"Using repository from git config: {repo}")

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


@click.argument('roadmap_file', type=click.Path(exists=True), metavar='ROADMAP_FILE')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--repo-name', help='Name for the new repository (defaults to roadmap name).')
@click.option('--org', help='GitHub organization to create the repository in (defaults to user).')
@click.option('--private', is_flag=True, help='Make the new repository private.')
@click.option('--dry-run', is_flag=True, help='Simulate the process without creating a repository or issues.')
@click.option('--ai-extract', is_flag=True, help='Use AI to parse issues from an unstructured Markdown file.')
@click.option('--ai-enrich', is_flag=True, help='Use AI to enrich issue descriptions with more details.')
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


@cli.command(name="sync", help=click.style('Sync roadmap with a GitHub repository', fg='cyan'))
@click.argument('roadmap_file', type=click.Path(exists=True), metavar='MARKDOWN_FILE')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to git origin.')
@click.option('--dry-run', is_flag=True, help='Simulate and show what would be created, without making changes.')
@click.option('--ai-enrich', is_flag=True, help='Use AI to enrich descriptions of new issues being created.')
def sync(roadmap_file, token, repo, dry_run, ai_enrich):
    """Sync a Markdown roadmap with a GitHub repository.

    If the repository is empty, it populates it with issues from the roadmap.
    If the repository has issues, it performs a diff between the roadmap and the issues.
    """
    click.echo("Starting 'sync' command...")
    actual_token = token if token else get_github_token()
    if not actual_token:
        click.echo("GitHub token is required to proceed. Exiting.", err=True)
        sys.exit(1)
    
    click.echo("Successfully obtained GitHub token.")
    if not repo:
        click.echo("No --repo provided, attempting to find repository from git config...")
        repo = get_repo_from_git_config()
        if not repo:
            click.echo("Could not determine repository from git config. Please use --repo. Exiting.", err=True)
            sys.exit(1)
        click.echo(f"Using repository from current git config: {repo}")
    else:
        click.echo(f"Using repository provided via --repo flag: {repo}")

    path = Path(roadmap_file)
    suffix = path.suffix.lower()
    if suffix not in ('.md', '.markdown'):
        click.echo("Error: `sync` only supports Markdown files (.md/.markdown).", err=True)
        sys.exit(1)

    openai_api_key_for_ai = None
    if ai_enrich:
        openai_api_key_for_ai = get_openai_api_key()
        if not openai_api_key_for_ai:
            return 1

    raw_roadmap_data = parse_markdown(roadmap_file)
    validated_roadmap = validate_roadmap(raw_roadmap_data)
    
    try:
        gh_client = GitHubClient(actual_token, repo)
        click.echo(f"Successfully connected to repository '{repo}'.")
    except GithubException as e:
        if e.status == 404:
            click.echo(f"Error: Repository '{repo}' not found. Please check the name and your permissions.", err=True)
        elif e.status == 401:
            click.echo("Error: GitHub token is invalid or has insufficient permissions.", err=True)
        else:
            click.echo(f"An unexpected GitHub error occurred: {e}", err=True)
        sys.exit(1)

    click.echo("Fetching existing issue titles...")
    existing_issue_titles = gh_client.get_all_issue_titles()

    if not existing_issue_titles:
        click.secho("Repository is empty. Populating with issues from roadmap.", fg="green")
        context_text = path.read_text(encoding='utf-8') if ai_enrich else ''
        _populate_repo_from_roadmap(
            gh_client=gh_client,
            roadmap_data=validated_roadmap,
            dry_run=dry_run,
            ai_enrich=ai_enrich,
            openai_api_key=openai_api_key_for_ai,
            context_text=context_text,
            roadmap_file_path=path
        )
    else:
        click.secho(f"Repository has {len(existing_issue_titles)} issues. Performing a diff against the roadmap.", fg="yellow")
        
        roadmap_titles = {feat.title for feat in validated_roadmap.features}
        for feat in validated_roadmap.features:
            for task in feat.tasks:
                roadmap_titles.add(task.title)

        missing = sorted(roadmap_titles - existing_issue_titles)
        extra = sorted(existing_issue_titles - roadmap_titles)

        if not missing and not extra:
            click.secho("\n✓ Roadmap and GitHub issues are in sync.", fg="green")
        else:
            if missing:
                click.secho("\nItems in local roadmap but not on GitHub (missing):", fg="yellow", bold=True)
                for title in missing:
                    click.secho(f"  - {title}", fg="yellow")
            
            if extra:
                click.secho("\nItems on GitHub but not in local roadmap (extra):", fg="cyan", bold=True)
                for title in extra:
                    click.secho(f"  - {title}", fg="cyan")

    click.echo("Sync command finished.")
    

@cli.command(name='diff', help=click.style('Diff local roadmap vs GitHub issues', fg='cyan'))
@click.argument('roadmap_file', type=click.Path(exists=True), metavar='MARKDOWN_FILE')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to git origin.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
def diff(roadmap_file, repo, token):
    """Compare a local Markdown roadmap file with GitHub issues and list differences."""
    click.secho("\n=== Diff Roadmap vs GitHub Issues ===", fg="bright_blue", bold=True)
    actual_token = token if token else get_github_token()
    if not actual_token:
        click.secho("Error: GitHub token is required to proceed.", fg="red", err=True)
        sys.exit(1)
    
    click.echo("Successfully obtained GitHub token.")

    if not repo:
        click.echo("No --repo provided, attempting to find repository from git config...")
        repo = get_repo_from_git_config()
        if not repo:
            click.echo("Could not determine repository from git config. Please use --repo. Exiting.", err=True)
            sys.exit(1)
        click.echo(f"Using repository from current git config: {repo}")
    else:
        click.echo(f"Using repository provided via --repo flag: {repo}")

    path = Path(roadmap_file)
    suffix = path.suffix.lower()
    if suffix not in ('.md', '.markdown'):
        raise click.UsageError('`diff` only supports Markdown files (.md, .markdown)')

    raw = parse_markdown(roadmap_file)
    validated = validate_roadmap(raw)
    
    roadmap_titles = {feat.title for feat in validated.features}
    for feat in validated.features:
        for task in feat.tasks:
            roadmap_titles.add(task.title)

    try:
        gh_client = GitHubClient(actual_token, repo)
        click.secho(f"Successfully connected to repository '{repo}'.", fg="green")
    except GithubException as e:
        if e.status == 404:
            click.echo(f"Error: Repository '{repo}' not found. Please check the name and your permissions.", err=True)
        elif e.status == 401:
            click.echo("Error: GitHub token is invalid or has insufficient permissions.", err=True)
        else:
            click.echo(f"An unexpected GitHub error occurred: {e}", err=True)
        sys.exit(1)

    click.secho(f"Fetching existing GitHub issue titles...", fg="cyan")
    gh_titles = gh_client.get_all_issue_titles()
    click.secho(f"Fetched {len(gh_titles)} issues; roadmap has {len(roadmap_titles)} items.", fg="magenta")
    
    missing = sorted(roadmap_titles - gh_titles)
    extra = sorted(gh_titles - roadmap_titles)
    
    if missing:
        click.secho("\nItems in local roadmap but not on GitHub (missing):", fg="yellow", bold=True)
        for title in missing:
            click.secho(f"  - {title}", fg="yellow")
    else:
        click.secho("\n✓ No missing issues on GitHub.", fg="green")

    if extra:
        click.secho("\nItems on GitHub but not in local roadmap (extra):", fg="cyan", bold=True)
        for title in extra:
            click.secho(f"  - {title}", fg="cyan")
    else:
        click.secho("✓ No extra issues on GitHub.", fg="green")


@cli.command(name="next", help=click.style('Show next action items', fg='cyan'))
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to the current git repo.')
@click.option('--token', help='GitHub API token (prompts if not set).')
def next_command(repo, token):
    """Shows open issues from the earliest active milestone."""
    actual_token = token if token else get_github_token()
    if not actual_token:
        click.echo("GitHub token is required.", err=True)
        sys.exit(1)

    if not repo:
        click.echo("No --repo provided, attempting to find repository from git config...")
        repo = get_repo_from_git_config()
        if not repo:
            click.echo("Could not determine repository from git config. Please use --repo. Exiting.", err=True)
            sys.exit(1)
        click.echo(f"Using repository from current git config: {repo}")
    else:
        click.echo(f"Using repository provided via --repo flag: {repo}")

    gh_client = GitHubClient(actual_token, repo)
    
    click.echo(f"Finding next action items in repository '{repo}'...")
    
    milestone, issues = gh_client.get_next_action_items()
    
    if not milestone:
        click.echo("No active milestones with open issues found.")
        return

    due_date_str = f"(due {milestone.due_on.strftime('%Y-%m-%d')})" if milestone.due_on else "(no due date)"
    click.secho(f"\nNext actions from milestone: '{milestone.title}' {due_date_str}", fg="green", bold=True)
    
    if not issues:
        # This case should be rare if get_next_action_items filters by m.open_issues > 0, but good to have
        click.echo("  No open issues found in this milestone.")
        return
        
    for issue in issues:
        assignee_str = ""
        if issue.assignees:
            assignees_str = ", ".join([f"@{a.login}" for a in issue.assignees])
            assignee_str = f" (assigned to {assignees_str})"
        click.echo(f"  - #{issue.number}: {issue.title}{assignee_str}")
        
    click.echo("\nCommand finished.")


@cli.command(name='delete-closed', help=click.style('Delete all closed issues', fg='cyan'))
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to git origin.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--dry-run', is_flag=True, help='List issues that would be deleted, without actually deleting them.')
@click.confirmation_option(prompt='Are you sure you want to permanently delete all closed issues? This is irreversible.')
def delete_closed_issues_command(repo, token, dry_run, yes): # 'yes' is injected by confirmation_option
    """Permanently delete all closed issues in a repository. Requires confirmation."""
    if not yes and not dry_run: # Check if confirmation was given, unless it's a dry run
        click.echo("Confirmation not received. Aborting.")
        return

    actual_token = token if token else get_github_token()
    if not actual_token:
        click.echo("GitHub token is required.", err=True)
        return 1
    # Determine repository: use --repo or infer from local git
    if not repo:
        repo = get_repo_from_git_config()
        if not repo:
            click.echo("Could not determine repository from git config. Please use --repo.", err=True)
            return
        click.echo(f"Using repository from git config: {repo}")

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


@cli.command(name='sanitize', help=click.style('Clean up issue titles', fg='cyan'))
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to the current git repo.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--dry-run', is_flag=True, help='List issues that would be changed, without actually changing them.')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation and immediately apply updates.')
def sanitize_command(repo, token, dry_run, yes):
    """Scan all issues and remove leading markdown characters like '#' from their titles."""
    click.echo("Starting 'sanitize' command...")
    actual_token = token if token else get_github_token()
    if not actual_token:
        click.echo("GitHub token is required to proceed. Exiting.")
        sys.exit(1)
    
    click.echo("Successfully obtained GitHub token.")

    if not repo:
        click.echo("No --repo provided, attempting to find repository from git config...")
        repo = get_repo_from_git_config()
        if not repo:
            click.echo("Could not determine repository from git config. Please use --repo. Exiting.")
            sys.exit(1)
        click.echo(f"Using repository from current git config: {repo}")
    else:
        click.echo(f"Using repository provided via --repo flag: {repo}")

    try:
        gh_client = GitHubClient(actual_token, repo)
        click.echo(f"Successfully connected to repository '{repo}'.")
    except GithubException as e:
        if e.status == 404:
            click.echo(f"Error: Repository '{repo}' not found. Please check the name and your permissions.")
        elif e.status == 401:
            click.echo("Error: GitHub token is invalid or has insufficient permissions.")
        else:
            click.echo(f"An unexpected GitHub error occurred: {e}")
        sys.exit(1)
    click.secho("Fetching all issues...", fg="cyan")
    # PaginatedList has no len(), so convert to list first
    all_issues = list(gh_client.get_all_issues())
    click.secho(f"Total issues fetched: {len(all_issues)}", fg="magenta")

    issues_to_update = []
    for issue in all_issues:
        original_title = issue.title
        cleaned_title = original_title.lstrip('# ').strip()
        if original_title != cleaned_title:
            issues_to_update.append((issue, cleaned_title))

    if not issues_to_update:
        click.secho("No issues with titles that need cleaning up.", fg="green", bold=True)
        return

    click.secho(f"Found {len(issues_to_update)} issues to clean up:", fg="yellow", bold=True)
    for issue, new_title in issues_to_update:
        click.secho(f"  - #{issue.number}: '{issue.title}' -> '{new_title}'", fg="white")
    
    if dry_run:
        click.secho("\n[dry-run] No issues were updated.", fg="blue")
        return

    click.secho("\nApplying cleanup updates...", fg="cyan")
    if not yes:
        prompt_text = click.style(f"Proceed with updating {len(issues_to_update)} issue titles in '{repo}'?", fg="yellow", bold=True)
        if not click.confirm(prompt_text):
            click.secho("Aborting.", fg="red")
            return

    updated_count = 0
    failed_count = 0
    for issue, new_title in issues_to_update:
        click.secho(f"Updating issue #{issue.number}...", fg="blue")
        try:
            issue.edit(title=new_title)
            click.secho(f"  Successfully updated issue #{issue.number}.", fg="green")
            updated_count += 1
        except GithubException as e:
            click.secho(f"  Failed to update issue #{issue.number}: {e}", fg="red", err=True)
            failed_count += 1
    
    click.secho("\nCleanup process finished.", fg="bright_green", bold=True)
    click.secho(f"Successfully updated: {updated_count} issues.", fg="bright_blue")
    if failed_count > 0:
        click.secho(f"Failed to update: {failed_count} issues", fg="red", err=True)


@cli.command(name='deduplicate', help=click.style('Close duplicate open issues', fg='cyan'))
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to the current git repo.')
@click.option('--token', help='GitHub API token (prompts if not set).')
@click.option('--dry-run', is_flag=True, help='List duplicate issues that would be closed, without actually closing them.')
def deduplicate_command(repo, token, dry_run):
    """Finds and closes duplicate open issues (based on title)."""
    click.secho("\n=== Deduplicate Issues ===", fg="bright_blue", bold=True)
    click.secho("Step 1: Authenticating...", fg="cyan")
    actual_token = token if token else get_github_token()
    if not actual_token:
        click.secho("Error: GitHub token is required to proceed.", fg="red", err=True)
        sys.exit(1)

    click.secho("Step 2: Resolving repository...", fg="cyan")
    if not repo:
        repo = get_repo_from_git_config()
        if not repo:
            click.secho("Error: Could not determine repository from git config. Please use --repo.", fg="red", err=True)
            sys.exit(1)
        click.secho(f"Using repository from git config: {repo}", fg="magenta")
    else:
        click.secho(f"Using repository flag: {repo}", fg="magenta")

    try:
        gh_client = GitHubClient(actual_token, repo)
        click.secho(f"Successfully connected to repository '{repo}'.", fg="green")
    except GithubException as e:
        if e.status == 404:
            click.echo(f"Error: Repository '{repo}' not found. Please check the name and your permissions.", err=True)
        elif e.status == 401:
            click.echo("Error: GitHub token is invalid or has insufficient permissions.", err=True)
        else:
            click.echo(f"An unexpected GitHub error occurred: {e}", err=True)
        sys.exit(1)

    click.secho("Step 3: Scanning for duplicates...", fg="cyan")
    duplicate_sets = gh_client.find_duplicate_issues()

    if not duplicate_sets:
        click.secho("No duplicate open issues found.", fg="green", bold=True)
        return

    issues_to_close = []
    click.secho(f"Found {len(duplicate_sets)} sets of duplicate issues:", fg="yellow", bold=True)
    for title, issues in duplicate_sets.items():
        original = issues['original']
        duplicates = issues['duplicates']
        click.secho(f"\n- Title: '{title}'", fg="white", bold=True)
        click.echo(f"  - Original: #{original.number} (created {original.created_at})")
        for dup in duplicates:
            click.echo(f"  - Duplicate to close: #{dup.number} (created {dup.created_at})")
            issues_to_close.append(dup)

    if dry_run:
        click.secho(f"\n[dry-run] Would close {len(issues_to_close)} issues. No changes were made.", fg="blue")
        return

    click.secho("Step 4: Executing closures...", fg="cyan")
    prompt_msg = f"Proceed with closing {len(issues_to_close)} duplicate issues?"
    if not click.confirm(prompt_msg, default=False):
        click.secho("Aborting.", fg="red")
        return

    closed_count = 0
    failed_count = 0
    for issue in issues_to_close:
        click.secho(f"Closing issue #{issue.number}...", fg="yellow")
        try:
            issue.edit(state='closed')
            click.secho(f"  Successfully closed issue #{issue.number}.", fg="green")
            closed_count += 1
        except GithubException as e:
            click.secho(f"  Failed to close issue #{issue.number}: {e}", fg="red", err=True)
            failed_count += 1
    
    click.secho("\nDeduplication finished.", fg="bright_green", bold=True)
    click.secho(f"Successfully closed: {closed_count} issues.", fg="green")
    if failed_count > 0:
        click.secho(f"Failed to close: {failed_count} issues.", fg="red", err=True)


@click.argument('repo_full_name', metavar='REPO')
@click.argument('markdown_file', type=click.Path(exists=True), metavar='MARKDOWN_FILE')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--openai-key', envvar='OPENAI_API_KEY', help='OpenAI API key (reads from .env or OPENAI_API_KEY env var).')
@click.option('--dry-run', is_flag=True, help='Simulate and print issues without creating them on GitHub.')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose logging to see script progress.')
@click.option('--heading-level', 'heading_level', type=int, default=1, show_default=True,
                   help='Markdown heading level to split issues by (e.g., 1 for #, 2 for ##).')
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

    # Go up one level from scaffold/ to find the sibling scripts/ directory
    script_path = Path(__file__).parent.parent / 'scripts' / 'import_md.py'
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
    

@cli.command(name='start-demo', help=click.style('Run the Streamlit demo', fg='cyan'))
def start_demo():
    """Starts the Streamlit demo app if it exists."""
    demo_app_path = Path('demo/app.py')
    if not demo_app_path.exists():
        click.secho(f"Demo application not found at '{demo_app_path}'.", fg='red', err=True)
        click.echo("You can create a new project with a demo using `gitscaffold setup-repository` or `gitscaffold setup-template`.")
        sys.exit(1)

    cmd = [sys.executable, "-m", "streamlit", "run", str(demo_app_path)]
    click.secho(f"Starting Streamlit demo: {' '.join(cmd)}", fg='green')
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        click.secho("Error: `streamlit` command not found.", fg='red', err=True)
        click.echo("Please install it with: pip install streamlit")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        click.secho(f"Demo server failed to start or exited with an error: {e}", fg='red', err=True)
        sys.exit(1)


@cli.command(name='start-api', help=click.style('Run the FastAPI server', fg='cyan'))
def start_api():
    """Starts the FastAPI application using Uvicorn."""
    # Based on the template, the api app is at src/api/app.py
    api_app_path = Path('src/api/app.py')
    if not api_app_path.exists():
        click.secho(f"API application not found at '{api_app_path}'.", fg='red', err=True)
        click.echo("You can create a new project with an API using `gitscaffold setup-repository` or `gitscaffold setup-template`.")
        sys.exit(1)
        
    # The import string for uvicorn is based on file path relative to project root
    # src/api/app.py with variable `app` becomes `src.api.app:app`
    app_import_string = "src.api.app:app"

    cmd = [sys.executable, "-m", "uvicorn", app_import_string, "--reload"]
    click.secho(f"Starting FastAPI server with Uvicorn: {' '.join(cmd)}", fg='green')
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError:
        click.secho("Error: `uvicorn` command not found.", fg='red', err=True)
        click.echo("Please install it with: pip install uvicorn[standard]")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        click.secho(f"API server failed to start or exited with an error: {e}", fg='red', err=True)
        sys.exit(1)
