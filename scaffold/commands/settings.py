import click
import os
from scaffold.github_cli import GitHubCLI

@click.group(name='settings', help='Manage config, tokens, install/uninstall.')
def settings_group():
    pass

@settings_group.command('doctor', help='Diagnose common issues with gitscaffold setup.')
def doctor():
    click.echo("Running gitscaffold doctor...")

    # 1. Check for gh executable
    try:
        gh_cli = GitHubCLI()
        click.echo(f"✅ gh executable found at: {gh_cli.gh}")
    except FileNotFoundError:
        click.secho("❌ gh executable not found.", fg='red')
        click.echo("   Suggestion: Run 'gitscaffold gh install' to bootstrap it.")
        return # Exit early if gh is not found

    # 2. Check gh auth status
    try:
        result = gh_cli._run(["auth", "status"], check=False, capture=True)
        if result.returncode == 0:
            click.echo("✅ gh authentication status: OK")
        else:
            click.secho("❌ gh authentication status: FAILED", fg='red')
            click.echo("   Suggestion: Run 'gh auth login' to authenticate with GitHub.")
    except Exception as e:
        click.secho(f"❌ Error checking gh auth status: {e}", fg='red')

    # 3. Check GITHUB_TOKEN environment variable
    if os.getenv('GITHUB_TOKEN'):
        click.echo("✅ GITHUB_TOKEN environment variable is set.")
    else:
        click.secho("❌ GITHUB_TOKEN environment variable is NOT set.", fg='red')
        click.echo("   Suggestion: Set the GITHUB_TOKEN environment variable for API access.")

    # 4. Check optional AI keys (placeholder)
    click.echo("ℹ️ Checking for optional AI keys (e.g., OPENAI_API_KEY, GEMINI_API_KEY) - [Not yet implemented]")
    # TODO: Implement checks for specific AI keys if needed

    click.echo("Doctor check complete.")