import os
import stat
from pathlib import Path

import pytest

from scaffold.core import env as core_env


@pytest.fixture
def mock_home(monkeypatch, tmp_path):
    monkeypatch.setattr(Path, 'home', lambda: tmp_path)
    return tmp_path


def test_global_config_path_and_permissions(mock_home):
    path = core_env.get_global_config_path()
    # Directory exists
    cfg_dir = path.parent
    assert cfg_dir.is_dir()
    # File may not exist yet, set a key to create it
    core_env.set_global_config_key('TEST_KEY', 'value')
    assert path.is_file()

    if os.name != 'nt':
        # Directory 0700, file 0600
        dir_mode = os.stat(cfg_dir).st_mode
        file_mode = os.stat(path).st_mode
        assert stat.S_IMODE(dir_mode) == 0o700
        assert stat.S_IMODE(file_mode) == 0o600


def test_get_github_token_from_env(monkeypatch, mock_home):
    # Avoid picking up a real project .env
    original = core_env.load_dotenv
    def mocked_load_dotenv(dotenv_path=None, **kwargs):
        if dotenv_path is not None:
            return original(dotenv_path=dotenv_path, **kwargs)
        return False
    monkeypatch.setattr(core_env, 'load_dotenv', mocked_load_dotenv)
    monkeypatch.setenv('GITHUB_TOKEN', 'env_token')
    token = core_env.get_github_token(noninteractive=True)
    assert token == 'env_token'


def test_get_github_token_from_global_config(monkeypatch, mock_home):
    # Avoid picking up a real project .env
    original = core_env.load_dotenv
    def mocked_load_dotenv(dotenv_path=None, **kwargs):
        if dotenv_path is not None:
            return original(dotenv_path=dotenv_path, **kwargs)
        return False
    monkeypatch.setattr(core_env, 'load_dotenv', mocked_load_dotenv)
    # Ensure env is not set
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    # Write into global config
    core_env.set_global_config_key('GITHUB_TOKEN', 'file_token')

    token = core_env.get_github_token(noninteractive=True)
    assert token == 'file_token'


def test_get_github_token_noninteractive_missing(monkeypatch, mock_home):
    # Avoid picking up a real project .env
    original = core_env.load_dotenv
    def mocked_load_dotenv(dotenv_path=None, **kwargs):
        if dotenv_path is not None:
            return original(dotenv_path=dotenv_path, **kwargs)
        return False
    monkeypatch.setattr(core_env, 'load_dotenv', mocked_load_dotenv)
    monkeypatch.delenv('GITHUB_TOKEN', raising=False)
    cfg = core_env.get_global_config_path()
    if cfg.exists():
        cfg.unlink()  # ensure no value present
    with pytest.raises(RuntimeError):
        core_env.get_github_token(noninteractive=True)
