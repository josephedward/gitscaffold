#!/usr/bin/env python3
"""
Enrich GitHub issues with context from ROADMAP.md.
"""
import os
import sys
import re
import difflib

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def parse_roadmap(path="ROADMAP.md"):
    """
    Parse ROADMAP.md and return a mapping of item title -> context dict:
      context: section or phase name,
      goal/tasks/deliverables (where applicable)
    Captures:
      - Phase sections (## Phase N: ...): goal, tasks, deliverables
      - Level-3 headings (### ...): bullet items
      - Next Steps, Time Estimates, Testing & Quality, Whitepaper table of contents
    """
    data = {}
    current = None
    section = None
    # Patterns
    phase_re = re.compile(r'^\s*##\s*Phase\s*(\d+):\s*(.+)$')
    hdr3_re = re.compile(r'^\s*###\s*(.+)$')
    goal_re = re.compile(r'^\s*\*\*Goal\*\*')
    tasks_re = re.compile(r'^\s*\*\*Tasks\*\*')
    deliver_re = re.compile(r'^\s*\*\*(?:Milestones\s*&\s*)?Deliverables\*\*')

    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                text = line.rstrip('\n')
                m = phase_re.match(text)
                if m:
                    num, title = m.group(1), m.group(2).strip()
                    ctx_name = f"Phase {num}: {title}"
                    current = ctx_name
                    data[current] = {'goal': [], 'tasks': [], 'deliverables': []}
                    section = None
                    continue
                m3 = hdr3_re.match(text)
                if m3:
                    section_name = m3.group(1).strip()
                    current = section_name
                    data[current] = {'goal': [], 'tasks': [], 'deliverables': []}
                    section = 'tasks'
                    continue
                if current is None:
                    continue
                if goal_re.match(text):
                    section = 'goal'
                    continue
                if tasks_re.match(text):
                    section = 'tasks'
                    continue
                if deliver_re.match(text):
                    section = 'deliverables'
                    continue
                if section in ('goal', 'deliverables') and text.strip().startswith('- '):
                    item = text.strip()[2:].strip()
                    data[current][section].append(item)
                    continue
                if section == 'tasks':
                    mnum = re.match(r'\s*\d+\.\s+(.*)$', text)
                    if mnum:
                        data[current]['tasks'].append(mnum.group(1).strip())
                        continue
                    if text.strip().startswith('- '):
                        data[current]['tasks'].append(text.strip()[2:].strip())
                        continue
    except FileNotFoundError:
        print(f"Error: ROADMAP file not found at {path}", file=sys.stderr)
        sys.exit(1)
    # Build item->context map
    mapping = {}
    for ctx_name, ctx in data.items():
        for key in ('goal', 'tasks', 'deliverables'):
            for item in ctx.get(key, []):
                mapping[item] = {'context': ctx_name, **ctx}
    return mapping

def build_body(issue_title, ctx, matched):
    # Special handling for Whitepaper TOC items
    if ctx.get('context') == 'Whitepaper Table of Contents':
        body = []
        body.append(f"**Whitepaper Section**: '{matched}'")
        body.append("")
        body.append(
            f"This issue tracks the drafting of the whitepaper section **'{matched}'**, as listed under 'AI Deception Whitepaper Table of Contents' in [README.md](../README.md)."
        )
        body.append("")
        body.append(
            "Please add the content for this section in the README or in a dedicated WHITEPAPER.md file, and link or summarize it here when ready."
        )
        return "\n".join(body)
    # Default context enrichment
    lines = []
    lines.append(
        f"_Auto-generated context for issue '{issue_title}', matched roadmap item '{matched}' in {ctx['context']}_"
    )
    lines.append("")
    if ctx.get('goal'):
        lines.append("**Goal**:")
        for g in ctx['goal']:
            lines.append(f"- {g}")
        lines.append("")
    if ctx.get('tasks'):
        lines.append("**Tasks**:")
        for t in ctx['tasks']:
            prefix = '* ' if t == matched else '- '
            lines.append(f"{prefix}{t}")
        lines.append("")
    if ctx.get('deliverables'):
        lines.append("**Deliverables**:")
        for d in ctx['deliverables']:
            prefix = '* ' if d == matched else '- '
            lines.append(f"{prefix}{d}")
        lines.append("")
    return "\n".join(lines)

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Enrich GitHub issues with context from ROADMAP.md"
    )
    parser.add_argument(
        '--repo', required=True,
        help='GitHub repo (owner/name)'
    )
    parser.add_argument(
        '--path', default='ROADMAP.md',
        help='Path to ROADMAP.md'
    )
    parser.add_argument(
        '--apply', action='store_true',
        help='Apply changes (updates)'
    )
    parser.add_argument(
        '--close-unmatched', action='store_true',
        help='Close issues that have no roadmap context or are skipped under technical-only'
    )
    parser.add_argument(
        '--technical-only', action='store_true',
        help='Only enrich issues from technical phases (2–6)'
    )
    args = parser.parse_args()

    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print('Error: GITHUB_TOKEN is not set', file=sys.stderr)
        sys.exit(1)
    try:
        from github import Github
        from github.GithubException import GithubException
    except ImportError:
        print(
            'Error: PyGithub not installed. Install with `pip install PyGithub`',
            file=sys.stderr
        )
        sys.exit(1)

    roadmap = parse_roadmap(args.path)
    gh = Github(token)
    try:
        repo = gh.get_repo(args.repo)
    except Exception as e:
        print(f"Error: cannot access repository {args.repo}: {e}", file=sys.stderr)
        sys.exit(1)

    issues = repo.get_issues(state='open')
    technical_prefixes = [f"Phase {i}:" for i in range(2, 7)]
    for issue in issues:
        title = issue.title.strip()
        matched = title
        ctx = roadmap.get(title)
        if not ctx:
            # attempt fuzzy match
            candidates = difflib.get_close_matches(
                title, roadmap.keys(), n=1, cutoff=0.5
            )
            if candidates:
                matched = candidates[0]
                ctx = roadmap[matched]
                print(f"Issue #{issue.number}: fuzzy matched to roadmap item '{matched}'")
            else:
                # no context: close if requested
                if args.close_unmatched:
                    if args.apply:
                        issue.create_comment(
                            "Closing this issue: no actionable context found in ROADMAP.md."
                        )
                        issue.edit(state='closed')
                        print(f"Closed issue #{issue.number}: '{title}'")
                    else:
                        print(f"Would close issue #{issue.number}: '{title}' (no roadmap context)")
                else:
                    print(f"No context found for issue #{issue.number}: '{title}'")
                continue
        if args.technical_only:
            context_name = ctx.get('context', '')
            if not any(
                context_name.startswith(pref) for pref in technical_prefixes
            ):
                # skip or close based on flag
                if args.close_unmatched:
                    if args.apply:
                        issue.create_comment(
                            f"Closing non-technical issue: context '{context_name}'"
                        )
                        issue.edit(state='closed')
                        print(f"Closed non-technical issue #{issue.number}: '{title}'")
                    else:
                        print(f"Would close non-technical issue #{issue.number}: '{title}' (context '{context_name}')")
                else:
                    print(
                        f"Skipping non-technical issue #{issue.number}: '{title}' (context '{context_name}')"
                    )
                continue
        body = build_body(title, ctx, matched)
        if args.apply:
            try:
                issue.edit(body=body)
                print(f"Updated issue #{issue.number}: {title}")
            except Exception as e:
                print(f"Failed to update issue #{issue.number}: {e}", file=sys.stderr)
        else:
            print(f"Would update issue #{issue.number}: {title} (matched '{matched}')")

if __name__ == '__main__':
    main()