import os
import sys
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv, set_key, dotenv_values


def get_global_config_path() -> Path:
    """Return path to global config file (~/.gitscaffold/config). Ensures dir exists with 0700 perms.

    Note: Permission enforcement on the file is best-effort and only applied on POSIX.
    """
    config_dir = Path.home() / ".gitscaffold"
    # Create with secure permissions where applicable
    config_dir.mkdir(mode=0o700, exist_ok=True)
    return config_dir / "config"


def _set_secure_file_permissions(path: Path) -> None:
    if os.name != "nt":
        try:
            os.chmod(path, 0o600)
        except Exception:
            # Best-effort; do not fail if chmod is not permitted
            pass


def set_global_config_key(key: str, value: str) -> None:
    """Set a key in the global config, normalizing quotes and securing permissions."""
    config_path = get_global_config_path()
    set_key(str(config_path), key, value)
    # Normalize quoting to double quotes for consistency
    try:
        text = config_path.read_text(encoding="utf-8")
        old = f"{key}='{value}'"
        new = f'{key}="{value}"'
        if old in text:
            config_path.write_text(text.replace(old, new), encoding="utf-8")
    except Exception:
        pass
    _set_secure_file_permissions(config_path)


def load_env(local_first: bool = True) -> None:
    """Load environment from .env and then from global config (without overriding existing env).

    Mirrors current CLI behavior: load local .env, then global config.
    """
    # Load local .env
    load_dotenv(override=False)
    # Load global config
    global_config_path = get_global_config_path()
    if global_config_path.exists():
        load_dotenv(dotenv_path=global_config_path, override=False)


def _is_interactive() -> bool:
    try:
        return sys.stdin.isatty()
    except Exception:
        return False


def _get_secret(
    env_var: str,
    prompt_label: str,
    config_key: Optional[str] = None,
    noninteractive: bool = False,
) -> str:
    """Retrieve a secret from env or global config, or prompt if interactive.

    - If present in environment, return it.
    - Else attempt to read from global config.
    - Else if interactive and not noninteractive, prompt and persist to global config.
    - Else raise RuntimeError.
    """
    # Load environment/config (idempotent)
    load_env()

    # 1) Environment variable
    value = os.getenv(env_var)
    if value:
        return value

    # 2) Global config
    config_path = get_global_config_path()
    if config_path.exists():
        vals = dotenv_values(config_path)
        if env_var in vals and vals[env_var]:
            return vals[env_var]  # type: ignore[return-value]

    # 3) Prompt if allowed
    if not noninteractive and _is_interactive():
        import click

        value = click.prompt(prompt_label, hide_input=True)
        if config_key is None:
            config_key = env_var
        set_global_config_key(config_key, value)
        os.environ[env_var] = value
        return value

    raise RuntimeError(f"Missing required secret: {env_var}; set it in env or global config.")


def get_github_token(noninteractive: bool = False) -> str:
    return _get_secret(
        env_var="GITHUB_TOKEN",
        prompt_label="Please enter your GitHub Personal Access Token (PAT)",
        config_key="GITHUB_TOKEN",
        noninteractive=noninteractive,
    )


def get_openai_api_key(noninteractive: bool = False) -> str:
    return _get_secret(
        env_var="OPENAI_API_KEY",
        prompt_label="Please enter your OpenAI API key",
        config_key="OPENAI_API_KEY",
        noninteractive=noninteractive,
    )


def get_gemini_api_key(noninteractive: bool = False) -> str:
    return _get_secret(
        env_var="GEMINI_API_KEY",
        prompt_label="Please enter your Google Gemini API key",
        config_key="GEMINI_API_KEY",
        noninteractive=noninteractive,
    )

