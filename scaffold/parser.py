"""Parser for roadmap files."""

import yaml

def parse_roadmap(roadmap_file):
    """Parse the roadmap file (YAML or JSON) and return a dictionary."""
    with open(roadmap_file, 'r') as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Roadmap file must contain a mapping at the top level, got {type(data).__name__}")
    return data