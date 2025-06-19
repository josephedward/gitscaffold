#!/usr/bin/env python3
"""
Batch enrich GitHub issues via LLM using roadmap context.
Supports CSV export, dry-run, interactive approval, and bulk apply.
"""
import os
import sys
import re
import difflib
import csv

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import openai
try:
    from github import Github, GithubException
except ImportError:
    print("Error: PyGithub not installed. Install with `pip install PyGithub` or `pip install -r requirements.txt`", file=sys.stderr)
    sys.exit(1)

def parse_roadmap(path="ROADMAP.md"):
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
                    ctx = f"Phase {num}: {title}"
                    data[ctx] = {'goal': [], 'tasks': [], 'deliverables': []}
                    current, section = ctx, None
                    continue
                m3 = hdr3_re.match(text)
                if m3:
                    ctx = m3.group(1).strip()
                    data[ctx] = {'goal': [], 'tasks': [], 'deliverables': []}
                    current, section = ctx, 'tasks'
                    continue
                if current is None:
                    continue
                if goal_re.match(text): section = 'goal'; continue
                if tasks_re.match(text): section = 'tasks'; continue
                if deliver_re.match(text): section = 'deliverables'; continue
                if section in ('goal','deliverables') and text.strip().startswith('- '):
                    item = text.strip()[2:].strip(); data[current][section].append(item); continue
                if section == 'tasks':
                    mnum = re.match(r'\s*\d+\.\s+(.*)$', text)
                    if mnum:
                        data[current]['tasks'].append(mnum.group(1).strip()); continue
                    if text.strip().startswith('- '):
                        data[current]['tasks'].append(text.strip()[2:].strip()); continue
    except FileNotFoundError:
        print(f"Error: ROADMAP file not found at {path}", file=sys.stderr)
        sys.exit(1)
    mapping = {}
    for ctx, ctxobj in data.items():
        for role in ('goal','tasks','deliverables'):
            for item in ctxobj.get(role, []):
                mapping[item] = {'context': ctx, **ctxobj}
    return mapping

def get_context_for_issue(title, roadmap):
    if title in roadmap:
        return roadmap[title], title
    candidates = difflib.get_close_matches(title, roadmap.keys(), n=1, cutoff=0.5)
    if candidates:
        m = candidates[0]
        return roadmap[m], m
    return None, None

def call_llm(issue_title, existing, ctx, matched):
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        print('Error: OPENAI_API_KEY not set', file=sys.stderr); sys.exit(1)
    try:
        openai.api_key = key
    except Exception:
        print("Error: invalid OPENAI_API_KEY or openai library issue.", file=sys.stderr)
        sys.exit(1)
    system = {"role":"system","content":"You are an expert software engineer and technical writer."}
    user_content = [f"Title: {issue_title}",f"Context: {ctx['context']}"]
    if ctx.get('goal'): user_content.append("Goal:"+"\n".join(f"- {g}" for g in ctx['goal']))
    if ctx.get('tasks'): user_content.append("Tasks:"+"\n".join(f"- {t}" for t in ctx['tasks']))
    if ctx.get('deliverables'): user_content.append("Deliverables:"+"\n".join(f"- {d}" for d in ctx['deliverables']))
    user_content.append(f"Existing description: '''{existing}'''")
    user_content.append(
        "Generate a detailed GitHub issue description with: background, scope, acceptance criteria, implementation outline, code snippets, and a checklist of subtasks."
    )
    resp = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[system,{"role":"user","content":"\n\n".join(user_content)}],
        temperature=0.7,
        max_tokens=800
    )
    return resp.choices[0].message.content.strip()

def main():
    import argparse
    p = argparse.ArgumentParser(description="Batch LLM-enrich GitHub issues from roadmap context.")
    p.add_argument('--repo', required=True)
    p.add_argument('--path', default='ROADMAP.md')
    p.add_argument('--csv', help='Write CSV of enrichments')
    p.add_argument('--interactive', action='store_true')
    p.add_argument('--apply', action='store_true', help='Apply updates')
    args = p.parse_args()
    token = os.getenv('GITHUB_TOKEN')
    if not token:
        print('Error: GITHUB_TOKEN not set', file=sys.stderr); sys.exit(1)
    gh = Github(token)
    try: repo = gh.get_repo(args.repo)
    except Exception as e:
        print(f"Error: cannot access repo {args.repo}: {e}", file=sys.stderr); sys.exit(1)
    roadmap = parse_roadmap(args.path)
    issues = list(repo.get_issues(state='open'))
    records = []
    for issue in issues:
        title = issue.title.strip()
        ctx, matched = get_context_for_issue(title, roadmap)
        if not ctx: continue
        enriched = call_llm(title, issue.body or '', ctx, matched)
        records.append((issue.number, title, ctx['context'], matched, enriched))
    if args.csv:
        with open(args.csv, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['issue','title','context','matched','enriched_body'])
            for r in records: w.writerow(r)
        print(f"Wrote {len(records)} records to {args.csv}")
        return
    if args.interactive:
        for num,title,ctxname,matched,body in records:
            print(f"\n--- Issue #{num}: {title} ({ctxname}) ---")
            print(body)
            ans = input("Apply this update? [y/N]: ").strip().lower()
            if ans=='y':
                try: repo.get_issue(num).edit(body=body); print(f"Updated #{num}")
                except Exception as e: print(f"Failed #{num}: {e}", file=sys.stderr)
            if ans=='q': break
        return
    if args.apply:
        for num,_,_,_,body in records:
            try: repo.get_issue(num).edit(body=body); print(f"Updated #{num}")
            except Exception as e: print(f"Failed #{num}: {e}", file=sys.stderr)
        return
    # default dry-run
    for num,title,ctxname,matched,_ in records:
        print(f"Would update #{num}: {title} (matched '{matched}' in {ctxname})")

if __name__=='__main__': main()