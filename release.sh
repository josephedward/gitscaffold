#!/usr/bin/env bash
set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <new-version>" >&2
  exit 1
fi

VERSION=$1
INIT_FILE="scaffold/__init__.py"

echo "Bumping version to $VERSION in $INIT_FILE..."
if sed --version >/dev/null 2>&1; then
  # GNU sed
  sed -i -E "s|^__version__ = \".*\"|__version__ = \"$VERSION\"|" "$INIT_FILE"
else
  # BSD sed (macOS)
  sed -i '' -E "s|^__version__ = \".*\"|__version__ = \"$VERSION\"|" "$INIT_FILE"
fi

git add "$INIT_FILE"
git commit -m "chore: bump version to $VERSION"
git tag "v$VERSION"
git push origin main --tags

echo "Building distributions..."
# Ensure build and twine are installed; skip installation if already present
if ! python3 -c "import build, twine" &>/dev/null; then
  pip install --upgrade build twine
else
  echo "build and twine already installed, skipping installation"
fi
python3 -m build

echo "Uploading to PyPI..."
twine upload dist/*

echo "Release $VERSION complete!"