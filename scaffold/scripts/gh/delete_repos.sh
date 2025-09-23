#!/usr/bin/env bash
set -euo pipefail

# Delete or archive GitHub repositories via gh.
#
# Usage:
#   scripts/delete_repos.sh [options] <repo> [<repo> ...]
#
# <repo> may be any of:
#   - Full URL: https://github.com/owner/name(.git)
#   - SSH URL:  git@github.com:owner/name(.git)
#   - Owner/name slug: owner/name
#
# Options:
#   -y, --yes               Proceed without interactive confirmation (dangerous)
#       --archive           Archive the repositories instead of deleting
#       --unarchive         Unarchive the repositories
#       --dry-run           Show actions without making changes
#   -h, --help              Show help
#
# Notes:
# - Requires gh (GitHub CLI) and authenticated user with proper permissions.

YES=false
ARCHIVE=false
UNARCHIVE=false
DRY_RUN=false

die() { echo "Error: $*" >&2; exit 1; }

usage() { grep '^#' "$0" | sed 's/^# \{0,1\}//'; }

require_cmd() { command -v "$1" >/dev/null 2>&1 || die "Missing required command: $1"; }

extract_owner_repo() {
  local in="$1" owner repo
  if [[ "$in" =~ ^https?://github.com/([^/]+)/([^/.]+)(\.git)?/?$ ]]; then
    owner="${BASH_REMATCH[1]}"; repo="${BASH_REMATCH[2]}"; printf '%s/%s' "$owner" "$repo"; return 0
  fi
  if [[ "$in" =~ ^git@github.com:([^/]+)/([^/.]+)(\.git)?$ ]]; then
    owner="${BASH_REMATCH[1]}"; repo="${BASH_REMATCH[2]}"; printf '%s/%s' "$owner" "$repo"; return 0
  fi
  if [[ "$in" =~ ^[^/[:space:]]+/[^/[:space:]]+$ ]]; then
    printf '%s' "$in"; return 0
  fi
  return 1
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -y|--yes) YES=true; shift ;;
      --archive) ARCHIVE=true; shift ;;
      --unarchive) UNARCHIVE=true; shift ;;
      --dry-run) DRY_RUN=true; shift ;;
      -h|--help) usage; exit 0 ;;
      --) shift; break ;;
      -*) die "Unknown option: $1" ;;
      *) break ;;
    esac
  done
  if [[ "$ARCHIVE" == true && "$UNARCHIVE" == true ]]; then
    die "--archive and --unarchive are mutually exclusive"
  fi
  REPOS=("$@")
  [[ ${#REPOS[@]} -gt 0 ]] || die "Provide at least one repository (URL or owner/name)"
}

ensure_gh_auth() {
  if ! gh auth status >/dev/null 2>&1; then
    echo "gh not authenticated. Launching web login..." >&2
    if [[ "$DRY_RUN" == true ]]; then
      echo "[dry-run] gh auth login -w"
    else
      gh auth login -w || die "GitHub auth failed"
    fi
  fi
}

do_delete_repo() {
  local slug="$1"
  if [[ "$DRY_RUN" == true ]]; then
    if [[ "$YES" == true ]]; then
      echo "[dry-run] gh repo delete $slug --yes"
    else
      echo "Planned delete: $slug (run with --yes to execute)"
    fi
  else
    if [[ "$YES" == true ]]; then
      gh repo delete "$slug" --yes
    else
      gh repo delete "$slug"
    fi
  fi
}

do_archive_repo() {
  local slug="$1" flag="$2"  # true/false
  local state msg
  if [[ "$flag" == true ]]; then state=true; msg="Archiving"; else state=false; msg="Unarchiving"; fi
  if [[ "$DRY_RUN" == true ]]; then
    echo "[dry-run] gh api -X PATCH /repos/$slug -f archived=$state  # $msg"
  else
    gh api -X PATCH "/repos/$slug" -f archived="$state"
  fi
}

main() {
  require_cmd gh
  ensure_gh_auth

  for input in "${REPOS[@]}"; do
    local slug
    if ! slug="$(extract_owner_repo "$input")"; then
      die "Unrecognized repo format: $input"
    fi

    if [[ "$ARCHIVE" == true ]]; then
      echo "Archiving $slug ..."
      do_archive_repo "$slug" true
    elif [[ "$UNARCHIVE" == true ]]; then
      echo "Unarchiving $slug ..."
      do_archive_repo "$slug" false
    else
      echo "Deleting $slug ..."
      do_delete_repo "$slug"
    fi
  done
  echo "Done."
}

parse_args "$@"
main

