import pytest
from click.testing import CliRunner
from unittest.mock import patch

from scaffold.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@patch('scaffold.cli.VibeKanbanClient')
@patch('scaffold.cli.GitHubClient')
def test_vibe_push_invokes_stub(mock_gh_client_class, mock_kanban_client_class, runner):
    """Test that `vibe push` command calls the VibeKanbanClient with correct arguments."""
    mock_gh_instance = mock_gh_client_class.return_value
    # The push command in cli.py was updated to filter issues, so we need to mock get_issues.
    mock_gh_instance.repo.get_issues.return_value = [{'title': 'Test Issue'}]
    mock_gh_instance._find_milestone.return_value = None # Assume milestone not found for simplicity

    mock_kanban_instance = mock_kanban_client_class.return_value
    mock_kanban_instance.push_issues_to_board.side_effect = NotImplementedError("push_issues_to_board")

    result = runner.invoke(cli, [
        'vibe', 'push',
        '--repo', 'owner/repo',
        '--board', 'My Awesome Board',
        '--kanban-api', 'http://fake.api/v1',
        '--token', 'fake-cli-token'
    ])

    assert result.exit_code == 0
    mock_gh_client_class.assert_called_with('fake-cli-token', 'owner/repo')
    mock_kanban_client_class.assert_called_with(api_url='http://fake.api/v1', token=None) # VIBE_KANBAN_TOKEN is not set
    mock_kanban_instance.push_issues_to_board.assert_called_with(
        board_name='My Awesome Board',
        issues=[{'title': 'Test Issue'}]
    )
    assert "Functionality not implemented: push_issues_to_board" in result.output


@patch('scaffold.cli.get_github_token', return_value='fake-token')
@patch('scaffold.cli.VibeKanbanClient')
@patch('scaffold.cli.GitHubClient')
def test_vibe_pull_invokes_stub(mock_gh_client_class, mock_kanban_client_class, mock_get_token, runner):
    """Test that `vibe pull` command calls the VibeKanbanClient."""
    mock_kanban_instance = mock_kanban_client_class.return_value
    mock_kanban_instance.pull_board_status.side_effect = NotImplementedError("pull_board_status")

    result = runner.invoke(cli, [
        'vibe', 'pull',
        '--repo', 'owner/repo',
        '--board', 'My Cool Board',
        '--kanban-api', 'http://fake.api/v1'
    ])

    assert result.exit_code == 0
    mock_gh_client_class.assert_called_with('fake-token', 'owner/repo')
    mock_kanban_client_class.assert_called_with(api_url='http://fake.api/v1', token=None)
    mock_kanban_instance.pull_board_status.assert_called_with(board_name='My Cool Board', bidirectional=False)
    assert "Functionality not implemented: pull_board_status" in result.output
