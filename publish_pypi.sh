#!/usr/bin/env bash
set -euo pipefail

# Clean previous builds
echo "Cleaning old distributions..."
rm -rf dist/

echo "Building source and wheel packages..."
python3 -m build --no-isolation

WHEEL=$(ls dist/gitscaffold-*.whl | head -n1)
echo "Verifying that 'scripts/import_md.py' is included in $WHEEL..."
if ! unzip -l "$WHEEL" | grep -q 'scripts/import_md.py'; then
  echo "Error: 'scripts/import_md.py' not found in $WHEEL" >&2
  exit 1
fi

echo "Uploading packages to PyPI..."
# Use TWINE_USERNAME/TWINE_PASSWORD or ~/.pypirc for credentials
twine upload dist/*

echo "Publish complete."