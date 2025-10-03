import pytest
from click.testing import CliRunner
from unittest.mock import patch, call, ANY
import subprocess
import sys
from pathlib import Path

from scaffold.cli import cli

@pytest.fixture
def runner():
    return CliRunner()

def test_run_action_locally_basic(runner):
    """Test that `run-action-locally` command calls the script with correct arguments."""
    script_path = Path(__file__).parent.parent / "scaffold" / "scripts" / "run_action_locally.py"
    
    with patch('scaffold.cli.subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        result = runner.invoke(cli, ['run-action-locally', '-W', '.github/workflows/ci.yml', '-e', 'push', '-j', 'build'])
        
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once_with(
            [sys.executable, str(script_path), "--workflow-file", ".github/workflows/ci.yml", "--event", "push", "--job", "build"],
            check=True
        )

def test_run_action_locally_dry_run(runner):
    """Test `run-action-locally` with dry-run option."""
    script_path = Path(__file__).parent.parent / "scaffold" / "scripts" / "run_action_locally.py"

    with patch('scaffold.cli.subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        result = runner.invoke(cli, ['run-action-locally', '-W', '.github/workflows/ci.yml', '--dry-run'])
        
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once_with(
            [sys.executable, str(script_path), "--workflow-file", ".github/workflows/ci.yml", "--event", "workflow_dispatch", "--dry-run"],
            check=True
        )

def test_run_action_locally_script_error(runner):
    """Test `run-action-locally` when the underlying script returns an error."""
    script_path = Path(__file__).parent.parent / "scaffold" / "scripts" / "run_action_locally.py"

    with patch('scaffold.cli.subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, [sys.executable, str(script_path)])
        result = runner.invoke(cli, ['run-action-locally', '-W', '.github/workflows/ci.yml'])
        
        assert result.exit_code == 1, result.output
        assert "Error running local action: Command" in result.output

# Test cases for the run_action_locally.py script itself

from scaffold.scripts.run_action_locally import check_act_installed, install_act_instructions, run_action_locally

def test_check_act_installed_true():
    """Test check_act_installed when act is present."""
    with patch('subprocess.run') as mock_run:
        mock_run.return_value.returncode = 0
        assert check_act_installed() is True
        mock_run.assert_called_once_with(["act", "--version"], capture_output=True, check=True)

def test_check_act_installed_false_filenotfound():
    """Test check_act_installed when act is not found."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = FileNotFoundError
        assert check_act_installed() is False
        mock_run.assert_called_once_with(["act", "--version"], capture_output=True, check=True)

def test_check_act_installed_false_calledprocesserror():
    """Test check_act_installed when act command fails (e.g., not executable)."""
    with patch('subprocess.run') as mock_run:
        mock_run.side_effect = subprocess.CalledProcessError(1, "act")
        assert check_act_installed() is False
        mock_run.assert_called_once_with(["act", "--version"], capture_output=True, check=True)

def test_install_act_instructions(capsys):
    """Test that install_act_instructions prints the correct message."""
    install_act_instructions()
    captured = capsys.readouterr()
    assert "Error: 'act' (nektos/act) is not installed or not found in your PATH." in captured.out
    assert "Please install 'act' to use this feature." in captured.out
    assert "Installation instructions:" in captured.out
    assert "brew install act" in captured.out

def test_run_action_locally_act_not_installed(capsys):
    """Test run_action_locally when act is not installed."""
    with patch('scaffold.scripts.run_action_locally.check_act_installed', return_value=False):
        exit_code = run_action_locally(workflow_file=".github/workflows/ci.yml")
        captured = capsys.readouterr()
        assert "Error: 'act' (nektos/act) is not installed or not found in your PATH." in captured.out
        assert exit_code == 1

def test_run_action_locally_act_installed(runner, capsys):
    """Test run_action_locally when act is installed and command runs successfully."""
    with patch('scaffold.scripts.run_action_locally.check_act_installed', return_value=True):
        with patch('subprocess.run') as mock_subprocess_run:
            mock_subprocess_run.return_value.returncode = 0
            run_action_locally(workflow_file=".github/workflows/ci.yml", event="push", job="test")
            captured = capsys.readouterr()
            assert "Running GitHub Action locally with command: act -W .github/workflows/ci.yml push -j test" in captured.out
            mock_subprocess_run.assert_called_once_with(
                ["act", "-W", ".github/workflows/ci.yml", "push", "-j", "test"],
                check=True, text=True, cwd=ANY
            )

def test_run_action_locally_act_command_fails(runner, capsys):
    """Test run_action_locally when the act command itself fails."""
    with patch('scaffold.scripts.run_action_locally.check_act_installed', return_value=True):
        with patch('subprocess.run') as mock_subprocess_run:
            mock_subprocess_run.side_effect = subprocess.CalledProcessError(1, "act")
            with patch('sys.exit') as mock_sys_exit:
                run_action_locally(workflow_file=".github/workflows/ci.yml")
                captured = capsys.readouterr()
                assert "Error running 'act': Command 'act' returned non-zero exit status 1." in captured.err
                mock_sys_exit.assert_called_once_with(1)
