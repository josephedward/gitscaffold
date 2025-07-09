"""AI-assisted extraction and enrichment utilities."""
import os
import json
import logging
from openai import OpenAI, OpenAIError # Updated import

# _get_api_key function is no longer needed as the OpenAI client handles API key loading.
# client = OpenAI() will automatically look for OPENAI_API_KEY environment variable.

def extract_issues_from_markdown(md_file, api_key: str, model_name=None, temperature=0.5): # Added api_key argument
    """Use OpenAI to extract a list of issues from unstructured Markdown."""
    logging.info(f"Extracting issues from markdown file: {md_file}")
    if not api_key:
        logging.error("OpenAI API key was not provided to extract_issues_from_markdown.")
        raise ValueError("OpenAI API key was not provided to extract_issues_from_markdown.")
    client = OpenAI(api_key=api_key)
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    prompt = (
        "You are a software project manager. "
        "Given the following project notes in Markdown, extract all actionable issues. "
        "For each issue, return an object with 'title' and 'description'. "
        "Output a JSON array only, without extra text.\n\n```markdown\n" # Using markdown code fence
        + content 
        + "\n```\n"
    )
    
    effective_model_name = model_name or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    logging.info(f"Using OpenAI model '{effective_model_name}' for issue extraction.")
    
    try:
        response = client.chat.completions.create(
            model=effective_model_name,
            messages=[
                {'role': 'system', 'content': 'You are an expert software project planner.'},
                {'role': 'user', 'content': prompt}
            ],
            temperature=float(os.getenv('OPENAI_TEMPERATURE', temperature)),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '1024')) # Increased max_tokens for potentially larger JSON
        )
        text = response.choices[0].message.content
        if text is None:
            raise ValueError("AI response content is None.")
        text = text.strip()
    except OpenAIError as e:
        logging.error(f"OpenAI API call failed during issue extraction: {e}")
        raise RuntimeError(f"OpenAI API call failed: {e}") from e

    try:
        # Attempt to strip markdown code fence if present before parsing JSON
        if text.startswith("```json"):
            text = text.split("```json", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
        elif text.startswith("```"): # Generic code fence
            text = text.split("```", 1)[1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
        text = text.strip()
        
        issues = json.loads(text)
    except json.JSONDecodeError as e:
        logging.error(f'Failed to parse JSON from AI response: {e}\nResponse: {text}')
        raise ValueError(f'Failed to parse JSON from AI response: {e}\nResponse: {text}')
    
    # Ensure each has title and description keys
    result = []
    if not isinstance(issues, list): # Ensure the response is a list
        raise ValueError(f"AI response was not a JSON list as expected.\nResponse: {text}")

    for itm in issues:
        if not isinstance(itm, dict) or 'title' not in itm: # Ensure item is a dict and has a title
            continue
        # Sanitize title to remove markdown heading characters
        title = itm['title'].lstrip('# ').strip()
        result.append({
            'title': title,
            'description': itm.get('description', ''),
            'labels': itm.get('labels', []), # Allow AI to suggest labels
            'assignees': itm.get('assignees', []), # Allow AI to suggest assignees
            'tasks': itm.get('tasks', []) # Allow AI to suggest sub-tasks (though current prompt doesn't ask for this)
        })
    return result

def enrich_issue_description(title, existing_body, api_key: str, context='', model_name=None, temperature=0.7): # Added api_key argument
    """Use OpenAI to generate an enriched GitHub issue body."""
    logging.info(f"Enriching issue description for: '{title}'")
    if not api_key:
        logging.error("OpenAI API key was not provided to enrich_issue_description.")
        raise ValueError("OpenAI API key was not provided to enrich_issue_description.")
    client = OpenAI(api_key=api_key)
    effective_model_name = model_name or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
    logging.info(f"Using OpenAI model '{effective_model_name}' for enrichment.")
    system_prompt = 'You are an expert software engineer and technical writer.'
    
    user_message_parts = [f"Title: {title}"]
    if context:
        user_message_parts.append('\nContext description:\n' + context)
    user_message_parts.append('\nExisting description (if any):\n' + (existing_body or 'N/A'))
    user_message_parts.append(
        '\n\nTask: Generate a detailed GitHub issue description based on the provided title, context, and existing description. '
        'The new description should be comprehensive and well-structured. Include sections like: '
        'Background, Scope of Work, Acceptance Criteria, Implementation Outline (if applicable), and a Checklist of sub-tasks or considerations. '
        'Format it clearly using Markdown.'
    )
    
    user_content = '\n'.join(user_message_parts)
    
    messages = [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': user_content}
    ]
    
    try:
        response = client.chat.completions.create(
            model=effective_model_name,
            messages=messages,
            temperature=float(os.getenv('OPENAI_TEMPERATURE', temperature)),
            max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '1500')) # Increased for more detailed descriptions
        )
        enriched_content = response.choices[0].message.content
        if enriched_content is None:
            return existing_body or '' # Fallback if content is None
        return enriched_content.strip()
    except OpenAIError as e:
        # Fallback to existing body or a simple message in case of API error
        logging.warning(f"OpenAI API call for enrichment failed: {e}. Returning existing body.")
        return existing_body or ''
