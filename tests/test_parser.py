import pytest

from scaffold.parser import parse_roadmap
  
def test_parse_markdown(tmp_path):
    content = """
# My Test Project

This is the project description.
It has two lines.

## Milestones
- **M1: First Milestone** — 2025-10-26
- **M2: Second Milestone**

## Features

### Feature A
This is the description for Feature A.
Milestone: M1: First Milestone
Labels: backend, core

#### Task A1
Description for Task A1.
Labels: db
Assignees: user1

Tests:
 - Test case 1 for A1.
 - Test case 2 for A1.

#### Task A2
Description for Task A2.

### Feature B
Description for B.
Labels: frontend
"""
    path = tmp_path / 'roadmap.md'
    path.write_text(content.strip())
    data = parse_roadmap(str(path))

    # Top-level fields
    assert data['name'] == 'My Test Project'
    assert data['description'] == 'This is the project description.\nIt has two lines.'

    # Milestones
    assert len(data['milestones']) == 2
    assert data['milestones'][0] == {'name': 'M1: First Milestone', 'due_date': '2025-10-26'}
    assert data['milestones'][1] == {'name': 'M2: Second Milestone', 'due_date': None}

    # Features
    assert len(data['features']) == 2

    # Feature A
    f1 = data['features'][0]
    assert f1['title'] == 'Feature A'
    assert f1['description'] == 'This is the description for Feature A.'
    assert f1['milestone'] == 'M1: First Milestone'
    assert f1['labels'] == ['backend', 'core']
    assert f1['assignees'] == []

    # Tasks for Feature A
    assert len(f1['tasks']) == 2
    
    # Task A1
    t1 = f1['tasks'][0]
    assert t1['title'] == 'Task A1'
    assert t1['description'] == 'Description for Task A1.'
    assert t1['labels'] == ['db']
    assert t1['assignees'] == ['user1']
    assert t1['tests'] == ['Test case 1 for A1.', 'Test case 2 for A1.']
    
    # Task A2
    t2 = f1['tasks'][1]
    assert t2['title'] == 'Task A2'
    assert t2['description'] == 'Description for Task A2.'
    assert t2['labels'] == []
    assert t2['assignees'] == []
    assert t2['tests'] == []
    
    # Feature B
    f2 = data['features'][1]
    assert f2['title'] == 'Feature B'
    assert f2['description'] == 'Description for B.'
    assert f2['labels'] == ['frontend']
    assert len(f2['tasks']) == 0
