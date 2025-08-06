"""
Vibe Kanban integration stubs.
"""
from .kanban_client import VibeKanbanClient

def list_boards(host=None):
    """List available Vibe Kanban boards.
    Returns a list of board identifiers or names.
    """
    # TODO: Implement integration with Vibe-Kanban API or CLI
    return []

def import_issues_to_board(board, issues, repo=None, token=None, host=None):
    """Import GitHub issues into a Vibe Kanban board.
    Args:
        board: Board identifier or name.
        issues: Iterable of issue dicts or titles.
        repo: GitHub repository in owner/repo format.
        token: GitHub token for authentication.
        host: Vibe Kanban host URL.
    """
    raise NotImplementedError("import_issues_to_board not implemented")

def export_board_to_github(board, repo, token=None, host=None):
    """Export Vibe Kanban board state back to GitHub issues.
    Args:
        board: Board identifier or name.
        repo: GitHub repository in owner/repo format.
        token: GitHub token for authentication.
        host: Vibe Kanban host URL.
    """
    raise NotImplementedError("export_board_to_github not implemented")