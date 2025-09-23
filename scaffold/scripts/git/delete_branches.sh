#!/usr/bin/env bash
set -euo pipefail

# Delete the N oldest remote branches (by author date), skipping the default branch.
#
# Usage:
#   delete_branches.sh [-n COUNT] [-r REMOTE] [--dry-run] [--keep BRANCH ...]
#
# Options:
#   -n COUNT       Number of oldest branches to delete (default: 20)
#   -r REMOTE      Git remote name (default: origin)
#   --dry-run      Show what would be deleted without pushing deletions
#   --keep BRANCH  Branch to keep (can be repeated). These are branch names
#                  without the remote prefix. Default branch is always kept.
#
# Examples:
#   delete_branches.sh                 # delete 20 oldest branches on origin
#   delete_branches.sh -n 10 --dry-run # preview 10 oldest
#   delete_branches.sh -r upstream --keep develop --keep release

count=20
remote="origin"
dry_run=false
keep_branches=()

while (( "$#" )); do
  case "$1" in
    -n)
      shift
      count="${1:-}"
      [[ -n "$count" && "$count" =~ ^[0-9]+$ ]] || { echo "ERROR: -n requires a numeric COUNT" >&2; exit 1; }
      ;;
    -r)
      shift
      remote="${1:-}"
      [[ -n "$remote" ]] || { echo "ERROR: -r requires REMOTE name" >&2; exit 1; }
      ;;
    --dry-run)
      dry_run=true
      ;;
    --keep)
      shift
      k="${1:-}"
      [[ -n "$k" ]] || { echo "ERROR: --keep requires a branch name" >&2; exit 1; }
      keep_branches+=("$k")
      ;;
    -h|--help)
      sed -n '1,60p' "$0" | sed -n '1,40p'
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
  shift || true
done

# Ensure we're in a git repository
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: Not inside a git repository" >&2
  exit 1
fi

# Fetch and prune to ensure we have current remote refs
if ! git fetch --prune "$remote"; then
  echo "ERROR: Failed to fetch from remote '$remote'" >&2
  exit 1
fi

# Discover default branch from remote HEAD
default_ref=$(git symbolic-ref -q --short "refs/remotes/${remote}/HEAD" || true)
if [[ -z "$default_ref" ]]; then
  # fallback via remote show
  default_branch=$(git remote show "$remote" 2>/dev/null | sed -n 's/.*HEAD branch: //p')
else
  default_branch="${default_ref#${remote}/}"
fi

if [[ -z "${default_branch:-}" ]]; then
  # fallback to main if unknown
  default_branch="main"
fi

# Build the list of remote branches sorted by author date (oldest first)
mapfile -t all_remote_branches < <(git for-each-ref --sort=authordate --format='%(refname:short)' "refs/remotes/${remote}")

# Filter out HEAD pointer and default branch; apply keep list
filtered=()
for rb in "${all_remote_branches[@]}"; do
  [[ "$rb" == "${remote}/HEAD" ]] && continue
  [[ "$rb" == "${remote}/${default_branch}" ]] && continue
  skip=false
  for kb in "${keep_branches[@]}"; do
    if [[ "$rb" == "${remote}/${kb}" ]]; then
      skip=true
      break
    fi
  done
  $skip && continue
  filtered+=("$rb")
done

# Select oldest N and strip remote prefix
selection=()
for rb in "${filtered[@]:0:$count}"; do
  selection+=("${rb#${remote}/}")
done

if [[ ${#selection[@]} -eq 0 ]]; then
  echo "No branches to delete (after filtering)." >&2
  exit 0
fi

printf "Remote: %s\n" "$remote"
printf "Default branch: %s\n" "$default_branch"
printf "Count requested: %d\n" "$count"
printf "Branches to delete (%d):\n" "${#selection[@]}"
printf '  - %s\n' "${selection[@]}"

if $dry_run; then
  echo "Dry-run: no changes pushed."
  exit 0
fi

# Confirm if running in interactive terminal
if [[ -t 0 ]]; then
  read -r -p "Proceed with deletion? [y/N] " ans
  case "$ans" in
    y|Y|yes|YES) ;;
    *) echo "Aborted."; exit 1;;
  esac
fi

# Push deletions
for b in "${selection[@]}"; do
  echo "Deleting $b on $remote ..."
  git push "$remote" --delete "$b"
done

echo "Done."

