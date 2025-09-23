import types
from click.testing import CliRunner
import pytest

import scaffold.scripts.import_md as vendored


def _fake_openai_resp(text: str):
    class _Msg:
        def __init__(self, content):
            self.content = content
    class _Choice:
        def __init__(self, content):
            self.message = _Msg(content)
    class _Resp:
        def __init__(self, content):
            self.choices = [_Choice(content)]
    return _Resp(text)


@pytest.fixture
def essential_env(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "t")
    monkeypatch.setenv("OPENAI_API_KEY", "k")


def test_vendored_import_md_dry_run(tmp_path, monkeypatch, essential_env):
    md = tmp_path / "notes.md"
    md.write_text("# First\nBody\n# Second\nMore")

    fake_openai = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(
                create=lambda **kwargs: _fake_openai_resp("enriched")
            )
        )
    )
    monkeypatch.setattr(vendored, "openai", fake_openai)

    class FakeRepo:
        full_name = "owner/repo"

    class FakeGithub:
        def __init__(self, token):
            pass
        def get_repo(self, repo):
            return FakeRepo()

    monkeypatch.setattr(vendored, "Github", FakeGithub)

    runner = CliRunner()
    res = runner.invoke(vendored.main, [
        "owner/repo",
        str(md),
        "--token", "t",
        "--dry-run",
        "--heading", "1",
        "--verbose",
    ])

    assert res.exit_code == 0, res.output
    assert "[dry-run] Issue: First" in res.output
    assert "[dry-run] Issue: Second" in res.output


def test_vendored_import_md_live_creates(tmp_path, monkeypatch):
    md = tmp_path / "notes.md"
    md.write_text("# OnlyOne\nBody")

    fake_openai = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(
                create=lambda **kwargs: _fake_openai_resp("generated body")
            )
        )
    )

    class FakeIssue:
        def __init__(self, number):
            self.number = number

    class FakeRepo:
        def create_issue(self, title, body):
            assert title == "OnlyOne"
            assert body == "generated body"
            return FakeIssue(1)

    class FakeGithub:
        def __init__(self, token):
            pass
        def get_repo(self, repo):
            assert repo == "owner/repo"
            return FakeRepo()

    monkeypatch.setattr(vendored, "openai", fake_openai)
    monkeypatch.setattr(vendored, "Github", FakeGithub)

    runner = CliRunner()
    res = runner.invoke(vendored.main, [
        "owner/repo",
        str(md),
        "--token", "t",
        "--openai-key", "k",
        "--heading", "1",
    ])

    assert res.exit_code == 0, res.output
    assert "Created issue #1: OnlyOne" in res.output


def test_vendored_import_md_no_headings(tmp_path, monkeypatch):
    md = tmp_path / "notes.md"
    md.write_text("no headings here")

    fake_openai = types.SimpleNamespace(
        chat=types.SimpleNamespace(
            completions=types.SimpleNamespace(
                create=lambda **kwargs: _fake_openai_resp("irrelevant")
            )
        )
    )
    monkeypatch.setattr(vendored, "openai", fake_openai)

    class FakeRepo:
        full_name = "owner/repo"

    class FakeGithub:
        def __init__(self, token):
            pass
        def get_repo(self, repo):
            return FakeRepo()

    monkeypatch.setattr(vendored, "Github", FakeGithub)

    runner = CliRunner()
    res = runner.invoke(vendored.main, [
        "owner/repo",
        str(md),
        "--token", "t",
        "--openai-key", "k",
        "--heading", "1",
    ])

    assert res.exit_code != 0
    assert "No headings found; nothing to import." in res.output
