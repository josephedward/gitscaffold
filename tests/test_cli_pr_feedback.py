import json
from click.testing import CliRunner
from unittest.mock import patch, ANY

from scaffold.cli import cli


class DummyCP:
    def __init__(self, args=None, returncode=0, stdout="", stderr=""):
        self.args = args
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


PR_JSON = {
    "number": 123,
    "title": "Test PR",
    "url": "https://github.com/owner/repo/pull/123",
    "reviews": [
        {"state": "APPROVED"},
        {"state": "CHANGES_REQUESTED"},
        {"state": "COMMENTED"},
    ],
    "reviewThreads": [
        {"comments": [{}, {}]},
        {"comments": [{}]},
    ],
    "comments": [{}, {}],
}


def test_pr_feedback_summarize_only():
    runner = CliRunner()
    with patch('scaffold.github_cli.find_gh_executable', return_value='/usr/bin/gh'), \
         patch('scaffold.github_cli.subprocess.run') as mock_run:
        # First call: gh pr view returns JSON
        mock_run.return_value = DummyCP(stdout=json.dumps(PR_JSON))

        result = runner.invoke(cli, [
            'gh', 'pr-feedback', '--repo', 'owner/repo', '--pr', '123', '--summarize'
        ])

        assert result.exit_code == 0, result.output
        assert "PR #123: Test PR" in result.output
        assert "Reviews: 3 (approved=1, changes_requested=1, commented=1)" in result.output
        assert "Review comments: 3" in result.output
        assert "Issue comments: 2" in result.output


def test_pr_feedback_label_on_changes_dry_run():
    runner = CliRunner()
    with patch('scaffold.github_cli.find_gh_executable', return_value='/usr/bin/gh'), \
         patch('scaffold.github_cli.subprocess.run') as mock_run:
        mock_run.return_value = DummyCP(stdout=json.dumps(PR_JSON))

        result = runner.invoke(cli, [
            'gh', 'pr-feedback', '--repo', 'owner/repo', '--pr', '123',
            '--label-on-changes', 'needs-changes', '--dry-run'
        ])

        assert result.exit_code == 0, result.output
        assert "Would add labels ['needs-changes'] to PR #123" in result.output


def test_pr_feedback_label_on_changes_live():
    runner = CliRunner()
    with patch('scaffold.github_cli.find_gh_executable', return_value='/usr/bin/gh'), \
         patch('scaffold.github_cli.subprocess.run') as mock_run:
        # First call -> view, then edit call (no capture_output expected)
        mock_run.side_effect = [
            DummyCP(stdout=json.dumps(PR_JSON)),
            DummyCP(returncode=0, stdout=""),
        ]

        result = runner.invoke(cli, [
            'gh', 'pr-feedback', '--repo', 'owner/repo', '--pr', '123',
            '--label-on-changes', 'needs-changes'
        ])

        assert result.exit_code == 0, result.output
        # Verify pr edit invocation
        # The first call is pr view
        # The second call should include: gh pr edit 123 --repo owner/repo --add-label needs-changes
        edit_call = mock_run.mock_calls[1]
        args_passed = edit_call.args[0]
        assert args_passed[:3] == ['/usr/bin/gh', 'pr', 'edit']
        assert '123' in args_passed
        assert '--repo' in args_passed and 'owner/repo' in args_passed
        assert '--add-label' in args_passed and 'needs-changes' in args_passed


def test_pr_feedback_post_comment_dry_run():
    runner = CliRunner()
    with patch('scaffold.github_cli.find_gh_executable', return_value='/usr/bin/gh'), \
         patch('scaffold.github_cli.subprocess.run') as mock_run:
        mock_run.return_value = DummyCP(stdout=json.dumps(PR_JSON))

        result = runner.invoke(cli, [
            'gh', 'pr-feedback', '--repo', 'owner/repo', '--pr', '123', '--comment', '--dry-run'
        ])

        assert result.exit_code == 0, result.output
        assert "Would post summary comment to PR #123" in result.output


def test_pr_feedback_post_comment_live():
    runner = CliRunner()
    with patch('scaffold.github_cli.find_gh_executable', return_value='/usr/bin/gh'), \
         patch('scaffold.github_cli.subprocess.run') as mock_run:
        mock_run.side_effect = [
            DummyCP(stdout=json.dumps(PR_JSON)),  # view
            DummyCP(returncode=0, stdout=""),    # comment
        ]

        result = runner.invoke(cli, [
            'gh', 'pr-feedback', '--repo', 'owner/repo', '--pr', '123', '--comment'
        ])

        assert result.exit_code == 0, result.output
        # Second call should be gh pr comment
        comment_call = mock_run.mock_calls[1]
        args_passed = comment_call.args[0]
        assert args_passed[:3] == ['/usr/bin/gh', 'pr', 'comment']
        assert '123' in args_passed
        assert '--repo' in args_passed and 'owner/repo' in args_passed
        assert '--body' in args_passed

