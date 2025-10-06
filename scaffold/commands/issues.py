import click
from scaffold.github_cli import GitHubCLI

# Import existing click Commands from the legacy CLI
from scaffold.core.config import get_repo_from_git_config


@click.group(name='issues', help='Work with GitHub issues directly.')
def issues():
    pass


# High‑value gh wrappers
@issues.command('list', help='List issues via GitHub CLI (gh)')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.option('--state', type=click.Choice(['open','closed','all']), default='open', show_default=True)
@click.option('--limit', default=50, show_default=True)
def gh_issue_list(repo, state, limit):
    repo = repo or get_repo_from_git_config()
    if not repo:
        click.secho('Could not detect repository. Use --repo.', fg='red')
        raise SystemExit(1)
    try:
        gh = GitHubCLI()
        # reuse underlying method but constrain fields to a simple display
        items = gh.list_issues(repo, state=state, limit=limit)
        if not items:
            click.echo('No issues found.')
            return
        for it in items:
            click.echo(f"#{it['number']} [{it['state']}] {it['title']}")
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')
    except Exception as e:
        import subprocess
        if isinstance(e, subprocess.CalledProcessError):
            click.secho(f"gh error: {e}", fg='red')
        else:
            raise


@issues.command('create', help='Create an issue via GitHub CLI (gh)')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.option('--title', required=True)
@click.option('--body', default='')
@click.option('--label', 'labels', multiple=True)
@click.option('--assignee', 'assignees', multiple=True)
@click.option('--milestone', default=None)
def gh_issue_create(repo, title, body, labels, assignees, milestone):
    repo = repo or get_repo_from_git_config()
    if not repo:
        click.secho('Could not detect repository. Use --repo.', fg='red')
        raise SystemExit(1)
    try:
        gh = GitHubCLI()
        created = gh.create_issue(repo, title=title, body=body or None,
                                  labels=list(labels) or None,
                                  assignees=list(assignees) or None,
                                  milestone=milestone)
        click.secho(f"Created issue #{created.get('number')} – {created.get('title')}", fg='green')
        if created.get('url'):
            click.echo(created['url'])
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')
    except Exception as e:
        import subprocess
        if isinstance(e, subprocess.CalledProcessError):
            click.secho(f"gh error: {e}", fg='red')
        else:
            raise


@issues.command('close', help='Close an issue via GitHub CLI (gh)')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
def gh_issue_close(repo, number):
    repo = repo or get_repo_from_git_config()
    if not repo:
        click.secho('Could not detect repository. Use --repo.', fg='red')
        raise SystemExit(1)
    try:
        gh = GitHubCLI()
        gh.close_issue(repo, number)
        click.secho(f"Closed issue #{number}", fg='green')
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')
    except Exception as e:
        import subprocess
        if isinstance(e, subprocess.CalledProcessError):
            click.secho(f"gh error: {e}", fg='red')
        else:
            raise


# Kanban via gh project (read-only for now)
@issues.group('projects', help='GitHub Projects (kanban) via gh')
def projects():
    pass


@projects.command('list')
@click.option('--owner', help='User owner for classic projects (optional)')
@click.option('--org', help='Organization for projects (optional)')
@click.option('--limit', default=30, show_default=True)
def projects_list(owner, org, limit):
    try:
        gh = GitHubCLI()
        if not gh.has_projects():
            click.secho('gh project is not available. Install gh extension or update gh.', fg='yellow')
            return
        out = gh.project_list(owner=owner, org=org, limit=limit)
        click.echo(out)
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')


@projects.command('view')
@click.argument('number', type=int)
def projects_view(number):
    try:
        gh = GitHubCLI()
        if not gh.has_projects():
            click.secho('gh project is not available. Install gh extension or update gh.', fg='yellow')
            return
        out = gh.project_view(number)
        click.echo(out)
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')


# Existing higher‑level operations (registered if legacy is available)
try:
    from scaffold.cli import sanitize as legacy_sanitize_cmd  # type: ignore
    issues.add_command(legacy_sanitize_cmd, name='sanitize')
except Exception:
    pass
try:
    from scaffold.cli import deduplicate as legacy_deduplicate_cmd  # type: ignore
    issues.add_command(legacy_deduplicate_cmd, name='deduplicate')
except Exception:
    pass
try:
    from scaffold.cli import delete_closed as legacy_delete_closed_cmd  # type: ignore
    issues.add_command(legacy_delete_closed_cmd, name='delete-closed')
except Exception:
    pass
try:
    from scaffold.cli import enrich as legacy_enrich_group  # type: ignore
    issues.add_command(legacy_enrich_group, name='enrich')
except Exception:
    pass
