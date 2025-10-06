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
