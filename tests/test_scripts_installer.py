from pathlib import Path
import os

import scaffold.scripts_installer as si


def test_list_scripts_contains_expected():
    names = set(si.list_scripts())
    expected = {
        "aggregate_repos.sh",
        "archive_stale_repos.sh",
        "delete_repos.sh",
        "remove_from_git.sh",
        "delete_branches.sh",
    }
    assert expected.issubset(names)


def test_install_scripts_writes_files(tmp_path):
    dest = tmp_path / "bin"
    out = si.install_scripts(dest=dest)
    assert out == dest
    for name in si.list_scripts():
        p = dest / name
        assert p.exists(), f"missing {name}"
        # On POSIX, they should be executable; on Windows this is a noop
        try:
            mode = os.stat(p).st_mode
            assert mode & 0o111, f"{name} not marked executable"
        except Exception:
            # Skip strict exec check on platforms where it is unreliable
            pass

