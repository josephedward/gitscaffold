<!-- Gitscaffold README -->
# Gitscaffold – Generate GitHub Issues from Markdown & YAML Roadmaps

Gitscaffold is a command-line tool and GitHub Action that primarily converts unstructured Markdown documents into GitHub issues and milestones using AI-driven extraction and enrichment. It also supports structured roadmap files (YAML/JSON) when you need strict schemas and milestones.

## Installation
```sh
pip install gitscaffold
```

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
  --heading 1 --dry-run --token $GITHUB_TOKEN

# Create enriched issues on GitHub
gitscaffold import-md owner/repo markdown_roadmap.md \
  --heading 1 --token $GITHUB_TOKEN
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
./gitscaffold.py import-md owner/repo markdown_roadmap.md --heading 2 --token $GITHUB_TOKEN

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

## Releasing

### Publishing to PyPI
1. Bump version in `pyproject.toml` under `[project]`.
2. Commit and tag:
   ```sh
   git add pyproject.toml
   git commit -m "release: vX.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```
3. Build and upload:
   ```sh
   pip install --upgrade build twine
   python -m build
   twine upload dist/*
   ```

### Automating Releases with GitHub Actions
Add `.github/workflows/release.yml`:
```yaml
name: Publish
on:
  push:
    tags:
      - 'v*.*.*'
jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.x'
      - run: pip install --upgrade build twine
      - run: python -m build
      - uses: pypa/gh-action-pypi-publish@v1.5.1
        with:
          password: ${{ secrets.PYPI_API_TOKEN }}
```