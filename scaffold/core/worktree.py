import subprocess
import click
from pathlib import Path
from typing import Optional, List, Dict

def _run_git_command(args: List[str], check: bool = True, capture_output: bool = True) -> subprocess.CompletedProcess:
    cmd = ["git"] + args
    try:
        result = subprocess.run(cmd, check=check, capture_output=capture_output, text=True)
        return result
    except subprocess.CalledProcessError as e:
        click.secho(f"Error running git command: {' '.join(cmd)}", fg='red', err=True)
        click.secho(f"Stdout: {e.stdout}", fg='red', err=True)
        click.secho(f"Stderr: {e.stderr}", fg='red', err=True)
        raise
    except FileNotFoundError:
        click.secho("Error: 'git' command not found. Please ensure Git is installed and in your PATH.", fg='red', err=True)
        raise

def add_worktree(branch: str, path_override: Optional[str] = None, create_new: bool = False):
    """Adds a new Git worktree."""
    repo_root = _run_git_command(["rev-parse", "--show-toplevel"]).stdout.strip()
    base_path = Path(repo_root) / ".." / "worktrees" # Default to parent/worktrees
    
    if path_override:
        worktree_path = Path(path_override).resolve()
    else:
        worktree_path = (base_path / branch).resolve()

    if worktree_path.exists():
        click.secho(f"Error: Worktree path '{worktree_path}' already exists.", fg='red')
        return

    args = ["worktree", "add", str(worktree_path)]
    if create_new:
        args += ["--track", "-b", branch]
    else:
        args += [branch]

    click.echo(f"Adding worktree for branch '{branch}' at '{worktree_path}'...")
    _run_git_command(args, capture_output=False)
    click.secho(f"Worktree '{branch}' added successfully.", fg='green')

def list_worktrees() -> List[Dict[str, str]]:
    """Lists existing Git worktrees."""
    result = _run_git_command(["worktree", "list", "--porcelain"])
    output = result.stdout.strip()
    
    worktrees = []
    current_worktree: Dict[str, str] = {}
    for line in output.splitlines():
        if line.startswith("worktree "):
            if current_worktree:
                worktrees.append(current_worktree)
            current_worktree = {"path": line.split(" ", 1)[1]}
        elif line.startswith("bare"):
            current_worktree["bare"] = line.split(" ", 1)[1]
        elif line.startswith("HEAD"):
            current_worktree["hash"] = line.split(" ", 1)[1]
        elif line.startswith("branch"):
            current_worktree["branch"] = line.split(" ", 1)[1].replace("refs/heads/", "")
        elif line.startswith("detached"):
            current_worktree["detached"] = "true"
    if current_worktree:
        worktrees.append(current_worktree)
    return worktrees

def remove_worktree(branch_or_path: str, delete_branch: bool = False):
    """Removes a Git worktree."""
    worktrees = list_worktrees()
    target_worktree_path: Optional[Path] = None

    for wt in worktrees:
        if wt["path"] == branch_or_path or wt.get("branch") == branch_or_path:
            target_worktree_path = Path(wt["path"])
            break
    
    if not target_worktree_path:
        click.secho(f"Error: Worktree or branch '{branch_or_path}' not found.", fg='red')
        return

    args = ["worktree", "remove", str(target_worktree_path)]
    if delete_branch:
        args += ["--force"] # --force is needed to remove the branch if it's not fully merged
    
    click.echo(f"Removing worktree '{target_worktree_path}'...")
    _run_git_command(args, capture_output=False)
    
    if delete_branch:
        click.echo(f"Deleting branch '{branch_or_path}'...")
        _run_git_command(["branch", "-D", branch_or_path], capture_output=False) # -D for force delete
    
    click.secho(f"Worktree '{target_worktree_path}' removed successfully.", fg='green')

def prune_worktrees():
    """Prunes stale Git worktrees."""
    click.echo("Pruning stale worktrees...")
    _run_git_command(["worktree", "prune"], capture_output=False)
    click.secho("Stale worktrees pruned successfully.", fg='green')