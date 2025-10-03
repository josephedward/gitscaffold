import os
import platform
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path
from typing import List, Optional


def _home_bin_dir() -> Path:
    return Path.home() / ".gitscaffold" / "bin"


def find_gh_executable() -> Optional[str]:
    """Find a usable gh executable (PATH or ~/.gitscaffold/bin/gh)."""
    gh_path = shutil.which("gh")
    if gh_path:
        return gh_path
    candidate = _home_bin_dir() / "gh"
    if candidate.exists():
        return str(candidate)
    # Windows fallback
    candidate_exe = _home_bin_dir() / "gh.exe"
    if candidate_exe.exists():
        return str(candidate_exe)
    return None


def _detect_os_arch() -> tuple[str, str]:
    sysname = platform.system().lower()
    machine = platform.machine().lower()

    if sysname.startswith("darwin") or sysname == "mac":
        os_id = "macOS"
    elif sysname.startswith("linux"):
        os_id = "linux"
    elif sysname.startswith("windows") or sysname.startswith("msys") or sysname.startswith("cygwin"):
        os_id = "windows"
    else:
        raise RuntimeError(f"Unsupported OS: {platform.system()}")

    if machine in ("x86_64", "amd64"):
        arch = "amd64"
    elif machine in ("aarch64", "arm64"):
        arch = "arm64"
    else:
        raise RuntimeError(f"Unsupported CPU architecture: {platform.machine()}")

    return os_id, arch


def _download(url: str, dest: Path):
    import urllib.request
    dest.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)


def _extract_archive(archive: Path, target_dir: Path) -> Path:
    """Extract archive and return path to contained gh binary."""
    target_dir.mkdir(parents=True, exist_ok=True)
    gh_bin_path: Optional[Path] = None
    if archive.suffixes[-2:] == [".tar", ".gz"] or archive.suffix == ".tgz":
        with tarfile.open(archive, "r:gz") as tf:
            tf.extractall(target_dir)
            # Find gh binary in extracted folder
            for p in target_dir.rglob("gh"):
                if p.is_file() and os.access(p, os.X_OK):
                    gh_bin_path = p
                    break
    elif archive.suffix == ".zip":
        with zipfile.ZipFile(archive, "r") as zf:
            zf.extractall(target_dir)
            for p in target_dir.rglob("gh.exe"):
                if p.is_file():
                    gh_bin_path = p
                    break
    else:
        raise RuntimeError(f"Unsupported archive format: {archive.name}")

    if not gh_bin_path:
        raise RuntimeError("Failed to locate gh binary inside archive")
    return gh_bin_path


def install_gh(version: str = "latest") -> str:
    """
    Install GitHub CLI into ~/.gitscaffold/bin and return path to installed binary.
    Uses official release artifacts from https://github.com/cli/cli/releases.
    """
    os_id, arch = _detect_os_arch()
    base = "https://github.com/cli/cli/releases"
    if version == "latest":
        # Redirect-safe latest download URLs
        # e.g., .../latest/download/gh_2.45.0_linux_amd64.tar.gz
        if os_id == "windows":
            artifact = f"gh_{version}_windows_{arch}.zip"  # latest resolves to concrete version
        else:
            artifact = f"gh_{version}_{os_id}_{arch}.tar.gz"
        url = f"{base}/latest/download/{artifact}"
    else:
        tag = f"v{version.lstrip('v')}"
        if os_id == "windows":
            artifact = f"gh_{version}_windows_{arch}.zip"
        else:
            artifact = f"gh_{version}_{os_id}_{arch}.tar.gz"
        url = f"{base}/download/{tag}/{artifact}"

    bin_dir = _home_bin_dir()
    tmp_dir = bin_dir / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    archive_path = tmp_dir / (artifact if 'artifact' in locals() else "gh_download")
    _download(url, archive_path)

    extracted_root = tmp_dir / "extracted"
    gh_bin = _extract_archive(archive_path, extracted_root)

    # Final destination
    dest = bin_dir / ("gh.exe" if os_id == "windows" else "gh")
    shutil.copy2(gh_bin, dest)
    if os_id != "windows":
        os.chmod(dest, 0o755)

    # Cleanup temp
    try:
        shutil.rmtree(tmp_dir)
    except Exception:
        pass

    return str(dest)


class GitHubCLI:
    def __init__(self):
        self.gh = find_gh_executable()
        if not self.gh:
            raise FileNotFoundError(
                "gh not found. Run 'gitscaffold gh install' to bootstrap it."
            )

    def _run(self, args: List[str], check: bool = True, capture: bool = True) -> subprocess.CompletedProcess:
        cmd = [self.gh] + args
        if capture:
            return subprocess.run(cmd, check=check, capture_output=True, text=True)
        return subprocess.run(cmd, check=check)

    def version(self) -> str:
        cp = self._run(["--version"])  # type: ignore[arg-type]
        return cp.stdout.strip()

    def list_issues(self, repo: str, state: str = "open", limit: int = 100) -> list:
        fields = "number,title,state,labels,assignees,milestone,author,createdAt,url,body"
        cp = self._run([
            "issue", "list", "--repo", repo, "--state", state, "--limit", str(limit),
            "--json", fields
        ])
        import json
        return json.loads(cp.stdout or "[]")

    def create_issue(
        self,
        repo: str,
        title: str,
        body: Optional[str] = None,
        labels: Optional[list] = None,
        assignees: Optional[list] = None,
        milestone: Optional[str] = None,
    ) -> dict:
        args = ["issue", "create", "--repo", repo, "--title", title]
        if body:
            args += ["--body", body]
        for l in (labels or []):
            args += ["--label", l]
        for a in (assignees or []):
            args += ["--assignee", a]
        if milestone:
            args += ["--milestone", milestone]
        args += ["--json", "number,title,url"]
        cp = self._run(args)
        import json
        return json.loads(cp.stdout or "{}")

    def close_issue(self, repo: str, number: int) -> None:
        self._run(["issue", "close", str(number), "--repo", repo], capture=False)

    def list_prs(self, repo: str, state: str = "open", limit: int = 100, fields: list = None) -> list:
        if fields is None:
            fields = ["number", "title", "state", "headRefName", "baseRefName", "author", "createdAt", "url"]
        json_fields = ",".join(fields)
        cp = self._run([
            "pr", "list", "--repo", repo, "--state", state, "--limit", str(limit),
            "--json", json_fields
        ])
        import json
        return json.loads(cp.stdout or "[]")

    def edit_pr(self, repo: str, number: int, body: str) -> None:
        self._run(["pr", "edit", str(number), "--repo", repo, "--body", body], capture=False)

