import click


@click.group(name='roadmap', help='Manipulate, sync, or diff roadmap files.')
def roadmap():
    pass


# Register legacy commands if available
try:
    from scaffold.cli import sync as legacy_sync_cmd  # type: ignore
    roadmap.add_command(legacy_sync_cmd, name='sync')
except Exception:
    pass
try:
    from scaffold.cli import diff as legacy_diff_cmd  # type: ignore
    roadmap.add_command(legacy_diff_cmd, name='diff')
except Exception:
    pass
try:
    from scaffold.cli import import_md as legacy_import_md_cmd  # type: ignore
    roadmap.add_command(legacy_import_md_cmd, name='import')
except Exception:
    pass
