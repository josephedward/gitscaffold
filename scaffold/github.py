"""GitHub client wrapper using PyGitHub."""

from datetime import date, datetime
from github import Github
from github.GithubException import GithubException

class GitHubClient:
    """Wrapper for GitHub API interactions via PyGitHub."""

    def __init__(self, token: str, repo_full_name: str):
        """Initialize the GitHub client with a token and repository name (owner/repo)."""
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_full_name)

    def _find_milestone(self, name: str):
        """Return an existing milestone by name, or None if not found."""
        try:
            for m in self.repo.get_milestones(state='all'):
                if m.title == name:
                    return m
        except GithubException:
            pass
        return None

    def create_milestone(self, name: str, due_on: date = None):
        """Create or retrieve a milestone in the repository."""
        m = self._find_milestone(name)
        if m:
            return m
        params = {'title': name}
        if due_on:
            # PyGitHub accepts datetime for due_on
            if isinstance(due_on, date) and not isinstance(due_on, datetime):
                due = datetime(due_on.year, due_on.month, due_on.day)
            else:
                due = due_on
            params['due_on'] = due
        return self.repo.create_milestone(**params)

    def _find_issue(self, title: str):
        """Return an existing issue by title, or None if not found."""
        try:
            # search through all issues (open and closed)
            for issue in self.repo.get_issues(state='all'):
                if issue.title == title:
                    return issue
        except GithubException:
            pass
        return None

    def create_issue(
        self,
        title: str,
        body: str = None,
        assignees: list = None,
        labels: list = None,
        milestone: str = None,
    ):
        """Create or retrieve an issue; if exists, returns the existing issue."""
        issue = self._find_issue(title)
        if issue:
            return issue
        # prepare create parameters
        params = {'title': title}
        if body:
            params['body'] = body
        if assignees:
            params['assignees'] = assignees
        if labels:
            params['labels'] = labels
        if milestone:
            m = self._find_milestone(milestone)
            if not m:
                raise ValueError(f"Milestone '{milestone}' not found for issue '{title}'")
            params['milestone'] = m.number
        return self.repo.create_issue(**params)