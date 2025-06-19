import click
from . import __version__

from .parser import parse_roadmap
from .validator import validate_roadmap
from .github import GitHubClient
from .ai import extract_issues_from_markdown, enrich_issue_description
from pathlib import Path

@click.group()
@click.version_option(version=__version__, prog_name="gitscaffold")
def cli():
    """Scaffold – Convert roadmaps to GitHub issues."""
    pass

@cli.command()
@click.argument('roadmap_file', type=click.Path(exists=True))
@click.option('--token', envvar='GITHUB_TOKEN', help='GitHub API token', required=True)
@click.option('--repo', help='GitHub repository (owner/repo)', required=True)
@click.option('--dry-run', is_flag=True, help='Validate without creating issues')
@click.option('--ai-extract', is_flag=True, help='Use AI to extract issues from Markdown')
@click.option('--ai-enrich', is_flag=True, help='Use AI to enrich issue descriptions')
def create(roadmap_file, token, repo, dry_run, ai_extract, ai_enrich):
    """Create GitHub issues from a roadmap file (YAML/JSON or Markdown)."""
    path = Path(roadmap_file)
    suffix = path.suffix.lower()
    # Determine raw data
    if ai_extract:
        if suffix not in ('.md', '.markdown'):
            raise click.UsageError('--ai-extract only supported for Markdown files')
        click.echo(f"AI-extracting issues from {roadmap_file}...")
        features = extract_issues_from_markdown(roadmap_file)
        raw = {'name': path.stem, 'description': '', 'milestones': [], 'features': features}
    else:
        raw = parse_roadmap(roadmap_file)
    # Validate
    roadmap = validate_roadmap(raw)
    click.echo(f"Loaded roadmap '{roadmap.name}' with {len(roadmap.milestones)} milestones and {len(roadmap.features)} features.")
    gh = GitHubClient(token, repo)
    # Prepare context for enrichment
    context_text = ''
    if ai_enrich and suffix in ('.md', '.markdown'):
        context_text = path.read_text(encoding='utf-8')
    # Process milestones
    for m in roadmap.milestones:
        if dry_run:
            click.echo(f"[dry-run] Would create or fetch milestone: {m.name} (due: {m.due_date})")
        else:
            gh.create_milestone(name=m.name, due_on=m.due_date)
            click.echo(f"Milestone created or exists: {m.name}")
    # Process features and tasks
    for feat in roadmap.features:
        # Enrich feature body
        body = feat.description or ''
        if ai_enrich:
            if dry_run:
                click.echo(f"[dry-run] Would AI-enrich feature: {feat.title}")
            else:
                click.echo(f"AI-enriching feature: {feat.title}...")
                body = enrich_issue_description(feat.title, body, context_text)
        # Create or get feature issue
        if dry_run:
            click.echo(f"[dry-run] Would create or fetch feature issue: {feat.title}")
            feat_issue = None
        else:
            feat_issue = gh.create_issue(
                title=feat.title,
                body=body,
                assignees=feat.assignees,
                labels=feat.labels,
                milestone=feat.milestone
            )
            click.echo(f"Issue created or exists: #{feat_issue.number} {feat.title}")
        # Sub-tasks
        for task in feat.tasks:
            # Enrich task body
            t_body = task.description or ''
            if ai_enrich:
                if dry_run:
                    click.echo(f"[dry-run] Would AI-enrich sub-task: {task.title}")
                else:
                    click.echo(f"AI-enriching sub-task: {task.title}...")
                    t_body = enrich_issue_description(task.title, t_body, context_text)
            # Create or get sub-task issue
            if dry_run:
                parent = feat_issue.number if feat_issue else 'N/A'
                click.echo(f"[dry-run] Would create sub-task: {task.title} (parent: {parent})")
            else:
                content = t_body
                if feat_issue:
                    content = f"{t_body}\n\nParent issue: #{feat_issue.number}".strip()
                gh.create_issue(
                    title=task.title,
                    body=content,
                    assignees=task.assignees,
                    labels=task.labels,
                    milestone=feat.milestone
                )
                click.echo(f"Sub-task created or exists: {task.title}")
