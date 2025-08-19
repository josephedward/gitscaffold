import click
from . import __version__

import os
import sys
import subprocess
import logging
import shlex
import shutil
from pathlib import Path
try:
    from dotenv import load_dotenv, set_key, unset_key
except ImportError:
    def load_dotenv(*args, **kwargs):
        # python-dotenv not installed; skipping .env loading
        return False
    def set_key(path, key, value):
        # Cannot write to .env without python-dotenv
        import click
        raise click.ClickException(
            "python-dotenv is required to save tokens to .env files. "
            "Install it or set tokens via environment variables."
        )
    def unset_key(path, key):
        # Cannot remove keys without python-dotenv
        import click
        raise click.ClickException(
            "python-dotenv is required to remove tokens from .env files. "
            "Install it or set tokens via environment variables."
        )
try:
    from github import Github, GithubException
except ImportError:
    # Define a dummy exception class if PyGithub is not installed.
    # This allows the CLI to load and show help text without the library.
    class GithubException(Exception):
        pass

from .parser import parse_markdown, parse_roadmap, write_roadmap
from .validator import validate_roadmap, Feature, Task
from .github import GitHubClient
from .vibe_kanban import VibeKanbanClient
from .ai import enrich_issue_description, extract_issues_from_markdown
from datetime import date
import re
import random
import webbrowser
import time
import difflib
from openai import OpenAI, OpenAIError
from collections import defaultdict
import csv

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
    """Scaffold – Convert roadmaps to GitHub issues (AI-first extraction for Markdown by default; disable with --no-ai)."""
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # Load env files. Precedence is: shell env -> local .env -> global config.
    load_dotenv()  # Load local .env file first.
    global_config_path = get_global_config_path()
    if global_config_path.exists():
        # Load global config, which will not override vars from shell or local .env
        load_dotenv(dotenv_path=global_config_path)
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


@cli.group(name='config', help='Manage global configuration and secrets.')
def config():
    """Manages global configuration stored in a file like ~/.gitscaffold/config."""
    pass

@config.command('set', help='Set a configuration key-value pair.')
@click.argument('key')
@click.argument('value')
def config_set(key, value):
    """Sets a key-value pair in the global config file."""
    set_global_config_key(key.upper(), value)
    config_path = get_global_config_path()
    click.secho(f"Set {key.upper()} in {config_path}", fg="green")

@config.command('get', help='Get a configuration value.')
@click.argument('key')
def config_get(key):
    """Gets a value from the global config file."""
    config_path = get_global_config_path()
    try:
        from dotenv import dotenv_values
    except ImportError:
        click.secho("python-dotenv is required to read config files.", fg="red", err=True)
        sys.exit(1)
        
    if not config_path.exists():
        click.secho(f"Config file not found: {config_path}", fg="yellow")
        sys.exit(1)

    values = dotenv_values(config_path)
    value = values.get(key.upper())
    if value is not None:
        click.echo(value)
    else:
        click.secho(f"Key '{key.upper()}' not found in {config_path}", fg="yellow")
        sys.exit(1)

@config.command('list', help='List all global configuration key-value pairs.')
def config_list():
    """Lists all key-value pairs from the global config file."""
    config_path = get_global_config_path()
    if not config_path.exists():
        click.secho(f"Config file not found: {config_path}", fg="yellow")
        return

    try:
        from dotenv import dotenv_values
    except ImportError:
        click.secho("python-dotenv is required to read config files.", fg="red", err=True)
        sys.exit(1)

    values = dotenv_values(config_path)
    if not values:
        click.echo("Config file is empty.")
        return
    
    table = Table(title=f"Global Configuration ({config_path})")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="magenta")
    for key, value in values.items():
        table.add_row(key, value)
    
    console = Console()
    console.print(table)

@config.command('path', help='Show path to the global config file.')
def config_path_command():
    """Shows the path to the global config file."""
    click.echo(get_global_config_path())
@config.command('remove', help='Remove a configuration key.')
@click.argument('key')
def config_remove(key):
    """Removes a key-value pair from the global config file."""
    config_path = get_global_config_path()
    try:
        removed, _ = unset_key(str(config_path), key.upper())
        if removed:
            click.secho(f"Removed {key.upper()} from {config_path}", fg="green")
        else:
            click.secho(f"Key '{key.upper()}' not found in {config_path}", fg="yellow")
    except click.ClickException:
        raise
    except Exception as e:
        click.secho(f"Error removing key '{key.upper()}': {e}", fg="red", err=True)


def prompt_for_github_token():
    """
    Prompts the user for a GitHub token.

    The token is not saved and is only used for the current session.
    """
    token = click.prompt('Please enter your GitHub Personal Access Token (PAT)', hide_input=True)
    # For immediate use, ensure os.environ is updated for this session:
    os.environ['GITHUB_TOKEN'] = token
    return token


def get_github_token():
    """
    Retrieves the GitHub token from environment or config files, or prompts the user if not found.
    Saves the token to the global config file if newly provided.
    Assumes load_dotenv() has already been called.
    """
    # load_dotenv() # Moved to cli()
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        logging.warning("GitHub PAT not found in environment or config files.")
        token = click.prompt('Please enter your GitHub Personal Access Token (PAT)', hide_input=True)
        # Save to global config file with secure permissions
        set_global_config_key('GITHUB_TOKEN', token)
        logging.info("GitHub PAT saved to global config file.")
        click.secho("GitHub PAT saved to global config file.", fg="green")
        # It's often better to ask the user to re-run so all parts of the app pick up the new env var.
        # Or, for immediate use, ensure os.environ is updated:
        os.environ['GITHUB_TOKEN'] = token
    return token


def get_openai_api_key():
    """
    Retrieves the OpenAI API key from environment or config files.
    Assumes load_dotenv() has already been called.
    """
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logging.warning("OPENAI_API_KEY not found in environment or config files.")
        api_key = click.prompt('Please enter your OpenAI API key', hide_input=True)
        set_global_config_key('OPENAI_API_KEY', api_key)
        logging.info("OpenAI API key saved to global config file.")
        click.secho("OpenAI API key saved to global config file.", fg="green")
        os.environ['OPENAI_API_KEY'] = api_key
    return api_key
  
def prompt_for_openai_key():
    """
    Prompt for an OpenAI API key, save it to the global config and environment, and return it.
    """
    key = click.prompt('Please enter your OpenAI API key', hide_input=True)
    set_global_config_key('OPENAI_API_KEY', key)
    click.secho("OpenAI API key saved to global config file.", fg="green")
    os.environ['OPENAI_API_KEY'] = key
    return key

def get_gemini_api_key():
    """
    Retrieves the Google Gemini API key from environment or config files.
    Assumes load_dotenv() has already been called.
    """
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logging.warning("GEMINI_API_KEY not found in environment or config files.")
        api_key = click.prompt('Please enter your Google Gemini API key', hide_input=True)
        set_global_config_key('GEMINI_API_KEY', api_key)
        logging.info("Google Gemini API key saved to global config file.")
        click.secho("Google Gemini API key saved to global config file.", fg="green")
        os.environ['GEMINI_API_KEY'] = api_key
    return api_key

def prompt_for_gemini_key():
    """
    Prompt for a Google Gemini API key, save it to the global config and environment, and return it.
    """
    key = click.prompt('Please enter your Google Gemini API key', hide_input=True)
    set_global_config_key('GEMINI_API_KEY', key)
    click.secho("Google Gemini API key saved to global config file.", fg="green")
    os.environ['GEMINI_API_KEY'] = key
    return key


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
        https_match = re.search(r'(?:www\.)?github\.com/([^/]+/[^/]+?)(\.git)?$', url)
        if https_match:
            repo = https_match.group(1)
            logging.info(f"Parsed repository '{repo}' from HTTPS URL.")
            return repo

        logging.warning(f"Could not parse repository from git remote URL: {url}")
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.warning("Could not get repo from git config. Not a git repository or git is not installed.")
        return None


def get_global_config_path():
    """Returns the path to the global config file, creating parent dir if needed."""
    config_dir = Path.home() / '.gitscaffold'
    # Create with secure permissions (user access only)
    config_dir.mkdir(mode=0o700, exist_ok=True)
    return config_dir / 'config'


def set_global_config_key(key: str, value: str):
    """Sets a key-value pair in the global config file with secure permissions."""
    config_path = get_global_config_path()
    # Use python-dotenv to write or update the key
    set_key(str(config_path), key, value)
    # Normalize quoting: convert single quotes to double quotes for consistency
    try:
        text = config_path.read_text(encoding='utf-8')
        # Replace lines like KEY='value' with KEY="value"
        old = f"{key}='{value}'"
        new = f'{key}="{value}"'
        if old in text:
            text = text.replace(old, new)
            config_path.write_text(text, encoding='utf-8')
    except Exception:
        # If normalization fails, ignore and leave as-is
        pass
    # Ensure config file has secure permissions (owner read/write only).
    # This is not applicable/standard on Windows.
    if os.name != 'nt':
        os.chmod(config_path, 0o600)


