# Release Notes

## v0.1.16 (2025-07-30)
- **Fix**: Corrected the OpenAI API client initialization in the `enrich` command, which was using a deprecated calling convention and would fail.
- **Docs**: Added a troubleshooting section to `usage.md` for the `command not found` error.

## v0.1.15 (2025-07-30)
- **Fix**: Corrected package configuration in `pyproject.toml` to ensure the `gitscaffold` command-line script is created upon installation.
- **Fix**: Added retry logic for OpenAI API calls in `sync` and `diff` commands. If an invalid API key is detected, the user is prompted to enter a new one, which is then saved to `.env` for immediate use.

## v0.1.14 (2025-07-30)
- **Feature**: Default AI-first extraction for unstructured Markdown in `sync` and `diff` commands; use `--no-ai` to disable or `--ai` to force.
- **CLI**: Help texts updated to prominently mention `OPENAI_API_KEY` requirement and AI-first behavior.
- **Fix**: Removed duplicate missing-token/key messages and streamlined prompting flow without requiring a rerun.
- **Docs**: Trimmed duplicate blocks in `usage.md`, polished wording across README and usage guide.
- **Version**: Bumped package version to `0.1.14`.

## v0.1.11 (2025-07-18)
- **Feature**: Add `import-md` as a top-level command for AI-driven issue creation from unstructured markdown files.
- **Fix**: Resolve issue with duplicate `import-md` command definitions in the CLI, which caused argument parsing errors.
- **Fix**: Corrected package configuration in `pyproject.toml` to ensure the `gitscaffold` command-line script is created upon installation.
- **Fix**: Added retry logic for OpenAI API calls in `sync` and `diff` commands. If an invalid API key is detected, the user is prompted to enter a new one, which is then saved to `.env` for immediate use.

## v0.1.14 (2025-07-30)
- **Feature**: Default AI-first extraction for unstructured Markdown in `sync` and `diff` commands; use `--no-ai` to disable or `--ai` to force.
- **CLI**: Help texts updated to prominently mention `OPENAI_API_KEY` requirement and AI-first behavior.
- **Fix**: Removed duplicate missing-token/key messages and streamlined prompting flow without requiring a rerun.
- **Docs**: Trimmed duplicate blocks in `usage.md`, polished wording across README and usage guide.
- **Version**: Bumped package version to `0.1.14`.

## Releasing

### Publishing to PyPI
1. Bump version in `scaffold/__init__.py`.
2. Update release notes in `docs/release.md`.
3. Commit and tag:
   ```sh
   git add scaffold/__init__.py docs/release.md
   git commit -m "release: vX.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```
3. Build and upload:
   ```sh
   pip install --upgrade build twine
   rm -rf dist/
   python -m build
   twine upload dist/*
   ```

### Automating Releases with GitHub Actions
Add `.github/workflows/release.md`:
```
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
