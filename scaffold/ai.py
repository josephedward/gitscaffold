"""AI-assisted extraction and enrichment utilities."""
import os
import json
import openai

def _get_api_key():
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        raise RuntimeError('OPENAI_API_KEY not set')
    return key

def extract_issues_from_markdown(md_file, model=None, temperature=0.5):
    """Use OpenAI to extract a list of issues from unstructured Markdown."""
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    prompt = (
        "You are a software project manager. "
        "Given the following project notes in Markdown, extract all actionable issues. "
        "For each issue, return an object with 'title' and 'description'. "
        "Output a JSON array only, without extra text.\n\n```
" + content + "\n```"
    )
    openai.api_key = _get_api_key()
    model = model or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {'role': 'system', 'content': 'You are an expert software project planner.'},
            {'role': 'user', 'content': prompt}
        ],
        temperature=float(os.getenv('OPENAI_TEMPERATURE', temperature)),
        max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '512'))
    )
    text = response.choices[0].message.content.strip()
    try:
        issues = json.loads(text)
    except json.JSONDecodeError as e:
        raise ValueError(f'Failed to parse JSON from AI response: {e}\nResponse: {text}')
    # Ensure each has title and description keys
    result = []
    for itm in issues:
        if 'title' not in itm:
            continue
        result.append({
            'title': itm['title'],
            'description': itm.get('description', ''),
            'labels': [],
            'assignees': [],
            'tasks': []
        })
    return result

def enrich_issue_description(title, existing_body, context='', model=None, temperature=0.7):
    """Use OpenAI to generate an enriched GitHub issue body."""
    openai.api_key = _get_api_key()
    model = model or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    system = {'role': 'system', 'content': 'You are an expert software engineer and technical writer.'}
    parts = [f"Title: {title}"]
    if context:
        parts.append('Context description:')
        parts.append(context)
    parts.append('Existing description:')
    parts.append(existing_body or '')
    parts.append(
        'Generate a detailed GitHub issue description including background, scope, acceptance criteria, '  
        'implementation outline, and a checklist.'
    )
    messages = [system, {'role': 'user', 'content': '\n\n'.join(parts)}]
    response = openai.ChatCompletion.create(
        model=model,
        messages=messages,
        temperature=float(os.getenv('OPENAI_TEMPERATURE', temperature)),
        max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '800'))
    )
    return response.choices[0].message.content.strip()