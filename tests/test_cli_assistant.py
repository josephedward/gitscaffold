import pytest
from click.testing import CliRunner
from unittest.mock import patch, call, ANY
import subprocess

from scaffold.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_assistant_passthrough(runner):
    """Test that `assistant` command passes arguments to aider."""
    with patch('scaffold.cli.subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        result = runner.invoke(cli, ['assistant', 'some/file.py', '--message', 'a fix'])
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once_with(
            ['aider', 'some/file.py', '--message', 'a fix'],
            env=ANY,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )

def test_assistant_process_issues_success(runner, tmp_path):
    """Test the process-issues subcommand with successful execution."""
    issues_file = tmp_path / "issues.txt"
    issues_file.write_text("issue 1\nissue 2")
    
    with patch('scaffold.cli.subprocess.run') as mock_run:
        # Mock successful execution
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = "stdout"
        mock_run.return_value.stderr = ""

        result = runner.invoke(cli, ['assistant', 'process-issues', str(issues_file)])
        
        assert result.exit_code == 0, result.output
        assert "Processing: issue 1" in result.output
        assert "✅ SUCCESS: issue 1" in result.output
        assert "Processing: issue 2" in result.output
        assert "✅ SUCCESS: issue 2" in result.output

        expected_calls = [
            call(['aider', '--message', 'issue 1', '--yes', '--no-stream', '--auto-commits'], capture_output=True, text=True, timeout=300, encoding='utf-8'),
            call(['aider', '--message', 'issue 2', '--yes', '--no-stream', '--auto-commits'], capture_output=True, text=True, timeout=300, encoding='utf-8')
        ]
        mock_run.assert_has_calls(expected_calls, any_order=False)
        assert mock_run.call_count == 2

def test_assistant_process_issues_failure(runner, tmp_path):
    """Test the process-issues subcommand with a failed execution."""
    issues_file = tmp_path / "issues.txt"
    issues_file.write_text("issue 1")
    
    with patch('scaffold.cli.subprocess.run') as mock_run:
        # Mock failed execution
        mock_run.return_value.returncode = 1
        mock_run.return_value.stdout = "stdout"
        mock_run.return_value.stderr = "stderr"

        result = runner.invoke(cli, ['assistant', 'process-issues', str(issues_file)])
        
        assert result.exit_code == 0, result.output
        assert "Processing: issue 1" in result.output
        assert "❌ FAILED: issue 1" in result.output
        assert "Log:" in result.output

        mock_run.assert_called_once_with(
            ['aider', '--message', 'issue 1', '--yes', '--no-stream', '--auto-commits'],
            capture_output=True, text=True, timeout=300, encoding='utf-8'
        )
        
def test_assistant_process_issues_file_not_found(runner):
    """Test process-issues with a non-existent file."""
    result = runner.invoke(cli, ['assistant', 'process-issues', 'nonexistent.txt'])
    assert result.exit_code != 0
    assert "Error: Invalid value for 'ISSUES_FILE': Path 'nonexistent.txt' does not exist." in result.output
    
def test_assistant_process_issues_timeout(runner, tmp_path):
    """Test process-issues with a subprocess timeout."""
    issues_file = tmp_path / "issues.txt"
    issues_file.write_text("long running issue")
    
    with patch('scaffold.cli.subprocess.run', side_effect=subprocess.TimeoutExpired(cmd='aider', timeout=300)) as mock_run:
        result = runner.invoke(cli, ['assistant', 'process-issues', str(issues_file)])
        assert result.exit_code == 0, result.output
        assert "Processing: long running issue" in result.output
        assert "❌ TIMEOUT: long running issue" in result.output
        assert "Log:" in result.output
        mock_run.assert_called_once()
