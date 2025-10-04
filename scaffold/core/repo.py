import logging
import re
import subprocess
from typing import Optional


def sanitize_repo_string(repo_string: Optional[str]) -> Optional[str]:
    """Extract 'owner/repo' from a string or URL. Returns None if input is None/empty.

    Accepts formats:
    - owner/repo
    - https://github.com/owner/repo(.git)
    - git@github.com:owner/repo(.git)
    """
    if not repo_string:
        return None

    s = repo_string.strip()
    # Normalize possible .git suffix early
    if s.endswith('.git'):
        s = s[:-4]
    if not s:
        return None

    # Simple case: already owner/repo
    if re.fullmatch(r"[^/\s]+/[^/\s]+", s):
        return s

    # Explicit SSH form
    if s.startswith('git@github.com:') or 'github.com:' in s:
        repo = s.split('github.com:', 1)[1] if 'github.com:' in s else s.split(':', 1)[1]
        return repo

    # SSH and HTTPS URL patterns
    match = re.search(r"(?:git@)?(?:www\.)?github\.com[/:]([^/]+/[^/]+)$", s)
    if match:
        return match.group(1)

    # Fallback parsing for edge cases
    if 'github.com' in s:
        try:
            post = s.split('github.com', 1)[1]
            if post.startswith(':') or post.startswith('/'):
                post = post[1:]
            parts = post.split('/')
            if len(parts) >= 2:
                return f"{parts[0]}/{parts[1]}"
        except Exception:
            pass

    return s


def get_repo_from_git_config() -> Optional[str]:
    """Return 'owner/repo' from `git config --get remote.origin.url` if available."""
    logging.info("Attempting to get repository from git config.")
    try:
        url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        logging.info(f"Found git remote URL: {url}")

        # Handle SSH URLs: git@github.com:owner/repo.git
        ssh_match = re.search(r"github\.com:([^/]+/[^/]+?)(\.git)?$", url)
        if ssh_match:
            return ssh_match.group(1)

        # Handle HTTPS URLs: https://github.com/owner/repo.git
        https_match = re.search(r"(?:www\.)?github\.com/([^/]+/[^/]+?)(\.git)?$", url)
        if https_match:
            return https_match.group(1)

        logging.warning(f"Could not parse repository from git remote URL: {url}")
        return None
    except (subprocess.CalledProcessError, FileNotFoundError):
        logging.warning("Could not get repo from git config. Not a git repository or git is not installed.")
        return None
