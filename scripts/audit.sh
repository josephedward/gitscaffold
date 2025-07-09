#!/usr/bin/env bash
#
# Audit script to run cleanup, deduplicate, and diff operations in one go.
#
set -euo pipefail

echo "This script will perform the following actions in sequence:"
echo " 1. cleanup-issue-titles"
echo " 2. deduplicate-issues"
echo " 3. diff"

# Prompt for GitHub repository
read -rp "Enter GitHub repository (owner/repo): " REPO

# Prompt for GitHub token if not set
if [ -z "${GITHUB_TOKEN:-}" ]; then
  read -rsp "Enter GitHub token: " GITHUB_TOKEN
  echo
fi
export GITHUB_TOKEN

# Prompt for roadmap file path
read -rp "Enter path to local roadmap file (YAML/Markdown): " ROADMAP

echo
echo "Running cleanup-issue-titles..."
gitscaffold cleanup-issue-titles \
  --repo "$REPO" \
  --token "$GITHUB_TOKEN"

echo
echo "Running deduplicate-issues..."
gitscaffold deduplicate-issues \
  --repo "$REPO" \
  --token "$GITHUB_TOKEN"

echo
echo "Running diff..."
gitscaffold diff "$ROADMAP" \
  --repo "$REPO" \
  --token "$GITHUB_TOKEN"

echo
echo "Audit complete."