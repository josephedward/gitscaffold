import click


@click.group(name='api', help='Manage the API server lifecycle.')
def api():
    pass


try:
    from scaffold.cli import start_api as legacy_start_api_cmd  # type: ignore
    api.add_command(legacy_start_api_cmd, name='start')
except Exception:
    pass

@api.command(name='status')
def api_status():
    """Report API status (stub)."""
    click.secho('API status: not implemented yet', fg='yellow')

@api.command(name='stop')
def api_stop():
    """Stop API (stub)."""
    click.secho('API stop: not implemented yet', fg='yellow')
