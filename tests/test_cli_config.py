import pytest
from click.testing import CliRunner
from pathlib import Path
import os
import stat

from scaffold.cli import cli, get_global_config_path, get_github_token

@pytest.fixture
def runner():
    return CliRunner()

@pytest.fixture
def mock_home(monkeypatch, tmp_path):
    """Mocks Path.home() to use a temporary directory."""
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    return tmp_path

def test_config_path(runner, mock_home):
    """Test the `config path` command."""
    result = runner.invoke(cli, ['config', 'path'])
    assert result.exit_code == 0
    expected_path = str(mock_home / '.gitscaffold' / 'config')
    assert expected_path in result.output

def test_config_set_and_get(runner, mock_home):
    """Test setting and getting a config value."""
    # Test set
    result = runner.invoke(cli, ['config', 'set', 'MY_KEY', 'my_value'])
    assert result.exit_code == 0
    assert "Set MY_KEY" in result.output
    
    config_file = get_global_config_path()
    assert config_file.exists()
    assert "MY_KEY=my_value" in config_file.read_text()

    # Test get
    result = runner.invoke(cli, ['config', 'get', 'MY_KEY'])
    assert result.exit_code == 0
    assert "my_value" == result.output.strip()

    # Test get non-existent key
    result = runner.invoke(cli, ['config', 'get', 'NON_EXISTENT'])
    assert result.exit_code == 1
    assert "not found" in result.output

def test_config_list(runner, mock_home):
    """Test listing config values."""
    runner.invoke(cli, ['config', 'set', 'KEY_ONE', 'value_one'])
    runner.invoke(cli, ['config', 'set', 'KEY_TWO', 'value_two'])
    
    result = runner.invoke(cli, ['config', 'list'])
    assert result.exit_code == 0
    assert "KEY_ONE" in result.output
    assert "value_one" in result.output
    assert "KEY_TWO" in result.output
    assert "value_two" in result.output

def test_get_github_token_reads_from_global_config(runner, mock_home, monkeypatch):
    """Test that get_github_token reads from the global config file."""
    # Setup global config
    runner.invoke(cli, ['config', 'set', 'GITHUB_TOKEN', 'global_test_token'])

    # Mock os.getenv to ensure it's not reading from shell env var
    original_getenv = os.getenv
    def mock_getenv(key, default=None):
        if key == 'GITHUB_TOKEN':
            return None # Force reading from file
        return original_getenv(key, default)
    monkeypatch.setattr(os, 'getenv', mock_getenv)

    # Use a dummy command that triggers get_github_token
    @cli.command('test-token-read')
    def test_token_read():
        token = get_github_token()
        print(f"TOKEN={token}")

    result = runner.invoke(cli, ['test-token-read'])
    assert result.exit_code == 0
    assert "TOKEN=global_test_token" in result.output

def test_get_github_token_prompts_and_saves_to_global_config(runner, mock_home, monkeypatch):
    """Test that get_github_token prompts and saves to global config when no token is found."""
    # Mock os.getenv to return None for tokens
    monkeypatch.setattr(os, 'getenv', lambda key, default=None: None)
    
    @cli.command('test-token-prompt')
    def test_token_prompt():
        token = get_github_token()
        print(f"TOKEN={token}")

    result = runner.invoke(cli, ['test-token-prompt'], input='prompted_token\n')
    assert result.exit_code == 0
    assert "TOKEN=prompted_token" in result.output
    assert "GitHub PAT saved to global config file" in result.output

    config_file = get_global_config_path()
    assert config_file.exists()
    content = config_file.read_text()
    assert "GITHUB_TOKEN=prompted_token" in content

def test_config_file_permissions(runner, mock_home):
    """Test that the config directory and file are created with secure permissions."""
    runner.invoke(cli, ['config', 'set', 'SOME_KEY', 'some_value'])
    
    config_dir = mock_home / '.gitscaffold'
    config_file = config_dir / 'config'
    
    assert config_dir.is_dir()
    assert config_file.is_file()

    if os.name == 'nt':
        pytest.skip("Permission checks are not applicable on Windows")

    # Check directory permissions (owner rwx)
    dir_mode = os.stat(config_dir).st_mode
    assert stat.S_IMODE(dir_mode) == 0o700
    
    # Check file permissions (owner rw)
    file_mode = os.stat(config_file).st_mode
    assert stat.S_IMODE(file_mode) == 0o600
