"""Parser for roadmap files."""

import yaml
import os

def parse_markdown(roadmap_file):
    """Naively parse an unstructured Markdown file into a roadmap dict."""
    name = os.path.splitext(os.path.basename(roadmap_file))[0]
    description_lines = []
    features = []
    current_feature = None
    current_task = None
    context_lines = []
    with open(roadmap_file, 'r', encoding='utf-8') as f:
        for raw in f:
            line = raw.rstrip('\n')
            if line.startswith('# '):
                if current_task:
                    current_task['description'] = '\n'.join(context_lines).strip()
                    current_feature['tasks'].append(current_task)
                    current_task = None
                    context_lines = []
                if current_feature:
                    current_feature['description'] = '\n'.join(context_lines).strip()
                    features.append(current_feature)
                    context_lines = []
                current_feature = {'title': line[2:].strip(), 'description': '', 'labels': [], 'assignees': [], 'tasks': []}
            elif line.startswith('## '):
                if not current_feature:
                    continue
                if current_task:
                    current_task['description'] = '\n'.join(context_lines).strip()
                    current_feature['tasks'].append(current_task)
                    context_lines = []
                current_task = {'title': line[3:].strip(), 'description': '', 'labels': [], 'assignees': []}
                context_lines = []
            else:
                if current_feature:
                    context_lines.append(line)
                else:
                    description_lines.append(line)
    # flush any remaining task or feature
    if current_task and current_feature:
        current_task['description'] = '\n'.join(context_lines).strip()
        current_feature['tasks'].append(current_task)
        current_task = None
        context_lines = []
    if current_feature:
        current_feature['description'] = '\n'.join(context_lines).strip()
        features.append(current_feature)
    return {
        'name': name,
        'description': '\n'.join(description_lines).strip(),
        'milestones': [],
        'features': features
    }

def parse_roadmap(roadmap_file):
    """Parse the roadmap file:
    - YAML/JSON (default)
    - Markdown (.md/.markdown): headings become features/tasks
    Returns a dict suitable for validation and processing."""
    suffix = Path(roadmap_file).suffix.lower()
    if suffix in ('.md', '.markdown'):
        return parse_markdown(roadmap_file)
    with open(roadmap_file, 'r') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Roadmap file must contain a mapping at the top level, got {type(data).__name__}")
    return data