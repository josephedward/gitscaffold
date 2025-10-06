import click
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

CONFIG_FILE_NAME = ".gitscaffold-worktree.yml"

def _get_config_path() -> Path:
    return Path.cwd() / CONFIG_FILE_NAME

def _load_config() -> Dict[str, Any]:
    config_path = _get_config_path()
    if not config_path.exists():
        return {}
    with open(config_path, 'r') as f:
        return yaml.safe_load(f) or {}

def _save_config(config: Dict[str, Any]):
    config_path = _get_config_path()
    with open(config_path, 'w') as f:
        yaml.dump(config, f, indent=2)

def init_config():
    """Initializes a new .gitscaffold-worktree.yml config file."""
    config_path = _get_config_path()
    if config_path.exists():
        click.secho(f"Config file '{CONFIG_FILE_NAME}' already exists.", fg='yellow')
        return

    default_config = {
        "worktree": {
            "base_path": "../worktrees",
            "post_create_hooks": [
                {
                    "type": "copy",
                    "from": ".env.example",
                    "to": ".env"
                },
                {
                    "type": "command",
                    "command": "npm install"
                }
            ]
        },
        "agents": {
            "aider": {
                "command": "aider",
                "auto_start": True
            },
            "cursor": {
                "command": "cursor .",
                "auto_start": False
            }
        }
    }
    _save_config(default_config)
    click.secho(f"Initialized default config file: '{CONFIG_FILE_NAME}'.", fg='green')

def show_config():
    """Displays the current .gitscaffold-worktree.yml config."""
    config = _load_config()
    if not config:
        click.secho(f"Config file '{CONFIG_FILE_NAME}' not found. Run 'gitscaffold source worktree config init'.", fg='yellow')
        return
    click.echo(yaml.dump(config, indent=2))

def list_templates():
    """Lists available post-create hook templates (currently hardcoded examples)."""
    click.secho("Available post-create hook templates:", fg='cyan')
    click.echo("  - default: Copies .env.example and runs npm install.")
    click.echo("  - python-venv: Creates a Python virtual environment and installs requirements.")
    click.echo("  - custom-script: Runs a custom shell script.")
