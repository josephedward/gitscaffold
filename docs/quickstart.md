# Quickstart

This guide gets you from zero to value in minutes.

## 1) Install and authenticate
- Install gitscaffold (editable or from PyPI) and `gh` if not present.
- Authenticate gh: `gh auth login`
- Set tokens (or use settings config):
  - `export GITHUB_TOKEN=...`
  - Optional AI: `export OPENAI_API_KEY=...` or `GEMINI_API_KEY=...`

## 2) Configure
- `gitscaffold settings config set GITHUB_TOKEN <token>`
- Verify: `gitscaffold settings config list`

## 3) Roadmap → issues
- Prepare `docs/ROADMAP.md` (or JSON/YAML).
- Diff: `gitscaffold roadmap diff docs/ROADMAP.md --repo owner/repo`
- Sync: `gitscaffold roadmap sync docs/ROADMAP.md --repo owner/repo`

## 4) Work with issues (via gh)
- List: `gitscaffold issues list --repo owner/repo`
- Create: `gitscaffold issues create --repo owner/repo --title "My task"`
- Close: `gitscaffold issues close --repo owner/repo 123`

## 5) PRs & workflows (via gh)
- PRs: `gitscaffold ci prs list --repo owner/repo`
- Workflows (coming soon): `gitscaffold ci workflows list --repo owner/repo`

## 6) Troubleshooting
- Run: `gitscaffold settings doctor` (coming soon)
- See: `docs/troubleshooting.md`
