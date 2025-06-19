# Release Guide

## 1. Releasing to PyPI

1. Create a PyPI API token scoped to this project.
2. Add `PYPI_API_TOKEN` to your GitHub repo secrets.
3. Bump the `version` in `pyproject.toml`, commit, and tag:

   ```
   git add pyproject.toml
   git commit -m "chore(release): vX.Y.Z"
   git tag vX.Y.Z
   git push origin main --tags
   ```

4. Build and upload:

   ```
   pip install --upgrade build twine
   python -m build
   python -m twine upload dist/* \
     --username __token__ \
     --password "$PYPI_API_TOKEN"
   ```

5. Draft a GitHub Release for `vX.Y.Z`.

## 2. Publishing the GitHub Action

1. Ensure `action.yml`, `Dockerfile`, and `entrypoint.sh` are committed.
2. Tag the same version (`vX.Y.Z`) and push.
3. On GitHub → Marketplace tab → “Publish this action” → select `vX.Y.Z`.

## 3. Automating with GitHub Actions

Add the following file to `.github/workflows/release.yml` to publish on every new tag.