def _sanitize_repo_string(repo_string: str) -> str:
    """Extracts 'owner/repo' from a potential GitHub URL."""
    if not repo_string:
        return None
    
    repo_string = repo_string.strip()

    # Simple case: it's already owner/repo
    if re.fullmatch(r'[^/\s]+/[^/\s]+', repo_string):
        return repo_string
        
    # Try to extract from URL-like strings
    match = re.search(r'(?:www\.)?github\.com[/:]([^/]+\/[^/]+)', repo_string)
    if match:
        repo = match.group(1)
        if repo.endswith('.git'):
            return repo[:-4]
        return repo
        
    # Fallback for other cases, return as is.
    return repo_string


def _populate_repo_from_roadmap(
    gh_client: GitHubClient,
    roadmap_data,
    dry_run: bool,
    ai_enrich: bool,
    ai_provider: str,
    ai_api_key: str,
    context_text: str,
    roadmap_file_path: Path # For context if needed, though context_text is passed
):
    """Helper function to populate a repository with milestones and issues from roadmap data."""
    logging.info(f"Populating repo '{gh_client.repo.full_name}' from roadmap '{roadmap_data.name}'. Dry run: {dry_run}")
    click.secho(f"Processing roadmap '{roadmap_data.name}' for repository '{gh_client.repo.full_name}'.", fg="white")
    click.secho(f"Found {len(roadmap_data.milestones)} milestones and {len(roadmap_data.features)} features.", fg="magenta")
    logging.info(f"Found {len(roadmap_data.milestones)} milestones and {len(roadmap_data.features)} features.")

    # Process milestones
    for m in roadmap_data.milestones:
        if dry_run:
            click.secho(f"[dry-run] Milestone '{m.name}' not found. Would create", fg="blue")
        else:
            click.secho(f"Milestone '{m.name}' not found. Creating...", fg="yellow")
            gh_client.create_milestone(name=m.name, due_on=m.due_date)
            click.secho(f"Milestone created: {m.name}", fg="green")

    # Process features and tasks
    for feat in roadmap_data.features:
        body = feat.description or ''
        if ai_enrich:
            if dry_run:
                msg = f"Would AI-enrich feature: {feat.title}"
                logging.info(f"[dry-run] {msg}")
                click.secho(f"[dry-run] {msg}", fg="blue")
            elif ai_api_key: # Only enrich if key is available
                logging.info(f"AI-enriching feature: {feat.title}...")
                click.secho(f"AI-enriching feature: {feat.title}...", fg="cyan")
                body = enrich_issue_description(feat.title, body, ai_provider, ai_api_key, context_text)
        
        if dry_run:
            click.secho(f"[dry-run] Feature '{feat.title.strip()}' not found. Would prompt to create.", fg="blue")
            feat_issue_number = 'N/A (dry-run)'
            feat_issue_obj = None
        else:
            click.secho(f"Creating feature issue: {feat.title.strip()}", fg="yellow")
            feat_issue = gh_client.create_issue(
                title=feat.title.strip(),
                body=body,
                assignees=feat.assignees,
                labels=feat.labels,
                milestone=feat.milestone
            )
            click.secho(f"Feature issue created: #{feat_issue.number} {feat.title.strip()}", fg="green")
            feat_issue_number = feat_issue.number
            feat_issue_obj = feat_issue

        for task in feat.tasks:
            t_body = task.description or ''
            if ai_enrich:
                if dry_run:
                    msg = f"Would AI-enrich sub-task: {task.title}"
                    logging.info(f"[dry-run] {msg}")
                    click.secho(f"[dry-run] {msg}", fg="blue")
                elif ai_api_key: # Only enrich if key is available
                    logging.info(f"AI-enriching sub-task: {task.title}...")
                    click.secho(f"AI-enriching sub-task: {task.title}...", fg="cyan")
                    t_body = enrich_issue_description(task.title, t_body, ai_provider, ai_api_key, context_text)
            
            if dry_run:
                click.secho(
                    f"[dry-run] Task '{task.title.strip()}' (for feature '{feat.title.strip()}') not found. Would prompt to create.",
                    fg="blue"
                )
            else:
                click.secho(f"Creating task issue: {task.title.strip()}", fg="yellow")
                content = t_body
                if feat_issue_obj:
                    content = f"{t_body}\n\nParent issue: #{feat_issue_obj.number}".strip()
                task_issue = gh_client.create_issue(
                    title=task.title.strip(),
                    body=content,
                    assignees=task.assignees,
                    labels=task.labels,
                    milestone=feat.milestone
                )
                click.secho(f"Task issue created: #{task_issue.number} {task.title.strip()}", fg="green")


ROADMAP_TEMPLATE = """\
# My Project Roadmap

A brief description of your project.

## Milestones

| Milestone     | Due Date   |
|---------------|------------|
| v0.1 Planning | 2025-01-01 |
| v0.2 MVP      | 2025-02-01 |

## Features

### Core Feature
- **Description:** Implement the main functionality of the application.
- **Milestone:** v0.2 MVP
- **Labels:** core, feature

**Tasks:**
- Design the application architecture
- Implement the core feature
"""


@cli.command(name="setup", help='Initialize a new project with default files')
def setup():
    """Creates a sample ROADMAP.md and a .env file to get started."""
    click.secho("Setting up new project...", fg="cyan", bold=True)

    # Create ROADMAP.md
    roadmap_path = Path('ROADMAP.md')
    if not roadmap_path.exists():
        roadmap_path.write_text(ROADMAP_TEMPLATE)
        click.secho(f"✓ Created sample '{roadmap_path}'", fg="green")
    else:
        click.secho(f"✓ '{roadmap_path}' already exists, skipping.", fg="yellow")

    # Create or update .env file
    env_path = Path('.env')
    if not env_path.exists():
        env_path.write_text("GITHUB_TOKEN=\nOPENAI_API_KEY=\n")
        click.secho("✓ Created '.env' file for your secrets.", fg="green")
        click.secho("  -> Please add your GITHUB_TOKEN and OPENAI_API_KEY to this file.", fg="white")
    else:
        click.secho("✓ '.env' file already exists.", fg="yellow")
        content = env_path.read_text()
        made_changes = False
        if 'GITHUB_TOKEN' not in content:
            with env_path.open('a') as f:
                f.write("\nGITHUB_TOKEN=")
            made_changes = True
            click.secho("  -> Added GITHUB_TOKEN to '.env'. Please fill it in.", fg="white")

        if 'OPENAI_API_KEY' not in content:
            with env_path.open('a') as f:
                f.write("\nOPENAI_API_KEY=")
            made_changes = True
            click.secho("  -> Added OPENAI_API_KEY to '.env'. Please fill it in.", fg="white")

        if not made_changes:
            click.secho("  -> Secrets seem to be configured. No changes made.", fg="green")

    click.secho("\nSetup complete! You can now run `git-scaffold sync ROADMAP.md` or `python3 -m scaffold.cli sync ROADMAP.md`", fg="bright_green", bold=True)


