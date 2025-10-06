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


@click.group(name='settings', help='Manage config, tokens, install/uninstall.')
def settings_group():
    pass


@settings_group.group(name='config', help='Manage global configuration and secrets.')
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


# AI provider settings (keys + default provider)
@settings_group.group('ai', help='Manage AI providers and API keys.')
def settings_ai():
    pass


def _mask(val: str) -> str:
    if not val:
        return ''
    if len(val) <= 6:
        return '*' * len(val)
    return val[:3] + '*' * (len(val) - 6) + val[-3:]


@settings_ai.command('list')
def ai_list():
    import os
    from scaffold.core.config import get_default_ai_provider
    prov = get_default_ai_provider() or '(not set)'
    keys = {
        'openai': os.getenv('OPENAI_API_KEY'),
        'gemini': os.getenv('GEMINI_API_KEY'),
        'perplexity': os.getenv('PERPLEXITY_API_KEY'),
        'openrouter': os.getenv('OPENROUTER_API_KEY'),
    }
    click.secho(f"Default provider: {prov}", fg='cyan')
    for name, val in keys.items():
        click.echo(f"- {name}: {'configured ' + _mask(val) if val else 'not set'}")


@settings_ai.command('set')
@click.option('--provider', type=click.Choice(['openai','gemini','perplexity','openrouter']), required=True)
@click.option('--key', help='API key value (if omitted, prompts)')
def ai_set(provider, key):
    from scaffold.core.config import set_global_config_key
    if not key:
        key = click.prompt(f'Enter {provider} API key', hide_input=True)
    env_key = {
        'openai': 'OPENAI_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'perplexity': 'PERPLEXITY_API_KEY',
        'openrouter': 'OPENROUTER_API_KEY',
    }[provider]
    set_global_config_key(env_key, key)
    click.secho(f"Saved {provider} key.", fg='green')


@settings_ai.command('get')
@click.option('--provider', type=click.Choice(['openai','gemini','perplexity','openrouter']), required=True)
@click.option('--show', is_flag=True, help='Show full key (unsafe)')
def ai_get(provider, show):
    import os
    env_key = {
        'openai': 'OPENAI_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'perplexity': 'PERPLEXITY_API_KEY',
        'openrouter': 'OPENROUTER_API_KEY',
    }[provider]
    val = os.getenv(env_key)
    if not val:
        click.secho(f"No key found for {provider}", fg='yellow')
        return
    click.echo(val if show else _mask(val))


@settings_ai.command('remove')
@click.option('--provider', type=click.Choice(['openai','gemini','perplexity','openrouter']), required=True)
def ai_remove(provider):
    from scaffold.core.config import remove_global_config_key
    env_key = {
        'openai': 'OPENAI_API_KEY',
        'gemini': 'GEMINI_API_KEY',
        'perplexity': 'PERPLEXITY_API_KEY',
        'openrouter': 'OPENROUTER_API_KEY',
    }[provider]
    removed = remove_global_config_key(env_key)
    if removed:
        click.secho(f"Removed {provider} key.", fg='green')
    else:
        click.secho(f"No {provider} key to remove.", fg='yellow')


@settings_ai.command('use')
@click.option('--provider', type=click.Choice(['openai','gemini','perplexity','openrouter']), required=True)
def ai_use(provider):
    from scaffold.core.config import set_default_ai_provider
    set_default_ai_provider(provider)


@settings_ai.command('show')
def ai_show():
    from scaffold.core.config import get_default_ai_provider
    prov = get_default_ai_provider() or '(not set)'
    click.secho(f"Default provider: {prov}", fg='cyan')
