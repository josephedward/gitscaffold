import pytest
from click.testing import CliRunner
from pathlib import Path
import json

from scaffold.cli import cli # Main CLI entry point
from scaffold.github import GitHubClient # To mock its methods

# Sample roadmap data for testing
SAMPLE_ROADMAP_DATA = {
    "name": "Test Project Sync",
    "description": "A test project for sync functionality.",
    "milestones": [
        {"name": "M1: Setup", "due_date": "2025-01-01"}
    ],
    "features": [
        {
            "title": "Feature A: Core Logic",
            "description": "Implement the core logic.",
            "milestone": "M1: Setup",
            "labels": ["enhancement", "core"],
            "tasks": [
                {
                    "title": "Task A.1: Design",
                    "description": "Design the core logic.",
                    "labels": ["design"]
                },
                {
                    "title": "Task A.2: Implement",
                    "description": "Implement the core logic.",
                    "labels": ["implementation"]
                }
            ]
        },
        {
            "title": "Feature B: API",
            "description": "Develop the API.",
            "milestone": "M1: Setup",
            "labels": ["api"],
            "tasks": [
                {
                    "title": "Task B.1: Define Endpoints",
                    "description": "Define API endpoints.",
                    "labels": ["api", "design"]
                }
            ]
        }
    ]
}

@pytest.fixture
def runner():
    return CliRunner()

from unittest.mock import MagicMock

# Helper classes at module level
class MockIssue:
    def __init__(self, number, title, body="", milestone=None, labels=None, assignees=None):
        self.number = number
        self.title = title
        self.body = body
        self.milestone = milestone # Should be a MockMilestone object or None
        self.labels = labels or []
        self.assignees = assignees or []

class MockMilestone:
    def __init__(self, title, number=1, due_on=None):
        self.title = title
        self.number = number
        self.due_on = due_on


@pytest.fixture
def mock_github_client(monkeypatch):
    """Mocks GitHubClient by replacing its instantiation in scaffold.cli."""
    
    # Shared state for the mock client methods
    mock_issues_created_list = []
    mock_milestones_created_list = []
    existing_issue_titles_set = set()
    existing_milestones_map = {}  # title -> MockMilestone object
    pre_existing_issues_map = {} # title -> MockIssue object (for issues that exist "remotely")

    class MockedGitHubClientInstance:
        def __init__(self, token, repo_full_name_arg):
            self.token = token # Not used, but part of real signature
            # Mock self.repo.full_name as it's used by the sync command
            self.repo = MagicMock()
            self.repo.full_name = repo_full_name_arg
            
            # Methods will operate on the shared state from the outer fixture scope
            # This is a form of closure over the lists/dicts defined above.

        def get_all_issue_titles(self) -> set[str]:
            return existing_issue_titles_set

        def _find_milestone(self, name: str):
            return existing_milestones_map.get(name)

        def create_milestone(self, name: str, due_on=None):
            if name in existing_milestones_map: # If it "pre-existed"
                return existing_milestones_map[name]
            
            # Check if it was already created in this "session" by this mock
            for m in mock_milestones_created_list:
                if m.title == name:
                    return m

            new_m = MockMilestone(title=name, due_on=due_on, number=len(existing_milestones_map) + len(mock_milestones_created_list) + 1)
            # Unlike real client, we might add to existing_milestones_map here so _find_milestone can see it immediately
            # Or rely on tests to populate existing_milestones_map for pre-existing ones.
            # For simplicity, let's assume create_milestone makes it findable by _find_milestone.
            existing_milestones_map[name] = new_m 
            mock_milestones_created_list.append(new_m)
            return new_m
        
        def _find_issue(self, title: str):
            # Check issues created during this sync operation first
            for issue in mock_issues_created_list:
                if issue.title == title:
                    return issue
            # Then check "pre-existing" issues (simulating those already on GitHub)
            return pre_existing_issues_map.get(title)

        def create_issue(self, title: str, body: str = None, assignees: list = None, labels: list = None, milestone: str = None):
            # Real client's create_issue calls _find_issue first.
            # Our sync logic checks `title in existing_issue_titles` then calls create_issue if not found and confirmed.
            # So, this mock method assumes the decision to create has been made.

            milestone_obj = None
            if milestone: # milestone is a name string
                milestone_obj = self._find_milestone(milestone) # Uses mocked _find_milestone
                if not milestone_obj:
                    # This behavior is consistent with the real GitHubClient if a milestone name is provided
                    # but the milestone doesn't exist (it would try to find it, then fail).
                    # The sync logic in cli.py should ensure milestones exist before creating issues with them.
                    # However, the GitHubClient.create_issue itself raises ValueError if milestone not found by name.
                    raise ValueError(f"Mocked GitHubClient: Milestone '{milestone}' not found for issue '{title}'")

            new_issue = MockIssue(
                number=len(mock_issues_created_list) + 100, # Arbitrary starting number for new issues
                title=title,
                body=body,
                milestone=milestone_obj, # Pass the MockMilestone object
                labels=labels,
                assignees=assignees
            )
            mock_issues_created_list.append(new_issue)
            existing_issue_titles_set.add(title) # Ensure it's now "existing"
            return new_issue

    # This is what the tests will use to set up pre-existing state and check results.
    fixture_data_access = {
        "existing_issue_titles_set": existing_issue_titles_set,
        "existing_milestones_map": existing_milestones_map,
        "pre_existing_issues_map": pre_existing_issues_map,
        "mock_issues_created": mock_issues_created_list, # Renamed for clarity
        "mock_milestones_created": mock_milestones_created_list # Renamed for clarity
    }

    # Patch the GitHubClient class in the context of scaffold.cli module
    # When scaffold.cli.GitHubClient(token, repo) is called, it will now call this lambda,
    # which returns an instance of our MockedGitHubClientInstance.
    monkeypatch.setattr("scaffold.cli.GitHubClient", lambda token, repo_full_name: MockedGitHubClientInstance(token, repo_full_name))
    
    return fixture_data_access


