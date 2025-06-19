#!/usr/bin/env python3
"""
delete_closed: General-purpose script to delete closed GitHub issues.

Usage:
  delete_closed --repo owner/repo [--method graphql|rest] [--dry-run] [--token TOKEN]
"""
import os
import sys

import click
import requests
from dotenv import load_dotenv, find_dotenv

@click.command()
@click.option('--repo', required=True, help='GitHub repository in owner/repo format')
@click.option('--method', type=click.Choice(['graphql', 'rest']), default='graphql',
              help='Method to list closed issues')
@click.option('--dry-run', is_flag=True, help='Only list closed issues without deleting')
@click.option('--token', help='GitHub token (overrides GITHUB_TOKEN/GH_TOKEN env vars)')
def main(repo, method, dry_run, token):
    """Delete all closed issues in a GitHub repository."""
    load_dotenv(find_dotenv())
    token = token or os.getenv('GITHUB_TOKEN') or os.getenv('GH_TOKEN')
    if not token:
        click.echo('Error: GitHub token required. Set GITHUB_TOKEN or pass --token.', err=True)
        sys.exit(1)
    try:
        owner, name = repo.split('/', 1)
    except ValueError:
        click.echo('Error: --repo must be in owner/repo format', err=True)
        sys.exit(1)
    session = requests.Session()
    session.headers.update({
        'Authorization': f'Bearer {token}',
        'Accept': 'application/vnd.github.v4+json',
        'User-Agent': 'delete-closed-issues'
    })

    issues = []
    if method == 'graphql':
        # Fetch via GraphQL pagination
        query = '''
        query($owner:String!,$repo:String!,$after:String) {
          repository(owner:$owner,name:$repo) {
            issues(first:100,states:CLOSED,after:$after) {
              pageInfo { hasNextPage endCursor }
              nodes { number title id }
            }
          }
        }
        '''
        cursor = None
        while True:
            resp = session.post('https://api.github.com/graphql', json={
                'query': query,
                'variables': {'owner': owner, 'repo': name, 'after': cursor}
            })
            resp.raise_for_status()
            data = resp.json()
            if data.get('errors'):
                click.echo(f"GraphQL error: {data['errors']}", err=True)
                sys.exit(1)
            nodes = data['data']['repository']['issues']['nodes']
            for n in nodes:
                issues.append({'number': n['number'], 'title': n['title'], 'node_id': n['id']})
            page_info = data['data']['repository']['issues']['pageInfo']
            if not page_info['hasNextPage']:
                break
            cursor = page_info['endCursor']
    else:
        # List via REST API
        page = 1
        while True:
            url = f'https://api.github.com/repos/{owner}/{name}/issues'
            resp = session.get(url, params={'state': 'closed', 'per_page': 100, 'page': page})
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            for issue in batch:
                issues.append({
                    'number': issue.get('number'),
                    'title': issue.get('title'),
                    'node_id': issue.get('node_id')
                })
            page += 1

    if not issues:
        click.echo('No closed issues found.')
        return

    if dry_run:
        click.echo(f'Found {len(issues)} closed issues:')
        for issue in issues:
            click.echo(f"- #{issue['number']}: {issue['title']}")
        return

    # Delete via GraphQL mutation
    mutation = '''
    mutation($id:ID!) {
      deleteIssue(input:{issueId:$id}) { clientMutationId }
    }
    '''
    for issue in issues:
        node_id = issue.get('node_id')
        number = issue['number']
        title = issue['title']
        if not node_id:
            click.echo(f"Skipping #{number}: missing node_id", err=True)
            continue
        click.echo(f"Deleting issue #{number}: {title}")
        resp = session.post('https://api.github.com/graphql', json={
            'query': mutation,
            'variables': {'id': node_id}
        })
        if resp.status_code != 200:
            click.echo(f"HTTP {resp.status_code} deleting #{number}: {resp.text}", err=True)
            continue
        result = resp.json()
        if result.get('errors'):
            click.echo(f"GraphQL errors deleting #{number}: {result['errors']}", err=True)
        else:
            click.echo(f"Deleted #{number}")

if __name__ == '__main__':
    main()