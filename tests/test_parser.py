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