@pytest.fixture
def sample_roadmap_file(tmp_path):
    """Creates a temporary roadmap JSON file."""
    roadmap_file = tmp_path / "roadmap.json"
    with open(roadmap_file, 'w') as f:
        json.dump(SAMPLE_ROADMAP_DATA, f, indent=2)
    return roadmap_file

def test_sync_dry_run_empty_repo(runner, sample_roadmap_file, mock_github_client, monkeypatch):
    """Test sync command with --dry-run on an empty repository."""
    # Mock click.confirm to always return False (or True, doesn't matter for dry-run)
    monkeypatch.setattr("click.confirm", lambda prompt, default: False)

    result = runner.invoke(cli, [
        'sync', str(sample_roadmap_file),
        '--repo', 'owner/repo',
        '--token', 'fake-token',
        '--dry-run'
    ])

    assert result.exit_code == 0
    assert "[dry-run] Milestone 'M1: Setup' not found. Would create" in result.output
    assert "[dry-run] Feature 'Feature A: Core Logic' not found. Would prompt to create." in result.output
    assert "[dry-run] Task 'Task A.1: Design' (for feature 'Feature A: Core Logic') not found. Would prompt to create." in result.output
    assert "[dry-run] Task 'Task A.2: Implement' (for feature 'Feature A: Core Logic') not found. Would prompt to create." in result.output
    assert "[dry-run] Feature 'Feature B: API' not found. Would prompt to create." in result.output
    assert "[dry-run] Task 'Task B.1: Define Endpoints' (for feature 'Feature B: API') not found. Would prompt to create." in result.output
    
    assert len(mock_github_client["mock_issues_created"]) == 0
    assert len(mock_github_client["mock_milestones_created"]) == 0

def test_sync_create_all_items_confirm_yes(runner, sample_roadmap_file, mock_github_client, monkeypatch):
    """Test sync command creating all items when user confirms yes."""
    # Mock click.confirm to always return True (user says "yes" to all creations)
    monkeypatch.setattr("click.confirm", lambda prompt, default: True)
    # Mock AI enrichment to do nothing
    monkeypatch.setattr("scaffold.cli.enrich_issue_description", lambda title, body, context: body)

    result = runner.invoke(cli, [
        'sync', str(sample_roadmap_file),
        '--repo', 'owner/repo',
        '--token', 'fake-token'
        # No --dry-run
    ])

    assert result.exit_code == 0
    
    # Check milestone
    assert "Milestone 'M1: Setup' not found. Creating..." in result.output
    assert "Milestone created: M1: Setup" in result.output
    assert len(mock_github_client["mock_milestones_created"]) == 1
    assert mock_github_client["mock_milestones_created"][0].title == "M1: Setup"

    # Check features and tasks created (2 features + 3 tasks = 5 issues)
    assert "Creating feature issue: Feature A: Core Logic" in result.output
    assert "Feature issue created: #100 Feature A: Core Logic" in result.output # Assuming mock issue numbers start at 100
    assert "Creating task issue: Task A.1: Design" in result.output
    assert "Task issue created: #101 Task A.1: Design" in result.output
    assert "Creating task issue: Task A.2: Implement" in result.output
    assert "Task issue created: #102 Task A.2: Implement" in result.output
    assert "Creating feature issue: Feature B: API" in result.output
    assert "Feature issue created: #103 Feature B: API" in result.output
    assert "Creating task issue: Task B.1: Define Endpoints" in result.output
    assert "Task issue created: #104 Task B.1: Define Endpoints" in result.output

    assert len(mock_github_client["mock_issues_created"]) == 5
    
    # Check parent linking for a task
    task_a1 = next(i for i in mock_github_client["mock_issues_created"] if i.title == "Task A.1: Design")
    assert "Parent issue: #100" in task_a1.body # Feature A was #100

    task_b1 = next(i for i in mock_github_client["mock_issues_created"] if i.title == "Task B.1: Define Endpoints")
    assert "Parent issue: #103" in task_b1.body # Feature B was #103

