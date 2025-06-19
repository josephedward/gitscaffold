# Scaffold – Roadmaps to GitHub Issues

Scaffold is a command-line tool and GitHub Action that converts structured roadmap files (YAML/JSON) into GitHub issues and milestones.

Installation:
```sh
pip install scaffold-roadmap
```

## CLI Usage

### As an installed package

After installing, the `scaffold` command is available:

```sh
# Create GitHub issues from a roadmap file
scaffold create ROADMAP.yml --repo owner/repo --token $GITHUB_TOKEN

# Validate without creating issues (dry run)
scaffold create ROADMAP.yml --repo owner/repo --token $GITHUB_TOKEN --dry-run
```

### Initialize a roadmap template
```sh
# Generate an example roadmap file
scaffold init example-roadmap.yml
```

### From the source checkout

You can also clone this repository and use the top-level `scaffold.py` script for additional commands:

```sh
# Setup GitHub labels, milestones, and (optionally) a project board
./scaffold.py setup owner/repo --phase phase-1 --create-project

# Delete all closed issues in a repository
./scaffold.py delete-closed owner/repo
# Use GraphQL API for deletion
./scaffold.py delete-closed owner/repo --api

# Enrich a single issue or batch enrich via LLM
./scaffold.py enrich owner/repo --issue 123 --path ROADMAP.md --apply
./scaffold.py enrich owner/repo --batch --path ROADMAP.md --csv output.csv --interactive

# Initialize a new roadmap YAML template
./scaffold.py init ROADMAP.yml
```

For detailed documentation and examples, see the project repository or run:
```sh
scaffold --help
``` 

## GitHub Action Usage

Use Scaffold as a GitHub Action in your workflow (e.g., .github/workflows/sync-roadmap.yml):
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
        uses: your-org/scaffold-action@v0.1.0
        with:
          roadmap-file: roadmap.yml
          repo: ${{ github.repository }}
          github-token: ${{ secrets.GITHUB_TOKEN }}
          dry-run: 'false'
```