import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Optional

import click

try:
    from dotenv import load_dotenv, set_key, unset_key
except ImportError:  # pragma: no cover - fallback when dotenv missing
    def load_dotenv(*args, **kwargs):
        return False
    def set_key(path, key, value):
        raise click.ClickException(
            "python-dotenv is required to save tokens to .env files. "
            "Install it or set tokens via environment variables."
        )
    def unset_key(path, key):
        raise click.ClickException(
            "python-dotenv is required to remove tokens from .env files. "
            "Install it or set tokens via environment variables."
        )


def get_global_config_path() -> Path:
    """Returns the path to the global config file, creating parent dir if needed."""
    config_dir = Path.home() / '.gitscaffold'
    config_dir.mkdir(mode=0o700, exist_ok=True)
    return config_dir / 'config'


def set_global_config_key(key: str, value: str) -> None:
    """Sets a key-value pair in the global config file with secure permissions."""
    config_path = get_global_config_path()
    set_key(str(config_path), key, value)
    try:
        text = config_path.read_text(encoding='utf-8')
        old = f"{key}='{value}'"
        new = f'{key}="{value}"'
        if old in text:
            text = text.replace(old, new)
            config_path.write_text(text, encoding='utf-8')
    except Exception:
        pass
    if os.name != 'nt':
        os.chmod(config_path, 0o600)


def remove_global_config_key(key: str) -> bool:
    """Remove a key from the global config; returns True if removed."""
    config_path = get_global_config_path()
    removed, _ = unset_key(str(config_path), key)
    return bool(removed)


def get_repo_from_git_config() -> Optional[str]:
    """Retrieves the 'owner/repo' from the git config."""
    logging.info("Attempting to get repository from git config.")
    try:
        url = subprocess.check_output(
            ['git', 'config', '--get', 'remote.origin.url'],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        logging.info(f"Found git remote URL: {url}")

        ssh_match = re.search(r'github\.com:([^/]+/[^/]+?)(\.git)?$', url)
        if ssh_match:
            return ssh_match.group(1)

        https_match = re.search(r'(?:www\.)?github\.com/([^/]+/[^/]+?)(\.git)?$', url)
        if https_match:
            return https_match.group(1)
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def get_github_token() -> str:
    """Retrieve GitHub token or prompt and persist globally."""
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        logging.warning("GitHub PAT not found in environment or config files.")
        token = click.prompt('Please enter your GitHub Personal Access Token (PAT)', hide_input=True)
        set_global_config_key('GITHUB_TOKEN', token)
        click.secho("GitHub PAT saved to global config file.", fg="green")
        os.environ['GITHUB_TOKEN'] = token
    return token


def get_openai_api_key() -> str:
    """Retrieve OpenAI API key or prompt and persist globally."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        logging.warning("OPENAI_API_KEY not found in environment or config files.")
        api_key = click.prompt('Please enter your OpenAI API key', hide_input=True)
        set_global_config_key('OPENAI_API_KEY', api_key)
        click.secho("OpenAI API key saved to global config file.", fg="green")
        os.environ['OPENAI_API_KEY'] = api_key
    return api_key


def get_gemini_api_key() -> str:
    """Retrieve Google Gemini API key or prompt and persist globally."""
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        logging.warning("GEMINI_API_KEY not found in environment or config files.")
        api_key = click.prompt('Please enter your Google Gemini API key', hide_input=True)
        set_global_config_key('GEMINI_API_KEY', api_key)
        click.secho("Google Gemini API key saved to global config file.", fg="green")
        os.environ['GEMINI_API_KEY'] = api_key
    return api_key
