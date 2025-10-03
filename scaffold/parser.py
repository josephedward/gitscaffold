"""Parser for roadmap files."""

import re
import logging
import json
import shutil
import subprocess
from pathlib import Path
try:
    import yaml
except ImportError:
    yaml = None  # PyYAML is optional; structured parsing may not be available

def parse_markdown(md_file):
    """Parse a Markdown roadmap file into a structured dictionary."""
    logging.info(f"Parsing markdown file: {md_file}")
    # If an external Rust parser is available, use it
    try:
        if shutil.which('mdparser'):
            # Guard against a hanging external binary by using a short timeout
            out = subprocess.check_output(['mdparser', md_file], text=True, timeout=5)
            data = json.loads(out)
            logging.info("Used external mdparser for parsing Markdown.")
            return data
    except (subprocess.TimeoutExpired, Exception):
        # On any error or timeout, fall back to the built-in parser
        logging.debug("External mdparser unavailable/failed or timed out; falling back to Python parser.")
    path = Path(md_file)
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    data = {'name': '', 'description': '', 'milestones': [], 'features': []}

    lines = content.strip().split('\n')
    if lines and lines[0].startswith('# '):
        data['name'] = lines.pop(0)[2:].strip()
        content = '\n'.join(lines)
    else:
        content = '\n'.join(lines)
    
    if not data['name']:
        data['name'] = path.stem

    # Split content by H2 headings (##). The regex captures the delimiter.
    sections = re.split(r'(^##\s+.*$)', content, flags=re.MULTILINE)
    
    data['description'] = sections[0].strip()

    # Process sections in pairs (header, content)
    for i in range(1, len(sections), 2):
        header = sections[i].strip()
        sec_content = sections[i+1]
        
        if re.match(r'^##\s*Milestones', header):
            lines = sec_content.strip().split('\n')
            # Detect table vs list format
            if any(l.strip().startswith('|') for l in lines):
                # Parse pipe-delimited table rows
                for row in lines:
                    row = row.strip()
                    if not row.startswith('|'):
                        continue
                    # Skip separator row (e.g., |---|---|)
                    if re.match(r'^\|\s*-+', row):
                        continue
                    # Split columns and strip
                    cols = [c.strip() for c in row.strip().strip('|').split('|')]
                    # Skip header row with column names
                    if cols and cols[0].lower().startswith('milestone'):
                        continue
                    if len(cols) >= 2:
                        name_val = cols[0]
                        due_val = cols[1] or None
                        data['milestones'].append({'name': name_val, 'due_date': due_val})
            else:
                # Parse old dash list format
                for line in lines:
                    if line.strip().startswith('- '):
                        m_line = line.strip()[2:].strip()
                        m_name, m_due = (m_line.split('—', 1) + [None])[:2]
                        m_name = m_name.strip().strip('**')
                        m_due = m_due.strip() if m_due else None
                        data['milestones'].append({'name': m_name, 'due_date': m_due})
        
        elif re.match(r'^##\s*Features', header):
            # Split this section into features by H3
            feature_parts = re.split(r'^###\s+', sec_content.strip(), flags=re.M)
            if feature_parts and not feature_parts[0].strip():
                 feature_parts.pop(0) # First element is empty if content starts with delimiter

            for feature_part in feature_parts:
                feature_lines = feature_part.strip().split('\n')
                feature_title = feature_lines.pop(0).strip()
                if not feature_title:
                    continue
                feature = {
                    'title': feature_title, 'description': '', 'tasks': [], 'labels': [], 'assignees': [], 'milestone': None
                }
                
                rest_of_feature = '\n'.join(feature_lines)

                # Split feature by H4 headings to separate tasks. The part before the first H4 is the feature body.
                task_parts_h4 = re.split(r'\n^####\s+', rest_of_feature, flags=re.M)
                feature_body_part = task_parts_h4.pop(0)

                # Within the feature body, split again to separate metadata from a **Tasks:** list.
                parts = re.split(r'\n\s*\*\*Tasks:\*\*\s*\n', feature_body_part, maxsplit=1, flags=re.IGNORECASE)
                meta_part_str = parts[0]
                tasks_list_str = parts[1] if len(parts) > 1 else ''

                # Parse metadata for the feature.
                desc_lines = []
                for line in meta_part_str.strip().split('\n'):
                    stripped_line = line.strip()
                    # General key-value parsing, handles "Labels: ..." and "- **Labels:** ..."
                    if ':' in stripped_line:
                        key, value = [s.strip() for s in stripped_line.split(':', 1)]
                        key_lower = re.sub(r'[\*\- ]', '', key).lower()

                        if key_lower == 'description':
                            feature['description'] = value
                        elif key_lower == 'milestone':
                            feature['milestone'] = value
                        elif key_lower == 'labels':
                            feature['labels'] = [l.strip() for l in value.split(',') if l.strip()]
                        elif key_lower == 'assignees':
                            feature['assignees'] = [a.strip() for a in value.split(',') if a.strip()]
                        else:
                            desc_lines.append(line)
                    else:
                        desc_lines.append(line)

                # If description wasn't an explicit field, use the collected lines.
                if not feature['description'] and desc_lines:
                    feature['description'] = '\n'.join(desc_lines).strip()

                # Parse tasks from H4 sections
                for task_part in task_parts_h4:
                    task_lines = task_part.strip().split('\n')
                    task_title = task_lines.pop(0).strip()
                    if not task_title:
                        continue
                    
                    task_body = '\n'.join(task_lines)
                    task = {'title': task_title, 'description': '', 'labels': [], 'assignees': [], 'tests': []}
                    
                    tests_parts = re.split(r'\nTests:\s*\n', task_body, flags=re.IGNORECASE)
                    meta_body = tests_parts[0]
                    tests_body = tests_parts[1] if len(tests_parts) > 1 else ''

                    task_desc_lines = []
                    for line in meta_body.strip().split('\n'):
                        stripped_line = line.strip()
                        if ':' in stripped_line:
                            key, value = [s.strip() for s in stripped_line.split(':', 1)]
                            key_lower = key.lower()
                            if key_lower == 'labels':
                                task['labels'] = [l.strip() for l in value.split(',') if l.strip()]
                            elif key_lower == 'assignees':
                                task['assignees'] = [a.strip() for a in value.split(',') if a.strip()]
                            else:
                                task_desc_lines.append(line)
                        else:
                            task_desc_lines.append(line)

                    if task_desc_lines:
                        task['description'] = '\n'.join(task_desc_lines).strip()
                    
                    if tests_body:
                        task['tests'] = [l.strip()[2:] for l in tests_body.strip().split('\n') if l.strip().startswith('- ')]

                    feature['tasks'].append(task)
                
                # Parse tasks from **Tasks:** list
                if tasks_list_str:
                    for line in tasks_list_str.strip().split('\n'):
                        stripped_line = line.strip()
                        if stripped_line.startswith('- '):
                            task_title = stripped_line[2:].strip()
                            if task_title:
                                feature['tasks'].append({'title': task_title, 'completed': False})
                
                data['features'].append(feature)

    logging.info(f"Parsed {len(data['features'])} features and {len(data['milestones'])} milestones from {md_file}")
    return data

