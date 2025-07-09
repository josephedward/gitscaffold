import pytest
from click.testing import CliRunner
from unittest.mock import MagicMock, patch

from scaffold.cli import cli

# Helper class for mocking GitHub Issue objects
class MockIssue:
    def __init__(self, number, title, created_at, state='open'):
        self.number = number
        self.title = title
        self.created_at = created_at
        self.state = state
        # Mock the edit method
        self.edit = MagicMock()

    def __repr__(self):
        return f"<MockIssue #{self.number} '{self.title}'>"

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_github_client_for_dedup(monkeypatch):
    """Mocks GitHubClient for deduplication command tests."""
    
    mock_issues = [
        MockIssue(1, "Original Issue", "2023-01-01T12:00:00Z"),
        MockIssue(2, "Unique Issue", "2023-01-02T12:00:00Z"),
        MockIssue(3, "Original Issue", "2023-01-03T12:00:00Z"), # duplicate of #1
        MockIssue(4, "Another Duplicate", "2023-01-04T12:00:00Z"),
        MockIssue(5, "Another Duplicate", "2023-01-05T12:00:00Z"), # duplicate of #4
    ]
    # Make a copy to prevent test state leakage
    for issue in mock_issues:
        issue.edit.reset_mock()

    class MockedGitHubClientInstance:
        def __init__(self, token, repo_full_name):
            self.repo = MagicMock()
            self.repo.full_name = repo_full_name
            # Re-implement logic here for test isolation
            # This logic must match the expected behavior of the real implementation
            open_issues = [i for i in mock_issues if i.state == 'open']
            
            issues_by_title = {}
            for issue in open_issues:
                if issue.title not in issues_by_title:
                    issues_by_title[issue.title] = []
                issues_by_title[issue.title].append(issue)

            self.duplicates_found = {}
            for title, issues in issues_by_title.items():
                if len(issues) > 1:
                    issues.sort(key=lambda i: i.number)
                    original = issues[0]
                    duplicates = issues[1:]
                    self.duplicates_found[title] = {
                        'original': original,
                        'duplicates': duplicates
                    }
        
        def find_duplicate_issues(self):
            return self.duplicates_found

    # Patch the GitHubClient class in the module where it's used (scaffold.cli)
    mock_client_class = MagicMock(return_value=MockedGitHubClientInstance("fake_token", "owner/repo"))
    monkeypatch.setattr('scaffold.cli.GitHubClient', mock_client_class)
    return mock_client_class, mock_issues

def test_deduplicate_dry_run(runner, mock_github_client_for_dedup):
    """Test deduplicate issues in dry-run mode."""
    mock_client, mock_issues = mock_github_client_for_dedup
    result = runner.invoke(cli, ['deduplicate', '--repo', 'owner/repo', '--dry-run', '--token', 'fake'])

    assert result.exit_code == 0
    assert "Found 2 sets of duplicate issues" in result.output
    assert "Original Issue" in result.output
    assert "Original: #1" in result.output
    assert "Duplicate to close: #3" in result.output
    assert "Another Duplicate" in result.output
    assert "Original: #4" in result.output
    assert "Duplicate to close: #5" in result.output
    assert "[dry-run] Would close 2 issues. No changes were made." in result.output

    # Ensure no issues were closed
    for issue in mock_issues:
        issue.edit.assert_not_called()

def test_deduplicate_live_run_confirm_yes(runner, mock_github_client_for_dedup):
    """Test deduplicate issues in live mode with confirmation."""
    mock_client, mock_issues = mock_github_client_for_dedup
    result = runner.invoke(cli, ['deduplicate', '--repo', 'owner/repo', '--token', 'fake'], input='y\n')

    assert result.exit_code == 0
    assert "Proceed with closing 2 duplicate issues" in result.output
    assert "Successfully closed: 2 issues." in result.output
    
    # issue #3 and #5 should be closed
    issue_3 = next(i for i in mock_issues if i.number == 3)
    issue_5 = next(i for i in mock_issues if i.number == 5)
    issue_3.edit.assert_called_once_with(state='closed')
    issue_5.edit.assert_called_once_with(state='closed')

    # others not called
    issue_1 = next(i for i in mock_issues if i.number == 1)
    issue_2 = next(i for i in mock_issues if i.number == 2)
    issue_4 = next(i for i in mock_issues if i.number == 4)
    issue_1.edit.assert_not_called()
    issue_2.edit.assert_not_called()
    issue_4.edit.assert_not_called()


def test_deduplicate_live_run_confirm_no(runner, mock_github_client_for_dedup):
    """Test deduplicate issues in live mode with user aborting."""
    mock_client, mock_issues = mock_github_client_for_dedup
    result = runner.invoke(cli, ['deduplicate', '--repo', 'owner/repo', '--token', 'fake'], input='n\n')

    assert result.exit_code == 0
    assert "Proceed with closing 2 duplicate issues" in result.output
    assert "Aborting." in result.output
    
    for issue in mock_issues:
        issue.edit.assert_not_called()


@patch('scaffold.cli.GitHubClient')
def test_deduplicate_no_duplicates_found(MockGitHubClient, runner):
    """Test deduplication when no duplicate issues are found."""
    mock_instance = MockGitHubClient.return_value
    mock_instance.find_duplicate_issues.return_value = {}

    result = runner.invoke(cli, ['deduplicate', '--repo', 'owner/repo', '--token', 'fake'])

    assert result.exit_code == 0
    assert "No duplicate open issues found." in result.output
    mock_instance.find_duplicate_issues.assert_called_once()
