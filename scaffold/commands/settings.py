import os
import sys
import time
import getpass
import click
from rich.console import Console
from rich.table import Table

from scaffold.core.config import (
    get_global_config_path,
    set_global_config_key,
    remove_global_config_key,
)

try:
    from dotenv import dotenv_values, set_key
except ImportError:  # pragma: no cover
    dotenv_values = None
    def set_key(path, key, value):  # type: ignore
        raise RuntimeError("python-dotenv is required for settings management")

# Optional color output (fallback to no color if unavailable)
try:  # pragma: no cover
    from colorama import Fore, Style, init as colorama_init
    colorama_init(autoreset=True)
except Exception:  # pragma: no cover
    class Fore:  # type: ignore
        RED = GREEN = CYAN = ''
    class Style:  # type: ignore
        BRIGHT = RESET_ALL = ''


@click.group(name='settings', help='Manage config, tokens, install/uninstall.')
def settings():
    pass


@settings.group(name='config', help='Manage global configuration and secrets.')
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


# --- Kubelingo-style AI key management (copied logic) ---
def _env_or_cfg(name: str, cfg: dict) -> str:
    return (os.getenv(name) or cfg.get(name) or '').strip()


def test_api_keys() -> dict:
    """Offline heuristic checks for AI API keys (no network calls).

    Copied from kubelingo with minimal adaptation. It validates only basic
    key patterns to avoid false negatives in restricted environments.
    """
    if dotenv_values is None:
        return {"gemini": False, "openai": False, "openrouter": False, "perplexity": False}

    # Prefer a repo-local .env; fallback to CWD .env
    try:
        project_root = os.getcwd()
        env_path = os.path.join(project_root, '.env')
        if os.path.exists(env_path):
            cfg = dotenv_values(env_path)  # type: ignore
        else:
            cfg = dotenv_values()  # type: ignore
    except Exception:
        cfg = dotenv_values()  # type: ignore

    assume_valid = os.getenv("KUBELINGO_ASSUME_KEYS_VALID", "false").lower() in ("1", "true", "yes")

    def has_value(name: str) -> bool:
        v = _env_or_cfg(name, cfg)
        return bool(v)

    if assume_valid:
        return {
            "gemini": has_value("GEMINI_API_KEY"),
            "openai": has_value("OPENAI_API_KEY"),
            "openrouter": has_value("OPENROUTER_API_KEY"),
            "perplexity": has_value("PERPLEXITY_API_KEY"),
        }

    gk = _env_or_cfg("GEMINI_API_KEY", cfg)
    ok = _env_or_cfg("OPENAI_API_KEY", cfg)
    ork = _env_or_cfg("OPENROUTER_API_KEY", cfg)
    pk = _env_or_cfg("PERPLEXITY_API_KEY", cfg)

    # Lightweight pattern checks (non-exhaustive)
    gemini_ok = gk.startswith("AIza") and len(gk) >= 20 if gk else False
    openai_ok = ok.startswith("sk-") and len(ok) >= 20 if ok else False
    openrouter_ok = ork.startswith("sk-or-") and len(ork) >= 20 if ork else False
    perplexity_ok = pk.startswith("pplx-") and len(pk) >= 15 if pk else False

    return {
        "gemini": gemini_ok,
        "openai": openai_ok,
        "openrouter": openrouter_ok,
        "perplexity": perplexity_ok,
    }


def _current_provider() -> str:
    prov = os.getenv('KUBELINGO_LLM_PROVIDER', '').strip()
    if prov:
        return prov
    try:
        cfg = dotenv_values() if dotenv_values else {}
        prov = (cfg.get('KUBELINGO_LLM_PROVIDER', '') or '').strip()  # type: ignore
        return prov
    except Exception:
        return ''


