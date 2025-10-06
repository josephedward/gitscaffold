import sys
import click
from rich.console import Console
from rich.table import Table

from scaffold.core.config import (
    get_global_config_path,
    set_global_config_key,
    remove_global_config_key,
)

try:
    from dotenv import dotenv_values
except ImportError:  # pragma: no cover
    dotenv_values = None


@click.group(name='config', help='Manage global configuration and secrets.')
def config():
    """Manages global configuration stored in a file like ~/.gitscaffold/config."""
    pass


@config.command('set', help='Set a configuration key-value pair.')
@click.argument('key')
@click.argument('value')
def config_set(key, value):
    set_global_config_key(key.upper(), value)
    config_path = get_global_config_path()
    click.secho(f"Set {key.upper()} in {config_path}", fg="green")


@config.command('get', help='Get a configuration value.')
@click.argument('key')
def config_get(key):
    if dotenv_values is None:
        click.secho("python-dotenv is required to read config files.", fg="red", err=True)
        sys.exit(1)

    config_path = get_global_config_path()
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
    if dotenv_values is None:
        click.secho("python-dotenv is required to read config files.", fg="red", err=True)
        sys.exit(1)

    config_path = get_global_config_path()
    if not config_path.exists():
        click.secho(f"Config file not found: {config_path}", fg="yellow")
        return

    values = dotenv_values(config_path)
    if not values:
        click.echo("Config file is empty.")
        return

    table = Table(title=f"Global Configuration ({config_path})")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="magenta")
    for k, v in values.items():
        table.add_row(k, v)
    console = Console()
    console.print(table)


@config.command('path', help='Show path to the global config file.')
def config_path_command():
    click.echo(get_global_config_path())


@config.command('remove', help='Remove a configuration key.')
@click.argument('key')
def config_remove(key):
    removed = remove_global_config_key(key.upper())
    config_path = get_global_config_path()
    if removed:
        click.secho(f"Removed {key.upper()} from {config_path}", fg="green")
    else:
        click.secho(f"Key '{key.upper()}' not found in {config_path}", fg="yellow")

