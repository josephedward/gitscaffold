import pytest
from click.testing import CliRunner
from unittest.mock import patch

from scaffold.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_diff_command(tmp_path, runner, monkeypatch):
    # Prepare a temporary roadmap YAML file with features and tasks
    roadmap = tmp_path / "roadmap.yaml"
    roadmap.write_text(
        "name: Dummy\n"
        "description: Dummy project\n"
        "milestones: []\n"
        "features:\n"
        "  - title: FeatureA\n"
        "    tasks:\n"
        "      - title: TaskA1\n"
        "  - title: FeatureB\n",
        encoding="utf-8"
    )
    # Mock GitHubClient.get_all_issue_titles to simulate existing issues
    class DummyClient:
        def __init__(self, token, repo):
            pass
        def get_all_issue_titles(self):
            return {"FeatureA", "ExtraIssue"}
    monkeypatch.setattr("scaffold.cli.GitHubClient", DummyClient)
    # Invoke diff command
    result = runner.invoke(
        cli,
        ["diff", str(roadmap), "--repo", "owner/repo", "--token", "fake-token"]
    )
    assert result.exit_code == 0
    # It should list missing items: TaskA1 and FeatureB
    assert "TaskA1" in result.output
    assert "FeatureB" in result.output
    # It should list extra items: ExtraIssue
    assert "ExtraIssue" in result.outputimport pytest
from click.testing import CliRunner
from unittest.mock import MagicMock

from scaffold.cli import cli

SAMPLE_ROADMAP_MD = """\
# Feature A
Core feature.

## Task A.1
## Task A.2

# Feature B
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