@cli.command(name="sync", help='Sync a local roadmap with a GitHub repository (AI-first extraction for unstructured Markdown; disable with --no-ai; requires an AI API key)')
@click.argument('roadmap_file', type=click.Path(), metavar='ROADMAP_FILE')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to git origin.')
@click.option('--dry-run', is_flag=True, help='Simulate and show what would be created, without making changes.')
@click.option('--ai', 'force_ai', is_flag=True, help='Force AI extraction for unstructured Markdown without prompt (requires an AI API key).')
@click.option('--no-ai', 'no_ai', is_flag=True, help='Disable default AI fallback for unstructured Markdown.')
@click.option('--ai-enrich', is_flag=True, help='Use AI to enrich descriptions of new issues (requires an AI API key).')
@click.option('--ai-provider', type=click.Choice(['openai', 'gemini']), default='openai', show_default=True, help='AI provider to use for extraction and enrichment.')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation and apply changes when populating an empty repo.')
@click.option('--update-local', is_flag=True, help='Update the local roadmap file with issues from GitHub.')
def sync(roadmap_file, token, repo, dry_run, force_ai, no_ai, ai_enrich, ai_provider, yes, update_local):
    """Sync a Markdown roadmap with a GitHub repository.

    If the repository is empty, it populates it with issues from the roadmap.
    if the repository has issues, it performs a diff between the roadmap and the issues.
    """
    if not Path(roadmap_file).exists():
        click.secho(f"Error: Roadmap file not found at '{roadmap_file}'", fg="red", err=True)
        # A little helpful message if they use the old path
        if roadmap_file == 'docs/roadmap.md' and Path('ROADMAP.md').exists():
            click.secho("Hint: Did you mean to use 'ROADMAP.md'?", fg="yellow")
        sys.exit(1)

    click.secho("Starting 'sync' command...", fg='cyan', bold=True)
    actual_token = token or get_github_token()
    if not actual_token:
        click.secho("GitHub token is required to proceed. Exiting.", fg="red", err=True)
        sys.exit(1)
    
    click.secho("Successfully obtained GitHub token.", fg='green')
    if not repo:
        click.secho("No --repo provided, attempting to find repository from git config...", fg='yellow')
        repo = get_repo_from_git_config()
        if not repo:
            click.secho("Could not determine repository from git config. Please use --repo. Exiting.", fg="red", err=True)
            sys.exit(1)
        click.secho(f"Using repository from current git config: {repo}", fg='magenta')
    else:
        click.secho(f"Using repository provided via --repo flag: {repo}", fg='magenta')

    repo = _sanitize_repo_string(repo)
    path = Path(roadmap_file)
    use_ai = force_ai

    # AI-first extraction fallback for unstructured Markdown
    if not use_ai and not no_ai and path.suffix.lower() in ['.md', '.mdx', '.markdown']:
        try:
            pre_raw = parse_roadmap(roadmap_file)
            pre_validated = validate_roadmap(pre_raw)
            if not pre_validated.features and not pre_validated.milestones:
                click.secho("Warning: Roadmap appears to be empty or unstructured.", fg="yellow")
                if click.confirm("Use AI to extract issues instead?", default=True):
                    use_ai = True
        except Exception:
            click.secho(f"Warning: Could not parse '{roadmap_file}' as a structured roadmap.", fg="yellow")
            if click.confirm("Use AI to extract issues instead?", default=True):
                use_ai = True
    
    ai_api_key = None
    if use_ai:
        if ai_provider == 'openai':
            ai_api_key = get_openai_api_key()
        elif ai_provider == 'gemini':
            ai_api_key = get_gemini_api_key()
        
        if not ai_api_key:
            sys.exit(1)
        click.secho(f"Using {ai_provider.capitalize()} to extract issues from unstructured roadmap...", fg="cyan")
        # Attempt extraction, retry once if API key invalid
        attempts = 0
        while True:
            try:
                issues = extract_issues_from_markdown(md_file=roadmap_file, provider=ai_provider, api_key=ai_api_key)
                break
            except Exception as e:
                err_msg = str(e)
                if attempts == 0 and ("invalid_api_key" in err_msg or "401" in err_msg or "API key is invalid" in err_msg):
                    click.secho(f"{ai_provider.capitalize()} API key appears invalid. Please enter a valid key.", fg="yellow")
                    if ai_provider == 'openai':
                        ai_api_key = prompt_for_openai_key()
                    else: # gemini
                        ai_api_key = prompt_for_gemini_key()
                    attempts += 1
                    continue
                click.secho(f"Error during AI extraction: {e}", fg="red", err=True)
                sys.exit(1)
        # Convert extracted issues into a single AI-extracted feature with tasks
        tasks = [Task(title=issue['title'], description=issue.get('description', '')) for issue in issues]
        feature = Feature(title=f"AI-Extracted Issues from {path.name}", tasks=tasks)
        raw_roadmap_data = {
            "name": f"Roadmap from {path.name}",
            "features": [feature.model_dump(exclude_none=True)]
        }
    else:
        try:
            raw_roadmap_data = parse_roadmap(roadmap_file)
        except Exception as e:
            click.secho(f"Error: Failed to parse roadmap file '{roadmap_file}': {e}", fg="red", err=True)
            sys.exit(1)

    validated_roadmap = validate_roadmap(raw_roadmap_data)

    # Attempt to connect to GitHub repo, with fallback to detect or prompt for repo if invalid
    attempts = 0
    while True:
        try:
            gh_client = GitHubClient(actual_token, repo)
            click.secho(f"Successfully connected to repository '{repo}'.", fg="green")
            break
        except GithubException as e:
            if e.status == 404:
                click.secho(f"Error: Repository '{repo}' not found. Please check the name and your permissions.", fg="red", err=True)
            elif e.status == 401:
                click.secho("Error: GitHub token is invalid or has insufficient permissions.", fg="red", err=True)
            else:
                click.secho(f"An unexpected GitHub error occurred: {e}", fg="red", err=True)
            if attempts == 0:
                # Try deriving from git config
                if click.confirm("Would you like to detect the repository from your local Git config?", default=True):
                    derived = get_repo_from_git_config()
                    if derived:
                        repo = derived
                        click.secho(f"Using repository from git config: {repo}", fg="magenta")
                        attempts += 1
                        continue
                    else:
                        click.secho("Could not detect repository from git config.", fg="yellow")
                # Prompt manual entry
                repo = click.prompt("Please enter your GitHub repository (owner/repo)")
                attempts += 1
                continue
            sys.exit(1)

    if update_local:
        click.secho("Updating local roadmap from GitHub...", fg="cyan")
        all_gh_issues = list(gh_client.get_all_issues())
        gh_issue_titles = {issue.title for issue in all_gh_issues}

        roadmap_titles = {f.title for f in validated_roadmap.features}
        for f in validated_roadmap.features:
            roadmap_titles.update({t.title for t in f.tasks})

        extra_titles = gh_issue_titles - roadmap_titles

        if not extra_titles:
            click.secho("Local roadmap is already up-to-date with GitHub.", fg="green")
            return

        click.secho(f"Found {len(extra_titles)} issues on GitHub to add to local roadmap:", fg="yellow")
        for issue in all_gh_issues:
            if issue.title in extra_titles:
                parent_issue_match = re.search(r'Parent issue: #(\d+)', issue.body or '')
                labels = [label.name for label in issue.labels]
                assignees = [assignee.login for assignee in issue.assignees]
                milestone = issue.milestone.title if issue.milestone else None

                if parent_issue_match:
                    parent_issue_num = int(parent_issue_match.group(1))
                    parent_feature = None
                    try:
                        parent_issue = gh_client.repo.get_issue(parent_issue_num)
                        parent_title = parent_issue.title.strip()
                        parent_feature = next((f for f in validated_roadmap.features if f.title == parent_title), None)
                    except GithubException:
                        click.secho(f"    (Warning: Parent issue #{parent_issue_num} not found on GitHub)", fg="magenta")

                    if parent_feature:
                        click.secho(f"  + Adding task '{issue.title}' to feature '{parent_feature.title}'", fg="green")
                        parent_feature.tasks.append(Task(title=issue.title, description=issue.body, labels=labels, assignees=assignees))
                    else:
                        click.secho(f"  + Adding task '{issue.title}' as a new feature (parent not in roadmap)", fg="yellow")
                        validated_roadmap.features.append(Feature(title=issue.title, description=issue.body, labels=labels, assignees=assignees, milestone=milestone))
                else:
                    click.secho(f"  + Adding feature '{issue.title}'", fg="green")
                    validated_roadmap.features.append(Feature(title=issue.title, description=issue.body, labels=labels, assignees=assignees, milestone=milestone))

        # Mark completed tasks in the local roadmap for closed GitHub issues
        closed_titles = {issue.title for issue in all_gh_issues if getattr(issue, 'state', None) == 'closed'}
        for feat in validated_roadmap.features:
            for task in feat.tasks:
                if task.title in closed_titles:
                    setattr(task, 'completed', True)
        
        if not dry_run:
            prompt_msg = f"Update '{roadmap_file}' with {len(extra_titles)} new items from GitHub?"
            if not yes and not click.confirm(prompt_msg, default=True):
                click.secho("Aborting update.", fg="red")
                return

            try:
                write_roadmap(roadmap_file, validated_roadmap)
                click.secho(f"Successfully updated '{roadmap_file}'.", fg="green")
            except Exception as e:
                click.secho(f"Error writing to roadmap file: {e}", fg="red", err=True)
                sys.exit(1)
        else:
            click.secho(f"[dry-run] Would have updated '{roadmap_file}' with {len(extra_titles)} new items.", fg="blue")
        return

    click.secho("Fetching existing issue titles...", fg='cyan')
    existing_issue_titles = gh_client.get_all_issue_titles()

    if not existing_issue_titles:
        click.secho("Repository is empty. Populating with issues from roadmap.", fg="green")
        
        context_text = path.read_text(encoding='utf-8') if use_ai else ''
        
        # Display what will be done. This is effectively a dry run preview.
        _populate_repo_from_roadmap(
            gh_client=gh_client,
            roadmap_data=validated_roadmap,
            dry_run=True,
            ai_enrich=use_ai,
            ai_provider=ai_provider,
            ai_api_key=ai_api_key,
            context_text=context_text,
            roadmap_file_path=path
        )
        
        if dry_run:
            # If this was a real dry run, we are done.
            click.secho("\n[dry-run] No changes were made.", fg="blue")
            return

        if not yes:
            prompt = click.style(
                f"\nProceed with populating '{repo}' with issues from '{roadmap_file}'?", fg="yellow", bold=True
            )
            if not click.confirm(prompt, default=True):
                click.secho("Aborting.", fg="red")
                return
        
        click.secho("\nApplying changes...", fg="cyan")
        _populate_repo_from_roadmap(
            gh_client=gh_client,
            roadmap_data=validated_roadmap,
            dry_run=False,
            ai_enrich=use_ai,
            ai_provider=ai_provider,
            ai_api_key=ai_api_key,
            context_text=context_text,
            roadmap_file_path=path
        )
    else:
        click.secho(f"Repository has {len(existing_issue_titles)} issues. Comparing with roadmap to find missing items...", fg="yellow")

        # 1. Collect what needs to be created and report on existing items
        milestones_to_create = []
        for m in validated_roadmap.milestones:
            if gh_client._find_milestone(m.name):
                click.secho(f"Milestone '{m.name}' already exists.", fg="green")
            else:
                milestones_to_create.append(m)

        features_to_create = []
        tasks_to_create = defaultdict(list)
        for feat in validated_roadmap.features:
            if feat.title in existing_issue_titles:
                click.secho(f"Feature '{feat.title}' already exists in GitHub issues. Checking its tasks...", fg="green")
            else:
                features_to_create.append(feat)

            for task in feat.tasks:
                if task.title in existing_issue_titles:
                    click.secho(f"Task '{task.title}' (for feature '{feat.title}') already exists in GitHub issues.", fg="green")
                else:
                    tasks_to_create[feat.title].append(task)
        
        total_tasks = sum(len(ts) for ts in tasks_to_create.values())
        total_new_items = len(milestones_to_create) + len(features_to_create) + total_tasks

        if total_new_items == 0:
            click.secho("No new items to create. Repository is up-to-date with the roadmap.", fg="green", bold=True)
            return

        # 2. Display summary of what will be created
        click.secho(f"\nFound {total_new_items} new items to create:", fg="yellow", bold=True)
        if milestones_to_create:
            click.secho("\nMilestones to be created:", fg="cyan")
            for m in milestones_to_create:
                click.secho(f"  - {m.name}", fg="magenta")

        if features_to_create:
            click.secho("\nFeatures to be created:", fg="cyan")
            for f in features_to_create:
                click.secho(f"  - {f.title}", fg="magenta")

        if tasks_to_create:
            click.secho("\nTasks to be created:", fg="cyan")
            new_feature_titles = {f.title for f in features_to_create}
            for feat_title, tasks in tasks_to_create.items():
                label = "new" if feat_title in new_feature_titles else "existing"
                click.secho(f"  Under {label} feature '{feat_title}':", fg="cyan")
                for task in tasks:
                    click.secho(f"    - {task.title}", fg="magenta")

        # 3. Handle dry run
        if dry_run:
            click.secho("\n[dry-run] No changes were made.", fg="blue")
            return

        # 4. Confirm before proceeding
        if not yes:
            prompt = click.style(f"\nProceed with creating {total_new_items} new items in '{repo}'?", fg="yellow", bold=True)
            if not click.confirm(prompt, default=True):
                click.secho("Aborting.", fg="red")
                return

        # 5. Apply changes
        click.secho("\nApplying changes...", fg="cyan")
        context_text = path.read_text(encoding='utf-8') if use_ai else ''

        for m in milestones_to_create:
            click.secho(f"Creating milestone: {m.name}", fg="cyan")
            gh_client.create_milestone(name=m.name, due_on=m.due_date)
            click.secho(f"  -> Milestone created: {m.name}", fg="green")

        feature_object_map = {}
        for feat in features_to_create:
            click.secho(f"Creating feature issue: {feat.title.strip()}", fg="cyan")
            # Prepare issue body
            body = getattr(feat, 'description', '') or ''
            if use_ai and ai_api_key:
                click.secho(f"  AI-enriching feature: {feat.title}...", fg="cyan")
                body = enrich_issue_description(feat.title, body, ai_provider, ai_api_key, context_text)
            try:
                feat_issue_obj = gh_client.create_issue(
                    title=feat.title.strip(), body=body, assignees=feat.assignees,
                    labels=feat.labels, milestone=feat.milestone
                )
            except GithubException as e:
                if e.status == 403:
                    click.secho(
                        "Error: Cannot create issue. Your GitHub token lacks permission to create issues. "
                        "Please grant 'repo' or 'issues' scope.", fg="red", err=True
                    )
                    sys.exit(1)
                raise
            feature_object_map[feat.title] = feat_issue_obj
            click.secho(f"  -> Feature issue created: #{feat_issue_obj.number}", fg="green")

        # Create all tasks, whether for new or existing features
        for feat_title, tasks in tasks_to_create.items():
            parent_issue_obj = feature_object_map.get(feat_title)
            if not parent_issue_obj:
                parent_issue_obj = gh_client._find_issue(feat_title)

            if not parent_issue_obj:
                click.secho(f"Warning: Cannot find parent issue '{feat_title}' for tasks. Skipping them.", fg="magenta")
                continue

            roadmap_feat = next((f for f in validated_roadmap.features if f.title == feat_title), None)
            milestone = roadmap_feat.milestone if roadmap_feat else None

            for task in tasks:
                click.secho(f"Creating task issue: {task.title.strip()} (under #{parent_issue_obj.number})", fg="cyan")
                body = task.description or ''
                if use_ai and ai_api_key:
                    click.secho(f"  AI-enriching task: {task.title}...", fg="cyan")
                    body = enrich_issue_description(task.title, body, ai_provider, ai_api_key, context_text)
                
                content = f"{body}\n\nParent issue: #{parent_issue_obj.number}".strip()
                try:
                    task_issue = gh_client.create_issue(
                        title=task.title.strip(), body=content, assignees=task.assignees,
                        labels=task.labels, milestone=milestone
                    )
                except GithubException as e:
                    if e.status == 403:
                        click.secho("Error: Cannot create task. Your GitHub token lacks permission to create issues. Please grant 'repo' or 'issues' scope.", fg="red", err=True)
                        sys.exit(1)
                    raise
                click.secho(f"  -> Task issue created: #{task_issue.number}", fg="green")



    
