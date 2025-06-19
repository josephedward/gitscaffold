#!/bin/sh
set -e

# Map action inputs to variables (hyphens replaced by underscores)
: "${INPUT_ROADMAP_FILE:=roadmap.yml}"
: "${INPUT_REPO:?repo input is required}"
: "${INPUT_GITHUB_TOKEN:=}"
: "${INPUT_DRY_RUN:=false}"

# Build arguments
args=(create "$INPUT_ROADMAP_FILE" --repo "$INPUT_REPO")
if [ -n "$INPUT_GITHUB_TOKEN" ]; then
  args+=(--token "$INPUT_GITHUB_TOKEN")
fi
if [ "$INPUT_DRY_RUN" = "true" ]; then
  args+=(--dry-run)
fi

exec gitscaffold "${args[@]}"
