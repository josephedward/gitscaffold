"""Parser for roadmap files."""

import json
import re
import logging
from pathlib import Path

def parse_markdown(md_file):
    """Parse a Markdown roadmap file into a roadmap dict, using '###' for features and '####' for tasks."""
    logging.info(f"Parsing markdown file: {md_file}")
    features = []
    current_feat = None
    current_task = None
    global_desc = []
    in_features = False
    path = Path(md_file)
    with open(md_file, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            # Detect start of features section
            if re.match(r'^##\s*Features', line):
                in_features = True
                continue
            # Before features section, collect global description
            if not in_features:
                if line.strip():
                    global_desc.append(line)
                continue
            # Inside features section
            # Feature heading (###)
            m_feat = re.match(r'^###\s+(.+)', line)
            if m_feat:
                if current_feat:
                    features.append(current_feat)
                current_feat = {
                    'title': m_feat.group(1).strip(),
                    'description': '',
                    'labels': [],
                    'assignees': [],
                    'tasks': []
                }
                current_task = None
                continue
            # Task heading (####)
            m_task = re.match(r'^####\s+(.+)', line)
            if m_task and current_feat is not None:
                task = {
                    'title': m_task.group(1).strip(),
                    'description': '',
                    'labels': [],
                    'assignees': []
                }
                current_feat['tasks'].append(task)
                current_task = task
                continue
            # Skip empty lines
            if not line.strip():
                continue
            # Assign content to current task or feature
            if current_task is not None:
                desc = current_task.get('description') or ''
                current_task['description'] = f"{desc}\n{line}".strip() if desc else line
            elif current_feat is not None:
                desc = current_feat.get('description') or ''
                current_feat['description'] = f"{desc}\n{line}".strip() if desc else line
            # else: ignore lines outside features
    # Append last feature
    if current_feat:
        features.append(current_feat)
    name = path.stem
    description = '\n'.join(global_desc).strip()
    logging.info(f"Parsed {len(features)} features from {md_file}")
    return {
        'name': name,
        'description': description,
        'milestones': [],
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
