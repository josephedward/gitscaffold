"""Parser for roadmap files."""

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
    # Global description: lines until first H2 (milestones or features)
    description_lines = []
    for line in lines[start_idx:]:
        if re.match(r'^##\s+', line):
            break
        if line.strip():
            description_lines.append(line.strip())
    description = '\n'.join(description_lines).strip()
    # Parse milestones
    milestones = []
    in_milestones = False
    for line in lines:
        if re.match(r'^##\s*Milestones', line):
            in_milestones = True
            continue
        if in_milestones:
            # end of milestones section
            if re.match(r'^##\s+', line) and not re.match(r'^##\s*Milestones', line):
                in_milestones = False
                continue
            m = re.match(r'^\s*-\s*\*\*(.+?)\*\*\s*(?:—\s*(\S+))?', line)
            if m:
                m_name = m.group(1).strip()
                due = m.group(2) or None
                milestones.append({'name': m_name, 'due_date': due})
            continue
    # Determine if there is an explicit Features section
    has_features_section = any(re.match(r'^##\s*Features', ln) for ln in lines)
    features = []
    current_feat = None
    current_task = None
    # Section-based parsing if '## Features' exists
    if has_features_section:
        in_features = False
        for line in lines:
            if re.match(r'^##\s*Features', line):
                in_features = True
                continue
            if not in_features:
                continue
            # Feature header (###)
            m_feat = re.match(r'^###\s+(.+)$', line)
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
            # Task header (####)
            m_task = re.match(r'^####\s+(.+)$', line)
            if m_task and current_feat:
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
            # Skip empty or outside-feature
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
            # Tests
            if content.startswith('Tests:'):
                continue
            m_test = re.match(r'^[-*]\s+(.+)$', content)
            if m_test and current_task:
                current_task['tests'].append(m_test.group(1).strip())
                continue
            # Description
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
        # Append last
        if current_task and current_feat:
            current_feat['tasks'].append(current_task)
        if current_feat:
            features.append(current_feat)
    else:
        # Fallback H1/H2 parsing
        for line in lines:
            # Feature header H1
            m_feat = re.match(r'^#\s+(.+)$', line)
            if m_feat and not re.match(r'^##\s+', line):
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
            # Task header H2 (exclude Milestones)
            m_task = re.match(r'^##\s+(.+)$', line)
            if m_task and current_feat and not line.startswith('## Milestones'):
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
            # Skip until in a feature
            if current_feat is None:
                continue
            content = line.strip()
            if not content:
                continue
            if content.startswith('Milestone:'):
                current_feat['milestone'] = content[len('Milestone:'):].strip()
                continue
            if content.startswith('Labels:'):
                items = [it.strip() for it in content[len('Labels:'):].split(',') if it.strip()]
                if current_task:
                    current_task['labels'] = items
                else:
                    current_feat['labels'] = items
                continue
            if content.startswith('Assignees:') and current_task:
                items = [it.strip() for it in content[len('Assignees:'):].split(',') if it.strip()]
                current_task['assignees'] = items
                continue
            if content.startswith('Tests:'):
                continue
            m_test = re.match(r'^[-*]\s+(.+)$', content)
            if m_test and current_task:
                current_task['tests'].append(m_test.group(1).strip())
                continue
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
    """Parse a roadmap file as Markdown and return a dictionary."""
    logging.info(f"Parsing roadmap file: {roadmap_file}")
    logging.info("Using markdown parser.")
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
