#!/usr/bin/env python3
"""
Scaffold: Generalized CLI for GitHub roadmap and enrichment tools.
"""
import os
import sys
import subprocess

# Simple CLI wrapper using click
try:
    import click
except ImportError:
    sys.stderr.write("Error: 'click' package is required. Install with 'pip install click'.\n")
    sys.exit(1)

@click.group()
@click.version_option()
def cli():
    """Scaffold - CLI wrapper for repository scripts."""
    pass

@cli.command()
@click.argument('repo')
@click.option('--phase', default='all', help='Which phase to setup (e.g., phase-1) or "all"')
@click.option('--create-project', is_flag=True, help='Create a GitHub project board')
def setup(repo, phase, create_project):
    """Setup GitHub labels, milestones, and issues based on project plan."""
    # Script lives under the scripts/ directory
    script = os.path.join(os.path.dirname(__file__), 'scripts', 'github_setup.py')
    cmd = [sys.executable, script, '--repo', repo, '--phase', phase]
    if create_project:
        cmd.append('--create-project')
    subprocess.run(cmd, check=True)

@cli.command(name='delete-closed')
@click.argument('repo')
@click.option('--method', type=click.Choice(['graphql', 'rest']), default='graphql',
              help='Method to list closed issues')
@click.option('--dry-run', is_flag=True, help='List closed issues without deleting them')
@click.option('--token', help='GitHub token override')
def delete_closed(repo, method, dry_run, token):
    """Delete all closed issues in a GitHub repository."""
    script_path = os.path.join(os.path.dirname(__file__), 'scripts', 'delete_closed.py')
    cmd = [sys.executable, script_path, '--repo', repo, '--method', method]
    if dry_run:
        cmd.append('--dry-run')
    if token:
        cmd.extend(['--token', token])
    subprocess.run(cmd, check=True)

@cli.command()
@click.argument('repo')
@click.option('--issue', 'issue_number', type=int, help='Issue number to enrich')
@click.option('--batch', is_flag=True, help='Batch enrich all open issues')
@click.option('--path', default='ROADMAP.md', help='Path to roadmap file')
@click.option('--csv', 'csv_file', help='Output CSV file for batch run')
@click.option('--interactive', is_flag=True, help='Interactive approval for batch')
@click.option('--apply', 'apply_changes', is_flag=True, help='Apply updates to issues')
def enrich(repo, issue_number, batch, path, csv_file, interactive, apply_changes):
    """Enrich issues using LLM based on roadmap context."""
    # Enrichment script resides under scripts/
    base = os.path.join(os.path.dirname(__file__), 'scripts', 'enrich.py')
    cmd = [sys.executable, base, '--repo', repo]
    if issue_number is not None:
        cmd.extend(['issue', '--issue', str(issue_number)])
    elif batch:
        cmd.append('batch')
    else:
        sys.stderr.write('Error: specify --issue or --batch.\n')
        sys.exit(1)
    cmd.extend(['--path', path])
    if csv_file:
        cmd.extend(['--csv', csv_file])
    if interactive:
        cmd.append('--interactive')
    if apply_changes:
        cmd.append('--apply')
    subprocess.run(cmd, check=True)

@cli.command()
@click.argument('output_file')
def init(output_file):
    """Initialize a new Markdown roadmap file with example structure."""
    ext = os.path.splitext(output_file)[1].lower()
    if ext not in ('.md', '.markdown'):
        click.echo("Error: init only supports Markdown (.md/.markdown)", err=True)
        sys.exit(1)
    # Markdown template
    example = '''# My Project Roadmap

A brief description of your project roadmap.

# User Authentication
Implement sign-up, login, and password reset flows.

## Task: Design Sign-up Form
Create wireframes for the registration page.

## Task: Implement Backend API
Build authentication endpoints using JWT.

# Reporting Dashboard
Provide analytics and reporting capabilities.

## Task: Define Report Schema
Enumerate fields and filters for reports.

## Task: Build UI Components
Develop charts and tables for the dashboard.
'''
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(example)
    click.echo(f'Initialized roadmap file: {output_file}')
    
@cli.command(name='import-md')
@click.argument('repo')
@click.argument('markdown_file', type=click.Path(exists=True))
@click.option('--token', help='GitHub token override')
@click.option('--openai-key', 'openai_key', help='OpenAI API key override')
@click.option('--dry-run', is_flag=True, help='List issues without creating them')
@click.option('--verbose', '-v', is_flag=True, help='Show progress logs')
@click.option('--heading-level', type=int, help='Markdown heading level to consider for issue creation (e.g., 1 for #, 2 for ##). Passed as --heading to the underlying script.')
# The --apply flag is removed for import-md as it always applies enrichment if not dry-run.
def import_md(repo, markdown_file, token, openai_key, dry_run, verbose, heading_level):
    """Import and enrich issues from an unstructured markdown file via AI."""
    script = os.path.join(os.path.dirname(__file__), 'scripts', 'import_md.py')
    cmd = [sys.executable, script, repo, markdown_file]
    if dry_run:
        cmd.append('--dry-run')
    if verbose:
        cmd.append('--verbose')
    if token:
        cmd.extend(['--token', token])
    if openai_key:
        cmd.extend(['--openai-key', openai_key])
    if heading_level is not None:
        cmd.extend(['--heading', str(heading_level)])
    subprocess.run(cmd, check=True)

if __name__ == '__main__':
    cli()
