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
    base = os.path.join(os.path.dirname(__file__), 'scripts', 'github_cli.py')
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
    """Initialize a new roadmap YAML file with example structure."""
    example = '''name: My Project
description: Project description
milestones:
  - name: MVP
    due_date: 2025-08-01
  - name: Beta
    due_date: 2025-09-15

features:
  - title: Feature 1
    description: Description of feature 1
    milestone: MVP
    labels: [enhancement, core]
    assignees: [username1]
    tasks:
      - title: Task 1.1
        description: Implementation details
        labels: [enhancement]
      - title: Task 1.2
        description: Testing and validation
        labels: [testing]
'''
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(example)
    click.echo(f'Initialized roadmap file: {output_file}')

if __name__ == '__main__':
    cli()
