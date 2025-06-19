"""Parser for roadmap files."""

import yaml
import re
from pathlib import Path

def parse_markdown(md_file):
    """Parse an unstructured Markdown file into a roadmap dict."""
    features = []
    current_feat = None
    current_task = None
    global_desc = []
    with open(md_file, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            # Level 1 heading -> new feature
            m1 = re.match(r'^# (.+)$', line)
            if m1:
                if current_feat:
                    features.append(current_feat)
                current_feat = {
                    'title': m1.group(1).strip(),
                    'description': '',
                    'labels': [],
                    'assignees': [],
                    'tasks': []
                }
                current_task = None
                continue
            # Level 2 heading -> sub-task
            m2 = re.match(r'^## (.+)$', line)
            if m2 and current_feat is not None:
                task = {
                    'title': m2.group(1).strip(),
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
            # Content lines: assign to task, else to feature, else global
            if current_task is not None:
                desc = current_task.get('description', '') or ''
                current_task['description'] = f"{desc}\n{line}".strip() if desc else line
            elif current_feat is not None:
                desc = current_feat.get('description', '') or ''
                current_feat['description'] = f"{desc}\n{line}".strip() if desc else line
            else:
                global_desc.append(line)
    # Append last feature
    if current_feat:
        features.append(current_feat)
    name = Path(md_file).stem
    description = '\n'.join(global_desc).strip()
    return {
        'name': name,
        'description': description,
        'milestones': [],
        'features': features
    }

def parse_roadmap(roadmap_file):
    """Parse the roadmap file (YAML/JSON or Markdown) and return a dictionary."""
    suffix = Path(roadmap_file).suffix.lower()
    if suffix in ('.md', '.markdown'):
        return parse_markdown(roadmap_file)
    with open(roadmap_file, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Roadmap file must contain a mapping at the top level, got {type(data).__name__}")
    return data