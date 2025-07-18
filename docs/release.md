# Release Notes

## v0.1.11 (2025-07-18)
- **Feature**: Add `import-md` as a top-level command for AI-driven issue creation from unstructured markdown files.
- **Fix**: Resolve issue with duplicate `import-md` command definitions in the CLI, which caused argument parsing errors.

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
