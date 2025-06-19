import pytest
from pydantic import ValidationError

from scaffold.validator import validate_roadmap

def test_validate_success():
    data = {
        'name': 'TestProject',
        'description': 'A test project',
        'milestones': [
            {'name': 'M1', 'due_date': '2025-01-01'}
        ],
        'features': [
            {
                'title': 'Feature1',
                'description': 'Desc',
                'milestone': 'M1',
                'labels': ['bug'],
                'assignees': ['alice'],
                'tasks': [
                    {'title': 'Task1', 'description': 'Tdesc'}
                ]
            }
        ]
    }
    roadmap = validate_roadmap(data)
    assert roadmap.name == 'TestProject'
    assert len(roadmap.milestones) == 1
    assert roadmap.milestones[0].name == 'M1'
    assert len(roadmap.features) == 1
    assert roadmap.features[0].tasks[0].title == 'Task1'

def test_validate_missing_name():
    # name is required
    data = {}
    with pytest.raises(ValidationError):
        validate_roadmap(data)

def test_validate_undefined_milestone_ref():
    data = {
        'name': 'TestProject',
        'milestones': [],
        'features': [
            {'title': 'Feature1', 'milestone': 'NonExistent'}
        ]
    }
    with pytest.raises(ValidationError):
        validate_roadmap(data)