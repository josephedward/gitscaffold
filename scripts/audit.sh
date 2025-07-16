#!/usr/bin/env bash
# Gitscaffold Audit: sanitize, deduplicate, and diff in one go
set -euo pipefail

echo "=== Gitscaffold Audit ==="
echo "Steps: 1) Sanitize titles, 2) Deduplication, 3) Diff vs GitHub"
echo

# Get inputs
read -rp "GitHub repo (owner/repo): " REPO
read -rsp "GitHub token: " TOKEN; echo
read -rp "Roadmap Markdown file (.md): " ROADMAP_FILE; echo

# Validate
[[ -z "$REPO" ]] && { echo "Error: repo required." >&2; exit 1; }
[[ -z "$TOKEN" ]] && { echo "Error: token required." >&2; exit 1; }
[[ ! "$ROADMAP_FILE" =~ \.(md|markdown)$ ]] && { echo "Error: Only Markdown (.md) supported." >&2; exit 1; }
[[ ! -f "$ROADMAP_FILE" ]] && { echo "Error: File not found: $ROADMAP_FILE" >&2; exit 1; }

echo
echo "--- Step 1: Sanitize issue titles ---"
gitscaffold sanitize --repo "$REPO" --token "$TOKEN"
echo
echo "--- Step 2: Deduplicate issues ---"
gitscaffold deduplicate --repo "$REPO" --token "$TOKEN"
echo
echo "--- Step 3: Diff roadmap vs GitHub ---"
gitscaffold diff "$ROADMAP_FILE" --repo "$REPO" --token "$TOKEN"
echo
echo "=== Audit Complete ==="
