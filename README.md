# Gitscaffold – Roadmaps to GitHub Issues

Gitscaffold is a command-line tool and GitHub Action that converts structured roadmap files (YAML/JSON) into GitHub issues and milestones.

Installation:
```sh
pip install gitscaffold
```

## CLI Usage

### As an installed package

After installing, the `gitscaffold` command is available:

```sh
# Create GitHub issues from a roadmap file
gitscaffold create ROADMAP.yml --repo owner/repo --token $GITHUB_TOKEN

# Validate without creating issues (dry run)
gitscaffold create ROADMAP.yml --repo owner/repo --token $GITHUB_TOKEN --dry-run
```

### Initialize a roadmap template
```sh
# Generate an example roadmap file
gitscaffold init example-roadmap.yml
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

# Import issues from an unstructured markdown file
./gitscaffold.py import-md owner/repo path/to/file.md --heading 2 --dry-run
./gitscaffold.py import-md owner/repo path/to/file.md --heading 2
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

