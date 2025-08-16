import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock

from scaffold.cli import cli
from scaffold.github import GitHubClient # To mock its methods

class MockIssue:
    def __init__(self, number, title):
        self.number = number
        self.title = title

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_github_client_for_import(monkeypatch):
    """Mocks GitHubClient for import-md command tests."""
    created_issues = []

    class MockedGitHubClientInstance:
        def __init__(self, token, repo_full_name):
            self.repo = MagicMock()
            self.repo.full_name = repo_full_name

        def create_issue(self, title, body, **kwargs):
            issue = MockIssue(number=len(created_issues) + 1, title=title)
            created_issues.append({'title': title, 'body': body})
            return issue
        
    monkeypatch.setattr("scaffold.cli.GitHubClient", MockedGitHubClientInstance)
    return created_issues

@pytest.fixture(autouse=True)
def mock_api_keys(monkeypatch):
    monkeypatch.setattr("scaffold.cli.get_github_token", lambda: "fake-gh-token")
    monkeypatch.setattr("scaffold.cli.get_openai_api_key", lambda: "fake-openai-key")
    monkeypatch.setattr("scaffold.cli.get_gemini_api_key", lambda: "fake-gemini-key")

def test_import_md_openai_dry_run(runner, tmp_path, monkeypatch):
    md_content = "- an issue to import"
    md_file = tmp_path / "test.md"
    md_file.write_text(md_content)

    def mock_extract(md_file, provider, api_key, model_name, temperature):
        assert provider == 'openai'
        return [{'title': 'an issue to import', 'description': 'openai body'}]
    
    monkeypatch.setattr("scaffold.cli.extract_issues_from_markdown", mock_extract)

    result = runner.invoke(cli, [
        'import-md', 'owner/repo', str(md_file), '--dry-run'
    ])

    assert result.exit_code == 0
    assert "[dry-run] Issue: an issue to import" in result.output
    assert "openai body" in result.output

def test_import_md_gemini_live_run(runner, tmp_path, mock_github_client_for_import, monkeypatch):
    md_content = "- another issue to import"
    md_file = tmp_path / "test.md"
    md_file.write_text(md_content)

    def mock_extract(md_file, provider, api_key, model_name, temperature):
        assert provider == 'gemini'
        return [{'title': 'another issue to import', 'description': 'gemini body'}]
    
    monkeypatch.setattr("scaffold.cli.extract_issues_from_markdown", mock_extract)

    result = runner.invoke(cli, [
        'import-md', 'owner/repo', str(md_file), '--ai-provider', 'gemini', '--yes'
    ])

    assert result.exit_code == 0
    assert "Successfully created issue #1." in result.output
    assert len(mock_github_client_for_import) == 1
    assert mock_github_client_for_import[0]['title'] == 'another issue to import'
    assert mock_github_client_for_import[0]['body'] == 'gemini body'
