"""Parser for roadmap files."""

import json
import re
import logging
from pathlib import Path

def parse_markdown(md_file):
    """Parse a Markdown roadmap file into a roadmap dict with milestones and features."""
    logging.info(f"Parsing markdown file: {md_file}")
    path = Path(md_file)
    with open(md_file, 'r', encoding='utf-8') as f:
        lines = [ln.rstrip('\n') for ln in f]
    # Extract project name (first H1)
    name = None
    for idx, line in enumerate(lines):
        m = re.match(r'^#\s+(.+)$', line)
        if m:
            name = m.group(1).strip()
            start_idx = idx + 1
            break
    if not name:
        name = path.stem
        start_idx = 0
    # Global description: lines until first H2
    description_lines = []
    i = start_idx
    while i < len(lines):
        if re.match(r'^##\s+', lines[i]):
            break
        if lines[i].strip():
            description_lines.append(lines[i].strip())
        i += 1
    description = '\n'.join(description_lines).strip()
    # Parse milestones (under '## Milestones')
    milestones = []
    while i < len(lines):
        if re.match(r'^##\s*Milestones', lines[i]):
            i += 1
            while i < len(lines) and not re.match(r'^##\s+', lines[i]):
                m = re.match(r'^\s*-\s*\*\*(.+?)\*\*\s*(?:—\s*(\S+))?', lines[i])
                if m:
                    m_name = m.group(1).strip()
                    due = m.group(2) or None
                    milestones.append({'name': m_name, 'due_date': due})
                i += 1
            break
        i += 1
    # Parse features and tasks
    features = []
    current_feat = None
    current_task = None
    # Continue from features section if present, or from start of lines
    for line in lines[i:]:
        # Feature header H1
        m_feat = re.match(r'^#\s+(.+)$', line)
        if m_feat:
            if current_task and current_feat:
                current_feat['tasks'].append(current_task)
                current_task = None
            if current_feat:
                features.append(current_feat)
            current_feat = {
                'title': m_feat.group(1).strip(),
                'description': '',
                'milestone': None,
                'labels': [],
                'assignees': [],
                'tasks': []
            }
            continue
        # Task header H2
        m_task = re.match(r'^##\s+(.+)$', line)
        if m_task and current_feat is not None:
            if current_task:
                current_feat['tasks'].append(current_task)
            current_task = {
                'title': m_task.group(1).strip(),
                'description': '',
                'labels': [],
                'assignees': [],
                'tests': []
            }
            continue
        # Skip empty or unrelated lines
        if not line.strip() or current_feat is None:
            continue
        content = line.strip()
        # Milestone assignment
        if content.startswith('Milestone:'):
            current_feat['milestone'] = content[len('Milestone:'):].strip()
            continue
        # Labels
        if content.startswith('Labels:'):
            items = [it.strip() for it in content[len('Labels:'):].split(',') if it.strip()]
            if current_task:
                current_task['labels'] = items
            else:
                current_feat['labels'] = items
            continue
        # Assignees
        if content.startswith('Assignees:') and current_task:
            items = [it.strip() for it in content[len('Assignees:'):].split(',') if it.strip()]
            current_task['assignees'] = items
            continue
        # Tests section
        if content.startswith('Tests:'):
            continue
        # Test bullets
        m_test = re.match(r'^[-*]\s+(.+)$', content)
        if m_test and current_task:
            current_task['tests'].append(m_test.group(1).strip())
            continue
        # Description lines
        if current_task:
            if current_task['description']:
                current_task['description'] += '\n' + content
            else:
                current_task['description'] = content
        else:
            if current_feat['description']:
                current_feat['description'] += '\n' + content
            else:
                current_feat['description'] = content
    # Append last task and feature
    if current_task and current_feat:
        current_feat['tasks'].append(current_task)
    if current_feat:
        features.append(current_feat)
    logging.info(f"Parsed {len(features)} features and {len(milestones)} milestones from {md_file}")
    return {
        'name': name,
        'description': description,
        'milestones': milestones,
        'features': features
    }

def parse_roadmap(roadmap_file):
    """Parse the roadmap file (JSON or Markdown) and return a dictionary."""
    logging.info(f"Parsing roadmap file: {roadmap_file}")
    path = Path(roadmap_file)
    suffix = path.suffix.lower()

    if suffix in ('.md', '.markdown'):
        logging.info("Using markdown heading parser for markdown file.")
        return parse_markdown(roadmap_file)

    with open(roadmap_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # For other file types, assume JSON.
    logging.info("Using JSON parser for non-markdown file.")
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {roadmap_file}") from e

    if not isinstance(data, dict):
        raise ValueError(f"Roadmap file must contain a mapping at the top level, got {type(data).__name__}")
    return data


def write_roadmap(roadmap_file, data):
    """Writes roadmap data to a file."""
    path = Path(roadmap_file)

    if hasattr(data, 'dict'):
        data_dict = data.dict(exclude_none=True)
    else:
        data_dict = data

    # Clean up empty lists to make output cleaner
    for feature in data_dict.get('features', []):
        if 'tasks' in feature and not feature['tasks']:
            del feature['tasks']
        if 'labels' in feature and not feature['labels']:
            del feature['labels']
        if 'assignees' in feature and not feature['assignees']:
            del feature['assignees']
        for task in feature.get('tasks', []):
            if 'tests' in task and not task['tests']:
                del task['tests']
            if 'labels' in task and not task['labels']:
                del task['labels']
            if 'assignees' in task and not task['assignees']:
                del task['assignees']

    new_json_content = json.dumps(data_dict, indent=2)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_json_content)
    
    logging.info(f"Updated roadmap file: {roadmap_file}")
