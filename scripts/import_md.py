#!/usr/bin/env python3
"""
import_md: General-purpose script to import issues from an unstructured markdown file.

Usage:
  import_md REPO MARKDOWN_FILE [--heading <level>] [--dry-run] [--token TOKEN] [--openai-key KEY]
"""
import os
import sys
import re
import click
import openai
from dotenv import load_dotenv, find_dotenv
from github import Github
from github.GithubException import GithubException

load_dotenv(find_dotenv())

@click.command()
@click.argument('repo', metavar='REPO')
@click.argument('markdown_file', type=click.Path(exists=True), metavar='MARKDOWN_FILE')
@click.option('--token', help='GitHub token (overrides GITHUB_TOKEN env var)')
@click.option('--openai-key', help='OpenAI API key (overrides OPENAI_API_KEY env var)')
@click.option('--model', default=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'), show_default=True,
              help='OpenAI model to use')
@click.option('--temperature', type=float, default=float(os.getenv('OPENAI_TEMPERATURE', '0.7')), show_default=True,
              help='OpenAI temperature')
@click.option('--max-tokens', 'max_tokens', type=int, default=int(os.getenv('OPENAI_MAX_TOKENS', '800')), show_default=True,
              help='OpenAI max tokens')
@click.option('--dry-run', is_flag=True, help='List issues without creating them')
@click.option('--verbose', '-v', is_flag=True, help='Show progress logs')
@click.option('--heading', 'heading', type=int, default=1, show_default=True,
              help='Markdown heading level to split issues (1 for "#", 2 for "##")')
def main(repo, markdown_file, token, openai_key, model, temperature, max_tokens, dry_run, verbose, heading):
    """Import issues from an unstructured markdown file using AI.

    This script parses a Markdown file, treating sections under headings of a specified
    level as potential GitHub issues. It uses an AI model to generate a title and a
    well-structured description for each issue. These are then created in the target
    GitHub repository.

    This is useful for quickly converting documents like meeting notes or brainstorming
    sessions into actionable GitHub issues.
    """
    if verbose:
        click.secho(f"Authenticating to GitHub repository '{repo}'", fg="cyan", err=True)
    # GitHub authentication
    token = token or os.getenv('GITHUB_TOKEN')
    if not token:
        click.secho('Error: GitHub token required. Set GITHUB_TOKEN or pass --token.', fg="red", err=True)
        sys.exit(1)
    try:
        gh = Github(token)
        repo_obj = gh.get_repo(repo)
    except GithubException as e:
        click.secho(f"Error: cannot access repo {repo}: {e}", fg="red", err=True)
        sys.exit(1)
    # OpenAI authentication
    openai_key = openai_key or os.getenv('OPENAI_API_KEY')
    if not openai_key:
        click.secho('Error: OpenAI API key required. Set OPENAI_API_KEY or pass --openai-key.', fg="red", err=True)
        sys.exit(1)
    openai.api_key = openai_key
    if verbose:
        click.secho(f"Reading markdown file: {markdown_file}", fg="cyan", err=True)

    def call_llm(title: str, raw: str) -> str:
        system = {"role": "system", "content": "You are an expert software engineer and technical writer specializing in GitHub issues."}
        user_content = (
            f"Title: {title}\n\n"
            f"Raw content:\n{raw or ''}\n\n"
            "Generate a well-structured GitHub issue description in markdown, including background, summary, acceptance criteria (as a checklist), and implementation notes."
        )
        messages = [system, {"role": "user", "content": user_content}]
        resp = openai.chat.completions.create(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )
        return resp.choices[0].message.content.strip()

    # Read and parse markdown into (title, body) pairs
    with open(markdown_file, encoding='utf-8') as f:
        lines = f.readlines()
    pattern = re.compile(r'^\s*{}(?!\#)\s*(.*)'.format('#' * heading))
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
        click.secho('No headings found; nothing to import.', fg="yellow", err=True)
        sys.exit(1)
    if verbose:
        click.secho(f"Found {len(issues)} headings at level {heading}", fg="cyan", err=True)

    # Create and enrich issues
    for idx, (title, raw_body) in enumerate(issues, start=1):
        if verbose:
            click.secho(f"[{idx}/{len(issues)}] Processing issue: {title}", fg="cyan", err=True)
        # Enrich issue body via OpenAI
        if verbose:
            click.secho("  Calling OpenAI to generate enriched description...", fg="cyan", err=True)
        try:
            enriched = call_llm(title, raw_body)
        except Exception as e:
            click.secho(f"Error calling OpenAI for '{title}': {e}", fg="red", err=True)
            enriched = raw_body
        if dry_run:
            click.secho(f"[dry-run] Issue: {title}\n{enriched}\n", fg="blue")
            continue
        try:
            issue = repo_obj.create_issue(title=title, body=enriched)
            click.secho(f"Created issue #{issue.number}: {title}", fg="green")
        except GithubException as e:
            click.secho(f"Error creating '{title}': {e}", fg="red", err=True)

if __name__ == '__main__':
    main()
