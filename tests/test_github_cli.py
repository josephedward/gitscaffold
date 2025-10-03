import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import scaffold.github_cli as ghcli


def test_find_gh_executable_prefers_path(monkeypatch):
    monkeypatch.setattr(ghcli.shutil, "which", lambda cmd: "/usr/bin/gh")
    # Ensure no fallback is used
    monkeypatch.setattr(ghcli.Path, "home", lambda: Path("/nonexistent"))
    assert ghcli.find_gh_executable() == "/usr/bin/gh"


def test_find_gh_executable_home_bin(tmp_path, monkeypatch):
    bin_dir = tmp_path / ".gitscaffold" / "bin"
    bin_dir.mkdir(parents=True)
    gh_path = bin_dir / "gh"
    gh_path.write_text("#!/bin/sh\nexit 0\n")
    os.chmod(gh_path, 0o755)

    monkeypatch.setattr(ghcli.shutil, "which", lambda cmd: None)
    monkeypatch.setattr(ghcli.Path, "home", lambda: tmp_path)

    found = ghcli.find_gh_executable()
    assert found is not None
    assert Path(found) == gh_path


def test_githubcli_version(monkeypatch):
    # Pretend gh exists at a fixed path
    monkeypatch.setattr(ghcli, "find_gh_executable", lambda: "/bin/gh")

    class FakeCP:
        def __init__(self, stdout):
            self.stdout = stdout

    def fake_run(cmd, check=True, capture_output=True, text=True):
        assert cmd[:1] == ["/bin/gh"]
        assert cmd[1:] == ["--version"]
        return FakeCP("gh version 2.45.0")

    monkeypatch.setattr(ghcli.subprocess, "run", fake_run)

    cli = ghcli.GitHubCLI()
    assert cli.version().startswith("gh version")


def test_list_issues_builds_json_and_parses(monkeypatch):
    monkeypatch.setattr(ghcli, "find_gh_executable", lambda: "/bin/gh")

    calls = []

    class FakeCP:
        def __init__(self, stdout):
            self.stdout = stdout

    def fake_run(cmd, check=True, capture_output=True, text=True):
        calls.append(cmd)
        return FakeCP("[{\"number\": 1, \"title\": \"T\"}]")

    monkeypatch.setattr(ghcli.subprocess, "run", fake_run)

    cli = ghcli.GitHubCLI()
    items = cli.list_issues("owner/repo", state="open", limit=5)
    assert isinstance(items, list)
    assert items and items[0]["number"] == 1

    # Verify command structure includes expected flags
    assert calls, "No gh calls captured"
    cmd = calls[-1]
    assert cmd[:2] == ["/bin/gh", "issue"]
    assert "--repo" in cmd and "owner/repo" in cmd
    assert "--state" in cmd and "open" in cmd
    assert "--limit" in cmd and "5" in cmd
    assert "--json" in cmd

