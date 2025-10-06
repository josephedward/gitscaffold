import click


@click.group(name='ci', help='CI/CD and GitHub tooling integration.')
def ci():
    pass


# Mount gh helpers and a local runner when available
try:
    from scaffold.cli import gh_group as legacy_gh_group  # type: ignore
    ci.add_command(legacy_gh_group, name='gh')
except Exception:
    pass


# Pull Requests (PR) helpers via gh
@ci.group('prs', help='Manage pull requests via gh')
def prs():
    pass


@prs.command('list')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.option('--state', type=click.Choice(['open','closed','all']), default='open', show_default=True)
@click.option('--limit', default=30, show_default=True)
def prs_list(repo, state, limit):
    try:
        from scaffold.core.config import get_repo_from_git_config
        repo = repo or get_repo_from_git_config()
        if not repo:
            click.secho('Could not detect repository. Use --repo.', fg='red')
            raise SystemExit(1)
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        prs = gh.list_prs(repo, state=state, limit=limit)
        if not prs:
            click.echo('No pull requests found.')
            return
        for pr in prs:
            click.echo(f"#{pr['number']} [{pr['state']}] {pr['title']}")
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')


@prs.command('view')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
def prs_view(repo, number):
    try:
        from scaffold.core.config import get_repo_from_git_config
        repo = repo or get_repo_from_git_config()
        if not repo:
            click.secho('Could not detect repository. Use --repo.', fg='red')
            raise SystemExit(1)
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        data = gh.pr_view(repo, number)
        title = data.get('title','')
        url = data.get('url','')
        click.echo(f"PR #{number}: {title}\n{url}")
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')


@prs.command('comment')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
@click.argument('body')
def prs_comment(repo, number, body):
    try:
        from scaffold.core.config import get_repo_from_git_config
        repo = repo or get_repo_from_git_config()
        if not repo:
            click.secho('Could not detect repository. Use --repo.', fg='red')
            raise SystemExit(1)
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        gh.pr_comment(repo, number, body)
        click.secho(f"Commented on PR #{number}", fg='green')
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')


@prs.command('label-add')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
@click.argument('label', nargs=-1)
def prs_label_add(repo, number, label):
    try:
        from scaffold.core.config import get_repo_from_git_config
        repo = repo or get_repo_from_git_config()
        if not repo:
            click.secho('Could not detect repository. Use --repo.', fg='red')
            raise SystemExit(1)
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        gh.pr_add_labels(repo, number, list(label))
        click.secho(f"Added labels to PR #{number}", fg='green')
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')


@prs.command('edit')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
@click.option('--body', required=True)
def prs_edit(repo, number, body):
    try:
        from scaffold.core.config import get_repo_from_git_config
        repo = repo or get_repo_from_git_config()
        if not repo:
            click.secho('Could not detect repository. Use --repo.', fg='red')
            raise SystemExit(1)
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        gh.edit_pr(repo, number, body)
        click.secho(f"Edited PR #{number}", fg='green')
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')


@prs.command('merge')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('number', type=int)
@click.option('--merge', 'merge_opt', is_flag=True, help='Use merge strategy')
@click.option('--squash', is_flag=True, help='Use squash strategy')
@click.option('--rebase', is_flag=True, help='Use rebase strategy')
@click.option('--delete-branch', is_flag=True, help='Delete branch after merge')
@click.option('--admin', is_flag=True, help='Use admin privileges, if authorized')
def prs_merge(repo, number, merge_opt, squash, rebase, delete_branch, admin):
    try:
        from scaffold.core.config import get_repo_from_git_config
        repo = repo or get_repo_from_git_config()
        if not repo:
            click.secho('Could not detect repository. Use --repo.', fg='red')
            raise SystemExit(1)
        from scaffold.github_cli import GitHubCLI
        gh = GitHubCLI()
        gh.pr_merge(repo, number, merge=merge_opt, squash=squash, rebase=rebase,
                    delete_branch=delete_branch, admin=admin)
        click.secho(f"Merged PR #{number}", fg='green')
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')
try:
    from scaffold.cli import run_action_locally as legacy_run_action_locally_cmd  # type: ignore
    ci.add_command(legacy_run_action_locally_cmd, name='run-local')
except Exception:
    pass


# Workflows via gh
@ci.group('workflows', help='GitHub Actions workflows via gh')
def workflows():
    pass


@workflows.command('list')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.option('--limit', default=50, show_default=True)
def workflows_list(repo, limit):
    try:
        from scaffold.core.config import get_repo_from_git_config
        from scaffold.github_cli import GitHubCLI
        repo = repo or get_repo_from_git_config()
        if not repo:
            click.secho('Could not detect repository. Use --repo.', fg='red')
            raise SystemExit(1)
        gh = GitHubCLI()
        items = gh.list_workflows(repo, limit=limit)
        if not items:
            click.echo('No workflows found.')
            return
        for w in items:
            click.echo(f"{w['id']}\t{w['name']} [{w['state']}]")
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')


@workflows.command('run')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.argument('workflow_id')
@click.option('--ref', default='main', show_default=True)
@click.option('-f', '--input', 'inputs', multiple=True, help='key=value input')
def workflows_run(repo, workflow_id, ref, inputs):
    try:
        from scaffold.core.config import get_repo_from_git_config
        from scaffold.github_cli import GitHubCLI
        repo = repo or get_repo_from_git_config()
        if not repo:
            click.secho('Could not detect repository. Use --repo.', fg='red')
            raise SystemExit(1)
        gh = GitHubCLI()
        inputs_dict = {}
        for kv in inputs:
            if '=' in kv:
                k, v = kv.split('=', 1)
                inputs_dict[k] = v
        out = gh.run_workflow(repo, workflow_id, ref=ref, inputs=inputs_dict or None)
        click.echo(out)
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')


@workflows.command('status')
@click.option('--repo', help='owner/repo. Defaults to current git remote.')
@click.option('--run-id', required=True)
def workflows_status(repo, run_id):
    try:
        from scaffold.core.config import get_repo_from_git_config
        from scaffold.github_cli import GitHubCLI
        repo = repo or get_repo_from_git_config()
        if not repo:
            click.secho('Could not detect repository. Use --repo.', fg='red')
            raise SystemExit(1)
        gh = GitHubCLI()
        out = gh.workflow_status(repo, run_id)
        click.echo(out)
    except FileNotFoundError as e:
        click.secho(str(e), fg='yellow')
