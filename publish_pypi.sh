#!/usr/bin/env bash
set -euo pipefail

# Clean previous builds
echo "Cleaning old distributions..."
rm -rf dist/

echo "Building source and wheel packages..."
python3 -m build --no-isolation


echo "Uploading packages to PyPI..."
# Use TWINE_USERNAME/TWINE_PASSWORD or ~/.pypirc for credentials
twine upload dist/*

echo "Publish complete."
