#!/usr/bin/env python3
"""
Import and enrich GitHub issues from an unstructured Markdown file using AI.
"""
import os
import sys
import json
import argparse
import re

try:
    import openai
except ImportError:
    sys.stderr.write("Error: 'openai' package is required. Install with 'pip install openai'.\n")
    sys.exit(1)
from github import Github, GithubException


def extract_issues(md_text):
    """Use AI to extract a list of issues with title and optional description."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        sys.stderr.write("Error: OPENAI_API_KEY not set\n")
        sys.exit(1)
    openai.api_key = api_key
    system = {"role": "system", "content": "You are an assistant that extracts GitHub issue titles and descriptions from markdown."}
    user_prompt = (
        "Given the following markdown document, extract a JSON array of issues to be created. "
        "Each issue should be an object with 'title' and optional 'description' fields. "
        "Respond with valid JSON only.\n\n" + md_text
    )
    try:
        resp = openai.ChatCompletion.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            messages=[system, {"role": "user", "content": user_prompt}],
            temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '512'))
        )
    except Exception as e:
        sys.stderr.write(f"Error calling OpenAI API: {e}\n")
        sys.exit(1)
    content = resp.choices[0].message.content.strip()
    # Attempt to parse JSON from response
    try:
        issues = json.loads(content)
    except json.JSONDecodeError:
        # Fallback: extract first JSON substring
        start = content.find('[')
        end = content.rfind(']')
        if start != -1 and end != -1:
            try:
                issues = json.loads(content[start:end+1])
            except json.JSONDecodeError:
                sys.stderr.write("Failed to parse JSON output from AI.\n")
                sys.exit(1)
        else:
            sys.stderr.write("No JSON array found in AI response.\n")
            sys.exit(1)
    if not isinstance(issues, list):
        sys.stderr.write("AI response JSON is not a list.\n")
        sys.exit(1)
    # Normalize each issue
    for i, itm in enumerate(issues):
        if not isinstance(itm, dict) or 'title' not in itm:
            sys.stderr.write(f"Invalid issue format at index {i}: {itm}\n")
            sys.exit(1)
    return issues


def enrich_issue(title, description, md_text):
    """Use AI to generate a detailed issue body given title and full markdown context."""
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key:
        sys.stderr.write("Error: OPENAI_API_KEY not set\n")
        sys.exit(1)
    openai.api_key = api_key
    system = {"role": "system", "content": "You are an expert software engineer and technical writer."}
    parts = [f"Title: {title}"]
    if description:
        parts.append(f"Existing description:\n{description}")
    parts.append(f"Full document context:\n{md_text}")
    parts.append("Generate a detailed GitHub issue description with background, scope, acceptance criteria, implementation outline, and checklist.")
    try:
        resp = openai.ChatCompletion.create(
            model=os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo'),
            messages=[system, {"role": "user", "content": "\n\n".join(parts)}],
            temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '800'))
        )
    except Exception as e:
        sys.stderr.write(f"Error calling OpenAI API for enrichment: {e}\n")
        sys.exit(1)
    return resp.choices[0].message.content.stri        return resp.choices[0].message.content.strip()

    return resp.choices[0].message.content.stridef parse_issues_via_llm(content: str) -> list:
    return resp.choices[0].message.content.stri    """
    return resp.choices[0].message.content.stri    Parse raw markdown into list of (title, body) tuples via AI.
    return resp.choices[0].message.content.stri    """
    return resp.choices[0].message.content.stri    prompt = (
    return resp.choices[0].message.content.stri        "Parse the following markdown into a JSON list of issues with 'title' and 'body' fields:\n\n"
    return resp.choices[0].message.content.stri        f"{content}"
    return resp.choices[0].message.content.stri    )
    return resp.choices[0].message.content.stri    messages = [
    return resp.choices[0].message.content.stri        {"role": "system", "content": "You are an expert software engineer specializing in GitHub issues."},
    return resp.choices[0].message.content.stri        {"role": "user", "content": prompt}
    return resp.choices[0].message.content.stri    ]
    return resp.choices[0].message.content.stri    resp = openai.chat.completions.create(
    return resp.choices[0].message.content.stri        model=model,
    return resp.choices[0].message.content.stri        messages=messages,
    return resp.choices[0].message.content.stri        temperature=temperature,
    return resp.choices[0].message.content.stri        max_tokens=max_tokens
    return resp.choices[0].message.content.stri    )
    return resp.choices[0].message.content.stri    text = resp.choices[0].message.content.strip()
    return resp.choices[0].message.content.stri    try:
    return resp.choices[0].message.content.stri        items = json.loads(text)
    return resp.choices[0].message.content.stri        return [(item['title'], item.get('body', '').strip()) for item in items]
    return resp.choices[0].message.content.stri    except Exception as e:
    return resp.choices[0].message.content.stri        raise ValueError(f"Invalid JSON from AI: {e}\n{text}")


def main():
    parser = argparse.ArgumentParser(description="Import and enrich GitHub issues from markdown via AI.")
    parser.add_argument('repo', help='GitHub repository (owner/repo)')
    parser.add_argument('markdown_file', help='Path to markdown file')
    parser.add_argument('--token', help='GitHub token override')
    parser.add_argument('--openai-key', dest='openai_key', help='OpenAI API key override')
    parser.add_argument('--dry-run', action='store_true', help='List issues without creating them')
    parser.add_argument('--apply', action='store_true', help='Apply created issues and enriched bodies')
    args = parser.parse_args()
    # override OpenAI key if provided
    if getattr(args, 'openai_key', None):
        os.environ['OPENAI_API_KEY'] = args.openai_key
    token = args.token or os.getenv('GITHUB_TOKEN')
    if not token:
        sys.stderr.write("Error: GITHUB_TOKEN not set\n")
        sys.exit(1)
    try:
        gh = Github(token)
        repo = gh.get_repo(args.repo)
    except GithubException as e:
        sys.stderr.write(f"Error accessing repo {args.repo}: {e}\n")
        sys.exit(1)
    # Read markdown
    try:
        with open(args.markdown_file, 'r', encoding='utf-8') as f:
            md_text = f.read()
    except FileNotFoundError:
        sys.stderr.write(f"Markdown file not found: {args.markdown_file}\n")
        sys.exit(1)
    # Extract issues
    issues = extract_issues(md_text)
    # Parse markdown via AI for additional issue candidates
    try:
        additional = parse_issues_via_llm(md_text)
        issues.extend(additional)
    except ValueError as e:
        sys.stderr.write(f"Error parsing additional issues: {e}\n")
        sys.exit(1)
    for itm in issues:
        title = itm.get('title')
        desc = itm.get('description', '')
        if args.dry_run:
            print(f"[dry-run] Would create and enrich issue: {title}")
            continue
        # Create issue
        gh_issue = repo.create_issue(title=title, body=desc)
        print(f"Created issue #{gh_issue.number}: {title}")
        # Enrich
        enriched_body = enrich_issue(title, desc, md_text)
        if args.apply:
            gh_issue.edit(body=enriched_body)
            print(f"Enriched and updated issue #{gh_issue.number}")
        else:
            print(f"[preview] Enriched body for issue #{gh_issue.number}:\n{enriched_body}\n")


if __name__ == '__main__':
    main()
