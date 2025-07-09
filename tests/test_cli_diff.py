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
    assert "ExtraIssue" in result.output