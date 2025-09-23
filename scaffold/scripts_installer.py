import os
import shutil
from pathlib import Path
from typing import List, Tuple

try:
    from importlib.resources import files as pkg_files
except ImportError:
    # Python <3.9 fallback
    from importlib_resources import files as pkg_files  # type: ignore


SCRIPT_ENTRIES: List[Tuple[str, str]] = [
    ("aggregate_repos.sh", "scripts/gh/aggregate_repos.sh"),
    ("archive_stale_repos.sh", "scripts/gh/archive_stale_repos.sh"),
    ("delete_repos.sh", "scripts/gh/delete_repos.sh"),
    ("remove_from_git.sh", "scripts/git/remove_from_git.sh"),
    ("delete_branches.sh", "scripts/git/delete_branches.sh"),
]


def default_install_dir() -> Path:
    return Path.home() / ".gitscaffold" / "bin"


def install_scripts(dest: Path = None, overwrite: bool = True) -> Path:
    """Copy bundled shell scripts into dest directory (default: ~/.gitscaffold/bin)."""
    if dest is None:
        dest = default_install_dir()
    dest.mkdir(parents=True, exist_ok=True)

    base = pkg_files("scaffold")

    for out_name, rel in SCRIPT_ENTRIES:
        src = base.joinpath(rel)
        if not src.exists():
            # Skip missing
            continue
        data = src.read_bytes()
        out_path = dest / out_name
        if out_path.exists() and not overwrite:
            continue
        out_path.write_bytes(data)
        try:
            os.chmod(out_path, 0o755)
        except Exception:
            pass
    return dest


def list_scripts() -> List[str]:
    """Return the filenames of bundled scripts."""
    return [name for name, _ in SCRIPT_ENTRIES]
