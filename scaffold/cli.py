import click

from .parser import parse_roadmap
from .validator import validate_roadmap
from .github import GitHubClient

@click.group()
@click.version_option()
def cli():
    """Scaffold – Convert roadmaps to GitHub issues."""
    pass

@cli.command()
@click.argument('roadmap_file', type=click.Path(exists=True))
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token', required=True)
@click.option('--repo', help='GitHub repository (owner/repo)', required=True)
@click.option('--dry-run', is_flag=True, help='Validate without creating issues')
def create(roadmap_file, token, repo, dry_run):
    """Create GitHub issues from a roadmap file."""
    # Load and validate roadmap
    raw = parse_roadmap(roadmap_file)
    roadmap = validate_roadmap(raw)
    click.echo(f"Loaded roadmap '{roadmap.name}' with {len(roadmap.milestones)} milestones and {len(roadmap.features)} features.")
    gh = GitHubClient(token, repo)
    # Process milestones
    for m in roadmap.milestones:
        if dry_run:
            click.echo(f"[dry-run] Would create or fetch milestone: {m.name} (due: {m.due_date})")
        else:
            gh.create_milestone(name=m.name, due_on=m.due_date)
            click.echo(f"Milestone created or exists: {m.name}")
    # Process features and tasks
    for feat in roadmap.features:
        # Feature issue
        if dry_run:
            click.echo(f"[dry-run] Would create or fetch feature issue: {feat.title}")
            feat_issue = None
        else:
            feat_issue = gh.create_issue(
                title=feat.title,
                body=feat.description,
                assignees=feat.assignees,
                labels=feat.labels,
                milestone=feat.milestone
            )
            click.echo(f"Issue created or exists: #{feat_issue.number} {feat.title}")
        # Sub-tasks
        for task in feat.tasks:
            if dry_run:
                parent = feat_issue.number if feat_issue else 'N/A'
                click.echo(f"[dry-run] Would create sub-task: {task.title} (parent: {parent})")
            else:
                # include parent link in body
                body = task.description or ''
                if feat_issue:
                    body = f"{body}\n\nParent issue: #{feat_issue.number}".strip()
                gh.create_issue(
                    title=task.title,
                    body=body,
                    assignees=task.assignees,
                    labels=task.labels,
                    milestone=feat.milestone
                )
                click.echo(f"Sub-task created or exists: {task.title}")