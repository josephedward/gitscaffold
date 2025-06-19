# Gitscaffold – Roadmaps and Markdown to GitHub Issues

Gitscaffold is a command-line tool and GitHub Action that converts structured roadmap files (YAML/JSON) and free-form Markdown documents into GitHub issues and milestones using AI-driven extraction and enrichment.

Installation:
```sh
pip install gitscaffold
```

## CLI Usage

### As an installed package

After installing, the `gitscaffold` command is available:

```sh
# Create GitHub issues from a structured roadmap file
gitscaffold create ROADMAP.yml --repo owner/repo --token $GITHUB_TOKEN

# Validate without creating issues (dry run)
gitscaffold create ROADMAP.yml --repo owner/repo --token $GITHUB_TOKEN --dry-run
```

### AI extraction & enrichment from unstructured Markdown

Use AI to extract actionable issues from free-form Markdown and generate detailed descriptions.  Invoke via the `create` command with the `--ai-extract` and `--ai-enrich` flags.

```sh
# Preview extracted and enriched issues without creating (dry run)
OPENAI_API_KEY=<your-openai-key> \
  gitscaffold create ROADMAP.md \
    --repo owner/repo --token $GITHUB_TOKEN \
    --ai-extract --ai-enrich --dry-run

# Create and enrich issues on GitHub
OPENAI_API_KEY=<your-openai-key> \
  gitscaffold create ROADMAP.md \
    --repo owner/repo --token $GITHUB_TOKEN \
    --ai-extract --ai-enrich
```

### Initialize a roadmap template
```sh
# Generate an example Markdown roadmap file
gitscaffold init example-roadmap.md
```

### From the source checkout

You can also clone this repository and use the top-level `gitscaffold.py` script for additional commands:

```sh
# Setup GitHub labels, milestones, and (optionally) a project board
./gitscaffold.py setup owner/repo --phase phase-1 --create-project

# Delete all closed issues in a repository
./gitscaffold.py delete-closed owner/repo
# Use GraphQL API for deletion
./gitscaffold.py delete-closed owner/repo --api

```
```sh
# Enrich a single issue or batch enrich via LLM
./gitscaffold.py enrich owner/repo --issue 123 --path ROADMAP.md --apply
./gitscaffold.py enrich owner/repo --batch --path ROADMAP.md --csv output.csv --interactive

```
```sh
# Initialize a new roadmap YAML template
./gitscaffold.py init ROADMAP.yml
```


For detailed documentation and examples, see the project repository or run:
```sh
gitscaffold --help
``` 

## GitHub Action Usage

Use Gitscaffold as a GitHub Action in your workflow (e.g., .github/workflows/sync-roadmap.yml):
```yaml
name: Sync Roadmap to Issues
on:
  workflow_dispatch:
jobs:
  scaffold:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run Scaffold
        uses: your-org/gitscaffold-action@v0.1.0
        with:
          roadmap-file: roadmap.yml
          repo: ${{ github.repository }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          dry-run: 'false'
```

See docs/integration_test.md for a quick sandbox recipe for CLI and GitHub Action integration tests.

