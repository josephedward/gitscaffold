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

from .parser import parse_markdown, parse_roadmap, write_roadmap
from .validator import validate_roadmap, Feature, Task
from .github import GitHubClient
from .ai import enrich_issue_description, extract_issues_from_markdown
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
            elif openai_api_key: # Only enrich if key is available
                logging.info(f"AI-enriching feature: {feat.title}...")
                click.secho(f"AI-enriching feature: {feat.title}...", fg="cyan")
                body = enrich_issue_description(feat.title, body, openai_api_key, context_text)
        
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
                elif openai_api_key: # Only enrich if key is available
                    logging.info(f"AI-enriching sub-task: {task.title}...")
                    click.secho(f"AI-enriching sub-task: {task.title}...", fg="cyan")
                    t_body = enrich_issue_description(task.title, t_body, openai_api_key, context_text)
            
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





@cli.command(name="sync", help=click.style('Sync roadmap with a GitHub repository', fg='cyan'))
@click.argument('roadmap_file', type=click.Path(exists=True), metavar='ROADMAP_FILE')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to git origin.')
@click.option('--dry-run', is_flag=True, help='Simulate and show what would be created, without making changes.')
@click.option('--ai-enrich', is_flag=True, help='Use AI to enrich descriptions of new issues being created.')
@click.option('--yes', '-y', is_flag=True, help='Skip confirmation and apply changes when populating an empty repo.')
@click.option('--update-local', is_flag=True, help='Update the local roadmap file with issues from GitHub.')
def sync(roadmap_file, token, repo, dry_run, ai_enrich, yes, update_local):
    """Sync a Markdown roadmap with a GitHub repository.

    If the repository is empty, it populates it with issues from the roadmap.
    If the repository has issues, it performs a diff between the roadmap and the issues.
    """
    click.secho("Starting 'sync' command...", fg='cyan', bold=True)
    actual_token = token if token else get_github_token()
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

    path = Path(roadmap_file)
    # Load and validate roadmap data (supports Markdown, YAML, or JSON)
    try:
        raw_roadmap_data = parse_roadmap(roadmap_file)
    except Exception as e:
        click.secho(f"Error: Failed to parse roadmap file '{roadmap_file}': {e}", fg="red", err=True)
        sys.exit(1)
    validated_roadmap = validate_roadmap(raw_roadmap_data)
    # Prepare AI enrichment key if requested
    openai_api_key_for_ai = None
    if ai_enrich:
        openai_api_key_for_ai = get_openai_api_key()
        if not openai_api_key_for_ai:
            sys.exit(1)

    try:
        gh_client = GitHubClient(actual_token, repo)
        click.secho(f"Successfully connected to repository '{repo}'.", fg="green")
    except GithubException as e:
        if e.status == 404:
            click.secho(f"Error: Repository '{repo}' not found. Please check the name and your permissions.", fg="red", err=True)
        elif e.status == 401:
            click.secho("Error: GitHub token is invalid or has insufficient permissions.", fg="red", err=True)
        else:
            click.secho(f"An unexpected GitHub error occurred: {e}", fg="red", err=True)
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
        
        context_text = path.read_text(encoding='utf-8') if ai_enrich else ''
        
        # Display what will be done. This is effectively a dry run preview.
        _populate_repo_from_roadmap(
            gh_client=gh_client,
            roadmap_data=validated_roadmap,
            dry_run=True,
            ai_enrich=ai_enrich,
            openai_api_key=openai_api_key_for_ai,
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
            ai_enrich=ai_enrich,
            openai_api_key=openai_api_key_for_ai,
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
        context_text = path.read_text(encoding='utf-8') if ai_enrich else ''

        for m in milestones_to_create:
            click.secho(f"Creating milestone: {m.name}", fg="cyan")
            gh_client.create_milestone(name=m.name, due_on=m.due_date)
            click.secho(f"  -> Milestone created: {m.name}", fg="green")

        feature_object_map = {}
        for feat in features_to_create:
            click.secho(f"Creating feature issue: {feat.title.strip()}", fg="cyan")
            body = feat.description or ''
            if ai_enrich and openai_api_key_for_ai:
                click.secho(f"  AI-enriching feature: {feat.title}...", fg="cyan")
                body = enrich_issue_description(feat.title, body, openai_api_key_for_ai, context_text)
            
            feat_issue_obj = gh_client.create_issue(
                title=feat.title.strip(), body=body, assignees=feat.assignees,
                labels=feat.labels, milestone=feat.milestone
            )
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
                if ai_enrich and openai_api_key_for_ai:
                    click.secho(f"  AI-enriching task: {task.title}...", fg="cyan")
                    body = enrich_issue_description(task.title, body, openai_api_key_for_ai, context_text)
                
                content = f"{body}\n\nParent issue: #{parent_issue_obj.number}".strip()
                task_issue = gh_client.create_issue(
                    title=task.title.strip(), body=content, assignees=task.assignees,
                    labels=task.labels, milestone=milestone
                )
                click.secho(f"  -> Task issue created: #{task_issue.number}", fg="green")

    click.secho("Sync command finished.", fg="green", bold=True)
    

@cli.command(name='diff', help=click.style('Diff local roadmap vs GitHub issues', fg='cyan'))
@click.argument('roadmap_file', type=click.Path(exists=True), metavar='ROADMAP_FILE')
@click.option('--repo', help='Target GitHub repository in `owner/repo` format. Defaults to git origin.')
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token (reads from .env or GITHUB_TOKEN env var).')
def diff(roadmap_file, repo, token):
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

    try:
        raw = parse_roadmap(roadmap_file)
        validated = validate_roadmap(raw)
    except Exception as e:
        click.echo(f"Error: Failed to parse roadmap file '{roadmap_file}': {e}", err=True)
        sys.exit(1)
    
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


@cli.command(name='sanitize', help=click.style('Clean up issue titles', fg='cyan'))
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


@cli.command(name='deduplicate', help=click.style('Close duplicate open issues', fg='cyan'))
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
