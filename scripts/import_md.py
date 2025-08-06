#!/usr/bin/env python3
import os
import re
import click
import openai
from github import Github

@click.command()
@click.argument("repo")
@click.argument("md_file", type=click.Path(exists=True))
@click.option("--heading", "-h", "heading_level", type=int, default=1, show_default=True,
              help="Markdown heading level to import as issues")
@click.option("--dry-run", is_flag=True, help="Show what would be done without creating issues")
def main(repo, md_file, heading_level, dry_run):
    """Import Markdown headings into GitHub issues."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        click.echo("GitHub token is required.", err=True)
        return 1

    try:
        text = open(md_file, encoding="utf-8").read()
    except Exception as e:
        click.echo(f"Error reading file '{md_file}': {e}", err=True)
        return 1

    pattern = re.compile(rf"^({'#' * heading_level})\s*(.+)", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        click.echo(f"No level-{heading_level} headings found in '{md_file}'.")
        return

    for idx, match in enumerate(matches):
        title = match.group(2).strip()
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        try:
            response = openai.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an AI assistant."},
                    {"role": "user", "content": f"Title: {title}\n{body}"}
                ],
                temperature=0.7,
                max_tokens=2000,
            )
            enriched = response.choices[0].message.content.strip()
        except Exception as e:
            click.echo(f"Error during enrichment: {e}", err=True)
            enriched = body

        if dry_run:
            click.echo(f"[dry-run] Issue: {title}")
            click.echo(enriched)
            continue

        gh = Github(token)
        try:
            repo_obj = gh.get_repo(repo)
            issue = repo_obj.create_issue(title=title, body=enriched)
            click.echo(f"Created issue #{issue.number}: {title}")
        except Exception as e:
            click.echo(f"Error creating issue '{title}': {e}", err=True)
    return

if __name__ == "__main__":
    main()