def parse_roadmap(roadmap_file):
    """Parse a roadmap file (YAML/JSON or Markdown) and return a dictionary."""
    path = Path(roadmap_file)
    logging.info(f"Parsing roadmap file: {roadmap_file}")
    suffix = path.suffix.lower()
    # Load raw content
    content = path.read_text(encoding='utf-8')
    # If markdown file, attempt YAML front-matter first
    if suffix in ('.md', '.markdown'):
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError:
            data = None
        if isinstance(data, dict):
            logging.info("Parsed markdown file as a structured roadmap.")
            return data
        if isinstance(data, list):
            raise ValueError("Roadmap file must contain a mapping at the top level, got list")
        # Fallback to heading-based markdown parser
        logging.info("Using markdown parser for non-structured markdown file.")
        return parse_markdown(roadmap_file)
    # If JSON file
    if suffix == '.json':
        import json
        logging.info("Using JSON parser.")
        return json.loads(content)
    # Otherwise, treat as YAML file
    try:
        data = yaml.safe_load(content)
    except yaml.YAMLError as e:
        raise ValueError(f"Roadmap file must contain a mapping at the top level, got YAML error: {e}")
    if not isinstance(data, dict):
        raise ValueError(f"Roadmap file must contain a mapping at the top level, got {type(data).__name__}")
    logging.info("Parsed file as structured roadmap.")
    return data


def write_roadmap(roadmap_file, data):
    """Writes roadmap data to a Markdown file."""
    path = Path(roadmap_file)

    if hasattr(data, 'dict'):
        # This handles Pydantic models
        data_dict = data.dict(exclude_none=True)
    else:
        data_dict = data

    content = []
    if data_dict.get('name'):
        content.append(f"# {data_dict['name']}")
        content.append('')

    if data_dict.get('description'):
        content.append(data_dict['description'])
        content.append('')

    if data_dict.get('milestones'):
        content.append('## Milestones')
        for m in data_dict['milestones']:
            due_date_str = f" — {m['due_date']}" if m.get('due_date') else ""
            content.append(f"- **{m['name']}**{due_date_str}")
        content.append('')

    content.append('## Features')
    content.append('')

    for feature in data_dict.get('features', []):
        content.append(f"### {feature['title']}")
        if feature.get('description'):
            content.append(feature['description'])
        # Also write milestone, labels, assignees for feature
        if feature.get('milestone'):
            content.append(f"Milestone: {feature['milestone']}")
        if feature.get('labels'):
            content.append(f"Labels: {', '.join(feature['labels'])}")
        if feature.get('assignees'):
            content.append(f"Assignees: {', '.join(feature['assignees'])}")
        content.append('')

        for task in feature.get('tasks', []):
            # Render completed status with checkbox
            title = task.get('title', '')
            completed = task.get('completed', False)
            checkbox = '[x]' if completed else '[ ]'
            content.append(f"#### {checkbox} {title}")
            if task.get('description'):
                content.append(task['description'])
            # Also write labels, assignees, tests for task
            if task.get('labels'):
                content.append(f"Labels: {', '.join(task['labels'])}")
            if task.get('assignees'):
                content.append(f"Assignees: {', '.join(task['assignees'])}")
            if task.get('tests'):
                content.append('')
                content.append("Tests:")
                for t in task['tests']:
                    content.append(f" - {t}")
            content.append('')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(content))

    logging.info(f"Updated roadmap file: {roadmap_file}")
