#!/bin/bash
set -e
set -o pipefail

# End-to-end workflow test for gitscaffold
# This script follows the workflow outlined in usage.md.
#
# Prerequisites:
# 1. The tool must be installed (`pip install -e .`)
# 2. The following environment variables must be set:
#    - GITHUB_TOKEN: A GitHub token with repo permissions.
#    - TEST_REPO: The full name of a test repository (e.g., "your_org/your_test_repo").
#
# Usage:
#   ./scripts/test_workflow.sh

# --- Configuration ---
if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN environment variable is not set."
    exit 1
fi

if [ -z "$TEST_REPO" ]; then
    echo "Error: TEST_REPO environment variable is not set."
    exit 1
fi

DEMO_ROADMAP="demo/example_roadmap.md"
TEMP_ROADMAP="temp_workflow_roadmap.md"
REPO_FLAG="--repo ${TEST_REPO}"

# --- Helper Functions ---
step() {
    echo "--------------------------------------------------"
    echo "STEP: $1"
    echo "--------------------------------------------------"
}

cleanup() {
    echo "Cleaning up temporary files..."
    rm -f "$TEMP_ROADMAP"
}

# --- Main Script ---
trap cleanup EXIT

step "1. Starting with a demo roadmap: ${DEMO_ROADMAP}"
cat "${DEMO_ROADMAP}"
echo ""

step "2. Importing the markdown roadmap into GitHub"
gitscaffold import-md ${REPO_FLAG} "${DEMO_ROADMAP}" --heading-level 2 --yes
echo ""

step "3. Checking what's next"
gitscaffold next ${REPO_FLAG}
echo ""

step "4. Creating a new roadmap file to add more tasks"
cp "${DEMO_ROADMAP}" "${TEMP_ROADMAP}"
cat <<EOF >> "${TEMP_ROADMAP}"

### New Feature

- [ ] A new task to be created
- [ ] Another new task
EOF
echo "New roadmap content:"
cat "${TEMP_ROADMAP}"
echo ""

step "5. Syncing the new roadmap"
# Using --ai because it's a markdown file that needs parsing.
gitscaffold sync "${TEMP_ROADMAP}" ${REPO_FLAG} --ai --yes
echo ""

step "6. Checking the diff"
# The diff should be empty now.
gitscaffold diff "${TEMP_ROADMAP}" ${REPO_FLAG} --ai
echo ""

step "7. Running cleanup commands (dry-run)"
gitscaffold sanitize ${REPO_FLAG} --dry-run
gitscaffold deduplicate ${REPO_FLAG} --dry-run
gitscaffold delete-closed ${REPO_FLAG} --dry-run
echo ""

step "Workflow test completed successfully!"
