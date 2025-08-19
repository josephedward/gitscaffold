import os
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from scaffold.cli import cli


@pytest.fixture(autouse=True)
def patch_subprocess(monkeypatch):
    calls = []
    class DummyResult:
        def __init__(self):
            self.returncode = 0
            self.stdout = "dummy output"
            self.stderr = ""

    def fake_run(cmd, capture_output, text, timeout, encoding):
        calls.append(cmd)
        return DummyResult()

    monkeypatch.setattr(subprocess, 'run', fake_run)
    return calls


def test_gemini_process_issues(tmp_path, patch_subprocess, monkeypatch):
    # Provide a fake GEMINI_API_KEY to suppress warning
    monkeypatch.setenv('GEMINI_API_KEY', 'fake-key')
    # Create a sample issues file
    issues = ["Fix foo", "Add bar"]
    issues_file = tmp_path / "issues.txt"
    issues_file.write_text("\n".join(issues))
    results_dir = tmp_path / "results"
    # Invoke the CLI command
    runner = CliRunner()
    result = runner.invoke(
        cli,
        ['gemini', 'process-issues', str(issues_file),
         '--results-dir', str(results_dir),
         '--timeout', '1']
    )
    assert result.exit_code == 0, result.output
    # Ensure subprocess.run was called for each issue
    assert len(patch_subprocess) == len(issues)
    # Ensure log files are created for each issue
    log_files = list(results_dir.glob('gemini_issue_*.log'))
    assert len(log_files) == len(issues)