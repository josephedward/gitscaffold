import click


@click.group(name='source', help='Source control operations for your repo.')
def source():
    pass


try:
    from scaffold.cli import ops_delete_branches as legacy_delete_branches_cmd  # type: ignore
    source.add_command(legacy_delete_branches_cmd, name='delete-branches')
except Exception:
    pass
try:
    from scaffold.cli import ops_remove_from_git as legacy_remove_from_git_cmd  # type: ignore
    source.add_command(legacy_remove_from_git_cmd, name='remove-from-git')
except Exception:
    pass


# --- Worktree management ---
@source.group('worktree', help='Manage Git worktrees for parallel branch work.')
def worktree():
    """Git worktree helpers (add/list/remove/prune)."""
    pass


@worktree.command('add')
@click.argument('branch')
@click.option('--path', 'path_', help='Custom path for the worktree')
@click.option('--new', 'create_new', is_flag=True, help='Create a new branch at current HEAD')
def wt_add(branch, path_, create_new):
    from scaffold.core.worktree import add_worktree
    add_worktree(branch=branch, path_override=path_, create_new=create_new)


@worktree.command('list')
def wt_list():
    from scaffold.core.worktree import list_worktrees
    rows = list_worktrees()
    if not rows:
        click.echo('No worktrees found.')
        return
    for r in rows:
        branch = r.get('branch') or '(detached)'
        click.echo(f"{r['path']}\t{r['hash']}\t{branch}")


@worktree.command('remove')
@click.argument('branch_or_path')
@click.option('--with-branch', is_flag=True, help='Also delete the local branch')
def wt_remove(branch_or_path, with_branch):
    from scaffold.core.worktree import remove_worktree
    remove_worktree(branch_or_path=branch_or_path, delete_branch=with_branch)


@worktree.command('prune')
def wt_prune():
    from scaffold.core.worktree import prune_worktrees
    prune_worktrees()


# Worktree config commands
@worktree.group('config', help='Manage worktree configuration.')
def wt_config():
    pass

@wt_config.command('init', help='Initialize a .gitscaffold-worktree.yml config file.')
def wt_config_init():
    from scaffold.core.worktree_config import init_config
    init_config()

@wt_config.command('show', help='Display the current worktree configuration.')
def wt_config_show():
    from scaffold.core.worktree_config import show_config
    show_config()

@wt_config.command('template-list', help='List available post-create hook templates.')
def wt_config_template_list():
    from scaffold.core.worktree_config import list_templates
    list_templates()


# Agents integration stubs under worktree
@worktree.group('agents', help='Multi-agent helpers for worktrees.')
def wt_agents():
    pass


@wt_agents.command('setup')
@click.option('--branches', help='Comma-separated list of branches to prepare')
def wt_agents_setup(branches):
    from scaffold.core.worktree_agents import setup_agents
    setup_agents(branches=branches)


@wt_agents.command('start')
@click.argument('branch')
@click.option('--agent', type=click.Choice(['aider','cursor','claude']), default='aider')
def wt_agents_start(branch, agent):
    from scaffold.core.worktree_agents import start_agent
    start_agent(branch=branch, agent_name=agent)


@wt_agents.command('status')
def wt_agents_status():
    from scaffold.core.worktree_agents import agent_status
    agent_status()


@wt_agents.command('kill')
@click.argument('branch')
def wt_agents_kill(branch):
    from scaffold.core.worktree_agents import kill_agent
    kill_agent(branch=branch)