@cli.command(name='diff', help='Diff a local roadmap with GitHub issues (AI-first extraction for unstructured Markdown; disable with --no-ai; requires an AI API key)')
@click.argument('roadmap_file', type=click.Path(exists=True), metavar='ROADMAP_FILE')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to git origin.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--no-ai', 'no_ai', is_flag=True, help='Disable AI fallback for unstructured Markdown.')
@click.option('--ai-provider', type=click.Choice(['openai', 'gemini']), default='openai', show_default=True, help='AI provider to use for extraction.')
@click.option('--ai-key', help='AI API key (reads from environment or config if not provided).')
def diff(roadmap_file, repo, token, no_ai, ai_provider, ai_key):
    """Compare a local roadmap file with GitHub issues and list differences."""
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

    repo = _sanitize_repo_string(repo)
    roadmap_titles = set()
    use_ai = False

    if not no_ai and roadmap_file.lower().endswith(('.md', '.mdx', '.markdown')):
        try:
            raw = parse_roadmap(roadmap_file)
            validated = validate_roadmap(raw)
            if not validated.features and not validated.milestones:
                click.secho("Warning: Roadmap appears to be empty or unstructured.", fg="yellow")
                if click.confirm("Would you like to use AI to extract issues from it?", default=True):
                    use_ai = True
        except Exception:
            click.secho(f"Warning: Could not parse '{roadmap_file}' as a structured roadmap.", fg="yellow")
            if click.confirm("Would you like to use AI to extract issues from it?", default=True):
                use_ai = True

    if use_ai:
        click.secho(f"Using {ai_provider.capitalize()} to extract issues from unstructured roadmap...", fg="cyan")
        actual_ai_key = ai_key
        if not actual_ai_key:
            if ai_provider == 'openai':
                actual_ai_key = get_openai_api_key()
            else: # gemini
                actual_ai_key = get_gemini_api_key()
        
        if not actual_ai_key:
            click.secho(f"Error: {ai_provider.capitalize()} API key is required for AI mode.", fg="red", err=True)
            sys.exit(1)
        # Attempt extraction, retry once on invalid API key
        attempts = 0
        while True:
            try:
                issues = extract_issues_from_markdown(
                    md_file=roadmap_file,
                    provider=ai_provider,
                    api_key=actual_ai_key
                )
                roadmap_titles = {issue['title'] for issue in issues}
                break
            except Exception as e:
                err_msg = str(e)
                if attempts == 0 and ("invalid_api_key" in err_msg or "401" in err_msg or "API key is invalid" in err_msg):
                    click.secho(f"{ai_provider.capitalize()} API key appears invalid. Please enter a valid key.", fg="yellow")
                    if ai_provider == 'openai':
                        actual_ai_key = prompt_for_openai_key()
                    else: # gemini
                        actual_ai_key = prompt_for_gemini_key()
                    attempts += 1
                    continue
                click.secho(f"Error during AI extraction: {e}", fg="red", err=True)
                sys.exit(1)
    else:
        try:
            raw = parse_roadmap(roadmap_file)
            validated = validate_roadmap(raw)
            roadmap_titles = {feat.title for feat in validated.features}
            for feat in validated.features:
                for task in feat.tasks:
                    roadmap_titles.add(task.title)
        except Exception as e:
            click.echo(f"Error: Failed to parse structured roadmap file '{roadmap_file}': {e}", err=True)
            sys.exit(1)

    # Attempt to connect to GitHub repo, with fallback to detect or prompt if invalid
    attempts = 0
    while True:
        try:
            gh_client = GitHubClient(actual_token, repo)
            click.secho(f"Successfully connected to repository '{repo}'.", fg="green")
            break
        except GithubException as e:
            if e.status == 404:
                click.secho(f"Error: Repository '{repo}' not found. Please check the name and your permissions.", fg="red", err=True)
            elif e.status == 401:
                click.secho("Error: GitHub token is invalid or has insufficient permissions.", fg="red", err=True)
            else:
                click.secho(f"An unexpected GitHub error occurred: {e}", fg="red", err=True)
            if attempts == 0:
                # Try deriving from git config
                if click.confirm("Would you like to detect the repository from your local Git config?", default=True):
                    derived = get_repo_from_git_config()
                    if derived:
                        repo = derived
                        click.secho(f"Using repository from git config: {repo}", fg="magenta")
                        attempts += 1
                        continue
                    else:
                        click.secho("Could not detect repository from git config.", fg="yellow")
                # Prompt manual entry
                repo = click.prompt("Please enter your GitHub repository (owner/repo)")
                attempts += 1
                continue
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

    if missing and click.confirm(
        click.style(f"\nCreate {len(missing)} missing issues on GitHub?", fg="yellow", bold=True), default=True
    ):
        click.secho("\nCreating missing issues...", fg="cyan")
        
        created_count = 0
        failed_count = 0
        
        for feat in validated.features:
            # Check if the feature itself is missing
            if feat.title in missing:
                click.secho(f"Creating feature issue: {feat.title.strip()}", fg="cyan")
                try:
                    feat_issue = gh_client.create_issue(
                        title=feat.title.strip(),
                        body=feat.description or '',
                        assignees=feat.assignees,
                        labels=feat.labels,
                        milestone=feat.milestone
                    )
                    click.secho(f"  -> Feature issue created: #{feat_issue.number}", fg="green")
                    created_count += 1
                except GithubException as e:
                    click.secho(f"  -> Failed to create feature issue '{feat.title.strip()}': {e}", fg="red")
                    failed_count += 1

            # Check for missing tasks within this feature
            parent_issue_for_tasks = None
            for task in feat.tasks:
                if task.title in missing:
                    if not parent_issue_for_tasks:
                        # Find the parent issue on GitHub. It might have just been created.
                        parent_issue_for_tasks = gh_client._find_issue(feat.title)
                    
                    if not parent_issue_for_tasks:
                        click.secho(f"Warning: Cannot find parent issue '{feat.title}' for task '{task.title}'. Skipping.", fg="magenta")
                        continue

                    click.secho(f"Creating task issue: {task.title.strip()} (under #{parent_issue_for_tasks.number})", fg="cyan")
                    content = f"{task.description or ''}\n\nParent issue: #{parent_issue_for_tasks.number}".strip()

                    try:
                        task_issue = gh_client.create_issue(
                            title=task.title.strip(),
                            body=content,
                            assignees=task.assignees,
                            labels=task.labels,
                            milestone=feat.milestone
                        )
                        click.secho(f"  -> Task issue created: #{task_issue.number}", fg="green")
                        created_count += 1
                    except GithubException as e:
                        click.secho(f"  -> Failed to create task issue '{task.title.strip()}': {e}", fg="red")
                        failed_count += 1
        
        click.secho("\nCreation finished.", fg="bright_green", bold=True)
        click.secho(f"Successfully created: {created_count} issues.", fg="green")
        if failed_count > 0:
            click.secho(f"Failed to create: {failed_count} issues.", fg="red", err=True)


