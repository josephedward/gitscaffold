#!/usr/bin/env python3
"""
import_md: General-purpose script to import issues from an unstructured markdown file.

Usage:
  import_md REPO MARKDOWN_FILE [--heading <level>] [--dry-run] [--token TOKEN]
"""
import os
import sys
import re
import click
from dotenv import load_dotenv, find_dotenv
from github import Github
from github.GithubException import GithubException

load_dotenv(find_dotenv())

@click.command()
@click.argument('repo', metavar='REPO')
@click.argument('file', type=click.Path(exists=True), metavar='MARKDOWN_FILE')
@click.option('--token', help='GitHub token (overrides GITHUB_TOKEN env var)')
@click.option('--dry-run', is_flag=True, help='List issues without creating them')
@click.option('--heading', 'heading', type=int, default=1, show_default=True,
              help='Markdown heading level to split issues (e.g., 1 for "#", 2 for "##")')
def main(repo, file, token, dry_run, heading):
    """Import issues from an unstructured markdown file."""
    token = token or os.getenv('GITHUB_TOKEN')
    if not token:
        click.echo('Error: GitHub token required. Set GITHUB_TOKEN or pass --token.', err=True)
        sys.exit(1)
    try:
        gh = Github(token)
        repo_obj = gh.get_repo(repo)
    except GithubException as e:
        click.echo(f"Error: cannot access repo {repo}: {e}", err=True)
        sys.exit(1)

    # Read and parse markdown into (title, body) pairs
    with open(file, encoding='utf-8') as f:
        lines = f.readlines()
    pattern = re.compile(r'^\s*' + ('#' * heading) + r'\s+(.*)')
    issues = []
    current_title = None
    current_body = []
    for line in lines:
        m = pattern.match(line)
        if m:
            if current_title:
                issues.append((current_title, ''.join(current_body).strip()))
            current_title = m.group(1).strip()
            current_body = []
        else:
            if current_title:
                current_body.append(line)
    if current_title:
        issues.append((current_title, ''.join(current_body).strip()))

    if not issues:
        click.echo('No headings found; nothing to import.', err=True)
        sys.exit(1)

    # Create issues
    for title, body in issues:
        if dry_run:
            click.echo(f"[dry-run] Issue: {title}")
        else:
            try:
                issue = repo_obj.create_issue(title=title, body=body or None)
                click.echo(f"Created issue #{issue.number}: {title}")
            except GithubException as e:
                click.echo(f"Error creating '{title}': {e}", err=True)

if __name__ == '__main__':
    main()