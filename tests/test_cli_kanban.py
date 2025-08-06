import pytest
from click.testing import CliRunner

from scaffold.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_kanban_export_placeholder(runner, tmp_path):
    """Test that the kanban export command shows a placeholder message."""
    roadmap_file = tmp_path / "ROADMAP.md"
    roadmap_file.write_text("# Test Roadmap")

    result = runner.invoke(cli, [
        'kanban', 'export',
        '--roadmap-file', str(roadmap_file),
        '--board-url', 'http://localhost:3000/board/1'
    ])

    assert result.exit_code == 0
    assert "Kanban export is not yet implemented." in result.output
    assert "Roadmap file:" in result.output
    assert "Board URL:" in result.output
