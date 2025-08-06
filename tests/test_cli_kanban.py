import pytest
from click.testing import CliRunner

from scaffold.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_vibe_push_placeholder(runner):
    """Test that the vibe push command shows a placeholder message."""
    result = runner.invoke(cli, [
        'vibe', 'push',
        '--repo', 'owner/repo',
        '--board', 'My Board'
    ])

    assert result.exit_code == 0
    assert "Vibe Kanban push is not yet implemented." in result.output
    assert "Repo: owner/repo" in result.output
    assert "Board: My Board" in result.output

def test_vibe_pull_placeholder(runner):
    """Test that the vibe pull command shows a placeholder message."""
    result = runner.invoke(cli, [
        'vibe', 'pull',
        '--repo', 'owner/repo',
        '--board', 'My Board'
    ])

    assert result.exit_code == 0
    assert "Vibe Kanban pull is not yet implemented." in result.output
    assert "Repo: owner/repo" in result.output
    assert "Board: My Board" in result.output