@cli.command(name='next', help='Show next action items')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to the current git repo.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (prompts if not set).')
@click.option('--roadmap-file', '-f', 'roadmap_file', type=click.Path(), default='ROADMAP.md', show_default=True,
              help='Local roadmap file to use if no active milestones found on GitHub.')
def next_command(repo, token, roadmap_file):
    """Shows open issues from the earliest active milestone."""
    # Determine GitHub token: use --token or prompt via get_github_token()
    actual_token = token if token else get_github_token()
    if not actual_token:
        raise click.ClickException("GitHub token is required.")

    if not repo:
        click.echo("No --repo provided, attempting to find repository from git config...")
        repo = get_repo_from_git_config()
        if not repo:
            click.echo("Could not determine repository from git config. Please use --repo. Exiting.", err=True)
            sys.exit(1)
        click.echo(f"Using repository from current git config: {repo}")
    else:
        click.echo(f"Using repository provided via --repo flag: {repo}")

    repo = _sanitize_repo_string(repo)
    gh_client = GitHubClient(actual_token, repo)
    
    click.echo(f"Finding next action items in repository '{repo}'...")
    
    milestone, issues = gh_client.get_next_action_items()
    
    if not milestone:
        click.secho("No active milestones with open issues found.", fg='yellow')
        # If there are any open issues, pick one at random
        try:
            open_issues = list(gh_client.repo.get_issues(state='open'))
        except Exception as e:
            click.secho(f"Error fetching open issues from GitHub: {e}", fg='red', err=True)
            open_issues = []
        if open_issues:
            issue = random.choice(open_issues)
            assignee_str = ""
            if issue.assignees:
                assignees_str = ", ".join([f"@{a.login}" for a in issue.assignees])
                assignee_str = f" (assigned to {assignees_str})"
            click.secho(
                f"Next GitHub issue: #{issue.number}: {issue.title}{assignee_str}",
                fg='green', bold=True
            )
            return
        # Fallback to local roadmap if no open issues
        click.secho(
            "No open GitHub issues available. Falling back to local roadmap tasks...",
            fg='yellow'
        )
        if not Path(roadmap_file).exists():
            click.secho(f"No tasks found in local roadmap ('{roadmap_file}' not found).", fg='yellow')
            return
        try:
            raw = parse_roadmap(roadmap_file)
            validated = validate_roadmap(raw)
        except Exception as e:
            click.secho(f"Error parsing local roadmap '{roadmap_file}': {e}", fg='red', err=True)
            return
        tasks = []
        for feat in validated.features:
            for task in feat.tasks:
                tasks.append((feat.title, task))
        if not tasks:
            click.secho("No tasks found in local roadmap.", fg='yellow')
            return
        feat_title, next_task = random.choice(tasks)
        click.secho(
            f"Next local task: {next_task.title} (feature: {feat_title})",
            fg='green', bold=True
        )
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


@cli.command(name='delete-closed', help='Delete all closed issues')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to git origin.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--dry-run', is_flag=True, help='List issues that would be deleted, without actually deleting them.')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt and immediately delete all closed issues.')
def delete_closed_issues_command(repo, token, dry_run, yes):
    """Permanently delete all closed issues in a repository. Requires confirmation."""
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

    repo = _sanitize_repo_string(repo)
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

    if not yes:
        prompt_text = click.style(f"Are you sure you want to permanently delete {len(closed_issues)} closed issues from '{repo}'? This is irreversible.", fg="yellow", bold=True)
        if not click.confirm(prompt_text):
            click.secho("Aborting.", fg="red")
            return
    
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


@cli.command(name='sanitize', help='Clean up issue titles')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to the current git repo.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--dry-run', is_flag=True, help='List issues that would be changed, without actually changing them.')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation prompt and immediately apply updates.')
def sanitize_command(repo, token, dry_run, yes):
    """Scan all issues and remove leading markdown characters like '#' from their titles."""
    click.echo("Starting 'sanitize' command...")
    actual_token = token if token else get_github_token()
    if not actual_token:
        click.secho("GitHub token is required to proceed.", fg="red", err=True)
        return
    
    click.echo("Successfully obtained GitHub token.")

    if not repo:
        click.echo("No --repo provided, attempting to find repository from git config...")
        repo = get_repo_from_git_config()
        if not repo:
            click.secho("Could not determine repository from git config. Please use --repo.", fg="red", err=True)
            return
        click.echo(f"Using repository from current git config: {repo}")
    else:
        click.echo(f"Using repository provided via --repo flag: {repo}")

    repo = _sanitize_repo_string(repo)
    try:
        gh_client = GitHubClient(actual_token, repo)
        click.echo(f"Successfully connected to repository '{repo}'.")
    except GithubException as e:
        if e.status == 404:
            click.secho(f"Error: Repository '{repo}' not found. Please check the name and your permissions.", fg="red", err=True)
        elif e.status == 401:
            click.secho("Error: GitHub token is invalid or has insufficient permissions.", fg="red", err=True)
        else:
            click.secho(f"An unexpected GitHub error occurred: {e}", fg="red", err=True)
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


@cli.command(name='deduplicate', help='Close duplicate open issues')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to the current git repo.')
@click.option('--token', help='GitHub API token (prompts if not set).')
@click.option('--dry-run', is_flag=True, help='List duplicate issues that would be closed, without actually closing them.')
@click.option('--yes', '-y', is_flag=True, default=False, help='Skip confirmation prompt and immediately apply updates.')
def deduplicate_command(repo, token, dry_run, yes):
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

    repo = _sanitize_repo_string(repo)
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
    if not yes:
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


# --- Enrichment Commands (from scripts/enrich.py) ---

