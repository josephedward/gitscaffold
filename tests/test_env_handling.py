import pytest
from click.testing import CliRunner
from unittest.mock import patch
from pathlib import Path

from scaffold.cli import get_github_token, get_openai_api_key, cli

@pytest.fixture
def temp_config_dir(tmp_path):
    """
    Creates a temporary config directory and patches get_global_config_path
    to return a file path within this directory.
    """
    config_dir = tmp_path / ".gitscaffold"
    config_dir.mkdir()
    config_file = config_dir / "config"
    with patch('scaffold.cli.get_global_config_path', return_value=config_file):
        yield config_file

def test_get_github_token_prompts_and_saves(temp_config_dir):
    """Test get_github_token prompts for a token and saves it when not found."""
    fake_token = "ghp_fake_token_for_test"
    
    # Patch os.getenv to simulate no token being set
    # Patch click.prompt to simulate user input
    with patch('os.getenv', return_value=None), \
         patch('click.prompt', return_value=fake_token):
        
        token = get_github_token()
        
        # Assert the correct token is returned
        assert token == fake_token
        
        # Assert the config file was created and contains the token
        assert temp_config_dir.exists()
        content = temp_config_dir.read_text()
        # python-dotenv can save with or without quotes, so check for both possibilities
        assert f'GITHUB_TOKEN="{fake_token}"' in content or f"GITHUB_TOKEN={fake_token}" in content

def test_get_openai_api_key_prompts_and_saves(temp_config_dir):
    """Test get_openai_api_key prompts for a key and saves it when not found."""
    fake_key = "sk-fake_api_key_for_test"
    
    with patch('os.getenv', return_value=None), \
         patch('click.prompt', return_value=fake_key):
        
        key = get_openai_api_key()
        
        assert key == fake_key
        assert temp_config_dir.exists()
        content = temp_config_dir.read_text()
        assert f'OPENAI_API_KEY="{fake_key}"' in content or f"OPENAI_API_KEY={fake_key}" in content

def test_get_github_token_loads_from_env(monkeypatch):
    """Test that get_github_token loads from environment and does not prompt."""
    fake_token = "ghp_token_from_environment"
    monkeypatch.setenv("GITHUB_TOKEN", fake_token)
    
    with patch('click.prompt') as mock_prompt:
        token = get_github_token()
        
        assert token == fake_token
        mock_prompt.assert_not_called()

def test_config_set_command(temp_config_dir):
    """Test `config set` command writes to the global config file."""
    runner = CliRunner()
    result = runner.invoke(cli, ['config', 'set', 'MY_TEST_KEY', 'my_test_value'])
    
    assert result.exit_code == 0
    assert "Set MY_TEST_KEY" in result.output
    
    content = temp_config_dir.read_text()
    assert 'MY_TEST_KEY="my_test_value"' in content or "MY_TEST_KEY=my_test_value" in content
