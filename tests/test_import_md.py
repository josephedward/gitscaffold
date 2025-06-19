import os
import re
import pytest
from click.testing import CliRunner

# Skip if openai SDK is not installed
pytest.importorskip("openai")

from scripts import import_md

class DummyChoice:
    def __init__(self, content):
        self.message = type("M", (), {"content": content})

class DummyResponse:
    def __init__(self, content):
        self.choices = [DummyChoice(content)]

@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "dummy-token")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy-openai-key")
    return

@pytest.fixture
def fake_github(monkeypatch):
    class DummyIssue:
        def __init__(self, number):
            self.number = number

    class DummyRepo:
        def __init__(self):
            self.created = []

        def create_issue(self, title, body=None):
            issue = DummyIssue(len(self.created) + 1)
            self.created.append((title, body))
            return issue

    class DummyGithub:
        def __init__(self, token):
            pass

        def get_repo(self, repo):
            assert repo == "owner/repo"
            return DummyRepo()

    monkeypatch.setattr(import_md, "Github", DummyGithub)
    return

@pytest.fixture
def fake_openai(monkeypatch):
    def fake_create(model, messages, temperature, max_tokens):
        # Extract title from the user message
        user_content = messages[-1]["content"]
        m = re.search(r"Title: (.+)\n", user_content)
        title = m.group(1) if m else ""
        return DummyResponse(f"Enriched {title}")

    # Monkeypatch the ChatCompletion.create method
    monkeypatch.setattr(import_md.openai.chat.completions, "create", fake_create)
    return

def test_import_md_dry_run(fake_openai, fake_github, tmp_path):
    md = tmp_path / "test.md"
    md.write_text("# Title\nContent\n\n# Another\nMore")
    runner = CliRunner()
    result = runner.invoke(import_md.main, ["owner/repo", str(md), "--heading", "1", "--dry-run"])
    assert result.exit_code == 0
    assert "[dry-run] Issue: Title" in result.output
    assert "Enriched Title" in result.output
    assert "[dry-run] Issue: Another" in result.output
    assert "Enriched Another" in result.output

def test_import_md_create(fake_openai, fake_github, tmp_path):
    md = tmp_path / "test2.md"
    md.write_text("## First\nEntry")
    runner = CliRunner()
    result = runner.invoke(import_md.main, ["owner/repo", str(md), "--heading", "2"])
    assert result.exit_code == 0
    assert "Created issue #1: First" in result.output