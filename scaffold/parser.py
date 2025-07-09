"""Parser for roadmap files."""

import re
import logging
from pathlib import Path

def parse_markdown(md_file):
    """Parse a Markdown roadmap file into a structured dictionary."""
    logging.info(f"Parsing markdown file: {md_file}")
    path = Path(md_file)
    with open(md_file, 'r', encoding='utf-8') as f:
        content = f.read()

    data = {'name': '', 'description': '', 'milestones': [], 'features': []}
    
    # Find name from first H1, handling initial whitespace/newlines
    lines = content.strip().split('\n')
    if lines and lines[0].startswith('# '):
        data['name'] = lines.pop(0)[2:].strip()
        content = '\n'.join(lines)
    else:
        # If no H1 is at the top, the whole content might be description before sections
        content = '\n'.join(lines)

    # Use regex to find sections. This is more robust.
    milestones_match = re.search(r'^##\s*Milestones\s*\n(.*?)(?=^##\s*|\Z)', content, re.S | re.M)
    features_match = re.search(r'^##\s*Features\s*\n(.*?)(?=^##\s*|\Z)', content, re.S | re.M)
    
    # Description is what's before the first section
    first_section_start = len(content)
    if milestones_match:
        first_section_start = min(first_section_start, milestones_match.start())
    if features_match:
        first_section_start = min(first_section_start, features_match.start())
    
    data['description'] = content[:first_section_start].strip()

    if milestones_match:
        milestones_content = milestones_match.group(1)
        for line in milestones_content.strip().split('\n'):
            if line.strip().startswith('- '):
                m_line = line.strip()[2:].strip()
                m_name, m_due = (m_line.split('—', 1) + [None])[:2]
                m_name = m_name.strip().strip('**')
                m_due = m_due.strip() if m_due else None
                data['milestones'].append({'name': m_name, 'due_date': m_due})

    if features_match:
        features_content = features_match.group(1)
        feature_parts = re.split(r'^###\s+', features_content.strip(), flags=re.M)
        if feature_parts and not feature_parts[0].strip():
             feature_parts.pop(0)

        for feature_part in feature_parts:
            feature_lines = feature_part.strip().split('\n')
            feature_title = feature_lines.pop(0).strip()
            feature = {
                'title': feature_title, 'description': '', 'tasks': [], 'labels': [], 'assignees': [], 'milestone': None
            }
            
            rest_of_feature = '\n'.join(feature_lines)
            task_parts = re.split(r'^####\s+', rest_of_feature.strip(), flags=re.M)

            feature_meta_part = task_parts.pop(0)
            desc_lines = []
            for line in feature_meta_part.strip().split('\n'):
                line_lower = line.lower()
                if line_lower.startswith('milestone:'):
                    feature['milestone'] = line.split(':', 1)[1].strip()
                elif line_lower.startswith('labels:'):
                    feature['labels'] = [l.strip() for l in line.split(':', 1)[1].strip().split(',')]
                elif line_lower.startswith('assignees:'):
                    feature['assignees'] = [a.strip() for a in line.split(':', 1)[1].strip().split(',')]
                else:
                    desc_lines.append(line)
            feature['description'] = '\n'.join(desc_lines).strip()
            
            for task_part in task_parts:
                if not task_part.strip():
                    continue
                task_lines = task_part.strip().split('\n')
                task_title = task_lines.pop(0).strip()
                task = {'title': task_title, 'description': '', 'tests': [], 'labels': [], 'assignees': []}
                
                desc_lines = []
                in_tests = False
                for line in task_lines:
                    line_lower = line.lower()
                    if line_lower.strip() == 'tests:':
                        in_tests = True
                        continue
                    
                    if in_tests:
                        if line.strip().startswith('- '):
                            task['tests'].append(line.strip()[2:])
                        else: # A non-list item ends the tests block
                            in_tests = False
                            if line.strip(): # if it's not empty, it's description
                                desc_lines.append(line)
                    elif line_lower.startswith('labels:'):
                        task['labels'] = [l.strip() for l in line.split(':', 1)[1].strip().split(',')]
                    elif line_lower.startswith('assignees:'):
                        task['assignees'] = [a.strip() for a in line.split(':', 1)[1].strip().split(',')]
                    else:
                        desc_lines.append(line)
                task['description'] = '\n'.join(desc_lines).strip()
                feature['tasks'].append(task)
            data['features'].append(feature)

    if not data['name']:
        data['name'] = path.stem
        
    logging.info(f"Parsed {len(data['features'])} features from {md_file}")
    return data

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
