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

    def get_all_issue_titles(self) -> set[str]:
        """Fetch all issue titles in the repository."""
        titles = set()
        try:
            for issue in self.repo.get_issues(state='all'):
                titles.add(issue.title)
        except GithubException as e:
            # Consider more robust error handling or logging if needed
            print(f"Warning: Error fetching issue titles: {e}. Proceeding with an empty list of existing titles.")
        return titles

    def get_closed_issues_for_deletion(self) -> list[dict]:
        """
        Fetch all closed issues with their numbers and node IDs for deletion.
        Handles pagination.
        """
        query = """
        query($owner: String!, $repo: String!, $after: String) {
          repository(owner: $owner, name: $repo) {
            issues(states: CLOSED, first: 100, after: $after) {
              pageInfo { hasNextPage, endCursor }
              nodes { id, number, title }
            }
          }
        }
        """
        issues_to_delete = []
        after = None
        owner, repo_name = self.repo.full_name.split('/')
        while True:
            variables = {"owner": owner, "repo": repo_name, "after": after}
            try:
                # PyGitHub's Github object has a direct graphql method
                data = self.github.graphql(query, variables=variables) 
            except GithubException as e: # More specific exception if PyGitHub's graphql raises one
                print(f"Error fetching closed issues via GraphQL: {e}")
                # Depending on desired robustness, could raise or return partial/empty
                return [] # Or raise a custom error
            except Exception as e: # Catch other potential errors like network issues
                print(f"An unexpected error occurred fetching closed issues: {e}")
                return []


            if not data or "repository" not in data or not data["repository"] or "issues" not in data["repository"]:
                print(f"Warning: Unexpected GraphQL response structure: {data}")
                break # Avoid erroring out on unexpected structure

            nodes = data["repository"]["issues"]["nodes"]
            issues_to_delete.extend([{"id": node["id"], "number": node["number"], "title": node["title"]} for node in nodes])
            
            page_info = data["repository"]["issues"]["pageInfo"]
            if not page_info["hasNextPage"]:
                break
            after = page_info["endCursor"]
        return issues_to_delete

    def delete_issue_by_node_id(self, node_id: str) -> bool:
        """Delete an issue by its GraphQL node ID."""
        mutation = """
        mutation($issueId: ID!) {
          deleteIssue(input: {issueId: $issueId}) {
            clientMutationId # Can be anything, just need to request something
          }
        }
        """
        variables = {"issueId": node_id}
        try:
            self.github.graphql(mutation, variables=variables)
            return True
        except GithubException as e:
            print(f"Error deleting issue {node_id} via GraphQL: {e}")
            return False
        except Exception as e:
            print(f"An unexpected error occurred deleting issue {node_id}: {e}")
            return False
