#!/usr/bin/env python3
"""
enrich: General-purpose CLI for GitHub issue enrichment via LLM using roadmap context.

Subcommands:
  issue   - Enrich a single issue with LLM using roadmap context
  batch   - Batch enrich issues with LLM using roadmap context
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

import openai

def parse_roadmap(path="ROADMAP.md"):
    """
    Parse ROADMAP.md and return a mapping of item title -> context dict.
    Captures goal, tasks, deliverables under sections/phases.
    """
    data = {}
    current = None
    section = None
    phase_re = re.compile(r'^\s*##\s*Phase\s*(\d+):\s*(.+)$')
    h3_re = re.compile(r'^\s*###\s*(.+)$')
    goal_re = re.compile(r'^\s*\*\*Goal\*\*')
    tasks_re = re.compile(r'^\s*\*\*Tasks\*\*')
    deliv_re = re.compile(r'^\s*\*\*(?:Milestones\s*&\s*)?Deliverables\*\*')
    try:
        with open(path, encoding='utf-8') as f:
            for line in f:
                t = line.rstrip()
                m = phase_re.match(t)
                if m:
                    ctx = f"Phase {m.group(1)}: {m.group(2).strip()}"
                    data[ctx] = {'goal': [], 'tasks': [], 'deliverables': []}
                    current, section = ctx, None
                    continue
                m3 = h3_re.match(t)
                if m3:
                    ctx = m3.group(1).strip()
                    data[ctx] = {'goal': [], 'tasks': [], 'deliverables': []}
                    current, section = ctx, 'tasks'
                    continue
                if current is None:
                    continue
                if goal_re.match(t): section = 'goal'; continue
                if tasks_re.match(t): section = 'tasks'; continue
                if deliv_re.match(t): section = 'deliverables'; continue
                if section in ('goal', 'deliverables') and t.strip().startswith('- '):
                    data[current][section].append(t.strip()[2:].strip()); continue
                if section == 'tasks':
                    mnum = re.match(r'\s*\d+\.\s+(.*)$', t)
                    if mnum:
                        data[current]['tasks'].append(mnum.group(1).strip()); continue
                    if t.strip().startswith('- '):
                        data[current]['tasks'].append(t.strip()[2:].strip()); continue
    except FileNotFoundError:
        print(f"Error: ROADMAP.md not found at {path}", file=sys.stderr)
        sys.exit(1)
    # Flatten mapping for lookups
    mapping = {}
    for ctx, obj in data.items():
        for key in ('goal', 'tasks', 'deliverables'):
            for itm in obj[key]:
                mapping[itm] = {'context': ctx, **obj}
    return mapping

def get_context(title, roadmap):
    if title in roadmap:
        return roadmap[title], title
    candidates = difflib.get_close_matches(title, roadmap.keys(), n=1, cutoff=0.5)
    if candidates:
        m = candidates[0]
        return roadmap[m], m
    return None, None

def call_llm(title, existing_body, ctx):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print('Error: OPENAI_API_KEY not set', file=sys.stderr)
        sys.exit(1)
    openai.api_key = api_key
    system = {"role": "system", "content": "You are an expert software engineer and technical writer."}
    parts = [f"Title: {title}", f"Context: {ctx['context']}"]
    if ctx.get('goal'):
        parts.append("Goal:\n" + "\n".join(f"- {g}" for g in ctx['goal']))
    if ctx.get('tasks'):
        parts.append("Tasks:\n" + "\n".join(f"- {t}" for t in ctx['tasks']))
    if ctx.get('deliverables'):
        parts.append("Deliverables:\n" + "\n".join(f"- {d}" for d in ctx['deliverables']))
    parts.append(f"Existing description:\n{existing_body or ''}")
    parts.append("Generate a detailed GitHub issue description with background, scope, acceptance criteria, implementation outline, code snippets, and a checklist.")
    response = openai.chat.completions.create(
        model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
        messages=[system, {"role": "user", "content": "\n\n".join(parts)}],
        temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
        max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '800'))
    )
    return response.choices[0].message.content.strip()

import argparse
from github import Github, GithubException


def enrich_one_issue(repo, issue_number, roadmap, apply_changes=False):
    """Enrich a single issue."""
    issue = repo.get_issue(number=issue_number)
    ctx, matched = get_context(issue.title.strip(), roadmap)
    if not ctx:
        print(f"No roadmap context for issue #{issue_number}", file=sys.stderr)
        sys.exit(1)
    enriched = call_llm(issue.title, issue.body, ctx)
    print(enriched)
    if apply_changes:
        issue.edit(body=enriched)
        print(f"Issue #{issue_number} updated.")


def enrich_batch(repo, roadmap, csv_path=None, interactive=False, apply_changes=False):
    """Batch enrich issues."""
    issues = list(repo.get_issues(state='open'))
    records = []
    for issue in issues:
        ctx, matched = get_context(issue.title.strip(), roadmap)
        if not ctx:
            continue
        enriched = call_llm(issue.title, issue.body, ctx)
        records.append((issue.number, issue.title, ctx['context'], matched, enriched))
    if csv_path:
        import csv
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['issue', 'title', 'context', 'matched', 'enriched_body'])
            writer.writerows(records)
        print(f"Wrote {len(records)} records to {csv_path}")
        return
    if interactive:
        for num, title, ctx_name, matched, body in records:
            print(f"\n--- Issue #{num}: {title} ({ctx_name}) matched '{matched}' ---")
            print(body)
            ans = input("Apply this update? [y/N/q]: ").strip().lower()
            if ans == 'y':
                repo.get_issue(num).edit(body=body)
                print(f"Updated issue #{num}")
            if ans == 'q':
                break
        return
    if apply_changes:
        for num, _, _, _, body in records:
            repo.get_issue(num).edit(body=body)
            print(f"Updated issue #{num}")
        return
    for num, title, ctx_name, matched, _ in records:
        print(f"Would update issue #{num}: {title} (matched '{matched}' in {ctx_name})")


def main():
    parser = argparse.ArgumentParser(description="GitHub LLM Enrichment CLI")
    sub = parser.add_subparsers(dest='command', required=True)
    pi = sub.add_parser('issue', help='Enrich a single issue via LLM')
    pi.add_argument('--repo', required=True, help='owner/repo')
    pi.add_argument('--issue', type=int, required=True, help='Issue number')
    pi.add_argument('--path', default='ROADMAP.md', help='Path to roadmap file')
    pi.add_argument('--apply', action='store_true', help='Apply the update')
    pb = sub.add_parser('batch', help='Batch enrich issues via LLM')
    pb.add_argument('--repo', required=True, help='owner/repo')
    pb.add_argument('--path', default='ROADMAP.md', help='Path to roadmap file')
    pb.add_argument('--csv', help='Output CSV file')
    pb.add_argument('--interactive', action='store_true', help='Interactive approval')
    pb.add_argument('--apply', action='store_true', help='Apply all updates')
    args = parser.parse_args()
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print('Error: GITHUB_TOKEN not set', file=sys.stderr)
        sys.exit(1)
    gh = Github(token)
    try:
        repo = gh.get_repo(args.repo)
    except GithubException as e:
        print(f"Error: cannot access repo {args.repo}: {e}", file=sys.stderr)
        sys.exit(1)
    roadmap = parse_roadmap(args.path)
    if args.command == 'issue':
        enrich_one_issue(repo, args.issue, roadmap, apply_changes=args.apply)
    else:
        enrich_batch(repo, roadmap, csv_path=args.csv, interactive=args.interactive, apply_changes=args.apply)

if __name__ == '__main__':
    main()
