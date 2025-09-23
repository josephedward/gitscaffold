#!/usr/bin/env bash
set -euo pipefail

# Remove a file or path from Git history and force-push main.
# Usage: remove_from_git.sh <path>

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <path>" >&2
  exit 2
fi

target="$1"

git add . && git commit -m "commit" || true
git filter-branch -f --index-filter "git rm -rf --cached --ignore-unmatch $target" HEAD
git push -f origin main

