import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from scaffold.cli import cli


# Helper classes for mock issues
class MockIssue:
    def __init__(self, number, title, body="", url="", state="open", labels=None):
        self.number = number
        self.title = title
        self.body = body
        self.html_url = url
        self.state = state
        self.labels = labels or []

class MockLabel:
    def __init__(self, name):
        self.name = name


@pytest.fixture
def runner():
    return CliRunner()


@patch('scaffold.cli.VibeKanbanClient')
@patch('scaffold.cli.GitHubClient')
def test_vibe_push_invokes_stub(mock_gh_client_class, mock_kanban_client_class, runner):
    """Test that `vibe push` command calls the VibeKanbanClient with correct arguments."""
    mock_gh_instance = mock_gh_client_class.return_value
    # Use a mock issue object instead of a dict
    mock_issue = MockIssue(1, "Test Issue", body="Test body", url="http://example.com/1", labels=[MockLabel("bug")])
    mock_gh_instance.repo.get_issues.return_value = [mock_issue]
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
    
    # Assert with correctly serialized issue data
    expected_issue_data = {
        "number": 1,
        "title": "Test Issue",
        "body": "Test body",
        "url": "http://example.com/1",
        "state": "open",
        "labels": ["bug"],
    }
    mock_kanban_instance.push_issues_to_board.assert_called_with(
        board_name='My Awesome Board',
        issues=[expected_issue_data]
    )
    assert "Functionality not implemented: push_issues_to_board" in result.output


@patch('scaffold.cli.VibeKanbanClient')
@patch('scaffold.cli.GitHubClient')
def test_vibe_pull_invokes_stub(mock_gh_client_class, mock_kanban_client_class, runner):
    """Test that `vibe pull` command calls the VibeKanbanClient."""
    mock_kanban_instance = mock_kanban_client_class.return_value
    mock_kanban_instance.pull_board_status.side_effect = NotImplementedError("pull_board_status")

    result = runner.invoke(cli, [
        'vibe', 'pull',
        '--repo', 'owner/repo',
        '--board', 'My Cool Board',
        '--kanban-api', 'http://fake.api/v1',
        '--token', 'fake-cli-token', # Pass token directly to avoid get_github_token mock issues
    ])

    assert result.exit_code == 0
    mock_gh_client_class.assert_called_with('fake-cli-token', 'owner/repo')
    mock_kanban_client_class.assert_called_with(api_url='http://fake.api/v1', token=None)
    mock_kanban_instance.pull_board_status.assert_called_with(board_name='My Cool Board', bidirectional=False)
    assert "Functionality not implemented: pull_board_status" in result.output
