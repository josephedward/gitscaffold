#!/usr/bin/env python3
"""
import_md: Vendored script to import issues from unstructured Markdown via AI.

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
    """Import issues from an unstructured markdown file, enriching via OpenAI LLM."""
    if verbose:
        click.echo(f"Authenticating to GitHub repository '{repo}'", err=True)
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
    openai_key = openai_key or os.getenv('OPENAI_API_KEY')
    if not openai_key:
        click.echo('Error: OpenAI API key required. Set OPENAI_API_KEY or pass --openai-key.', err=True)
        sys.exit(1)
    openai.api_key = openai_key
    if verbose:
        click.echo(f"Reading markdown file: {markdown_file}", err=True)

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

    with open(markdown_file, encoding='utf-8') as f:
        lines = f.readlines()
    pattern = re.compile(r'^\s*' + ('#' * heading) + r'\s*(.*)')
    issues = []
    current_title = None
    current_body = []
    for line in lines:
        m = pattern.match(line)
        if m:
            if current_title:
                issues.append((current_title, ''.join(current_body).strip()))
            current_title = m.group(1).lstrip('# ').strip()
            current_body = []
        else:
            if current_title:
                current_body.append(line)
    if current_title:
        issues.append((current_title, ''.join(current_body).strip()))

    if not issues:
        click.echo('No headings found; nothing to import.', err=True)
        sys.exit(1)
    if verbose:
        click.echo(f"Found {len(issues)} headings at level {heading}", err=True)

    for idx, (title, raw_body) in enumerate(issues, start=1):
        if verbose:
            click.echo(f"[{idx}/{len(issues)}] Processing issue: {title}", err=True)
        if verbose:
            click.echo("  Calling OpenAI to generate enriched description...", err=True)
        try:
            enriched = call_llm(title, raw_body)
        except Exception as e:
            click.echo(f"Error calling OpenAI for '{title}': {e}", err=True)
            enriched = raw_body
        if dry_run:
            click.echo(f"[dry-run] Issue: {title}\n{enriched}\n")
            continue
        try:
            issue = repo_obj.create_issue(title=title, body=enriched)
            click.echo(f"Created issue #{issue.number}: {title}")
        except GithubException as e:
            click.echo(f"Error creating '{title}': {e}", err=True)

if __name__ == '__main__':
    main()
