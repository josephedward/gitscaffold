import pytest
from click.testing import CliRunner
from github import GithubException

from scaffold.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

class MockIssue:
    def __init__(self, number, title, body=""):
        self.number = number
        self.title = title
        self.body = body
        self.edited_body = None

    def edit(self, body):
        self.edited_body = body

@pytest.fixture
def mock_github_repo(monkeypatch):
    mock_issue_123 = MockIssue(123, "Test Issue Title", "Old body")
    
    class MockRepo:
        def get_issue(self, number):
            if number == 123:
                return mock_issue_123
            raise GithubException(404, "Not Found")

    class MockGithub:
        def get_repo(self, repo_name):
            return MockRepo()

    monkeypatch.setattr("scaffold.cli.Github", lambda token: MockGithub())
    return mock_issue_123

@pytest.fixture
def mock_roadmap_parser(monkeypatch):
    roadmap_data = {
        "Test Issue Title": {
            "context": "Phase 1: Foundation",
            "goal": ["Build the core"],
            "tasks": ["Do the thing"],
            "deliverables": ["A working thing"]
        }
    }
    monkeypatch.setattr("scaffold.cli._enrich_parse_roadmap", lambda path: roadmap_data)
    # also need to patch get_github_token and get_gemini_api_key
    monkeypatch.setattr("scaffold.cli.get_github_token", lambda: "fake-token")
    monkeypatch.setattr("scaffold.cli.get_gemini_api_key", lambda: "fake-gemini-key")
    monkeypatch.setattr("scaffold.cli.get_openai_api_key", lambda: "fake-openai-key")


def test_enrich_issue_openai_dry_run(runner, mock_github_repo, mock_roadmap_parser, monkeypatch):
    """Test `enrich issue` with OpenAI in dry-run mode."""
    
    def mock_llm_call(title, existing_body, ctx, provider, api_key):
        assert provider == 'openai'
        return f"Enriched with OpenAI for '{title}'"
    
    monkeypatch.setattr("scaffold.cli._enrich_call_llm", mock_llm_call)
    
    result = runner.invoke(cli, [
        'enrich', '--ai-provider', 'openai', 'issue',
        '--repo', 'owner/repo',
        '--issue', '123'
        # No --apply
    ])
    
    assert result.exit_code == 0
    assert "Enriched with OpenAI for 'Test Issue Title'" in result.output
    assert mock_github_repo.edited_body is None # Should not be applied

def test_enrich_issue_gemini_apply(runner, mock_github_repo, mock_roadmap_parser, monkeypatch):
    """Test `enrich issue` with Gemini and apply the changes."""

    def mock_llm_call(title, existing_body, ctx, provider, api_key):
        assert provider == 'gemini'
        return f"Enriched with Gemini for '{title}'"
    
    monkeypatch.setattr("scaffold.cli._enrich_call_llm", mock_llm_call)
    
    result = runner.invoke(cli, [
        'enrich', '--ai-provider', 'gemini', 'issue',
        '--repo', 'owner/repo',
        '--issue', '123',
        '--apply'
    ])
    
    assert result.exit_code == 0
    assert "Enriched with Gemini for 'Test Issue Title'" in result.output
    assert "Issue #123 updated." in result.output
    assert mock_github_repo.edited_body == "Enriched with Gemini for 'Test Issue Title'"
