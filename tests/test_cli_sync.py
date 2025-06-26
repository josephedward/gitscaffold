import pytest
from click.testing import CliRunner
from pathlib import Path
import yaml

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

@pytest.fixture
def mock_github_client(monkeypatch):
    """Mocks GitHubClient and its relevant methods."""
    mock_issues_created = []
    mock_milestones_created = []
    
    class MockIssue:
        def __init__(self, number, title, body="", milestone=None, labels=None, assignees=None):
            self.number = number
            self.title = title
            self.body = body
            self.milestone = milestone
            self.labels = labels or []
            self.assignees = assignees or []

    class MockMilestone:
        def __init__(self, title, number=1, due_on=None):
            self.title = title
            self.number = number
            self.due_on = due_on

    # Store existing titles to simulate a GitHub repo state
    existing_issue_titles_set = set()
    existing_milestones_map = {} # title -> MockMilestone

    def _get_all_issue_titles():
        return existing_issue_titles_set

    def _find_milestone(name):
        return existing_milestones_map.get(name)

    def _create_milestone(name, due_on=None):
        if name in existing_milestones_map:
            return existing_milestones_map[name]
        new_m = MockMilestone(title=name, due_on=due_on, number=len(existing_milestones_map) + 1)
        existing_milestones_map[name] = new_m
        mock_milestones_created.append(new_m)
        return new_m
    
    def _find_issue(title):
        # This is a simplified find, real one might search a list of MockIssue objects
        # For sync, we primarily care about titles, so this might not be heavily used by sync's direct logic
        # if the title is in existing_issue_titles_set.
        # However, it's used to get the parent issue object.
        for issue in mock_issues_created: # Check newly created ones
            if issue.title == title:
                return issue
        # In a more complex mock, you'd also check "pre-existing" issues.
        return None


    def _create_issue(title, body, assignees, labels, milestone):
        # Simulate finding the milestone object if only name is passed
        milestone_obj = None
        if milestone and isinstance(milestone, str): # milestone name
            milestone_obj = existing_milestones_map.get(milestone)

        new_issue = MockIssue(
            number=len(mock_issues_created) + 100, # Arbitrary starting number
            title=title,
            body=body,
            milestone=milestone_obj,
            labels=labels,
            assignees=assignees
        )
        mock_issues_created.append(new_issue)
        existing_issue_titles_set.add(title) # Add to existing titles upon creation
        return new_issue

    monkeypatch.setattr(GitHubClient, "get_all_issue_titles", _get_all_issue_titles)
    monkeypatch.setattr(GitHubClient, "_find_milestone", _find_milestone)
    monkeypatch.setattr(GitHubClient, "create_milestone", _create_milestone)
    monkeypatch.setattr(GitHubClient, "_find_issue", _find_issue)
    monkeypatch.setattr(GitHubClient, "create_issue", _create_issue)
    
    # Allow tests to modify the "remote" state and check created items
    return {
        "existing_issue_titles_set": existing_issue_titles_set,
        "existing_milestones_map": existing_milestones_map,
        "mock_issues_created": mock_issues_created,
        "mock_milestones_created": mock_milestones_created
    }


@pytest.fixture
def sample_roadmap_file(tmp_path):
    """Creates a temporary roadmap YAML file."""
    roadmap_file = tmp_path / "roadmap.yaml"
    with open(roadmap_file, 'w') as f:
        yaml.dump(SAMPLE_ROADMAP_DATA, f)
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

    # Add a pre-existing milestone
    existing_m1 = mock_github_client["mock_milestones_created"].append(
        type('MockMilestone', (), {'title': 'M1: Setup', 'number': 1})
    )
    mock_github_client["existing_milestones_map"]["M1: Setup"] = existing_m1


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