def _enrich_parse_roadmap(path="ROADMAP.md"):
    """
    Parse ROADMAP.md and return a mapping of item title -> context dict.
    Captures goal, tasks, deliverables under sections/phases.
    """
    data = {}
    current = None
    section = None
    phase_re = re.compile(r'^\s*##\s*Phase\s*(\d+):\s*(.+)$')
    h3_re = re.compile(r'^\s*###\s*(.+)$')
    goal_re = re.compile(r'^\s*\*\*Goal\*\*')
    tasks_re = re.compile(r'^\s*\*\*Tasks\*\*')
    deliv_re = re.compile(r'^\s*\*\*(?:Milestones\s*&\s*)?Deliverables\*\*')
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                t = line.rstrip()
                m = phase_re.match(t)
                if m:
                    ctx = f"Phase {m.group(1)}: {m.group(2).strip()}"
                    data[ctx] = {'goal': [], 'tasks': [], 'deliverables': []}
                    current, section = ctx, None
                    continue
                m3 = h3_re.match(t)
                if m3:
                    ctx = m3.group(1).strip()
                    data[ctx] = {'goal': [], 'tasks': [], 'deliverables': []}
                    current, section = ctx, 'tasks'
                    continue
                if current is None:
                    continue
                if goal_re.match(t): section = 'goal'; continue
                if tasks_re.match(t): section = 'tasks'; continue
                if deliv_re.match(t): section = 'deliverables'; continue
                if section in ('goal', 'deliverables') and t.strip().startswith('- '):
                    data[current][section].append(t.strip()[2:].strip()); continue
                if section == 'tasks':
                    mnum = re.match(r'\s*\d+\.\s+(.*)$', t)
                    if mnum:
                        data[current]['tasks'].append(mnum.group(1).strip()); continue
                    if t.strip().startswith('- '):
                        data[current]['tasks'].append(t.strip()[2:].strip()); continue
    except FileNotFoundError:
        click.secho(f"Error: ROADMAP.md not found at {path}", fg="red", err=True)
        sys.exit(1)
    # Flatten mapping for lookups
    mapping = {}
    for ctx, obj in data.items():
        for key in ('goal', 'tasks', 'deliverables'):
            for itm in obj[key]:
                mapping[itm] = {'context': ctx, **obj}
    return mapping

def _enrich_get_context(title, roadmap):
    if title in roadmap:
        return roadmap[title], title
    candidates = difflib.get_close_matches(title, roadmap.keys(), n=1, cutoff=0.5)
    if candidates:
        m = candidates[0]
        return roadmap[m], m
    return None, None

def _enrich_call_llm(title, existing_body, ctx, provider, api_key):
    if not api_key:
        if provider == 'openai':
            api_key = get_openai_api_key()
        elif provider == 'gemini':
            api_key = get_gemini_api_key()
    
    if not api_key:
        sys.exit(1)

    # The actual call is now delegated to the unified `enrich_issue_description`
    context_parts = [f"Context: {ctx['context']}"]
    if ctx.get('goal'):
        context_parts.append("Goal:\n" + "\n".join(f"- {g}" for g in ctx['goal']))
    if ctx.get('tasks'):
        context_parts.append("Tasks:\n" + "\n".join(f"- {t}" for t in ctx['tasks']))
    if ctx.get('deliverables'):
        context_parts.append("Deliverables:\n" + "\n".join(f"- {d}" for d in ctx['deliverables']))
    
    full_context = "\n".join(context_parts)

    return enrich_issue_description(
        title=title,
        existing_body=existing_body,
        provider=provider,
        api_key=api_key,
        context=full_context
    )

@cli.group(name='enrich', help='Enrich GitHub issues using roadmap context via LLM')
@click.option('--ai-provider', type=click.Choice(['openai', 'gemini']), default='openai', show_default=True, help='AI provider to use.')
@click.pass_context
def enrich(ctx, ai_provider):
    """General-purpose CLI for GitHub issue enrichment via LLM using roadmap context."""
    ctx.obj = {'ai_provider': ai_provider}

@enrich.command('issue', help='Enrich a single issue')
@click.option('--repo', required=True, help='owner/repo')
@click.option('--issue', 'issue_number', type=int, required=True, help='Issue number')
@click.option('--path', 'roadmap_path', default='ROADMAP.md', help='Path to roadmap file')
@click.option('--apply', 'apply_changes', is_flag=True, help='Apply the update')
@click.pass_context
def enrich_issue_command(click_ctx, repo, issue_number, roadmap_path, apply_changes):
    """Enrich a single issue."""
    token = get_github_token()
    if not token: sys.exit(1)
    repo = _sanitize_repo_string(repo)
    gh = Github(token)
    try:
        repo_obj = gh.get_repo(repo)
    except GithubException as e:
        click.secho(f"Error: cannot access repo {repo}: {e}", fg="red", err=True)
        sys.exit(1)
    
    roadmap = _enrich_parse_roadmap(roadmap_path)
    issue = repo_obj.get_issue(number=issue_number)
    roadmap_ctx, matched = _enrich_get_context(issue.title.strip(), roadmap)
    if not roadmap_ctx:
        click.secho(f"No roadmap context for issue #{issue_number}", fg="red", err=True)
        sys.exit(1)
    enriched = _enrich_call_llm(issue.title, issue.body, roadmap_ctx, click_ctx.obj['ai_provider'], None)
    click.echo(enriched)
    if apply_changes:
        issue.edit(body=enriched)
        click.secho(f"Issue #{issue_number} updated.", fg="green")


@enrich.command('batch', help='Batch enrich issues')
@click.option('--repo', required=True, help='owner/repo')
@click.option('--path', 'roadmap_path', default='ROADMAP.md', help='Path to roadmap file')
@click.option('--csv', 'csv_path', help='Output CSV file')
@click.option('--interactive', is_flag=True, help='Interactive approval')
@click.option('--apply', 'apply_changes', is_flag=True, help='Apply all updates')
@click.pass_context
def enrich_batch_command(click_ctx, repo, roadmap_path, csv_path, interactive, apply_changes):
    """Batch enrich issues."""
    token = get_github_token()
    if not token: sys.exit(1)
    repo = _sanitize_repo_string(repo)
    gh = Github(token)
    try:
        repo_obj = gh.get_repo(repo)
    except GithubException as e:
        click.secho(f"Error: cannot access repo {repo}: {e}", fg="red", err=True)
        sys.exit(1)
    
    roadmap = _enrich_parse_roadmap(roadmap_path)
    issues = list(repo_obj.get_issues(state='open'))
    records = []
    for issue in issues:
        roadmap_ctx, matched = _enrich_get_context(issue.title.strip(), roadmap)
        if not roadmap_ctx:
            continue
        enriched = _enrich_call_llm(issue.title, issue.body, roadmap_ctx, click_ctx.obj['ai_provider'], None)
        records.append((issue.number, issue.title, roadmap_ctx['context'], matched, enriched))
    
    if csv_path:
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['issue', 'title', 'context', 'matched', 'enriched_body'])
            writer.writerows(records)
        click.secho(f"Wrote {len(records)} records to {csv_path}", fg="green")
        return
    
    if interactive:
        for num, title, ctx_name, matched, body in records:
            click.secho(f"\n--- Issue #{num}: {title} ({ctx_name}) matched '{matched}' ---", bold=True)
            click.echo(body)
            ans = click.prompt("Apply this update? [y/N/q]", default='n', show_default=False).strip().lower()
            if ans == 'y':
                repo_obj.get_issue(num).edit(body=body)
                click.secho(f"Updated issue #{num}", fg="green")
            if ans == 'q':
                break
        return

    if apply_changes:
        for num, _, _, _, body in records:
            repo_obj.get_issue(num).edit(body=body)
            click.secho(f"Updated issue #{num}", fg="green")
        return
        
    for num, title, ctx_name, matched, _ in records:
        click.echo(f"Would update issue #{num}: {title} (matched '{matched}' in {ctx_name})")