def test_sync_some_items_exist(runner, sample_roadmap_file, mock_github_client, monkeypatch):
    """Test sync when some items already exist in the repo."""
    # Pre-populate some "existing" items
    mock_github_client["existing_issue_titles_set"].add("Feature A: Core Logic")
    mock_github_client["existing_issue_titles_set"].add("Task A.1: Design")
    
    # Simulate Feature A already exists and has an issue number for parent linking
    # This part of the mock needs to be careful: _find_issue in the mock currently only checks mock_issues_created.
    # For this test, we need _find_issue to be able to return a "pre-existing" issue.
    # Let's refine the mock_github_client fixture or how we use it for this.
    # For now, let's assume Feature A was created in a previous run and its tasks are being added.
    # The current mock_github_client._find_issue will return None for "Feature A: Core Logic" initially.
    # The sync logic will then try to create it if user confirms.
    # To properly test "existing", the mock's _find_issue needs to be aware of pre-existing items.

    # Let's simplify: assume the titles exist, so sync won't prompt for them.
    # We'll test creation of the *remaining* items.

    monkeypatch.setattr("click.confirm", lambda prompt, default: True) # Confirm yes for new items
    monkeypatch.setattr("scaffold.cli.enrich_issue_description", lambda title, body, context: body)

    # Add a pre-existing milestone to the map that _find_milestone will check
    pre_existing_m1_obj = MockMilestone(title='M1: Setup', number=1, due_on="2025-01-01")
    mock_github_client["existing_milestones_map"]["M1: Setup"] = pre_existing_m1_obj
    
    # Simulate "Feature A: Core Logic" already exists "remotely" and has an issue number.
    # This allows _find_issue to return it, which is needed for parent task linking.
    pre_existing_feature_a_obj = MockIssue(title="Feature A: Core Logic", number=90, milestone=pre_existing_m1_obj)
    mock_github_client["pre_existing_issues_map"]["Feature A: Core Logic"] = pre_existing_feature_a_obj
    # Task A.1 also pre-exists by title, but we don't need its object for this specific test's assertions yet,
    # unless we were testing linking *to* it or its properties.

    result = runner.invoke(cli, [
        'sync', str(sample_roadmap_file),
        '--repo', 'owner/repo',
        '--token', 'fake-token'
    ])

    assert result.exit_code == 0

    assert "Milestone 'M1: Setup' already exists." in result.output
    assert "Feature 'Feature A: Core Logic' already exists in GitHub issues. Checking its tasks..." in result.output
    assert "Task 'Task A.1: Design' (for feature 'Feature A: Core Logic') already exists in GitHub issues." in result.output
    
    # These should be created
    assert "Creating task issue: Task A.2: Implement" in result.output
    assert "Creating feature issue: Feature B: API" in result.output
    assert "Creating task issue: Task B.1: Define Endpoints" in result.output

    # Total issues created in this run: Task A.2, Feature B, Task B.1 (3 issues)
    # mock_issues_created is cumulative in the mock if not reset.
    # Let's count based on output for simplicity here, or reset mock_issues_created.
    # For this test, let's assume mock_issues_created starts empty for this run.
    # The current mock_github_client fixture has mock_issues_created as a list that persists.
    # This needs careful handling in test setup if we want to count "newly created in this run".

    # A better check:
    created_titles_in_run = {issue.title for issue in mock_github_client["mock_issues_created"]}
    assert "Task A.2: Implement" in created_titles_in_run
    assert "Feature B: API" in created_titles_in_run
    assert "Task B.1: Define Endpoints" in created_titles_in_run
    assert "Feature A: Core Logic" not in created_titles_in_run # Because it pre-existed by title
    assert "Task A.1: Design" not in created_titles_in_run # Because it pre-existed by title
    assert len(created_titles_in_run) == 3


# TODO: Add more tests:
# - User declines creation of an item.
# - AI enrichment is triggered.
# - AI extraction is used (though sync's --ai-extract is for the initial roadmap parsing).
# - Error handling (e.g., milestone for a feature not found in roadmap data - though validator should catch this).
# - Syncing with a roadmap that has no milestones, or no tasks under features.
# - Test parent linking when feature already existed (mock _find_issue to return an existing feature).
# - Test that if a feature is skipped, its tasks are also effectively skipped or handled gracefully.
#   (Current logic: tasks are processed per feature; if feature is skipped, tasks won't be prompted under it).