def handle_keys_menu():
    """Interactive menu to set AI API keys and provider (kubelingo parity)."""
    statuses = test_api_keys()
    if not any(statuses.values()):
        print(f"{Fore.RED}Warning: No valid API keys found. Without a valid API key, some AI features will be limited.{Style.RESET_ALL}")

    cfg = dotenv_values() if dotenv_values else {}
    gemini_key = (cfg.get("GEMINI_API_KEY") or "Not Set") if cfg else "Not Set"  # type: ignore
    openai_key = (cfg.get("OPENAI_API_KEY") or "Not Set") if cfg else "Not Set"  # type: ignore
    openrouter_key = (cfg.get("OPENROUTER_API_KEY") or "Not Set") if cfg else "Not Set"  # type: ignore
    perplexity_key = (cfg.get("PERPLEXITY_API_KEY") or "Not Set") if cfg else "Not Set"  # type: ignore

    gemini_disp = f"{Fore.GREEN}****{str(gemini_key)[-4:]} (Valid){Style.RESET_ALL}" if statuses.get("gemini") else f"{Fore.RED}****{str(gemini_key)[-4:]} (Invalid){Style.RESET_ALL}"
    openai_disp = f"{Fore.GREEN}****{str(openai_key)[-4:]} (Valid){Style.RESET_ALL}" if statuses.get("openai") else f"{Fore.RED}****{str(openai_key)[-4:]} (Invalid){Style.RESET_ALL}"
    openrouter_disp = f"{Fore.GREEN}****{str(openrouter_key)[-4:]} (Valid){Style.RESET_ALL}" if statuses.get("openrouter") else f"{Fore.RED}****{str(openrouter_key)[-4:]} (Invalid){Style.RESET_ALL}"
    perplexity_disp = f"{Fore.GREEN}****{str(perplexity_key)[-4:]} (Valid){Style.RESET_ALL}" if statuses.get("perplexity") else f"{Fore.RED}****{str(perplexity_key)[-4:]} (Invalid){Style.RESET_ALL}"

    print(f"\n{Style.BRIGHT}{Fore.CYAN}--- API Key Configuration ---{Style.RESET_ALL}")
    print(f"  1. Set Gemini API Key (current: {gemini_disp}) (Model: gemini-1.5-flash-latest)")
    print(f"  2. Set OpenAI API Key (current: {openai_disp}) (Model: gpt-3.5-turbo)")
    print(f"  3. Set OpenRouter API Key (current: {openrouter_disp}) (Model: deepseek/deepseek-r1-0528:free)")
    print(f"  4. Set Perplexity API Key (current: {perplexity_disp}) (Model: sonar-medium-online)")

    provider = _current_provider()
    prov_disp = f"{Fore.GREEN}{provider}{Style.RESET_ALL}" if provider else f"{Fore.RED}None{Style.RESET_ALL}"
    print(f"\n{Style.BRIGHT}{Fore.CYAN}--- AI Provider Selection ---{Style.RESET_ALL}")
    print(f"  5. Choose AI Provider (current: {prov_disp})")
    print(f"  6. Back")

    while True:
        choice = input("Enter your choice: ").strip()
        if choice == '1':
            key = getpass.getpass("Enter your Gemini API Key: ").strip()
            if key:
                set_key(".env", "GEMINI_API_KEY", key)
                os.environ["GEMINI_API_KEY"] = key
                print("\nGemini API Key saved.")
            else:
                print("\nNo key entered.")
            time.sleep(1)
            break
        elif choice == '2':
            key = input("Enter your OpenAI API Key: ").strip()
            if key:
                set_key(".env", "OPENAI_API_KEY", key)
                os.environ["OPENAI_API_KEY"] = key
                print("\nOpenAI API Key saved.")
            else:
                print("\nNo key entered.")
            time.sleep(1)
            break
        elif choice == '3':
            key = input("Enter your OpenRouter API Key: ").strip()
            if key:
                set_key(".env", "OPENROUTER_API_KEY", key)
                os.environ["OPENROUTER_API_KEY"] = key
                print("\nOpenRouter API Key saved.")
            else:
                print("\nNo key entered.")
            time.sleep(1)
            break
        elif choice == '4':
            key = input("Enter your Perplexity API Key: ").strip()
            if key:
                set_key(".env", "PERPLEXITY_API_KEY", key)
                os.environ["PERPLEXITY_API_KEY"] = key
                print("\nPerplexity API Key saved.")
            else:
                print("\nNo key entered.")
            time.sleep(1)
            break
        elif choice == '5':
            print("\nSelect AI Provider:")
            print("  1. openrouter")
            print("  2. gemini")
            print("  3. openai")
            print("  4. perplexity")
            print("  5. none (disable AI)")
            sub = input("Enter your choice: ").strip()
            mapping = {'1': 'openrouter', '2': 'gemini', '3': 'openai', '4': 'perplexity', '5': ''}
            if sub in mapping:
                sel = mapping[sub]
                set_key(".env", "KUBELINGO_LLM_PROVIDER", sel)
                os.environ["KUBELINGO_LLM_PROVIDER"] = sel
                print(f"\nAI Provider set to {sel or 'none'}.")
            else:
                print("\nInvalid selection.")
            time.sleep(1)
            break
        elif choice == '6':
            return
        else:
            print("Invalid choice. Please try again.")
            time.sleep(1)


@settings.command('ai', help='Configure AI API keys and provider (interactive).')
def settings_ai():
    """Launch interactive menu to manage OpenAI, Gemini, OpenRouter, Perplexity keys and provider."""
    try:
        handle_keys_menu()
    except RuntimeError as e:
        click.secho(str(e), fg='red')
