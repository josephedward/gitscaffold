"""GitHub client wrapper using PyGitHub."""

from datetime import date, datetime
import logging
from github import Github
from github.GithubException import GithubException

class GitHubClient:
    """Wrapper for GitHub API interactions via PyGitHub."""

    def __init__(self, token: str, repo_full_name: str):
        """Initialize the GitHub client with a token and repository name (owner/repo)."""
        logging.info(f"Initializing GitHubClient for repo: {repo_full_name}")
        self.github = Github(token)
        self.repo = self.github.get_repo(repo_full_name)

    def _find_milestone(self, name: str):
        """Return an existing milestone by name, or None if not found."""
        logging.info(f"Searching for milestone: '{name}'")
        try:
            for m in self.repo.get_milestones(state='all'):
                if m.title == name:
                    logging.info(f"Found existing milestone: '{name}'")
                    return m
        except GithubException as e:
            logging.error(f"Error searching for milestone '{name}': {e}")
            pass
        logging.info(f"Milestone '{name}' not found.")
        return None

    def create_milestone(self, name: str, due_on: date = None):
        """Create or retrieve a milestone in the repository."""
        m = self._find_milestone(name)
        if m:
            return m
        logging.info(f"Creating new milestone: '{name}'")
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
        logging.info(f"Searching for issue: '{title}'")
        try:
            # search through all issues (open and closed)
            for issue in self.repo.get_issues(state='all'):
                if issue.title.strip() == title:
                    logging.info(f"Found existing issue: '{title}'")
                    return issue
        except GithubException as e:
            logging.error(f"Error searching for issue '{title}': {e}")
            pass
        logging.info(f"Issue '{title}' not found.")
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
        logging.info(f"Creating new issue: '{title}'")
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

    def get_all_issues(self):
        """Fetch all issue objects from the repository, handling pagination."""
        logging.info("Fetching all issues from repository.")
        try:
            # get_issues handles pagination automatically.
            return self.repo.get_issues(state='all')
        except GithubException as e:
            logging.error(f"Error fetching issues: {e}. Returning empty list.")
            return []

    def get_all_issue_titles(self) -> set[str]:
        """Fetch all issue titles in the repository."""
        logging.info("Fetching all issue titles from repository.")
        titles = set()
        try:
            for issue in self.repo.get_issues(state='all'):
                titles.add(issue.title.strip())
        except GithubException as e:
            # Consider more robust error handling or logging if needed
            logging.warning(f"Error fetching issue titles: {e}. Proceeding with an empty list of existing titles.")
        return titles

    def get_next_action_items(self):
        """
        Finds the earliest active milestone and returns it along with its open issues.
        The earliest milestone is determined by the due date.
        Milestones without a due date are considered after those with one.
        An active milestone is one that is open and has open issues.
        """
        logging.info("Finding next action items.")
        open_milestones = self.repo.get_milestones(state='open')

        # Filter for milestones with open issues
        active_milestones = [m for m in open_milestones if m.open_issues > 0]

        if not active_milestones:
            return None, []

        # Sort milestones by due date, None dates go last.
        active_milestones.sort(key=lambda m: (m.due_on is None, m.due_on))
        
        earliest_milestone = active_milestones[0]
        
        # Get open issues for the earliest milestone
        issues = self.repo.get_issues(milestone=earliest_milestone, state='open')
        
        return earliest_milestone, list(issues)

    def find_duplicate_issues(self) -> dict:
        """Finds open issues with duplicate titles."""
        logging.info("Finding duplicate issues.")
        open_issues = self.repo.get_issues(state='open')
        issues_by_title = {}
        for issue in open_issues:
            title = issue.title.strip()
            if title not in issues_by_title:
                issues_by_title[title] = []
            issues_by_title[title].append(issue)

        duplicates_found = {}
        for title, issues in issues_by_title.items():
            if len(issues) > 1:
                # Sort by issue number to find the original (oldest)
                issues.sort(key=lambda i: i.number)
                original = issues[0]
                duplicates = issues[1:]
                duplicates_found[title] = {
                    'original': original,
                    'duplicates': duplicates
                }
        return duplicates_found

    def get_closed_issues_for_deletion(self) -> list[dict]:
        """
        Fetch all closed issues with their numbers and node IDs for deletion.
        Handles pagination.
        """
        logging.info("Fetching closed issues for deletion via GraphQL.")
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
                logging.error(f"Error fetching closed issues via GraphQL: {e}")
                # Depending on desired robustness, could raise or return partial/empty
                return [] # Or raise a custom error
            except Exception as e: # Catch other potential errors like network issues
                logging.error(f"An unexpected error occurred fetching closed issues: {e}")
                return []


            if not data or "repository" not in data or not data["repository"] or "issues" not in data["repository"]:
                logging.warning(f"Warning: Unexpected GraphQL response structure: {data}")
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
        logging.info(f"Deleting issue by node ID: {node_id}")
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
            logging.info(f"Successfully deleted issue with node ID: {node_id}")
            return True
        except GithubException as e:
            logging.error(f"Error deleting issue {node_id} via GraphQL: {e}")
            return False
        except Exception as e:
            logging.error(f"An unexpected error occurred deleting issue {node_id}: {e}")
            return False
    
    def get_open_issues_by_milestone(self, milestone_name: str):
        """
        Fetch all open issues in a given milestone by its title.
        """
        m = self._find_milestone(milestone_name)
        if not m:
            return []
        try:
            open_issues = self.repo.get_issues(state='open')
            return [issue for issue in open_issues if issue.milestone and issue.milestone.title == milestone_name]
        except GithubException:
            return []
