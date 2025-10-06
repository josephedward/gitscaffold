# gh-first Guide

Use GitHub CLI (`gh`) as the primary engine for issues/PRs/projects.

## Install & auth
- Install: `brew install gh` (macOS) or see https://cli.github.com
- Login: `gh auth login`
- Verify: `gh auth status`

## Use via gitscaffold
- Issues: `gitscaffold issues list --repo owner/repo`
- PRs: `gitscaffold ci prs list --repo owner/repo`
- Projects: `gitscaffold issues projects list --org your-org`

## Tips
- Prefer `--repo owner/repo`; otherwise we try to detect from git origin.
- If a command errors, run the equivalent `gh ...` to verify auth and permissions.
