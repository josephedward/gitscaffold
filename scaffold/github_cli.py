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
    if gh_path and os.access(gh_path, os.X_OK):
        return gh_path
    candidate = _home_bin_dir() / "gh"
    if candidate.exists() and os.access(candidate, os.X_OK):
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


def _safe_tar_extract(tar: tarfile.TarFile, path: Path):
    """Safely extract a tar archive to path (mitigate path traversal)."""
    path = path.resolve()
    for member in tar.getmembers():
        member_path = (path / member.name).resolve()
        if not str(member_path).startswith(str(path)):
            raise RuntimeError(f"Unsafe path in archive: {member.name}")
    tar.extractall(path)


def _extract_archive(archive: Path, target_dir: Path) -> Path:
    """Extract archive and return path to contained gh binary."""
    target_dir.mkdir(parents=True, exist_ok=True)
    gh_bin_path: Optional[Path] = None
    if archive.suffixes[-2:] == [".tar", ".gz"] or archive.suffix == ".tgz":
        with tarfile.open(archive, "r:gz") as tf:
            _safe_tar_extract(tf, target_dir)
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


def _resolve_latest_version() -> str:
    """Resolve the latest gh version via HTTP redirect to the tag page."""
    import urllib.request
    with urllib.request.urlopen("https://github.com/cli/cli/releases/latest") as resp:
        final_url = resp.geturl()  # follows redirect to .../tag/vX.Y.Z
    tag = final_url.rstrip("/").split("/")[-1]
    return tag.lstrip("v")


def _download_checksums(version: str, dest: Path):
    base = "https://github.com/cli/cli/releases"
    url = f"{base}/download/v{version}/gh_{version}_checksums.txt"
    _download(url, dest)


