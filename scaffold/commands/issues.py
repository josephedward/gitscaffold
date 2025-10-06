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


@issues.command('view', help='View an issue via GitHub CLI (gh)')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
def gh_issue_view(repo, number):
    repo = repo or get_repo_from_git_config()
    if not repo:
        click.secho('Could not detect repository. Use --repo.', fg='red')
        raise SystemExit(1)
    try:
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        data = gh.view_issue(repo, number)
        title = data.get('title','')
        url = data.get('url','')
        body = data.get('body','') or ''
        click.echo(f"#{number} {title}\n{url}\n\n{body}")
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')
    except Exception as e:
        import subprocess
        if isinstance(e, subprocess.CalledProcessError):
            click.secho(f"gh error: {e}", fg='red')
        else:
            raise


@issues.command('comment', help='Comment on an issue via GitHub CLI (gh)')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
@click.argument('body')
def gh_issue_comment(repo, number, body):
    repo = repo or get_repo_from_git_config()
    if not repo:
        click.seho('Could not detect repository. Use --repo.', fg='red')
        raise SystemExit(1)
    try:
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        gh.comment_issue(repo, number, body)
        click.secho(f"Commented on issue #{number}", fg='green')
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')
    except Exception as e:
        import subprocess
        if isinstance(e, subprocess.CalledProcessError):
            click.secho(f"gh error: {e}", fg='red')
        else:
            raise


@issues.command('edit', help='Edit an issue via GitHub CLI (gh)')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
@click.option('--title')
@click.option('--body')
@click.option('--add-label', 'add_labels', multiple=True)
@click.option('--remove-label', 'remove_labels', multiple=True)
@click.option('--add-assignee', 'add_assignees', multiple=True)
@click.option('--remove-assignee', 'remove_assignees', multiple=True)
def gh_issue_edit(repo, number, title, body, add_labels, remove_labels, add_assignees, remove_assignees):
    repo = repo or get_repo_from_git_config()
    if not repo:
        click.secho('Could not detect repository. Use --repo.', fg='red')
        raise SystemExit(1)
    try:
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        gh.edit_issue(repo, number, title=title, body=body,
                      add_labels=list(add_labels) or None,
                      remove_labels=list(remove_labels) or None,
                      add_assignees=list(add_assignees) or None,
                      remove_assignees=list(remove_assignees) or None)
        click.secho(f"Edited issue #{number}", fg='green')
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')
    except Exception as e:
        import subprocess
        if isinstance(e, subprocess.CalledProcessError):
            click.secho(f"gh error: {e}", fg='red')
        else:
            raise


@issues.command('label-remove', help='Remove a label from an issue via gh')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
@click.argument('label', nargs=-1)
def gh_issue_label_remove(repo, number, label):
    repo = repo or get_repo_from_git_config()
    if not repo:
        click.secho('Could not detect repository. Use --repo.', fg='red')
        raise SystemExit(1)
    try:
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        for l in label:
            gh.edit_issue(repo, number, remove_labels=[l])
        click.secho(f"Removed labels from issue #{number}", fg='green')
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')
    except Exception as e:
        import subprocess
        if isinstance(e, subprocess.CalledProcessError):
            click.secho(f"gh error: {e}", fg='red')
        else:
            raise


# Labels group (stubs)
@issues.group('labels', help='Manage labels (stubs).')
def labels_group():
    pass


@labels_group.command('list')
def labels_list():
    click.secho('Listing labels is not implemented yet.', fg='yellow')


@labels_group.command('create')
@click.argument('name')
def labels_create(name):
    click.secho(f"Creating label '{name}' is not implemented yet.", fg='yellow')


@labels_group.command('delete')
@click.argument('name')
def labels_delete(name):
    click.secho(f"Deleting label '{name}' is not implemented yet.", fg='yellow')


# Milestones group (stubs)
@issues.group('milestones', help='Manage milestones (stubs).')
def milestones_group():
    pass


@milestones_group.command('list')
def milestones_list():
    click.secho('Listing milestones is not implemented yet.', fg='yellow')


@milestones_group.command('create')
@click.argument('title')
def milestones_create(title):
    click.secho(f"Creating milestone '{title}' is not implemented yet.", fg='yellow')


@milestones_group.command('close')
@click.argument('number')
def milestones_close(number):
    click.secho(f"Closing milestone #{number} is not implemented yet.", fg='yellow')


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
