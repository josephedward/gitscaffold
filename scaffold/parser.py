"""Parser for roadmap files."""

import re
import logging
from pathlib import Path

def parse_markdown(md_file):
    """Parse a Markdown roadmap file into a dict containing name, description, milestones, and features."""
    logging.info(f"Parsing markdown file: {md_file}")
    path = Path(md_file)
    text = path.read_text(encoding='utf-8')
    lines = text.splitlines()
    # Project name: first H1
    name = None
    for idx, line in enumerate(lines):
        if line.startswith('# '):
            name = line[2:].strip()
            desc_start = idx + 1
            break
    if not name:
        name = path.stem
        desc_start = 0
    # Global description: lines until first H2
    description_lines = []
    for line in lines[desc_start:]:
        if line.startswith('## '):
            break
        if line.strip():
            description_lines.append(line.strip())
    description = '\n'.join(description_lines).strip()
    # Parse milestones
    milestones = []
    in_milestones = False
    for line in lines:
        if line.startswith('## Milestones'):
            in_milestones = True
            continue
        if in_milestones:
            if line.startswith('## ') and not line.startswith('## Milestones'):
                in_milestones = False
                continue
            m = re.match(r'^\s*-\s*\*\*(.+?)\*\*\s*(?:—\s*(\S+))?', line)
            if m:
                m_name = m.group(1).strip()
                m_due = m.group(2).strip() if m.group(2) else None
                milestones.append({'name': m_name, 'due_date': m_due})
    # Parse features and tasks
    features = []
    has_features_section = any(line.startswith('## Features') for line in lines)
    if has_features_section:
        in_features = False
        current_feat = None
        current_task = None
        for line in lines:
            if line.startswith('## Features'):
                in_features = True
                continue
            if not in_features:
                continue
            
            if line.startswith('```'):
                break # Stop parsing at a code fence.

            if line.startswith('### '):
                if current_task and current_feat:
                    current_feat['tasks'].append(current_task)
                if current_feat:
                    features.append(current_feat)
                current_feat = {'title': line[4:].strip(), 'description': '', 'milestone': None, 'labels': [], 'assignees': [], 'tasks': []}
                current_task = None
                continue
            if line.startswith('#### ') and current_feat:
                if current_task:
                    current_feat['tasks'].append(current_task)
                current_task = {'title': line[5:].strip(), 'description': '', 'labels': [], 'assignees': [], 'tests': []}
                continue
            if not line.strip() or not current_feat:
                continue
            content = line.strip()
            if content.startswith('Milestone:'):
                current_feat['milestone'] = content.split(':', 1)[1].strip()
                continue
            if content.startswith('Labels:'):
                items = [i.strip() for i in content.split(':', 1)[1].split(',')]
                (current_task or current_feat)['labels'] = items
                continue
            if content.startswith('Assignees:') and current_task:
                items = [i.strip() for i in content.split(':', 1)[1].split(',')]
                current_task['assignees'] = items
                continue
            if content == 'Tests:':
                continue
            m_test = re.match(r'^[-*]\s+(.+)$', content)
            if m_test and current_task:
                current_task['tests'].append(m_test.group(1).strip())
                continue
            # description
            target = current_task if current_task else current_feat
            if target['description']:
                target['description'] += '\n' + content
            else:
                target['description'] = content
        if current_task and current_feat:
            current_feat['tasks'].append(current_task)
        if current_feat:
            features.append(current_feat)
    else:
        current_feat = None
        current_task = None
        for line in lines:
            if line.startswith('# '):
                if current_task and current_feat:
                    current_feat['tasks'].append(current_task)
                if current_feat:
                    features.append(current_feat)
                current_feat = {'title': line[2:].strip(), 'description': '', 'milestone': None, 'labels': [], 'assignees': [], 'tasks': []}
                current_task = None
                continue
            if line.startswith('## ') and current_feat:
                if current_task:
                    current_feat['tasks'].append(current_task)
                current_task = {'title': line[3:].strip(), 'description': '', 'labels': [], 'assignees': [], 'tests': []}
                continue
            if not line.strip() or not current_feat:
                continue
            content = line.strip()
            if content.startswith('Milestone:'):
                current_feat['milestone'] = content.split(':', 1)[1].strip()
                continue
            if content.startswith('Labels:'):
                items = [i.strip() for i in content.split(':', 1)[1].split(',')]
                (current_task or current_feat)['labels'] = items
                continue
            if content.startswith('Assignees:') and current_task:
                items = [i.strip() for i in content.split(':', 1)[1].split(',')]
                current_task['assignees'] = items
                continue
            if content == 'Tests:':
                continue
            m_test = re.match(r'^[-*]\s+(.+)$', content)
            if m_test and current_task:
                current_task['tests'].append(m_test.group(1).strip())
                continue
            target = current_task if current_task else current_feat
            if target['description']:
                target['description'] += '\n' + content
            else:
                target['description'] = content
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
    """Parse a roadmap file (JSON or Markdown) and return a dictionary."""
    path = Path(roadmap_file)
    logging.info(f"Parsing roadmap file: {roadmap_file}")

    if path.suffix == '.json':
        import json
        logging.info("Using JSON parser.")
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    logging.info("Using markdown parser for non-JSON file.")
    return parse_markdown(roadmap_file)


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
            content.append(f"#### {task['title']}")
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
