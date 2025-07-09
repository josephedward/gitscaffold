"""Parser for roadmap files."""

import yaml
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
    """Parse the roadmap file (YAML/JSON or Markdown) and return a dictionary."""
    logging.info(f"Parsing roadmap file: {roadmap_file}")
    suffix = Path(roadmap_file).suffix.lower()
    with open(roadmap_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # If it's a markdown file, try to parse it as structured YAML first.
    if suffix in ('.md', '.markdown'):
        try:
            data = yaml.safe_load(content)
            if isinstance(data, dict) and 'name' in data:
                logging.info("Parsed markdown file as a structured roadmap.")
                return data
        except yaml.YAMLError:
            pass  # Not YAML, so parse as regular markdown below.

        logging.info("Using markdown heading parser for markdown file.")
        return parse_markdown(roadmap_file)

    # For other file types, assume YAML/JSON.
    logging.info("Using YAML parser for non-markdown file.")
    data = yaml.safe_load(content)
    if not isinstance(data, dict):
        raise ValueError(f"Roadmap file must contain a mapping at the top level, got {type(data).__name__}")
    return data
