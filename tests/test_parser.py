import yaml
import pytest

from scaffold.parser import parse_roadmap

def test_parse_valid(tmp_path):
    data = {'key': 'value', 'list': [1, 2, 3]}
    path = tmp_path / 'roadmap.yml'
    path.write_text(yaml.dump(data))
    result = parse_roadmap(str(path))
    assert isinstance(result, dict)
    assert result == data

def test_parse_invalid_not_mapping(tmp_path):
    # Top-level must be a mapping
    path = tmp_path / 'roadmap.yml'
    # Write a YAML list
    path.write_text(yaml.dump([1, 2, 3]))
    with pytest.raises(ValueError) as exc:
        parse_roadmap(str(path))
    assert 'Roadmap file must contain a mapping' in str(exc.value)
  
def test_parse_markdown(tmp_path):
    content = '''This is a global description.
# Feature One
Feature one description line1.
Feature one line2.

## Task A
Task A description.

## Task B
Task B.

# Feature Two
## Task X
'''
    path = tmp_path / 'roadmap.md'
    path.write_text(content)
    data = parse_roadmap(str(path))
    # Top-level fields
    assert data['name'] == 'roadmap'
    assert data['description'] == 'This is a global description.'
    # Features
    assert len(data['features']) == 2
    f1 = data['features'][0]
    assert f1['title'] == 'Feature One'
    assert 'Feature one description line1.' in f1['description']
    assert len(f1['tasks']) == 2
    tA = f1['tasks'][0]
    assert tA['title'] == 'Task A'
    assert 'Task A description.' in tA['description']
    tB = f1['tasks'][1]
    assert tB['title'] == 'Task B'
    assert 'Task B.' in tB['description']
    # Second feature
    f2 = data['features'][1]
    assert f2['title'] == 'Feature Two'
    assert len(f2['tasks']) == 1
    tX = f2['tasks'][0]
    assert tX['title'] == 'Task X'
    assert tX['description'] == ''