def _verify_checksum(archive: Path, checksums_file: Path, artifact_name: str) -> None:
    import hashlib
    content = checksums_file.read_text(encoding="utf-8")
    expected = None
    for line in content.splitlines():
        if line.strip().endswith(artifact_name):
            expected = line.split()[0]
            break
    if not expected:
        raise RuntimeError(f"Checksum for {artifact_name} not found")
    sha256 = hashlib.sha256()
    with open(archive, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    actual = sha256.hexdigest()
    if actual.lower() != expected.lower():
        raise RuntimeError("Checksum verification failed for downloaded archive")


def install_gh(version: str = "latest") -> str:
    """
    Install GitHub CLI into ~/.gitscaffold/bin and return path to installed binary.
    Uses official release artifacts from https://github.com/cli/cli/releases.
    - Resolves the concrete version when 'latest' is requested.
    - Verifies SHA256 checksum using the published checksums file.
    - Performs safe archive extraction.
    """
    os_id, arch = _detect_os_arch()
    if version == "latest":
        version = _resolve_latest_version()
    base = "https://github.com/cli/cli/releases/download"
    if os_id == "windows":
        artifact = f"gh_{version}_windows_{arch}.zip"
    else:
        artifact = f"gh_{version}_{os_id}_{arch}.tar.gz"
    url = f"{base}/v{version}/{artifact}"

    bin_dir = _home_bin_dir()
    tmp_dir = bin_dir / "tmp"
    tmp_dir.mkdir(parents=True, exist_ok=True)

    archive_path = tmp_dir / artifact
    checksums_path = tmp_dir / f"gh_{version}_checksums.txt"
    _download(url, archive_path)
    _download_checksums(version, checksums_path)
    _verify_checksum(archive_path, checksums_path, artifact)

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

    def _run(self, args: List[str], check: bool = True, capture: bool = True, timeout: int = 60) -> subprocess.CompletedProcess:
        cmd = [self.gh] + args
        if capture:
            return subprocess.run(cmd, check=check, capture_output=True, text=True, timeout=timeout)
        return subprocess.run(cmd, check=check, timeout=timeout)

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

    def issue_view(self, repo: str, number: int, fields: Optional[str] = None) -> dict:
        """Return issue details via gh issue view --json ..."""
        if fields is None:
            fields = "number,title,state,labels,assignees,milestone,author,createdAt,url,body"
        args = [
            "issue", "view", str(number), "--repo", repo, "--json", fields
        ]
        cp = self._run(args)
        import json
        return json.loads(cp.stdout or "{}")

    def edit_issue(self, repo: str, number: int, title: Optional[str] = None, body: Optional[str] = None) -> None:
        args = ["issue", "edit", str(number), "--repo", repo]
        if title:
            args += ["--title", title]
        if body:
            args += ["--body", body]
        self._run(args, capture=False)

    def issue_comment(self, repo: str, number: int, body: str) -> None:
        args = ["issue", "comment", str(number), "--repo", repo, "--body", body]
        self._run(args, capture=False)

    def issue_remove_label(self, repo: str, number: int, label: str) -> None:
        args = ["issue", "edit", str(number), "--repo", repo, "--remove-label", label]
        self._run(args, capture=False)

    def list_labels(self, repo: str, limit: int = 100) -> list:
        fields = "name,description,color"
        cp = self._run([
            "label", "list", "--repo", repo, "--limit", str(limit),
            "--json", fields
        ])
        import json
        return json.loads(cp.stdout or "[]")

    def create_label(self, repo: str, name: str, description: Optional[str] = None, color: Optional[str] = None) -> dict:
        args = ["label", "create", "--repo", repo, name]
        if description:
            args += ["--description", description]
        if color:
            args += ["--color", color]
        args += ["--json", "name,description,color"]
        cp = self._run(args)
        import json
        return json.loads(cp.stdout or "{}")

    def delete_label(self, repo: str, name: str) -> None:
        self._run(["label", "delete", "--repo", repo, name, "--yes"], capture=False)

    def list_milestones(self, repo: str, state: str = "open", limit: int = 100) -> list:
        fields = "number,title,description,state,dueOn,url"
        cp = self._run([
            "milestone", "list", "--repo", repo, "--state", state, "--limit", str(limit),
            "--json", fields
        ])
        import json
        return json.loads(cp.stdout or "[]")

    def create_milestone(self, repo: str, title: str, description: Optional[str] = None, due_on: Optional[str] = None) -> dict:
        args = ["milestone", "create", "--repo", repo, title]
        if description:
            args += ["--description", description]
        if due_on:
            args += ["--due-on", due_on]
        args += ["--json", "number,title,url"]
        cp = self._run(args)
        import json
        return json.loads(cp.stdout or "{}")

    def close_milestone(self, repo: str, number: int) -> None:
        self._run(["milestone", "close", str(number), "--repo", repo], capture=False)

    def open_milestone(self, repo: str, number: int) -> None:
        self._run(["milestone", "open", str(number), "--repo", repo], capture=False)

    def delete_milestone(self, repo: str, number: int) -> None:
        self._run(["milestone", "delete", str(number), "--repo", repo, "--yes"], capture=False)

    def list_workflows(self, repo: str, limit: int = 100) -> list:
        fields = "id,name,state,createdAt,updatedAt"
        cp = self._run([
            "workflow", "list", "--repo", repo, "--limit", str(limit),
            "--json", fields
        ])
        import json
        return json.loads(cp.stdout or "[]")

    def run_workflow(self, repo: str, workflow_id: str, ref: str = "main", inputs: Optional[dict] = None) -> dict:
        args = ["workflow", "run", "--repo", repo, workflow_id, "--ref", ref]
        if inputs:
            for key, value in inputs.items():
                args += ["-f", f"{key}={value}"]
        cp = self._run(args)
        import json
        return json.loads(cp.stdout or "{}")

    def workflow_status(self, repo: str, run_id: str) -> dict:
        fields = "id,status,conclusion,createdAt,updatedAt,url"
        cp = self._run([
            "run", "view", "--repo", repo, run_id, "--json", fields
        ])
        import json
        return json.loads(cp.stdout or "{}")

    # ---- Projects (Kanban) helpers (require gh project plugin) ----
    def has_projects(self) -> bool:
        try:
            self._run(["project", "--help"], check=False)
            return True
        except Exception:
            return False

    def project_list(self, owner: Optional[str] = None, org: Optional[str] = None, limit: int = 30) -> str:
        args = ["project", "list", "--limit", str(limit)]
        if owner:
            args += ["--owner", owner]
        if org:
            args += ["--org", org]
        # Not all gh versions support --format json; return raw output for compatibility
        cp = self._run(args, capture=True, check=False)
        return (cp.stdout or "").strip()

    def project_view(self, number: int) -> str:
        args = ["project", "view", str(number)]
        cp = self._run(args, capture=True, check=False)
        return (cp.stdout or "").strip()

    def project_create(self, owner: Optional[str] = None, org: Optional[str] = None, title: str, body: Optional[str] = None, public: bool = False) -> dict:
        args = ["project", "create", "--title", title]
        if owner:
            args += ["--owner", owner]
        if org:
            args += ["--org", org]
        if body:
            args += ["--body", body]
        if public:
            args += ["--public"]
        cp = self._run(args)
        import json
        return json.loads(cp.stdout or "{}")

    def project_add_item(self, project_url: str, item_url: str) -> dict:
        args = ["project", "add-item", project_url, "--url", item_url]
        cp = self._run(args)
        import json
        return json.loads(cp.stdout or "{}")

    def project_move_item(self, project_url: str, item_id: str, status: str) -> dict:
        args = ["project", "move-item", project_url, "--item-id", item_id, "--field-id", status]
        cp = self._run(args)
        import json
        return json.loads(cp.stdout or "{}")

    # ---- Pull Request helpers ----
    def pr_view(self, repo: str, number: int, fields: Optional[str] = None) -> dict:
        """Return PR details via gh pr view --json ..."""
        if fields is None:
            # default fields important for feedback summarization
            fields = (
                "number,title,url,author,baseRefName,headRefName,reviewDecision,"
                "reviews,reviewThreads,comments,statusCheckRollup"
            )
        args = [
            "pr", "view", str(number), "--repo", repo, "--json", fields
        ]
        cp = self._run(args)
        import json
        return json.loads(cp.stdout or "{}")

    def pr_add_labels(self, repo: str, number: int, labels: list[str]) -> None:
        args = ["pr", "edit", str(number), "--repo", repo]
        for l in labels:
            args += ["--add-label", l]
        self._run(args, capture=False)

    def pr_comment(self, repo: str, number: int, body: str) -> None:
        args = ["pr", "comment", str(number), "--repo", repo, "--body", body]
        self._run(args, capture=False)

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

    def pr_merge(
        self,
        repo: str,
        number: int,
        merge: bool = False,
        squash: bool = False,
        rebase: bool = False,
        delete_branch: bool = False,
        admin: bool = False,
    ) -> None:
        args = ["pr", "merge", str(number), "--repo", repo]
        # default behavior is interactive; choose strategy flags when provided
        if merge:
            args += ["--merge"]
        if squash:
            args += ["--squash"]
        if rebase:
            args += ["--rebase"]
        if delete_branch:
            args += ["--delete-branch"]
        if admin:
            args += ["--admin"]
        self._run(args, capture=False)
