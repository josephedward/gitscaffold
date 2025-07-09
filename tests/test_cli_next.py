import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch
from datetime import datetime

from scaffold.cli import cli

# Mock Milestone and Issue classes to simulate GitHub objects
class MockMilestone:
    def __init__(self, title, due_on=None, open_issues=1):
        self.title = title
        # PyGitHub returns datetime objects for due_on
        self.due_on = datetime.strptime(due_on, "%Y-%m-%d") if due_on else None
        self.open_issues = open_issues

class MockIssue:
    def __init__(self, number, title, assignees=None):
        self.number = number
        self.title = title
        self.assignees = []
        if assignees:
            for assignee_login in assignees:
                mock_assignee = MagicMock()
                mock_assignee.login = assignee_login
                self.assignees.append(mock_assignee)

@pytest.fixture
def runner():
    """Fixture for invoking command-line interfaces."""
    return CliRunner()

@pytest.fixture
def mock_github_client_for_next(monkeypatch):
    """Mocks GitHubClient for `next` command tests."""
    mock_client_instance = MagicMock()

    class MockedGitHubClient:
        def __init__(self, token, repo_full_name):
            # Pass through the mock instance to be used in tests
            self.__class__.instance = mock_client_instance
            mock_client_instance.repo_full_name = repo_full_name
        
        def get_next_action_items(self):
            # Delegate to the instance so we can control it from tests
            return self.__class__.instance.get_next_action_items()

    monkeypatch.setattr('scaffold.cli.GitHubClient', MockedGitHubClient)
    return mock_client_instance


def test_next_no_active_milestones(runner, mock_github_client_for_next):
    """Test `next` command when no active milestones are found."""
    # Configure mock to return no milestone
    mock_github_client_for_next.get_next_action_items.return_value = (None, [])

    result = runner.invoke(cli, ['next', '--repo', 'owner/repo'])
    
    assert result.exit_code == 0
    assert "No active milestones with open issues found." in result.output
    mock_github_client_for_next.get_next_action_items.assert_called_once()


def test_next_with_active_milestone_and_issues(runner, mock_github_client_for_next):
    """Test `next` command with an active milestone and open issues."""
    milestone = MockMilestone("v1.0 Launch", due_on="2025-12-31")
    issues = [
        MockIssue(101, "Finalize documentation"),
        MockIssue(102, "Deploy to production", assignees=['testuser'])
    ]
    mock_github_client_for_next.get_next_action_items.return_value = (milestone, issues)

    result = runner.invoke(cli, ['next', '--repo', 'owner/repo'])
    
    assert result.exit_code == 0
    assert "Next actions from milestone: 'v1.0 Launch' (due 2025-12-31)" in result.output
    assert "- #101: Finalize documentation" in result.output
    assert "- #102: Deploy to production (assigned to @testuser)" in result.output
    mock_github_client_for_next.get_next_action_items.assert_called_once()

def test_next_milestone_with_no_due_date(runner, mock_github_client_for_next):
    """Test `next` command with a milestone that has no due date."""
    milestone = MockMilestone("Backlog")
    issues = [MockIssue(201, "Refactor core module")]
    mock_github_client_for_next.get_next_action_items.return_value = (milestone, issues)

    result = runner.invoke(cli, ['next', '--repo', 'owner/repo'])

    assert result.exit_code == 0
    assert "Next actions from milestone: 'Backlog' (no due date)" in result.output
    assert "- #201: Refactor core module" in result.output

def test_next_with_no_issues_in_milestone(runner, mock_github_client_for_next):
    """Test `next` command when the earliest milestone has no open issues listed (edge case)."""
    # The get_next_action_items function filters for m.open_issues > 0, so this case
    # where it returns a milestone but no issues should be handled gracefully.
    milestone = MockMilestone("Future Ideas", due_on="2026-01-01")
    mock_github_client_for_next.get_next_action_items.return_value = (milestone, [])

    result = runner.invoke(cli, ['next', '--repo', 'owner/repo'])

    assert result.exit_code == 0
    assert "Next actions from milestone: 'Future Ideas'" in result.output
    assert "No open issues found in this milestone." in result.output


@patch('scaffold.cli.get_repo_from_git_config', return_value='git/repo')
def test_next_without_repo_flag_uses_git_config(mock_get_repo, runner, mock_github_client_for_next):
    """Test that `next` command uses repo from git config if --repo is omitted."""
    mock_github_client_for_next.get_next_action_items.return_value = (None, [])
    
    result = runner.invoke(cli, ['next'])

    assert result.exit_code == 0
    assert "Using repository from current git config: git/repo" in result.output
    mock_get_repo.assert_called_once()
    assert mock_github_client_for_next.repo_full_name == 'git/repo'


@patch('scaffold.cli.get_repo_from_git_config', return_value=None)
def test_next_fails_if_no_repo_provided_or_found(mock_get_repo, runner):
    """Test `next` command fails if no repo is given and it can't be found in git config."""
    result = runner.invoke(cli, ['next'])
    
    assert result.exit_code == 1
    assert "Could not determine repository from git config. Please use --repo." in result.output
    mock_get_repo.assert_called_once()

@patch('scaffold.cli.get_github_token', return_value=None)
def test_next_fails_if_no_token(mock_get_token, runner, monkeypatch):
    """Test `next` command fails if no token is provided."""
    # We must unset GITHUB_TOKEN env var, because the --token option uses it as a default.
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    
    # Here we don't provide a token, so the command calls get_github_token.
    # We mock it to return None to simulate no token being available.
    result = runner.invoke(cli, ['next', '--repo', 'owner/repo'])

    assert result.exit_code == 1
    assert "GitHub token is required." in result.output
    mock_get_token.assert_called_once()
