from scaffold.core import repo as core_repo


def test_sanitize_repo_string_variants():
    assert core_repo.sanitize_repo_string('owner/repo') == 'owner/repo'
    assert core_repo.sanitize_repo_string('https://github.com/owner/repo') == 'owner/repo'
    assert core_repo.sanitize_repo_string('https://github.com/owner/repo.git') == 'owner/repo'
    assert core_repo.sanitize_repo_string('git@github.com:owner/repo.git') == 'owner/repo'
    assert core_repo.sanitize_repo_string(' git@github.com:owner/repo ')== 'owner/repo'
    assert core_repo.sanitize_repo_string(None) is None
    assert core_repo.sanitize_repo_string('') is None


def test_get_repo_from_git_config_https(monkeypatch):
    def fake_check_output(cmd, text=True, stderr=None):
        return 'https://github.com/owner/repo.git'  # typical https remote
    monkeypatch.setattr('subprocess.check_output', fake_check_output)
    assert core_repo.get_repo_from_git_config() == 'owner/repo'


def test_get_repo_from_git_config_ssh(monkeypatch):
    def fake_check_output(cmd, text=True, stderr=None):
        return 'git@github.com:owner/repo.git'  # typical ssh remote
    monkeypatch.setattr('subprocess.check_output', fake_check_output)
    assert core_repo.get_repo_from_git_config() == 'owner/repo'

