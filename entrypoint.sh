#!/bin/sh
set -e

# Map action inputs to variables (hyphens replaced by underscores)
: "${INPUT_ROADMAP_FILE:=roadmap.yml}"
: "${INPUT_REPO:?repo input is required}"
: "${INPUT_GITHUB_TOKEN:=}"
: "${INPUT_DRY_RUN:=false}"
: "${INPUT_OPENAI_KEY:=}"
: "${INPUT_APPLY:=false}"

# Determine subcommand based on file extension
ext="${INPUT_ROADMAP_FILE##*.}"
case "$ext" in
  md|markdown)
    cmd="import-md"
    args=("$cmd" "$INPUT_REPO" "$INPUT_ROADMAP_FILE")
    ;;
  *)
    cmd="create"
    args=("$cmd" "$INPUT_ROADMAP_FILE" --repo "$INPUT_REPO")
    ;;
esac

# Export OpenAI key if provided
if [ -n "$INPUT_OPENAI_KEY" ]; then
  export OPENAI_API_KEY="$INPUT_OPENAI_KEY"
fi

# Append flags
if [ "$INPUT_DRY_RUN" = "true" ]; then
  args+=(--dry-run)
fi
if [ "$cmd" = "import-md" ] && [ "$INPUT_APPLY" = "true" ]; then
  args+=(--apply)
fi
if [ -n "$INPUT_GITHUB_TOKEN" ]; then
  args+=(--token "$INPUT_GITHUB_TOKEN")
fi

exec gitscaffold "${args[@]}"
