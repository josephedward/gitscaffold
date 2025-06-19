import datetime
import pytest

from scaffold.github import GitHubClient

class FakeMilestone:
    def __init__(self, title, due_on=None, number=1):
        self.title = title
        self.due_on = due_on
        self.number = number

class FakeIssue:
    def __init__(self, title, number=1):
        self.title = title
        self.number = number

class FakeRepo:
    def __init__(self):
        # existing milestone and issue
        self.milestones = [FakeMilestone('Exist', number=1)]
        self.issues = [FakeIssue('ExistIssue', number=42)]
        self.created_milestones = []
        self.created_issues = []

    def get_milestones(self, state='all'):
        return self.milestones

    def create_milestone(self, **params):
        m = FakeMilestone(params['title'], params.get('due_on'), number=2)
        self.created_milestones.append(params)
        self.milestones.append(m)
        return m

    def get_issues(self, state='all'):
        return self.issues

    def create_issue(self, **params):
        issue = FakeIssue(params['title'], number=101)
        self.created_issues.append(params)
        self.issues.append(issue)
        return issue

class FakeGithub:
    def __init__(self, token):
        self.token = token

    def get_repo(self, full_name):
        assert full_name == 'owner/repo'
        return FakeRepo()

@pytest.fixture(autouse=True)
def _patch_github(monkeypatch):
    # Patch PyGitHub's Github class
    monkeypatch.setattr('scaffold.github.Github', FakeGithub)
    yield

def test_create_milestone_existing():
    client = GitHubClient('token', 'owner/repo')
    m = client.create_milestone('Exist')
    assert isinstance(m, FakeMilestone)
    assert m.number == 1

def test_create_milestone_new():
    client = GitHubClient('token', 'owner/repo')
    due = datetime.date(2025, 1, 1)
    m2 = client.create_milestone('NewMilestone', due_on=due)
    assert m2.number == 2

def test_create_issue_existing():
    client = GitHubClient('token', 'owner/repo')
    issue = client.create_issue(title='ExistIssue')
    assert isinstance(issue, FakeIssue)
    assert issue.number == 42

def test_create_issue_new_with_milestone():
    client = GitHubClient('token', 'owner/repo')
    issue = client.create_issue(
        title='NewIssue',
        body='desc',
        labels=['L'],
        assignees=['user'],
        milestone='Exist'
    )
    assert issue.number == 101
    # Ensure milestone mapping passed
    params = client.repo.created_issues[-1]
    assert params.get('milestone') == 1

def test_create_issue_new_no_milestone_error():
    client = GitHubClient('token', 'owner/repo')
    with pytest.raises(ValueError) as exc:
        client.create_issue(title='X', milestone='Missing')
    assert "Milestone 'Missing' not found" in str(exc.value)