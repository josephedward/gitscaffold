"""Parser for roadmap files."""

import re
import logging
from pathlib import Path
import yaml

def parse_markdown(md_file):
    """Parse a Markdown roadmap file into a structured dictionary."""
    logging.info(f"Parsing markdown file: {md_file}")
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
                # Split feature content into tasks by H4
                task_parts = re.split(r'^####\s+', rest_of_feature.strip(), flags=re.M)

                # Part before first task is feature metadata
                feature_meta_part = task_parts.pop(0)
                desc_lines = []
                for line in feature_meta_part.strip().split('\n'):
                    line_lower = line.lower()
                    if line_lower.startswith('milestone:'):
                        feature['milestone'] = line.split(':', 1)[1].strip()
                    elif line_lower.startswith('labels:'):
                        feature['labels'] = [l.strip() for l in line.split(':', 1)[1].split(',') if l.strip()]
                    elif line_lower.startswith('assignees:'):
                        feature['assignees'] = [a.strip() for a in line.split(':', 1)[1].split(',') if a.strip()]
                    else:
                        desc_lines.append(line)
                feature['description'] = '\n'.join(desc_lines).strip()
                
                # Remaining parts are tasks
                for task_part in task_parts:
                    if not task_part.strip():
                        continue
                    task_lines = task_part.strip().split('\n')
                    task_title = task_lines.pop(0).strip()
                    if not task_title:
                        continue
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
                                task['tests'].append(line.strip()[2:].strip())
                            else: # A non-list item ends the tests block
                                in_tests = False
                                if line.strip(): # if it's not empty, it's description
                                    desc_lines.append(line)
                        elif line_lower.startswith('labels:'):
                            task['labels'] = [l.strip() for l in line.split(':', 1)[1].split(',') if l.strip()]
                        elif line_lower.startswith('assignees:'):
                            task['assignees'] = [a.strip() for a in line.split(':', 1)[1].split(',') if a.strip()]
                        else:
                            desc_lines.append(line)
                    task['description'] = '\n'.join(desc_lines).strip()
                    feature['tasks'].append(task)
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
            raise ValueError(f"Roadmap file must contain a mapping at the top level, got list")
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
