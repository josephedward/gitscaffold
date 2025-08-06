import pytest
from click.testing import CliRunner

from scaffold.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_vibe_help_lists_push_and_pull(runner):
    result = runner.invoke(cli, ['vibe', '--help'])
    assert result.exit_code == 0
    output = result.output
    assert 'push' in output
    assert 'pull' in output