@cli.command(name='import-md', help='Import issues from an unstructured Markdown file via AI')
@click.argument('repo', metavar='REPO')
@click.argument('markdown_file', type=click.Path(), metavar='MARKDOWN_FILE')
@click.option('--token', help='GitHub token (overrides GITHUB_TOKEN env var)')
@click.option('--ai-provider', type=click.Choice(['openai', 'gemini']), default='openai', show_default=True, help='AI provider to use.')
@click.option('--ai-key', help='AI API key (overrides environment variables).')
@click.option('--model', help='AI model to use (e.g., gpt-4-turbo-preview, gemini-pro).')
@click.option('--temperature', type=float, help='AI temperature (e.g., 0.5).')
@click.option('--dry-run', is_flag=True, help='List issues without creating them')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation and create all issues')
@click.option('--verbose', '-v', is_flag=True, help='Show progress logs')
def import_md(repo, markdown_file, token, ai_provider, ai_key, model, temperature, dry_run, yes, verbose):
    """Import issues from an unstructured markdown file using AI.

    This command parses a Markdown file, using an AI model to extract potential
    GitHub issues from the text. This is useful for quickly converting documents like
    meeting notes or brainstorming sessions into actionable GitHub issues.
    """
    if not Path(markdown_file).exists():
        click.secho(f"Error: The file '{markdown_file}' does not exist.", fg="red", err=True)
        sys.exit(1)

    if verbose:
        click.secho("Starting 'import-md' command...", fg="cyan", bold=True)
    
    # Get tokens
    actual_token = token or get_github_token()
    if not actual_token:
        click.secho("GitHub token is required to proceed. Exiting.", fg="red", err=True)
        sys.exit(1)

    actual_ai_key = ai_key
    if not actual_ai_key:
        if ai_provider == 'openai':
            actual_ai_key = get_openai_api_key()
        else: # gemini
            actual_ai_key = get_gemini_api_key()
    if not actual_ai_key:
        click.secho(f"{ai_provider.capitalize()} API key is required. Exiting.", fg="red", err=True)
        sys.exit(1)
    
    if verbose:
        click.secho(f"Using repository: {repo}", fg='magenta')

    repo = _sanitize_repo_string(repo)
    try:
        gh_client = GitHubClient(actual_token, repo)
        if verbose:
            click.secho(f"Successfully connected to repository '{repo}'.", fg="green")
    except GithubException as e:
        if e.status == 404:
            click.secho(f"Error: Repository '{repo}' not found. Please check the name and your permissions.", fg="red", err=True)
        elif e.status == 401:
            click.secho("Error: GitHub token is invalid or has insufficient permissions.", fg="red", err=True)
        else:
            click.secho(f"An unexpected GitHub error occurred: {e}", fg="red", err=True)
        sys.exit(1)
    
    if verbose:
        click.secho(f"Extracting issues from '{markdown_file}' using {ai_provider.capitalize()} (model: {model or 'default'})...", fg='cyan')
    
    # Set defaults for model and temperature if not provided
    if ai_provider == 'openai':
        final_model = model or os.getenv('OPENAI_MODEL', 'gpt-4-turbo-preview')
        final_temp = temperature if temperature is not None else float(os.getenv('OPENAI_TEMPERATURE', '0.5'))
    else: # gemini
        final_model = model or os.getenv('GEMINI_MODEL', 'gemini-pro')
        final_temp = temperature if temperature is not None else float(os.getenv('GEMINI_TEMPERATURE', '0.5'))

    try:
        issues = extract_issues_from_markdown(
            md_file=markdown_file,
            provider=ai_provider,
            api_key=actual_ai_key,
            model_name=final_model,
            temperature=final_temp
        )
    except Exception as e:
        click.secho(f"Error extracting issues from markdown: {e}", fg="red", err=True)
        sys.exit(1)

    if not issues:
        click.secho("No issues extracted from the markdown file.", fg="yellow")
        return

    click.secho(f"Extracted {len(issues)} potential issues:", fg="green", bold=True)
    for issue in issues:
        click.secho(f"  - Title: {issue['title']}", fg="white")

    if dry_run:
        click.secho("\n[dry-run] No issues will be created. The following issues would be created:", fg="blue")
        for issue in issues:
            click.secho(f"\n--- [dry-run] Issue: {issue['title']} ---", fg="blue", bold=True)
            click.echo(issue.get('description', ''))
        return

    if not yes:
        prompt = click.style(
            f"\nProceed with creating {len(issues)} issues in '{repo}'?", fg="yellow", bold=True
        )
        if not click.confirm(prompt, default=True):
            click.secho("Aborting.", fg="red")
            return

    click.secho("\nCreating issues on GitHub...", fg="cyan")
    created_count = 0
    failed_count = 0
    for issue in issues:
        title = issue['title']
        body = issue.get('description', '')
        if verbose:
            click.secho(f"Creating issue: '{title}'", fg="yellow")
        try:
            created_issue = gh_client.create_issue(title=title, body=body)
            click.secho(f"  -> Successfully created issue #{created_issue.number}.", fg="green")
            created_count += 1
        except Exception as e:
            click.secho(f"  -> Failed to create issue '{title}': {e}", fg="red", err=True)
            failed_count += 1
    
    click.secho("\n'import-md' command finished.", fg="green", bold=True)
    click.secho(f"Successfully created: {created_count} issues.", fg="green")
    if failed_count > 0:
        click.secho(f"Failed to create: {failed_count} issues.", fg="red", err=True)


@cli.command(name='start-demo', help='Run the Streamlit demo')
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


# Vibe Kanban integration commands
@cli.group('vibe', help='Manage Vibe Kanban integration commands.')
def vibe():
    """Vibe Kanban integration subcommands."""
    pass


@vibe.command('push', help='Push GitHub issues to a Vibe Kanban board')
@click.option('--repo', required=True, help='GitHub repository in owner/repo format.')
@click.option('--board', 'board_name', help='Vibe Kanban board name or ID.', required=True)
@click.option('--milestone', help='Only include issues in this milestone')
@click.option('--label', 'labels', multiple=True, help='Only include issues with these labels')
@click.option('--state', default='open', show_default=True, help='Only include issues with this state')
@click.option('--kanban-api', envvar='VIBE_KANBAN_API', help='Vibe Kanban API base URL.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token.')
def push(repo, board_name, milestone, labels, state, kanban_api, token):
    """Push GitHub issues into a Vibe Kanban board."""
    actual_token = token or get_github_token()
    repo = _sanitize_repo_string(repo)
    gh_client = GitHubClient(actual_token, repo)

    # Build query parameters for fetching issues
    params = {'state': state}
    if labels:
        try:
            # PyGithub expects Label objects, not strings
            params['labels'] = [gh_client.repo.get_label(l) for l in labels]
        except GithubException as e:
            click.secho(f"Error: Could not find one or more labels: {labels}. Details: {e}", fg="red", err=True)
            sys.exit(1)

    if milestone:
        milestone_obj = gh_client._find_milestone(milestone)
        if not milestone_obj:
            click.secho(f"Error: Milestone '{milestone}' not found.", fg="red", err=True)
            sys.exit(1)
        params['milestone'] = milestone_obj
    
    click.secho(f"Fetching issues from '{repo}'...", fg="cyan")
    try:
        issues = list(gh_client.repo.get_issues(**params))
    except GithubException as e:
        click.secho(f"Error fetching issues from GitHub: {e}", fg="red", err=True)
        sys.exit(1)

    click.echo(f"Found {len(issues)} issues to push.")
    if not issues:
        click.secho("No issues match the criteria. Nothing to push.", fg="yellow")
        return

    # Serialize PyGithub issue objects into a simple format for the client
    issues_data = [
        {
            "number": issue.number,
            "title": issue.title,
            "body": issue.body or "",
            "url": issue.html_url,
            "state": issue.state,
            "labels": [label.name for label in issue.labels],
        }
        for issue in issues
    ]
    
    # Initialize Vibe Kanban client
    kanban_token = os.getenv('VIBE_KANBAN_TOKEN')
    kanban_client = VibeKanbanClient(api_url=kanban_api, token=kanban_token)
    click.echo(f"Pushing {len(issues_data)} issues to board '{board_name}'...")
    try:
        kanban_client.push_issues_to_board(board_name=board_name, issues=issues_data)
        click.secho("Push completed.", fg="green")
    except NotImplementedError as e:
        click.secho(f"Functionality not implemented: {e}", fg="yellow")
    except Exception as e:
        click.secho(f"An error occurred while pushing to Vibe Kanban: {e}", fg="red", err=True)
        sys.exit(1)


@vibe.command('pull', help='Pull task status from a Vibe Kanban board')
@click.option('--repo', required=True, help='GitHub repository in owner/repo format.')
@click.option('--board', 'board_name', required=True, help='Vibe Kanban board name or ID.')
@click.option('--kanban-api', envvar='VIBE_KANBAN_API', required=True, help='Vibe Kanban API base URL.')
@click.option('--bidirectional', is_flag=True, help='Also sync comments from GitHub back to Vibe Kanban')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token.')
def pull(repo, board_name, kanban_api, bidirectional, token):
    """Pull task status from a Vibe Kanban board into GitHub."""
    actual_token = token or get_github_token()
    repo = _sanitize_repo_string(repo)
    gh_client = GitHubClient(actual_token, repo)

    # Initialize Vibe Kanban client
    kanban_token = os.getenv('VIBE_KANBAN_TOKEN')
    kanban_client = VibeKanbanClient(api_url=kanban_api, token=kanban_token)
    click.echo(f"Pulling board status from '{board_name}'...")
    try:
        statuses = kanban_client.pull_board_status(board_name=board_name, bidirectional=bidirectional)
        click.echo(f"Pulled {len(statuses)} updates from board '{board_name}'.")

        # Process updates and sync to GitHub
        for status in statuses:
            issue_number = status.get("issue_number")
            new_state = status.get("state")
            if issue_number and new_state:
                click.echo(f"Updating issue #{issue_number} to state '{new_state}'...")
                try:
                    issue = gh_client.repo.get_issue(number=issue_number)
                    issue.edit(state=new_state)
                    click.secho(f"  -> Successfully updated issue #{issue_number}.", fg="green")
                except GithubException as e:
                    click.secho(f"  -> Failed to update issue #{issue_number}: {e}", fg="red")

    except NotImplementedError as e:
        click.secho(f"Functionality not implemented: {e}", fg="yellow")
        return
    except Exception as e:
        click.secho(f"An error occurred while pulling from Vibe Kanban: {e}", fg="red", err=True)
        sys.exit(1)
    click.secho("Pull completed.", fg="green")


