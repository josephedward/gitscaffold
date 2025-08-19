"""AI-assisted extraction and enrichment utilities."""
import os
import json
import logging
from openai import OpenAI, OpenAIError
try:
    import google.generativeai as genai
except ImportError:
    genai = None


def extract_issues_from_markdown(md_file, provider: str, api_key: str, model_name=None, temperature=0.5):
    """Use an AI provider to extract a list of issues from unstructured Markdown."""
    logging.info(f"Extracting issues from markdown file: {md_file} using {provider}")
    if not api_key:
        logging.error(f"{provider.upper()} API key was not provided.")
        raise ValueError(f"{provider.upper()} API key was not provided.")
    
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    prompt = (
        "You are a software project manager. "
        "Given the following project notes in Markdown, extract all actionable issues. "
        "For each issue, return an object with 'title' and 'description'. "
        "Output a JSON array only, without extra text.\n\n```markdown\n"
        + content 
        + "\n```\n"
    )
    
    if provider == 'openai':
        client = OpenAI(api_key=api_key, timeout=20.0, max_retries=3)
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
                max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '4096'))
            )
            text = response.choices[0].message.content
        except OpenAIError as e:
            logging.error(f"OpenAI API call failed during issue extraction: {e}")
            raise RuntimeError(f"OpenAI API call failed: {e}") from e

    elif provider == 'gemini':
        if genai is None:
            raise ImportError("google-generativeai is not installed. Please install it to use Gemini.")
        genai.configure(api_key=api_key)
        effective_model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-pro')
        logging.info(f"Using Gemini model '{effective_model_name}' for issue extraction.")
        model = genai.GenerativeModel(effective_model_name)
        try:
            response = model.generate_content(prompt)
            text = response.text
        except Exception as e:
            logging.error(f"Gemini API call failed during issue extraction: {e}")
            raise RuntimeError(f"Gemini API call failed: {e}") from e
    else:
        raise ValueError(f"Unsupported AI provider: {provider}")

    if text is None:
        raise ValueError("AI response content is None.")
    text = text.strip()

    try:
        if text.startswith("```json"):
            text = text.split("```json", 1)[1].rsplit("```", 1)[0]
        elif text.startswith("```"):
            text = text.split("```", 1)[1].rsplit("```", 1)[0]
        text = text.strip()
        issues = json.loads(text)
    except (json.JSONDecodeError, IndexError) as e:
        logging.error(f'Failed to parse JSON from AI response: {e}\nResponse: {text}')
        raise ValueError(f'Failed to parse JSON from AI response: {e}\nResponse: {text}')
    
    result = []
    if not isinstance(issues, list):
        raise ValueError(f"AI response was not a JSON list as expected.\nResponse: {text}")

    for itm in issues:
        if not isinstance(itm, dict) or 'title' not in itm:
            continue
        title = itm['title'].lstrip('# ').strip()
        result.append({
            'title': title,
            'description': itm.get('description', ''),
            'labels': itm.get('labels', []),
            'assignees': itm.get('assignees', []),
            'tasks': itm.get('tasks', [])
        })
    return result

def enrich_issue_description(title, existing_body, provider: str, api_key: str, context='', model_name=None, temperature=0.7):
    """Use an AI provider to generate an enriched GitHub issue body."""
    logging.info(f"Enriching issue description for: '{title}' using {provider}")
    if not api_key:
        logging.error(f"{provider.upper()} API key was not provided.")
        raise ValueError(f"{provider.upper()} API key was not provided.")

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

    if provider == 'openai':
        client = OpenAI(api_key=api_key, timeout=20.0, max_retries=3)
        effective_model_name = model_name or os.getenv('OPENAI_MODEL', 'gpt-3.5-turbo')
        logging.info(f"Using OpenAI model '{effective_model_name}' for enrichment.")
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_content}
        ]
        try:
            response = client.chat.completions.create(
                model=effective_model_name,
                messages=messages,
                temperature=float(os.getenv('OPENAI_TEMPERATURE', temperature)),
                max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '1500'))
            )
            enriched_content = response.choices[0].message.content
        except OpenAIError as e:
            logging.warning(f"OpenAI API call for enrichment failed: {e}. Returning existing body.")
            return existing_body or ''

    elif provider == 'gemini':
        if genai is None:
            raise ImportError("google-generativeai is not installed. Please install it to use Gemini.")
        genai.configure(api_key=api_key)
        effective_model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-pro')
        logging.info(f"Using Gemini model '{effective_model_name}' for enrichment.")
        model = genai.GenerativeModel(effective_model_name)
        # Gemini doesn't have a system prompt in the same way, so we prepend it to the user content.
        full_prompt = f"{system_prompt}\n\n{user_content}"
        try:
            response = model.generate_content(full_prompt)
            enriched_content = response.text
        except Exception as e:
            logging.warning(f"Gemini API call for enrichment failed: {e}. Returning existing body.")
            return existing_body or ''
    else:
        raise ValueError(f"Unsupported AI provider: {provider}")

    if enriched_content is None:
        return existing_body or ''
    return enriched_content.strip()


def generate_code_changes(issue_prompt, file_contents, provider: str, api_key: str, model_name=None, temperature=0.2):
    """Use an AI provider to generate code changes based on an issue and file contexts."""
    logging.info(f"Generating code for: '{issue_prompt}' using {provider}")
    if not api_key:
        raise ValueError(f"{provider.upper()} API key was not provided.")

    prompt = f"""
You are an expert software engineer. You have been asked to resolve the following issue:
"{issue_prompt}"

Here are the contents of the relevant files in the project:
"""
    for path, content in file_contents.items():
        prompt += f"\n--- {path} ---\n{content}\n"

    prompt += """

Please provide the full, updated content for any files that need to be changed to resolve the issue.
Your response should be in the following format, and nothing else. Do not add any commentary or explanation.
For each file to be changed, use this format:

--- START FILE: path/to/file.py ---
(new content of file.py)
--- END FILE: path/to/file.py ---

If no files need to be changed, provide an empty response.
"""

    if provider == 'gemini':
        if genai is None:
            raise ImportError("google-generativeai is not installed. Please install it to use Gemini.")
        genai.configure(api_key=api_key)
        effective_model_name = model_name or os.getenv('GEMINI_MODEL', 'gemini-pro')
        logging.info(f"Using Gemini model '{effective_model_name}' for code generation.")
        model = genai.GenerativeModel(effective_model_name)
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            logging.error(f"Gemini API call failed during code generation: {e}")
            raise RuntimeError(f"Gemini API call failed: {e}") from e
    elif provider == 'openai':
        # Similar implementation for OpenAI if needed in the future
        raise NotImplementedError("Code generation for OpenAI is not yet implemented.")
    else:
        raise ValueError(f"Unsupported AI provider: {provider}")
