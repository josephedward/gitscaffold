#!/usr/bin/env python3
"""
Example CLI wrapper for GitScaffold scripts.

This minimal click-based wrapper shows how you can invoke
the built-in scripts in the `scripts/` directory.
"""
import os
import sys
import subprocess

try:
    import click
except ImportError:
    sys.stderr.write("Error: 'click' package is required. Install with 'pip install click'.\n")
    sys.exit(1)

@click.group()
@click.version_option()
def cli():
    """GitScaffold: CLI wrapper for repository scripts."""
    pass

@cli.command()
@click.argument('repo')
@click.option('--phase', default='all', help='Which phase to setup (e.g., phase-1) or "all"')
@click.option('--create-project', is_flag=True, help='Create a GitHub project board')
def setup(repo, phase, create_project):
    """Setup GitHub labels, milestones, and issues based on project plan."""
    script = os.path.join(os.path.dirname(__file__), 'github_roadmap_setup.py')
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
    script = os.path.join(os.path.dirname(__file__), 'delete_closed.py')
    cmd = [sys.executable, script, '--repo', repo, '--method', method]
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
    """Enrich issues using AI based on roadmap context."""
    script = os.path.join(os.path.dirname(__file__), 'enrich.py')
    cmd = [sys.executable, script, '--repo', repo]
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

if __name__ == '__main__':
    cli()