@cli.command(name='start-api', help='Run the FastAPI server')
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


@cli.command('process-issues', help='Process a list of issues sequentially with an AI agent.')
@click.argument('issues_file', type=click.Path(exists=True))
@click.option('--agent', type=click.Choice(['aider', 'gemini']), default='aider', show_default=True, help='The AI agent to use for processing issues.')
@click.option('--results-dir', default='results', show_default=True, help='Directory to save detailed logs.')
@click.option('--timeout', default=300, show_default=True, help='Timeout in seconds for each agent process.')
def process_issues(issues_file, agent, results_dir, timeout):
    """
    Reads a list of issues from a file (one per line) and runs an AI agent on each one sequentially.
    This implements the "atomic issue resolution" pattern.
    """
    results_path = Path(results_dir)
    results_path.mkdir(exist_ok=True)
    
    with open(issues_file, 'r', encoding='utf-8') as f:
        issues = [line.strip() for line in f if line.strip()]

    click.secho(f"Found {len(issues)} issues to process with the '{agent}' agent.", fg='magenta')
    click.secho(f"Issues to process: {issues}", fg='magenta')

    for issue in issues:
        click.secho(f"Processing: {issue}", fg='cyan')
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        
        if agent == 'aider':
            result_file = results_path / f"aider_issue_{timestamp}.log"
            cmd = [
                "aider",
                "--message", issue,
                "--yes",
                "--no-stream",
                "--auto-commits"
            ]
            try:
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=timeout,
                    encoding='utf-8'
                )
                with open(result_file, 'w', encoding='utf-8') as log_f:
                    log_f.write(f"Issue: {issue}\n")
                    log_f.write(f"Exit status: {result.returncode}\n\n")
                    log_f.write("---" + "STDOUT" + "---" + "\n")
                    log_f.write(result.stdout)
                    log_f.write("\n---" + "STDERR" + "---" + "\n")
                    log_f.write(result.stderr)
                
                if result.returncode == 0:
                    click.secho(f"✅ SUCCESS (Aider): {issue}", fg='green')
                else:
                    click.secho(f"❌ FAILED (Aider): {issue}", fg='red')
                    click.secho(f"  Exit status: {result.returncode}. Log: {result_file}", fg='red')
            
            except FileNotFoundError:
                click.secho('Aider CLI not found. Please ensure the "aider" package is installed.', fg='red')
                sys.exit(1)
            except subprocess.TimeoutExpired:
                click.secho(f"❌ TIMEOUT (Aider): {issue}. Log: {result_file}", fg='red')
                with open(result_file, 'w', encoding='utf-8') as log_f:
                    log_f.write(f"Issue: {issue}\n")
                    log_f.write(f"Result: TIMEOUT after {timeout} seconds.\n")

        elif agent == 'gemini':
            result_file = results_path / f"gemini_issue_{timestamp}.log"
            try:
                gemini_api_key = get_gemini_api_key()
                if not gemini_api_key:
                    click.secho("Gemini API key is required for the gemini agent.", fg="red")
                    sys.exit(1)
                click.secho(f"  -> Gemini API key obtained: {bool(gemini_api_key)}", fg='blue')

                # Gather context from python files
                files = list(Path.cwd().glob('**/*.py'))
                file_contents = {}
                for p in files:
                    try:
                        file_contents[str(p.relative_to(Path.cwd()))] = p.read_text(encoding='utf-8')
                    except Exception as e:
                        click.secho(f"    - Warning: Could not read file {p}: {e}", fg='magenta')
                click.secho(f"  -> Sending {len(file_contents)} Python files as context to Gemini.", fg='blue')

                # Call the Gemini API to get code changes
                click.secho("  -> Asking Gemini for code changes...", fg='yellow')
                changes_text = generate_code_changes(issue, file_contents, 'gemini', gemini_api_key)
                click.secho(f"  -> Raw changes_text from Gemini: {changes_text[:200]}...", fg='blue')

                if not changes_text or changes_text.strip() == "":
                    click.secho("  -> Gemini returned no changes.", fg='green')
                    continue

                # Parse the response and apply changes
                click.secho("  -> Applying changes...", fg='yellow')
                changed_files = []
                parts = changes_text.split('--- START FILE: ')
                for part in parts:
                    if not part.strip():
                        continue
                    try:
                        file_path_str, content = part.split(' ---\n', 1)
                        file_path = Path(file_path_str.strip())
                        content, _ = content.rsplit('\n--- END FILE:', 1)
                        
                        # Ensure the file path is relative to the current working directory
                        # and create parent directories if they don't exist
                        full_file_path = Path.cwd() / file_path
                        full_file_path.parent.mkdir(parents=True, exist_ok=True)
                        full_file_path.write_text(content.strip(), encoding='utf-8')
                        changed_files.append(str(full_file_path))
                        click.secho(f"    - Modified {full_file_path}", fg='green')
                    except Exception as e:
                        click.secho(f"    - Error parsing or writing file change for part: {part[:100]}... Error: {e}", fg='red')

                # Commit changes
                if changed_files:
                    click.secho("  -> Committing changes...", fg='yellow')
                    try:
                        subprocess.run(['git', 'add'] + changed_files, check=True, cwd=Path.cwd())
                        commit_message = f"fix: {issue}"
                        subprocess.run(['git', 'commit', '-m', commit_message], check=True, cwd=Path.cwd())
                        click.secho(f"    - Committed with message: '{commit_message}'", fg='green')
                        click.secho(f"✅ SUCCESS (Gemini): {issue}", fg='green')
                    except subprocess.CalledProcessError as e:
                        click.secho(f"  -> Git operation failed: {e}", fg='red')
                        click.secho(f"❌ FAILED (Gemini): {issue}", fg='red')
                else:
                    click.secho("  -> No files were changed.", fg='yellow')

            except Exception as e:
                click.secho(f"❌ FAILED (Gemini): {issue}. Error: {e}", fg='red')
                with open(result_file, 'w', encoding='utf-8') as log_f:
                    log_f.write(f"Issue: {issue}\n")
                    log_f.write(f"Error: {e}\n")

        time.sleep(2) # Brief pause between issues

    click.secho("\nGemini processing complete.", fg='green') 
                text=True, 
                timeout=timeout,
                encoding='utf-8'
            )
            
            with open(result_file, 'w', encoding='utf-8') as log_f:
                log_f.write(f"Issue: {issue}\n")
                log_f.write(f"Exit status: {result.returncode}\n\n")
                log_f.write("--- STDOUT ---\n")
                log_f.write(result.stdout)
                log_f.write("\n--- STDERR ---\n")
                log_f.write(result.stderr)
                
            if result.returncode == 0:
                click.secho(f"✅ SUCCESS: {issue}", fg='green')
            else:
                click.secho(f"❌ FAILED: {issue}", fg='red')
                click.secho(f"  Exit status: {result.returncode}. Log: {result_file}", fg='red')
        
        except FileNotFoundError:
            click.secho('Aider CLI not found. Please ensure the "aider" package is installed.', fg='red')
            sys.exit(1)
        except subprocess.TimeoutExpired:
            click.secho(f"❌ TIMEOUT: {issue}. Log: {result_file}", fg='red')
            with open(result_file, 'w', encoding='utf-8') as log_f:
                log_f.write(f"Issue: {issue}\n")
                log_f.write(f"Result: TIMEOUT after {timeout} seconds.\n")

    click.secho("\nProcessing complete.", fg='green')

@cli.command(name='uninstall', help='Uninstall gitscaffold and clean up config.')
def uninstall():
    """Provides instructions for uninstalling and offers to clean up config data."""
    click.secho("Uninstalling `gitscaffold` requires two steps:", fg='yellow')
    click.secho("\n1. Uninstall the package itself:", fg="cyan", bold=True)
    click.secho("   Run: pip uninstall gitscaffold", fg="green")

    click.secho("\n2. Clean up global configuration directory:", fg="cyan", bold=True)
    config_path = get_global_config_path()
    config_dir = config_path.parent

    if not config_dir.exists():
        click.secho("No global configuration directory found to remove.", fg="green")
        return

    click.echo(f"   Your global configuration is stored at: {config_dir}")
    prompt = click.style(f"   Do you want to permanently delete this directory?", fg="yellow", bold=True)
    if click.confirm(prompt, default=False):
        try:
            shutil.rmtree(config_dir)
            click.secho(f"Successfully deleted {config_dir}", fg="green")
        except OSError as e:
            click.secho(f"Error deleting directory {config_dir}: {e}", fg="red", err=True)
    else:
        click.secho("Aborted directory deletion.", fg="yellow")


