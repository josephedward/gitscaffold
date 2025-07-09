<!-- Gitscaffold README -->
# Gitscaffold – Generate GitHub Issues from Markdown Roadmaps
  
<!-- Badges -->
[![CI](https://github.com/OWNER/REPO/actions/workflows/test-and-update-coverage.yml/badge.svg)](https://github.com/OWNER/REPO/actions)
[![Coverage Status](https://img.shields.io/codecov/c/gh/OWNER/REPO.svg?logo=codecov)](https://codecov.io/gh/OWNER/REPO)
[![Documentation Status](https://readthedocs.org/projects/RTD_PROJECT_NAME/badge/?version=latest)](https://RTD_PROJECT_NAME.readthedocs.io)

Gitscaffold is a command-line tool and GitHub Action that converts Markdown-based roadmaps into GitHub issues and milestones using AI-driven extraction and enrichment.

## Key Features

*   **AI-Powered Issue Extraction**: Convert free-form Markdown documents into structured GitHub issues using OpenAI.
*   **Roadmap Synchronization (`sync`)**: Compare your Markdown roadmap with an existing GitHub repository and interactively create missing issues to keep them aligned.
*   **Bulk Delete Closed Issues (`delete-closed`)**: Clean up your repository by permanently removing all closed issues, with dry-run and confirmation steps.
*   **Cleanup Issue Titles (`sanitize`)**: Strip leading Markdown header characters from existing GitHub issue titles, with preview and confirmation.
*   **AI Enrichment**: Enhance issue descriptions with AI-generated content for clarity and context.
*   **Roadmap Initialization**: Quickly scaffold a new roadmap template file.
*   **Show Next Action Items (`next`)**: Display open issues for the earliest active milestone.
*   **Show Next Task (`next-task`)**: Display or select your next open task for the current roadmap phase, with optional random pick and browser opening.
*   **Diff Local Roadmap vs GitHub Issues (`diff`)**: Compare your local Markdown roadmap file against your repository’s open and closed issues.
*   **Flexible Authentication**: Supports GitHub tokens and OpenAI keys via environment variables, `.env` files, or command-line options.

## Installation
```sh
pip install gitscaffold
```

## Authentication and API Keys

`gitscaffold` requires a GitHub Personal Access Token (PAT) for interacting with GitHub and an OpenAI API key for AI-driven features.

You can provide these keys in a few ways:
1.  **Environment Variables**: Set `GITHUB_TOKEN` and `OPENAI_API_KEY` in your shell.
2.  **`.env` file**: Create a `.env` file in your project's root directory. `gitscaffold` will automatically load it.
    ```
    GITHUB_TOKEN="your_github_personal_access_token"
    OPENAI_API_KEY="your_openai_api_key"
    ```
    *   **GitHub Token (`GITHUB_TOKEN`)**:
        *   You'll need a [Personal Access Token (PAT)](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens#creating-a-personal-access-token-classic).
        *   For operations on *existing* repositories (e.g., `gitscaffold create`, `gitscaffold import-md`), the token primarily needs the `issues:write` permission.
        *   If you use commands that *create new repositories* (e.g., `gitscaffold setup-repository` from the `scaffold.cli` or `./gitscaffold.py setup`), your PAT will need the `repo` scope (which includes `public_repo` and `repo:status`).
    *   **OpenAI API Key (`OPENAI_API_KEY`)**: This is your standard API key from [OpenAI](https://platform.openai.com/api-keys).
    *   **Important**: Add your `.env` file to your `.gitignore` to prevent accidentally committing your secret keys.
3.  **Command-line Options**: Pass them directly, e.g., `--token YOUR_GITHUB_TOKEN`.

If a token/key is provided via a command-line option, it will take precedence over environment variables or `.env` file settings. If not provided via an option, environment variables are checked next, followed by the `.env` file. Some commands like `gitscaffold create` may prompt for the GitHub token if it's not found.

## CLI Usage


### Import and enrich from unstructured Markdown
When you have a free-form Markdown document, use `import-md` to extract and enrich issues.

**Example Markdown roadmap** (`markdown_roadmap.md`):
```markdown
# Authentication Service
Implement login, logout, and registration flows.

## Database Schema
- Define `users` table: id, email, password_hash
- Define `sessions` table: id, user_id, expires_at

# Payment Integration
Enable subscription payments with Stripe.

## Stripe Webhook
- Listen to payment events and update user plans
```

```sh
# Preview extracted and enriched issues (dry-run)
export OPENAI_API_KEY=<your-openai-key>
gitscaffold import-md owner/repo markdown_roadmap.md \
  --heading-level 1 --dry-run --token $GITHUB_TOKEN

# Show detailed progress logs during extraction and enrichment
gitscaffold import-md owner/repo markdown_roadmap.md \
  --heading-level 1 --dry-run --verbose --token $GITHUB_TOKEN --openai-key $OPENAI_API_KEY

# Create enriched issues on GitHub
gitscaffold import-md owner/repo markdown_roadmap.md \
  --heading-level 1 --token $GITHUB_TOKEN
```

### Sync Roadmap with Repository
Use `sync` to create and update GitHub issues from a roadmap file. It compares the roadmap with the repository and creates any missing milestones or issues.

It supports two kinds of roadmaps:
1.  **Structured Roadmap**: A file containing JSON structure. With the latest changes, it can parse this format from any file type, including `.md` files.
2.  **Unstructured Markdown**: A free-form markdown document (e.g., `notes.md`). Use the `--ai-extract` flag to parse this with an LLM.

```sh
# Sync with a structured roadmap file (can be .md, .md, etc.)
gitscaffold sync ROADMAP.md --repo owner/repo

# To enrich descriptions of new issues with AI during sync
gitscaffold sync ROADMAP.md --repo owner/repo --ai-enrich

# Sync with an unstructured Markdown file, using AI to extract issues
# Make sure OPENAI_API_KEY is set in your environment or .env file
gitscaffold sync design_notes.md \
  --repo owner/repo \
  --ai-extract

# Simulate any sync operation without making changes
gitscaffold sync ROADMAP.md --repo owner/repo --dry-run
```

### Delete closed issues
Use `delete-closed` to permanently remove all closed issues from a specified repository. This action is irreversible and requires confirmation.

```sh
# List closed issues that would be deleted (dry run)
gitscaffold delete-closed --repo owner/repo --token $GITHUB_TOKEN --dry-run

# Delete all closed issues (will prompt for confirmation)
gitscaffold delete-closed --repo owner/repo --token $GITHUB_TOKEN
```

### Sanitize Issue Titles

Use `sanitize` to remove leading Markdown header markers (e.g., `#`) from existing issue titles in a repository.

```sh
# Dry-run: list titles that need cleanup
gitscaffold sanitize --repo owner/repo --token $GITHUB_TOKEN --dry-run

# Apply fixes (will prompt for confirmation)
gitscaffold sanitize --repo owner/repo --token $GITHUB_TOKEN
```

### Show Next Action Items

Use `next` to view all open issues from the earliest active milestone in your repository.

```sh
gitscaffold next --repo owner/repo --token $GITHUB_TOKEN
```

### Show Next Task for Current Phase

Use `next-task` to pick your next open task for the current roadmap phase. By default, the oldest task is shown; use `--pick` to choose randomly and `--browse` to open it in your browser.

```sh
gitscaffold next-task ROADMAP_FILE --repo owner/repo --token $GITHUB_TOKEN [--pick] [--browse]
```

### Diff Roadmap and GitHub Issues

Use `diff` to compare a local roadmap file against GitHub issues. It lists items present in your roadmap but missing on GitHub, and issues on GitHub not in your roadmap.

```sh
gitscaffold diff ROADMAP.md --repo owner/repo --token $GITHUB_TOKEN
```

### Initialize a roadmap template
```sh
gitscaffold init example-roadmap.md
```

### From the source checkout
You can clone this repository and use the top-level `gitscaffold.py` script:
```sh
## Setup GitHub labels, milestones, and project board
./gitscaffold.py setup owner/repo --phase phase-1 --create-project

## Delete all closed issues in a repository
./gitscaffold.py delete-closed owner/repo

## Enrich a single issue or batch
./gitscaffold.py enrich owner/repo --issue 123 --path ROADMAP.md --apply
./gitscaffold.py enrich owner/repo --batch --path ROADMAP.md --csv out.csv --interactive

## Import from unstructured Markdown (via AI)
./gitscaffold.py import-md owner/repo markdown_roadmap.md --heading-level 2 --token $GITHUB_TOKEN

# Show detailed progress logs during import
./gitscaffold.py import-md owner/repo markdown_roadmap.md \
  --heading-level 2 --dry-run --verbose --token $GITHUB_TOKEN --openai-key $OPENAI_API_KEY

## Initialize a new roadmap Markdown template
./gitscaffold.py init ROADMAP.md
```

### Audit Repository (cleanup, deduplicate, diff)

Use the provided `scripts/audit.sh` to run cleanup, deduplicate, and diff in one go. It will prompt for your GitHub repo, token, and local roadmap file.

```sh
bash scripts/audit.sh
```

## Test Coverage
<!-- COVERAGE_START -->

```text
============================= test session starts ==============================
platform linux -- Python 3.11.13, pytest-8.4.1, pluggy-1.6.0
rootdir: /home/runner/work/gitscaffold/gitscaffold
configfile: pyproject.toml
plugins: anyio-4.9.0, cov-6.2.1
collected 35 items

tests/test_cli_cleanup.py ......                                         [ 17%]
tests/test_cli_deduplicate.py ....                                       [ 28%]
tests/test_cli_diff.py ....                                              [ 40%]
tests/test_cli_next.py FFFFFF.                                           [ 60%]
tests/test_cli_sync.py ...                                               [ 68%]
tests/test_github.py .....                                               [ 82%]
tests/test_import_md.py ..                                               [ 88%]
tests/test_parser.py .                                                   [ 91%]
tests/test_validator.py ...                                              [100%]

=================================== FAILURES ===================================
________________________ test_next_no_active_milestones ________________________

runner = <click.testing.CliRunner object at 0x7f50a5380090>
mock_github_client_for_next = <MagicMock id='139984346026448'>

    def test_next_no_active_milestones(runner, mock_github_client_for_next):
        """Test `next` command when no active milestones are found."""
        # Configure mock to return no milestone
        mock_github_client_for_next.get_next_action_items.return_value = (None, [])
    
        result = runner.invoke(cli, ['next', '--repo', 'owner/repo'])
    
>       assert result.exit_code == 0
E       assert 1 == 0
E        +  where 1 = <Result SystemExit(1)>.exit_code

tests/test_cli_next.py:58: AssertionError
------------------------------ Captured log call -------------------------------
WARNING  root:cli.py:118 GitHub PAT not found in environment or .env file.
__________________ test_next_with_active_milestone_and_issues __________________

runner = <click.testing.CliRunner object at 0x7f50a538c290>
mock_github_client_for_next = <MagicMock id='139984345812688'>

    def test_next_with_active_milestone_and_issues(runner, mock_github_client_for_next):
        """Test `next` command with an active milestone and open issues."""
        milestone = MockMilestone("v1.0 Launch", due_on="2025-12-31")
        issues = [
            MockIssue(101, "Finalize documentation"),
            MockIssue(102, "Deploy to production", assignees=['testuser'])
        ]
        mock_github_client_for_next.get_next_action_items.return_value = (milestone, issues)
    
        result = runner.invoke(cli, ['next', '--repo', 'owner/repo'])
    
>       assert result.exit_code == 0
E       assert 1 == 0
E        +  where 1 = <Result SystemExit(1)>.exit_code

tests/test_cli_next.py:74: AssertionError
------------------------------ Captured log call -------------------------------
WARNING  root:cli.py:118 GitHub PAT not found in environment or .env file.
_____________________ test_next_milestone_with_no_due_date _____________________

runner = <click.testing.CliRunner object at 0x7f50a5408c10>
mock_github_client_for_next = <MagicMock id='139984346579152'>

    def test_next_milestone_with_no_due_date(runner, mock_github_client_for_next):
        """Test `next` command with a milestone that has no due date."""
        milestone = MockMilestone("Backlog")
        issues = [MockIssue(201, "Refactor core module")]
        mock_github_client_for_next.get_next_action_items.return_value = (milestone, issues)
    
        result = runner.invoke(cli, ['next', '--repo', 'owner/repo'])
    
>       assert result.exit_code == 0
E       assert 1 == 0
E        +  where 1 = <Result SystemExit(1)>.exit_code

tests/test_cli_next.py:88: AssertionError
------------------------------ Captured log call -------------------------------
WARNING  root:cli.py:118 GitHub PAT not found in environment or .env file.
____________________ test_next_with_no_issues_in_milestone _____________________

runner = <click.testing.CliRunner object at 0x7f50a53ba0d0>
mock_github_client_for_next = <MagicMock id='139984346267216'>

    def test_next_with_no_issues_in_milestone(runner, mock_github_client_for_next):
        """Test `next` command when the earliest milestone has no open issues listed (edge case)."""
        # The get_next_action_items function filters for m.open_issues > 0, so this case
        # where it returns a milestone but no issues should be handled gracefully.
        milestone = MockMilestone("Future Ideas", due_on="2026-01-01")
        mock_github_client_for_next.get_next_action_items.return_value = (milestone, [])
    
        result = runner.invoke(cli, ['next', '--repo', 'owner/repo'])
    
>       assert result.exit_code == 0
E       assert 1 == 0
E        +  where 1 = <Result SystemExit(1)>.exit_code

tests/test_cli_next.py:101: AssertionError
------------------------------ Captured log call -------------------------------
WARNING  root:cli.py:118 GitHub PAT not found in environment or .env file.
_________________ test_next_without_repo_flag_uses_git_config __________________

mock_get_repo = <MagicMock name='get_repo_from_git_config' id='139984347725072'>
runner = <click.testing.CliRunner object at 0x7f50a551d4d0>
mock_github_client_for_next = <MagicMock id='139984347712464'>

    @patch('scaffold.cli.get_repo_from_git_config', return_value='git/repo')
    def test_next_without_repo_flag_uses_git_config(mock_get_repo, runner, mock_github_client_for_next):
        """Test that `next` command uses repo from git config if --repo is omitted."""
        mock_github_client_for_next.get_next_action_items.return_value = (None, [])
    
        result = runner.invoke(cli, ['next'])
    
>       assert result.exit_code == 0
E       assert 1 == 0
E        +  where 1 = <Result SystemExit(1)>.exit_code

tests/test_cli_next.py:113: AssertionError
------------------------------ Captured log call -------------------------------
WARNING  root:cli.py:118 GitHub PAT not found in environment or .env file.
_________________ test_next_fails_if_no_repo_provided_or_found _________________

mock_get_repo = <MagicMock name='get_repo_from_git_config' id='139984346254864'>
runner = <click.testing.CliRunner object at 0x7f50a53ba110>

    @patch('scaffold.cli.get_repo_from_git_config', return_value=None)
    def test_next_fails_if_no_repo_provided_or_found(mock_get_repo, runner):
        """Test `next` command fails if no repo is given and it can't be found in git config."""
        result = runner.invoke(cli, ['next'])
    
        assert result.exit_code == 1
>       assert "Could not determine repository from git config. Please use --repo." in result.output
E       AssertionError: assert 'Could not determine repository from git config. Please use --repo.' in 'GitHub PAT not found in environment or .env file.
Please enter your GitHub Personal Access Token (PAT): 

Aborted!
'
E        +  where 'GitHub PAT not found in environment or .env file.
Please enter your GitHub Personal Access Token (PAT): 

Aborted!
' = <Result SystemExit(1)>.output

tests/test_cli_next.py:125: AssertionError
------------------------------ Captured log call -------------------------------
WARNING  root:cli.py:118 GitHub PAT not found in environment or .env file.
=============================== warnings summary ===============================
../../../../../opt/hostedtoolcache/Python/3.11.13/x64/lib/python3.11/site-packages/scaffold/validator.py:32
  /opt/hostedtoolcache/Python/3.11.13/x64/lib/python3.11/site-packages/scaffold/validator.py:32: PydanticDeprecatedSince20: Pydantic V1 style `@root_validator` validators are deprecated. You should migrate to Pydantic V2 style `@model_validator` validators, see the migration guide for more details. Deprecated in Pydantic V2.0 to be removed in V3.0. See Pydantic V2 Migration Guide at https://errors.pydantic.dev/2.11/migration/
    @root_validator(skip_on_failure=True)

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
================================ tests coverage ================================
_______________ coverage: platform linux, python 3.11.13-final-0 _______________

Name                             Stmts   Miss  Cover   Missing
--------------------------------------------------------------
scaffold/__init__.py                 1      1     0%   2
scaffold/__main__.py                 3      3     0%   1-4
scaffold/ai.py                      72     72     0%   2-129
scaffold/cli.py                    661    661     0%   1-944
scaffold/github.py                 155    155     0%   3-241
scaffold/main.py                     0      0   100%
scaffold/parser.py                 177    177     0%   3-238
scaffold/scripts/__init__.py         1      1     0%   2
scaffold/scripts/import_md.py       88     88     0%   8-117
scaffold/templates/__init__.py       0      0   100%
scaffold/validator.py               35     35     0%   3-44
--------------------------------------------------------------
TOTAL                             1193   1193     0%
=========================== short test summary info ============================
FAILED tests/test_cli_next.py::test_next_no_active_milestones - assert 1 == 0
 +  where 1 = <Result SystemExit(1)>.exit_code
FAILED tests/test_cli_next.py::test_next_with_active_milestone_and_issues - assert 1 == 0
 +  where 1 = <Result SystemExit(1)>.exit_code
FAILED tests/test_cli_next.py::test_next_milestone_with_no_due_date - assert 1 == 0
 +  where 1 = <Result SystemExit(1)>.exit_code
FAILED tests/test_cli_next.py::test_next_with_no_issues_in_milestone - assert 1 == 0
 +  where 1 = <Result SystemExit(1)>.exit_code
FAILED tests/test_cli_next.py::test_next_without_repo_flag_uses_git_config - assert 1 == 0
 +  where 1 = <Result SystemExit(1)>.exit_code
FAILED tests/test_cli_next.py::test_next_fails_if_no_repo_provided_or_found - AssertionError: assert 'Could not determine repository from git config. Please use --repo.' in 'GitHub PAT not found in environment or .env file.
Please enter your GitHub Personal Access Token (PAT): 

Aborted!
'
 +  where 'GitHub PAT not found in environment or .env file.
Please enter your GitHub Personal Access Token (PAT): 

Aborted!
' = <Result SystemExit(1)>.output
=================== 6 failed, 29 passed, 1 warning in 1.94s ====================
```

<!-- COVERAGE_END -->

## GitHub Action Usage
```
name: Sync Roadmap to Issues
on: workflow_dispatch
jobs:
  scaffold:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Gitscaffold CLI
        uses: your-org/gitscaffold-action@vX.Y.Z
        with:
          roadmap-file: docs/example_roadmap.md
          repo: ${{ github.repository }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          dry-run: 'true'
```
