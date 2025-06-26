<!-- Gitscaffold README -->
# Gitscaffold – Generate GitHub Issues from Markdown & YAML Roadmaps

Gitscaffold is a command-line tool and GitHub Action that primarily converts unstructured Markdown documents into GitHub issues and milestones using AI-driven extraction and enrichment. It also supports structured roadmap files (YAML/JSON) when you need strict schemas and milestones.

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
When you have a free-form Markdown document instead of a structured YAML roadmap, use `import-md` to extract and enrich issues.

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

# Create enriched issues on GitHub
gitscaffold import-md owner/repo markdown_roadmap.md \
  --heading-level 1 --token $GITHUB_TOKEN
```

### Generate issues from structured YAML/JSON roadmap
Use `create` for structured YAML or JSON roadmaps:

```sh
# Create GitHub issues from a structured roadmap file
gitscaffold create ROADMAP.yml \
  --repo owner/repo \
  --token $GITHUB_TOKEN

# Validate without creating issues (dry run)
gitscaffold create ROADMAP.yml \
  --repo owner/repo \
  --token $GITHUB_TOKEN \
  --dry-run
```

### Delete closed issues
Use `delete-closed` to permanently remove all closed issues from a specified repository. This action is irreversible and requires confirmation.

```sh
# List closed issues that would be deleted (dry run)
gitscaffold delete-closed --repo owner/repo --token $GITHUB_TOKEN --dry-run

# Delete all closed issues (will prompt for confirmation)
gitscaffold delete-closed --repo owner/repo --token $GITHUB_TOKEN
```

### Initialize a roadmap template
```sh
gitscaffold init example-roadmap.yml
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

## Initialize a new roadmap YAML template
./gitscaffold.py init ROADMAP.yml
```

## GitHub Action Usage
```yaml
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
          roadmap-file: roadmap.yml
          repo: ${{ github.repository }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          dry-run: 'true'
```
