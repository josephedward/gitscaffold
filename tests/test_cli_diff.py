import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch
from pathlib import Path

from scaffold.cli import cli

SAMPLE_ROADMAP_MD = """\
# Test Project for Diff

## Features

### Feature A
Core feature.

#### Task A.1
#### Task A.2

### Feature B
"""


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def sample_roadmap_file(tmp_path):
    """Creates a temporary roadmap Markdown file."""
    roadmap_path = tmp_path / "ROADMAP.md"
    roadmap_path.write_text(SAMPLE_ROADMAP_MD)
    return roadmap_path


@pytest.fixture
def mock_github_client_for_diff(monkeypatch):
    """Mocks GitHubClient for diff command tests."""
    mock_client_instance = MagicMock()
    monkeypatch.setattr('scaffold.cli.GitHubClient', lambda token, repo: mock_client_instance)
    return mock_client_instance


def test_diff_no_differences(runner, sample_roadmap_file, mock_github_client_for_diff):
    """Test `diff` when local roadmap and GitHub are in sync."""
    mock_github_client_for_diff.get_all_issue_titles.return_value = {
        "Feature A",
        "Task A.1",
        "Task A.2",
        "Feature B",
    }

    result = runner.invoke(cli, ['diff', str(sample_roadmap_file), '--repo', 'owner/repo', '--token', 'fake'])

    assert result.exit_code == 0
    assert "✓ No missing issues on GitHub." in result.output
    assert "✓ No extra issues on GitHub." in result.output
    mock_github_client_for_diff.get_all_issue_titles.assert_called_once()


def test_diff_issues_missing_on_github(runner, sample_roadmap_file, mock_github_client_for_diff):
    """Test `diff` when some issues are missing from GitHub."""
    mock_github_client_for_diff.get_all_issue_titles.return_value = {
        "Feature A",
        "Task A.1",
    }

    result = runner.invoke(cli, ['diff', str(sample_roadmap_file), '--repo', 'owner/repo', '--token', 'fake'])

    assert result.exit_code == 0
    assert "Items in local roadmap but not on GitHub (missing):" in result.output
    assert "  - Feature B" in result.output
    assert "  - Task A.2" in result.output
    assert "✓ No extra issues on GitHub." in result.output
    mock_github_client_for_diff.get_all_issue_titles.assert_called_once()


def test_diff_issues_on_github_not_in_roadmap(runner, sample_roadmap_file, mock_github_client_for_diff):
    """Test `diff` when extra issues are found on GitHub."""
    mock_github_client_for_diff.get_all_issue_titles.return_value = {
        "Feature A",
        "Task A.1",
        "Task A.2",
        "Feature B",
        "Extra Issue 1",
        "Extra Issue 2",
    }

    result = runner.invoke(cli, ['diff', str(sample_roadmap_file), '--repo', 'owner/repo', '--token', 'fake'])

    assert result.exit_code == 0
    assert "✓ No missing issues on GitHub." in result.output
    assert "Items on GitHub but not in local roadmap (extra):" in result.output
    assert "  - Extra Issue 1" in result.output
    assert "  - Extra Issue 2" in result.output
    mock_github_client_for_diff.get_all_issue_titles.assert_called_once()


def test_diff_shows_both_missing_and_extra(runner, sample_roadmap_file, mock_github_client_for_diff):
    """Test `diff` when there are both missing and extra issues."""
    mock_github_client_for_diff.get_all_issue_titles.return_value = {
        "Feature A",
        "Task A.1",
        "Extra Issue 1",
    }

    result = runner.invoke(cli, ['diff', str(sample_roadmap_file), '--repo', 'owner/repo', '--token', 'fake'])

    assert result.exit_code == 0
    assert "Items in local roadmap but not on GitHub (missing):" in result.output
    assert "  - Feature B" in result.output
    assert "  - Task A.2" in result.output
    assert "Items on GitHub but not in local roadmap (extra):" in result.output
    assert "  - Extra Issue 1" in result.output
    mock_github_client_for_diff.get_all_issue_titles.assert_called_once()


def test_diff_unstructured_md_prompts_for_ai(runner, tmp_path, mock_github_client_for_diff):
    """Test `diff` with unstructured MD prompts for AI and works."""
    unstructured_md = "# My Project\nThis is a plan with some items.\n- An item to do.\n- Another thing."
    roadmap_path = tmp_path / "unstructured.md"
    roadmap_path.write_text(unstructured_md)
    
    mock_github_client_for_diff.get_all_issue_titles.return_value = {"An item to do."}
    
    with patch('scaffold.cli.extract_issues_from_markdown') as mock_extract, \
         patch('click.confirm') as mock_confirm, \
         patch('scaffold.cli.get_openai_api_key', return_value='fake-key'):
        
        mock_extract.return_value = [{'title': 'An item to do.'}, {'title': 'Another thing.'}]
        mock_confirm.return_value = True # User says yes to AI

        result = runner.invoke(cli, ['diff', str(roadmap_path), '--repo', 'owner/repo', '--token', 'fake'])

    assert result.exit_code == 0
    mock_confirm.assert_called()
    mock_extract.assert_called_once()
    assert "Items in local roadmap but not on GitHub (missing):" in result.output
    assert "  - Another thing." in result.output
