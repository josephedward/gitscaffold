#!/bin/bash
#
# This script demonstrates using gitscaffold on its own repository.
# It runs a "sync" to create missing issues from the local ROADMAP.md on GitHub.

set -e # Exit immediately if a command exits with a non-zero status.

echo "--- Dogfooding gitscaffold ---"

# Ensure GITHUB_TOKEN is set from .env or environment
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | xargs)
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is not set, and could not be found in .env"
    echo "Please set it to your GitHub Personal Access Token."
    exit 1
fi

echo "Step 1: Installing gitscaffold..."
# Install the package in editable mode to make the CLI available
pip install -e .

echo ""
echo "Step 2: Running sync against josephedward/gitscaffold..."
# Run the sync command to create missing issues. The --yes flag auto-confirms.
gitscaffold sync ROADMAP.md --repo josephedward/gitscaffold --token "$GITHUB_TOKEN" --yes

echo ""
echo "--- Demonstration complete ---"
