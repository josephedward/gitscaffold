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

## Releasing

### Publishing to PyPI

1. Bump the version in `pyproject.toml` under the `[project]` table.
2. Commit and tag the release:

   ```sh
   git add pyproject.toml
   git commit -m "Release vX.Y.Z"
   git tag vX.Y.Z
   ```

3. Build distribution packages:

   ```sh
   pip install --upgrade build twine
   python -m build
   ```

4. Upload to PyPI:

   ```sh
   twine upload dist/*
   ```

5. Push commits and tags:

   ```sh
   git push origin main --tags
   ```

### Automating releases with GitHub Actions

Add a workflow file (e.g., `.github/workflows/release.yml`) to publish on tag push:

```yaml
name: Publish

on:
  push:
    tags:
      - 'v*.*.*'

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.x'
      - run: pip install --upgrade build twine
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@v1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
``` 
Ensure you’ve added a `PYPI_API_TOKEN` secret in your repository settings.