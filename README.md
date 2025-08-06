<!-- Gitscaffold README -->
# Gitscaffold – Generate GitHub Issues from Markdown Roadmaps
  
<!-- CI Badge -->
[![CI](https://github.com/josephedward/gitscaffold/actions/workflows/test-and-update-coverage.yml/badge.svg)](https://github.com/josephedward/gitscaffold/actions)

Gitscaffold is a command-line tool and GitHub Action that converts Markdown-based roadmaps into GitHub issues and milestones using AI-driven extraction and enrichment.

## Key Features

*   **AI-Powered Issue Extraction**: Convert free-form Markdown documents into structured GitHub issues using OpenAI.
*   **Roadmap Synchronization (`sync`)**: Compare your Markdown roadmap with an existing GitHub repository and interactively create missing issues to keep them aligned.
*   **Bulk Delete Closed Issues (`delete-closed`)**: Clean up your repository by permanently removing all closed issues, with dry-run and confirmation steps.
*   **Cleanup Issue Titles (`sanitize`)**: Strip leading Markdown header characters from existing GitHub issue titles, with preview and confirmation.
*   **Deduplicate Issues (`deduplicate`)**: Find and close duplicate open issues based on their title.
*   **AI Enrichment**: Enhance issue descriptions with AI-generated content for clarity and context.
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

## Getting Started: A Basic Workflow

Here's how to use `gitscaffold` to populate a new repository with issues from a roadmap:

1.  **Create a Roadmap File**

    Create a file named `ROADMAP.md` and add your project structure. You can start with a simple structured format like this:

    ```json
    {
        "name": "My New Project",
        "milestones": [
            {
                "name": "v1.0: Launch",
                "due_date": "2025-12-31"
            }
        ],
        "features": [
            {
                "title": "Setup initial project structure",
                "milestone": "v1.0: Launch",
                "labels": ["setup", "chore"]
            },
            {
                "title": "Implement user authentication",
                "milestone": "v1.0: Launch",
                "labels": ["feature", "auth"],
                "tasks": [
                    { "title": "Add login page" },
                    { "title": "Add registration page" }
                ]
            }
        ]
    }
    ```

2.  **Sync with GitHub**

    Run the `sync` command to create the milestones and issues in your repository. `gitscaffold` will show you a plan and ask for confirmation before making any changes.

    ```sh
    # Make sure you have set GITHUB_TOKEN
    gitscaffold sync ROADMAP.md --repo your-github-name/your-repo
    ```

    That's it! Your repository is now populated based on your roadmap.

## CLI Usage


Use `sync` to create and update GitHub issues from a structured roadmap file. It compares the roadmap with the repository and creates any missing milestones or issues.

```sh
# Sync with a structured roadmap file (e.g., ROADMAP.md containing JSON)
gitscaffold sync ROADMAP.md --repo owner/repo

# To enrich descriptions of new issues with AI during sync
gitscaffold sync ROADMAP.md --repo owner/repo --ai-enrich

# Simulate the sync operation without making changes
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

Use `next` to view open issues from the earliest active milestone in your repository.
If there are no active milestones but open issues exist on GitHub, `next` will pick one at random.
Only if there are no open issues will it fall back to your local roadmap tasks (from `ROADMAP.md` by default).

```sh
# List open issues for the next milestone:
gitscaffold next --repo owner/repo --token $GITHUB_TOKEN

# If no milestones, pick a random open issue:
gitscaffold next --repo owner/repo --token $GITHUB_TOKEN

# If no open issues at all, fall back to local roadmap tasks:
gitscaffold next --repo owner/repo --token $GITHUB_TOKEN --roadmap-file ROADMAP.md
```

### Show Next Task for Current Phase

Use `next-task` to pick your next open task for the current roadmap phase. By default, the oldest task is shown; use `--pick` to choose randomly and `--browse` to open it in your browser.

```sh
gitscaffold next-task ROADMAP_FILE --repo owner/repo --token $GITHUB_TOKEN [--pick] [--browse]
```

### Diff Roadmap and GitHub Issues

Use `diff` to compare a local roadmap file against GitHub issues. It lists items present in your roadmap but missing on GitHub, and issues on GitHub not in your roadmap.

For unstructured Markdown roadmaps, AI extraction is prompted by default; disable with the `--no-ai` flag.

```sh
# Compare a structured roadmap file
gitscaffold diff ROADMAP.md --repo owner/repo

# Compare an unstructured roadmap file using AI
gitscaffold diff docs/brainstorm.md --repo owner/repo --ai
```

### From the source checkout
Clone this repository, install it in editable mode, and use the `gitscaffold` CLI:

```bash
# Clone and install
git clone https://github.com/josephedward/gitscaffold.git
cd gitscaffold
pip install -e .

# Now any command is available via `gitscaffold`:
gitscaffold setup
gitscaffold sync ROADMAP.md --repo owner/repo
gitscaffold import-md markdown_roadmap.md --repo owner/repo
gitscaffold delete-closed --repo owner/repo
gitscaffold enrich batch --repo owner/repo --path ROADMAP.md --apply
```

### Audit Repository (cleanup, deduplicate, diff)

Use the provided `scripts/audit.sh` to run cleanup, deduplicate, and diff in one go. It will prompt for your GitHub repo, token, and local roadmap file.

```sh
bash scripts/audit.sh
```


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
