#!/usr/bin/env python3
"""
I’ve migrated the LLM call to the v1 OpenAI Python interface so it’ll work with the latest openai package:

* Replaced `openai.ChatCompletion.create(...)` with `openai.chat.completions.create(...)`.
* Added `openai>=0.27.0` to requirements.txt.
* Kept response parsing the same (`resp.choices[0].message.content`).

Now, after installing/upgrading your dependencies (`pip install -r requirements.txt`), you can run:

    # Preview the new AI-generated body for issue #42
    python scripts/github_enrich_issue_llm.py \
      --repo owner/repo \
      --issue 42

    # If it looks good, push it to GitHub:
    python scripts/github_enrich_issue_llm.py \
      --repo owner/repo \
      --issue 42 \
      --apply

This will fetch the issue, pull in ROADMAP.md context, call the Chat API to draft a full issue description (background, scope, outline, checklist, code snippets, etc.), and then overwrite the issue body when `--apply` is given.
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
from github import Github
from github.GithubException import GithubException
# Utility: parse README for project context
def parse_readme(path="README.md"):
    """
    Return the first non-empty paragraph after the main title in README.md.
    """
    try:
        with open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
    except FileNotFoundError:
        return None
    idx = 0
    for i, l in enumerate(lines):
        if l.lstrip().startswith('# '):
            idx = i + 1
            break
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    intro = []
    while idx < len(lines) and lines[idx].strip():
        intro.append(lines[idx].strip())
        idx += 1
    return ' '.join(intro) if intro else None
# Utility: search code for relevant snippets
def search_code(title, path='.'):
    """
    Grep repo for title keywords, return top few matches.
    """
    tokens = [tok for tok in re.split(r'\W+', title) if len(tok) > 4]
    hits = []
    seen = set()
    for tok in tokens[:5]:
        try:
            out = subprocess.check_output(
                ['grep', '-R', '-n', tok, path], stderr=subprocess.DEVNULL,
                text=True, timeout=5
            )
        except Exception:
            continue
        for line in out.splitlines()[:3]:
            if line not in seen:
                hits.append(line)
                seen.add(line)
    return '\n'.join(hits)

def parse_roadmap(path="ROADMAP.md"):
    """
    Parse ROADMAP.md and return a mapping of item title -> context dict:
      context: section or phase name,
      goal/tasks/deliverables lists
    """
    data = {}
    current = None
    section = None
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
                    data[ctx_name] = {'goal': [], 'tasks': [], 'deliverables': []}
                    current = ctx_name
                    section = None
                    continue
                m3 = hdr3_re.match(text)
                if m3:
                    ctx_name = m3.group(1).strip()
                    data[ctx_name] = {'goal': [], 'tasks': [], 'deliverables': []}
                    current = ctx_name
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
        print(f"Error: ROADMAP.md not found at {path}", file=sys.stderr)
        sys.exit(1)
    mapping = {}
    for ctx_name, ctx in data.items():
        for key in ('goal', 'tasks', 'deliverables'):
            for item in ctx.get(key, []):
                mapping[item] = {'context': ctx_name, **ctx}
    return mapping

def get_context_for_issue(title, roadmap_mapping):
    if title in roadmap_mapping:
        return roadmap_mapping[title], title
    candidates = difflib.get_close_matches(title, roadmap_mapping.keys(), n=1, cutoff=0.5)
    if candidates:
        matched = candidates[0]
        return roadmap_mapping[matched], matched
    return None, None

def call_llm(issue_title, existing_body, ctx, matched):
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        print('Error: OPENAI_API_KEY is not set', file=sys.stderr)
        sys.exit(1)
    openai.api_key = api_key
    # Build combined context
    readme_ctx = parse_readme() or ''
    code_snippets = search_code(issue_title)
    # Construct user message with roadmap, README, and code context
    user_content = (
        f"Generate a detailed GitHub issue description.\n"
        f"Title: {issue_title}\n"
        f"Existing description: '''{existing_body}'''\n"
        f"Roadmap section: {ctx['context']}\n"
    )
    if ctx.get('goal'):
        user_content += "Goal:\n" + "\n".join(f"- {g}" for g in ctx['goal']) + "\n"
    if ctx.get('tasks'):
        user_content += "Tasks:\n" + "\n".join(f"- {t}" for t in ctx['tasks']) + "\n"
    if ctx.get('deliverables'):
        user_content += "Deliverables:\n" + "\n".join(f"- {d}" for d in ctx['deliverables']) + "\n"
    if readme_ctx:
        user_content += f"\nProject README context:\n{readme_ctx}\n"
    if code_snippets:
        user_content += f"\nRelevant code snippets:\n{code_snippets}\n"
    user_content += (
        "\nInclude in the issue: summary, scope, acceptance criteria, implementation steps, "
        "code examples if applicable, and a checklist of subtasks."
    )
    messages = [
        {"role": "system", "content": "You are a helpful coding assistant and software engineer."},
        {"role": "user", "content": user_content}
    ]
    # Call LLM
    resp = openai.chat.completions.create(
        model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
        messages=messages,
        temperature=0.2,
        max_tokens=800
    )
    return resp.choices[0].message.content.strip()

def main():
    import argparse
    parser = argparse.ArgumentParser(
        description="Enrich a single GitHub issue via LLM and roadmap context"
    )
    parser.add_argument('--repo', required=True, help='GitHub repo (owner/name)')
    parser.add_argument('--issue', type=int, required=True, help='Issue number')
    parser.add_argument('--path', default='ROADMAP.md', help='Path to ROADMAP.md')
    parser.add_argument('--apply', action='store_true', help='Apply change to GitHub issue')
    args = parser.parse_args()
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print('Error: GITHUB_TOKEN is not set', file=sys.stderr)
        sys.exit(1)
    gh = Github(token)
    try:
        repo = gh.get_repo(args.repo)
    except GithubException as e:
        print(f"Error: cannot access repo {args.repo}: {e}", file=sys.stderr)
        sys.exit(1)
    try:
        issue = repo.get_issue(number=args.issue)
    except Exception as e:
        print(f"Error: cannot fetch issue #{args.issue}: {e}", file=sys.stderr)
        sys.exit(1)
    roadmap_mapping = parse_roadmap(args.path)
    ctx, matched = get_context_for_issue(issue.title.strip(), roadmap_mapping)
    if not ctx:
        print(f"No roadmap context found for issue #{args.issue}: {issue.title}", file=sys.stderr)
        sys.exit(1)
    existing_body = issue.body or ''
    enriched = call_llm(issue.title, existing_body, ctx, matched)
    print("=== Enriched Issue Body ===")
    print(enriched)
    if args.apply:
        try:
            issue.edit(body=enriched)
            print(f"Issue #{args.issue} updated.")
        except Exception as e:
            print(f"Failed to update issue: {e}", file=sys.stderr)
            sys.exit(1)

if __name__ == '__main__':
    main()