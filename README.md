<!-- Gitscaffold README -->
# Gitscaffold – Generate GitHub Issues from Markdown Roadmaps
  
<!-- Badges -->
[![CI](https://github.com/josephedward/gitscaffold/actions/workflows/test-and-update-coverage.yml/badge.svg)](https://github.com/josephedward/gitscaffold/actions)
[![Coverage Status](https://img.shields.io/codecov/c/gh/josephedward/gitscaffold/main.svg?logo=codecov)](https://codecov.io/gh/josephedward/gitscaffold)
[![Documentation Status](https://readthedocs.org/projects/gitscaffold/badge/?version=latest)](https://gitscaffold.readthedocs.io)

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
