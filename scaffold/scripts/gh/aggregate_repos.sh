#!/usr/bin/env bash
set -euo pipefail

# Aggregate external GitHub repos as local branches in the current repo.
#
# Requirements:
# - gh (GitHub CLI)
# - git
#
# Default behavior:
# - For each provided repo URL, determine its default branch via `gh`.
# - Fetch that branch directly into a local branch named `${PREFIX}<repo-name>`.
# - If the target branch exists, it will be updated to the latest from the source repo.
#
# Usage:
#   scripts/aggregate_repos.sh [options] <repo-url> [<repo-url> ...]
#
# Options:
#   -p, --prefix <prefix>       Branch name prefix (default: none)
#   -n, --no-overwrite          Do not move existing branches (skip if exists)
#   -d, --depth <n>             Shallow history depth (omit for full history)
#       --dry-run               Show actions without making changes
#   -h, --help                  Show help
#
# Notes:
# - You must be authenticated with `gh auth login -w` (web) or equivalent.
# - Works with https:// and git@github.com: URL forms, with or without .git.

PREFIX=""
NO_OVERWRITE=false
DEPTH=""
DRY_RUN=false

die() { echo "Error: $*" >&2; exit 1; }

usage() {
  grep '^#' "$0" | sed 's/^# \{0,1\}//'
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -p|--prefix)
        PREFIX="${2:-}"; [[ -n "$PREFIX" ]] || die "--prefix requires a value"; shift 2 ;;
      -n|--no-overwrite)
        NO_OVERWRITE=true; shift ;;
      -d|--depth)
        DEPTH="${2:-}"; [[ -n "$DEPTH" ]] || die "--depth requires a value"; shift 2 ;;
      --dry-run)
        DRY_RUN=true; shift ;;
      -h|--help)
        usage; exit 0 ;;
      --)
        shift; break ;;
      -*)
        die "Unknown option: $1" ;;
      *)
        # Start of positional args (repo URLs)
        break ;;
    esac
  done
  REPOS=("$@")
  [[ ${#REPOS[@]} -gt 0 ]] || die "Provide at least one repo URL"
}

# Extract owner and repo from a GitHub URL.
# Supports: https://github.com/owner/repo(.git), git@github.com:owner/repo(.git)
extract_owner_repo() {
  local url="$1" owner repo
  if [[ "$url" =~ ^https?://github.com/([^/]+)/([^/.]+)(\.git)?/?$ ]]; then
    owner="${BASH_REMATCH[1]}"; repo="${BASH_REMATCH[2]}"
  elif [[ "$url" =~ ^git@github.com:([^/]+)/([^/.]+)(\.git)?$ ]]; then
    owner="${BASH_REMATCH[1]}"; repo="${BASH_REMATCH[2]}"
  else
    return 1
  fi
  printf '%s/%s' "$owner" "$repo"
}

default_branch_for() {
  local owner_repo="$1"
  # Prefer gh api for stability and speed
  gh api "/repos/${owner_repo}" --jq .default_branch 2>/dev/null || return 1
}

# Check if a remote has a given branch
remote_has_branch() {
  local url="$1" branch="$2"
  # Query the specific ref and verify exact match; handle spaces or tabs
  if git ls-remote --heads "$url" "refs/heads/${branch}" 2>/dev/null | grep -qE "[[:space:]]refs/heads/${branch}$"; then
    return 0
  fi
  # Some servers also match without the fully qualified input
  if git ls-remote --heads "$url" "$branch" 2>/dev/null | grep -qE "[[:space:]]refs/heads/${branch}$"; then
    return 0
  fi
  return 1
}

# Resolve the branch that remote HEAD points to, e.g., main/master
remote_head_branch() {
  local url="$1"
  # Output example: "ref: refs/heads/main\tHEAD" OR with spaces
  git ls-remote --symref "$url" HEAD 2>/dev/null \
    | awk '/^ref: refs\/heads\// {ref=$2; sub(/^refs\/heads\//, "", ref); print ref; exit}'
}

ensure_in_git_repo() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "Run inside a git repository"
}

branch_exists() {
  git show-ref --verify --quiet "refs/heads/$1"
}

fetch_into_branch() {
  local url="$1" src_ref="$2" dest_branch="$3"
  # Use a force update on the destination branch unless NO_OVERWRITE=true
  local refspec
  if [[ "$NO_OVERWRITE" == true ]]; then
    refspec="refs/heads/${src_ref}:refs/heads/${dest_branch}"
  else
    refspec="+refs/heads/${src_ref}:refs/heads/${dest_branch}"
  fi
  if [[ "$DRY_RUN" == true ]]; then
    if [[ -n "$DEPTH" ]]; then
      echo "[dry-run] git fetch --depth $DEPTH --no-tags --quiet $url $refspec"
    else
      echo "[dry-run] git fetch --no-tags --quiet $url $refspec"
    fi
  else
    if [[ -n "$DEPTH" ]]; then
      git fetch --depth "$DEPTH" --no-tags --quiet "$url" "$refspec"
    else
      git fetch --no-tags --quiet "$url" "$refspec"
    fi
  fi
}

main() {
  require_cmd git
  require_cmd gh
  ensure_in_git_repo

  # Check gh auth; if not authenticated, prompt the user to login via web.
  if ! gh auth status >/dev/null 2>&1; then
    echo "gh not authenticated. Launching web login..." >&2
    if [[ "$DRY_RUN" == true ]]; then
      echo "[dry-run] gh auth login -w"
    else
      gh auth login -w || die "GitHub auth failed"
    fi
  fi

  for url in "${REPOS[@]}"; do
    echo "Processing $url ..."
    local owner_repo
    if ! owner_repo="$(extract_owner_repo "$url")"; then
      die "Unrecognized GitHub URL format: $url"
    fi

    local repo_name
    repo_name="${owner_repo##*/}"
    local target_branch
    target_branch="${PREFIX}${repo_name}"

    local def_branch
    # 1) Ask GitHub API for default branch
    if ! def_branch="$(default_branch_for "$owner_repo")" || [[ -z "$def_branch" ]]; then
      def_branch=""
    fi

    # 2) Validate the branch against the remote; if not present, try fallbacks
    if [[ -z "$def_branch" ]] || ! remote_has_branch "$url" "$def_branch"; then
      local head_branch
      head_branch="$(remote_head_branch "$url" || true)"
      if [[ -n "$head_branch" ]] && remote_has_branch "$url" "$head_branch"; then
        echo "- Note: Using remote HEAD branch '${head_branch}'"
        def_branch="$head_branch"
      else
        # 3) Try common branch names as a last resort
        for candidate in main master trunk; do
          if remote_has_branch "$url" "$candidate"; then
            echo "- Note: Falling back to branch '${candidate}'"
            def_branch="$candidate"
            break
          fi
        done
      fi
    fi

    [[ -n "$def_branch" ]] || die "Failed to resolve a valid default branch for $owner_repo"

    if [[ "$NO_OVERWRITE" == true ]] && branch_exists "$target_branch"; then
      echo "- Skipping existing branch: $target_branch"
      continue
    fi

    echo "- Importing ${owner_repo}@${def_branch} -> ${target_branch}"
    fetch_into_branch "$url" "$def_branch" "$target_branch"
  done

  if [[ -n "$PREFIX" ]]; then
    echo "Done. Created/updated branches with prefix '${PREFIX}'."
  else
    echo "Done. Created/updated branches."
  fi
}

parse_args "$@"
main

