#!/usr/bin/env bash
set -euo pipefail

# Archive repos not updated since the start of a given year (default: 2025).
# Uses GitHub CLI `gh` and its built-in jq filter (`--jq`) so no external jq is required.
#
# Usage examples:
#   bash archive_stale_repos.sh -o my-org                  # dry-run, year=2025
#   bash archive_stale_repos.sh -o my-user --apply         # actually archive
#   bash archive_stale_repos.sh -o my-org --year 2024      # repos not touched in 2024 or earlier
#   bash archive_stale_repos.sh -o my-org --include-forks  # include forks
#   bash archive_stale_repos.sh -o my-org --no-private     # exclude private repos
#   bash archive_stale_repos.sh -o my-org --match '^svc-'  # only names matching regex
#   bash archive_stale_repos.sh -o my-org --exclude 'playground'
#   bash archive_stale_repos.sh -o my-org --apply --yes    # no confirmation prompt

YEAR=2025
OWNER=""
INCLUDE_FORKS=false
INCLUDE_PRIVATE=true
APPLY=false
ASSUME_YES=false
LIMIT=1000
MATCH_PATTERN=""
EXCLUDE_PATTERN=""

print_help() {
  cat <<EOF
Archive GitHub repositories not updated since the start of a year.

Required:
  -o, --owner OWNER         GitHub org or user handle (e.g., my-org or my-user)

Optional:
  -y, --year YEAR           Cutoff year; repos with updatedAt < YEAR-01-01 get archived (default: ${YEAR})
      --include-forks       Include forks (default: exclude)
      --no-private          Exclude private repos (default: include)
      --match REGEX         Only include repos where nameWithOwner matches regex
      --exclude REGEX       Exclude repos where nameWithOwner matches regex
      --limit N             Max repos to fetch (default: ${LIMIT})
      --apply               Perform archival (default: dry-run)
      --yes                 Skip confirmation prompt when applying
  -h, --help                Show this help

Examples:
  bash archive_stale_repos.sh -o my-org
  bash archive_stale_repos.sh -o my-user --apply --yes
  bash archive_stale_repos.sh -o my-org --year 2024 --include-forks --no-private
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--owner)
      OWNER="$2"; shift 2 ;;
    -y|--year)
      YEAR="$2"; shift 2 ;;
    --include-forks)
      INCLUDE_FORKS=true; shift ;;
    --no-private)
      INCLUDE_PRIVATE=false; shift ;;
    --match)
      MATCH_PATTERN="$2"; shift 2 ;;
    --exclude)
      EXCLUDE_PATTERN="$2"; shift 2 ;;
    --limit)
      LIMIT="$2"; shift 2 ;;
    --apply)
      APPLY=true; shift ;;
    --yes)
      ASSUME_YES=true; shift ;;
    -h|--help)
      print_help; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      print_help; exit 2 ;;
  esac
done

if [[ -z "${OWNER}" ]]; then
  echo "Error: --owner is required" >&2
  print_help
  exit 2
fi

# Validate gh auth
if ! gh auth status >/dev/null 2>&1; then
  echo "GitHub CLI is not authenticated. Run: gh auth login" >&2
  exit 1
fi

CUTOFF="${YEAR}-01-01T00:00:00Z"

# Build jq filter dynamically (for gh's built-in --jq)
# Start core predicate: not archived and older than cutoff
PREDICATE=".isArchived==false and (.updatedAt < \"${CUTOFF}\")"

# Optionally exclude forks
if [[ "${INCLUDE_FORKS}" != "true" ]]; then
  PREDICATE="${PREDICATE} and (.isFork==false)"
fi

# Optionally exclude private
if [[ "${INCLUDE_PRIVATE}" != "true" ]]; then
  PREDICATE="${PREDICATE} and (.isPrivate==false)"
fi

# Optional name filters
if [[ -n "${MATCH_PATTERN}" ]]; then
  # Use regex test on nameWithOwner
  PREDICATE="${PREDICATE} and (.nameWithOwner | test(\"${MATCH_PATTERN}\"))"
fi
if [[ -n "${EXCLUDE_PATTERN}" ]]; then
  PREDICATE="${PREDICATE} and ((.nameWithOwner | test(\"${EXCLUDE_PATTERN}\")) | not)"
fi

# Full jq filter maps to list of names
JQ_FILTER="map(select(${PREDICATE})) | .[].nameWithOwner"

echo "Finding repos for owner '${OWNER}' not updated since ${CUTOFF}..." >&2

# Fetch and filter using gh's built-in --jq (no external jq dependency)
# Avoid 'mapfile' for macOS's older Bash (3.x) compatibility.
REPOS=()
while IFS= read -r _line; do
  # Skip empties
  [[ -z "$_line" ]] && continue
  # Strip surrounding quotes if jq emitted them
  _line="${_line%\"}"
  _line="${_line#\"}"
  REPOS+=("$_line")
done < <(gh repo list "${OWNER}" \
  --limit "${LIMIT}" \
  --json nameWithOwner,updatedAt,isArchived,isFork,isPrivate \
  --jq "${JQ_FILTER}" 2>/dev/null)

COUNT=${#REPOS[@]}

if (( COUNT == 0 )); then
  echo "No repositories match the criteria. Nothing to do." >&2
  exit 0
fi

echo "Matched ${COUNT} repositories:" >&2
printf '  %s\n' "${REPOS[@]}" >&2

if [[ "${APPLY}" != "true" ]]; then
  echo "Dry-run: not archiving. Re-run with --apply to archive." >&2
  exit 0
fi

if [[ "${ASSUME_YES}" != "true" ]]; then
  read -r -p "Archive these ${COUNT} repositories now? [y/N] " ans
  case "${ans}" in
    y|Y|yes|YES) ;; # continue
    *) echo "Aborted."; exit 1 ;;
  esac
fi

echo "Archiving ${COUNT} repositories..." >&2
errors=0
for repo in "${REPOS[@]}"; do
  # First try the gh subcommand; capture stderr for diagnostics
  if out=$(gh repo archive "${repo}" 2>&1); then
    echo "Archived: ${repo}"
  else
    # Fallback to REST API via gh api
    owner_part="${repo%%/*}"
    name_part="${repo#*/}"
    if api_out=$(gh api -X PATCH \
      "repos/${owner_part}/${name_part}" \
      -f archived=true 2>&1); then
      echo "Archived: ${repo} (via API)"
    else
      echo "Failed:   ${repo}" >&2
      # Show the last error line for context
      if [[ -n "$out" ]]; then
        echo "  gh repo archive error: $out" >&2
      fi
      if [[ -n "$api_out" ]]; then
        echo "  gh api PATCH error: $api_out" >&2
      fi
      errors=$((errors+1))
    fi
  fi
  # gentle throttle
  sleep 0.2
done

if (( errors > 0 )); then
  echo "Completed with ${errors} failures." >&2
  exit 1
fi

echo "All done. Archived ${COUNT} repositories." >&2

