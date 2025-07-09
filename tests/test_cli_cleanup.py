import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock
from github import GithubException

from scaffold.cli import cli

# Helper class for mock issues
class MockIssue:
    def __init__(self, number, title, body=""):
        self.number = number
        self.title = title
        self.body = body
        # Mock the edit method
        self.edit = MagicMock()

    def __repr__(self):
        return f"<MockIssue #{self.number} '{self.title}'>"

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_github_client_for_cleanup(monkeypatch):
    """Mocks GitHubClient for cleanup command tests."""
    
    # Pre-defined list of issues to be returned by get_all_issues
    mock_issues = [
        MockIssue(1, "A clean title"),
        MockIssue(2, "# A title with one hash"),
        MockIssue(3, "## Another title with hashes"),
        MockIssue(4, "  ### Spaced and hashed title"),
        MockIssue(5, "#NoSpaceHash"),
    ]
    
    class MockedGitHubClientInstance:
        def __init__(self, token, repo_full_name):
            self.repo = MagicMock()
            self.repo.full_name = repo_full_name

        def get_all_issues(self):
            return mock_issues

    monkeypatch.setattr("scaffold.cli.GitHubClient", MockedGitHubClientInstance)
    return mock_issues

def test_sanitize_dry_run(runner, mock_github_client_for_cleanup):
    """Test sanitize with --dry-run."""
    result = runner.invoke(cli, [
        'sanitize',
        '--repo', 'owner/repo',
        '--token', 'fake-token',
        '--dry-run'
    ])
    
    assert result.exit_code == 0
    assert "Found 4 issues to clean up:" in result.output
    assert "#1: 'A clean title'" not in result.output
    assert "  - #2: '# A title with one hash' -> 'A title with one hash'" in result.output
    assert "  - #3: '## Another title with hashes' -> 'Another title with hashes'" in result.output
    assert "  - #4: '  ### Spaced and hashed title' -> 'Spaced and hashed title'" in result.output
    assert "  - #5: '#NoSpaceHash' -> 'NoSpaceHash'" in result.output
    assert "[dry-run] No issues were updated." in result.output
    
    # Check that no edit calls were made
    for issue in mock_github_client_for_cleanup:
        issue.edit.assert_not_called()

def test_sanitize_live_run_confirm_yes(runner, mock_github_client_for_cleanup, monkeypatch):
    """Test sanitize in a live run where user confirms."""
    monkeypatch.setattr("click.confirm", lambda prompt: True)
    
    result = runner.invoke(cli, [
        'sanitize',
        '--repo', 'owner/repo',
        '--token', 'fake-token',
    ])

    assert result.exit_code == 0
    # Check for logs of successful updates for each modified issue
    assert "Updating issue #2..." in result.output
    assert "  Successfully updated issue #2." in result.output
    assert "Updating issue #3..." in result.output
    assert "  Successfully updated issue #3." in result.output
    assert "Updating issue #4..." in result.output
    assert "  Successfully updated issue #4." in result.output
    assert "Updating issue #5..." in result.output
    assert "  Successfully updated issue #5." in result.output

    # Check that clean issue was not touched
    assert "Updating issue #1..." not in result.output

    assert "Cleanup process finished." in result.output
    assert "Successfully updated: 4 issues." in result.output
    
    issue1 = next(i for i in mock_github_client_for_cleanup if i.number == 1)
    issue2 = next(i for i in mock_github_client_for_cleanup if i.number == 2)
    issue3 = next(i for i in mock_github_client_for_cleanup if i.number == 3)
    issue4 = next(i for i in mock_github_client_for_cleanup if i.number == 4)
    issue5 = next(i for i in mock_github_client_for_cleanup if i.number == 5)

    issue1.edit.assert_not_called()
    issue2.edit.assert_called_once_with(title="A title with one hash")
    issue3.edit.assert_called_once_with(title="Another title with hashes")
    issue4.edit.assert_called_once_with(title="Spaced and hashed title")
    issue5.edit.assert_called_once_with(title="NoSpaceHash")

def test_sanitize_live_run_confirm_no(runner, mock_github_client_for_cleanup, monkeypatch):
    """Test sanitize in a live run where user aborts."""
    monkeypatch.setattr("click.confirm", lambda prompt: False)
    
    result = runner.invoke(cli, [
        'sanitize',
        '--repo', 'owner/repo',
        '--token', 'fake-token',
    ])

    assert result.exit_code == 0
    assert "Aborting." in result.output
    
    for issue in mock_github_client_for_cleanup:
        issue.edit.assert_not_called()

def test_sanitize_no_issues_to_clean(runner, monkeypatch):
    """Test sanitize when no issues need title changes."""
    class MockedGitHubClientInstance:
        def __init__(self, token, repo_full_name):
            self.repo = MagicMock()
            self.repo.full_name = repo_full_name
        def get_all_issues(self):
            return [MockIssue(1, "Clean title 1"), MockIssue(2, "Clean title 2")]

    monkeypatch.setattr("scaffold.cli.GitHubClient", MockedGitHubClientInstance)
    
    result = runner.invoke(cli, [
        'sanitize',
        '--repo', 'owner/repo',
        '--token', 'fake-token',
    ])
    
    assert result.exit_code == 0
    assert "No issues with titles that need cleaning up." in result.output


def test_sanitize_fails_on_bad_repo(runner, monkeypatch):
    """Test that sanitize command fails gracefully with a bad repository name."""

    # This mock will raise a 404 exception when GitHubClient is instantiated
    def mock_init_raises_404(self, token, repo_full_name):
        raise GithubException(status=404, data={"message": "Not Found"})

    monkeypatch.setattr("scaffold.cli.GitHubClient.__init__", mock_init_raises_404)

    result = runner.invoke(cli, [
        'sanitize',
        '--repo', 'owner/bad-repo',
        '--token', 'fake-token'
    ])

    assert result.exit_code == 1
    assert "Error: Repository 'owner/bad-repo' not found." in result.output


def test_sanitize_fails_on_bad_token(runner, monkeypatch):
    """Test that sanitize command fails gracefully with a bad token."""

    def mock_init_raises_401(self, token, repo_full_name):
        raise GithubException(status=401, data={"message": "Bad credentials"})

    monkeypatch.setattr("scaffold.cli.GitHubClient.__init__", mock_init_raises_401)

    result = runner.invoke(cli, [
        'sanitize',
        '--repo', 'owner/repo',
        '--token', 'fake-token'
    ])

    assert result.exit_code == 1
    assert "Error: GitHub token is invalid or has insufficient permissions." in result.output
