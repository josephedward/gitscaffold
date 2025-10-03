<!-- Gitscaffold README -->
# Gitscaffold – Generate GitHub Issues from Markdown Roadmaps
  
<!-- CI Badge -->
[![CI](https://github.com/josephedward/gitscaffold/actions/workflows/test-and-update-coverage.yml/badge.svg)](https://github.com/josephedward/gitscaffold/actions)

<!-- COVERAGE_START -->

```text
Coverage report will be inserted by CI.
```

<!-- COVERAGE_END -->

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
*   **High-Performance Parsing**: Optional Rust-based parser (`mdparser`) for significantly faster Markdown processing, with a graceful fallback to the native Python parser.
*   **Flexible Authentication**: Supports GitHub tokens and OpenAI keys via environment variables, `.env` files, or command-line options.

## Installation
```sh
pip install gitscaffold
```

### GitHub CLI (gh)
- The Docker image used by the GitHub Action bundles the GitHub CLI (`gh`). Workflows have `gh` available out of the box.
- For local installs via `pip`, `gh` is not installed automatically. You have two options:
  - Install via your OS package manager (e.g., `brew install gh`, `apt install gh`).
  - Or bootstrap locally with: `gitscaffold gh install` (downloads to `~/.gitscaffold/bin/gh`).

Basic gh helpers in gitscaffold:
- `gitscaffold gh which` — shows which `gh` will be used.
- `gitscaffold gh version` — prints the `gh` version.
- `gitscaffold gh issue-list --repo owner/name [--state open|closed|all]` — lists issues.
- `gitscaffold gh issue-create --repo owner/name --title "..." [--body "..."] [--label L]... [--assignee U]... [--milestone M]` — creates an issue.
- `gitscaffold gh issue-close --repo owner/name NUMBER` — closes an issue.

Global preference:
- Add `--use-gh-cli` to prefer using `gh` where supported (more commands will honor this flag over time). For now, core features remain powered by the PyGithub backend, and the gh subcommands are available for direct use.

### Built-in Script Primitives
These maintenance scripts are part of gitscaffold and can be installed locally:

- Install to a bin dir: `gitscaffold scripts install` (defaults to `~/.gitscaffold/bin`)
- List bundled scripts: `gitscaffold scripts list`

Included scripts:
- `aggregate_repos.sh` — aggregate external repos as branches in current repo.
- `archive_stale_repos.sh` — archive repos not updated since a given year.
- `delete_repos.sh` — delete, archive, or unarchive repos in bulk.
- `remove_from_git.sh` — remove a path from Git history and force-push main.
- `delete_branches.sh` — delete oldest remote branches, with keep lists and dry-run.

After install, add the directory to PATH, e.g. `export PATH="$HOME/.gitscaffold/bin:$PATH"`.

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

    Create a file named `docs/ROADMAP.md` and add your project structure. You can start with a simple structured format like this:

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
    gitscaffold sync docs/ROADMAP.md --repo your-github-name/your-repo
    ```

    That's it! Your repository is now populated based on your roadmap.

## Example: Running Gitscaffold on Itself

You can run `gitscaffold` on its own repository to see it in action. The `diff` command is a great way to compare the `docs/ROADMAP.md` file with the current state of GitHub issues.

This is a process often called "dogfooding"—using your own product.

1.  **Install from source**:
    Make sure you have installed `gitscaffold` in editable mode from your local clone as described in the ["From the source checkout"](#from-the-source-checkout) section.

2.  **Set your GitHub Token**:
    Ensure you have set your `GITHUB_TOKEN` environment variable.

3.  **Run the `diff` command**:
    ```sh
    # From the root of the gitscaffold repository:
    gitscaffold diff docs/ROADMAP.md --repo josephinedward/gitscaffold
    ```

### Interpreting the Output

The command will analyze the repository and produce a report. If the roadmap and issues are perfectly aligned, you'll see:

```
✅ Roadmap and GitHub issues are perfectly in sync. No differences found.
```

Or, if there are discrepancies, the output will look something like this:

```
⚠️ Found differences between docs/ROADMAP.md and GitHub issues for josephinedward/gitscaffold.

Items in docs/ROADMAP.md but not in GitHub:
- [ ] A new task that was just added to the roadmap

Issues on GitHub but not in docs/ROADMAP.md:
- #99: A bug report filed directly on GitHub
```

This provides a clear overview of the alignment between your plan and the work being tracked in GitHub.

## CLI Usage


Use `sync` to create and update GitHub issues from a structured roadmap file. It compares the roadmap with the repository and creates any missing milestones or issues.

```sh
# Sync with a structured roadmap file (e.g., docs/ROADMAP.md containing JSON)
gitscaffold sync docs/ROADMAP.md --repo owner/repo

# To enrich descriptions of new issues with AI during sync
gitscaffold sync docs/ROADMAP.md --repo owner/repo --ai-enrich

# Simulate the sync operation without making changes
gitscaffold sync docs/ROADMAP.md --repo owner/repo --dry-run
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
Only if there are no open issues will it fall back to your local roadmap tasks (from `docs/ROADMAP.md` by default).

```sh
# List open issues for the next milestone:
gitscaffold next --repo owner/repo --token $GITHUB_TOKEN

# If no milestones, pick a random open issue:
gitscaffold next --repo owner/repo --token $GITHUB_TOKEN

# If no open issues at all, fall back to local roadmap tasks:
gitscaffold next --repo owner/repo --token $GITHUB_TOKEN --roadmap-file docs/ROADMAP.md
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
gitscaffold diff docs/ROADMAP.md --repo owner/repo

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
gitscaffold sync docs/ROADMAP.md --repo owner/repo
gitscaffold import-md markdown_roadmap.md --repo owner/repo
gitscaffold delete-closed --repo owner/repo
gitscaffold enrich batch --repo owner/repo --path docs/ROADMAP.md --apply
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

## Gemini Integration Feature

The Gemini integration allows `gitscaffold` to leverage Google's Gemini models for automated tasks such as AI-driven issue generation and enrichment. This feature is enabled through the use of the `--with-gemini-action` flag when running the `gitscaffold` command.

### Setting Up Gemini Integration

1. **Enable Gemini on your project:** Use the `--with-gemini-action` flag when you run `gitscaffold` to include the Gemini GitHub Action and configuration in your project.

2. **Configure your GitHub repository:**
   - You must set the `GEMINI_API_KEY` in your repository's secrets to authenticate with the Gemini API.
   - Ensure that the `GITHUB_TOKEN` is also set with appropriate permissions to interact with GitHub issues and pull requests.

### Example Usage

```sh
gitscaffold setup --with-gemini-action --repo your-github-name/your-new-repo
```

This command will scaffold a new project including the Gemini GitHub Action workflow and configuration file, enabling on-demand AI assistance directly in your GitHub repository's issues and pull requests.
