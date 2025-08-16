#!/bin/bash

set -e # Exit immediately if a command exits with a non-zero status.

# A script to run Aider continuously to integrate run-gemini-cli into the gitscaffold project.
#
# USAGE:
# 1. Place this script in your 'gitscaffold' project directory.
# 2. Make sure your 'aider' project directory is a sibling to your 'gitscaffold' directory.
#    (e.g., your projects folder looks like this:
#    projects/
#    ├── aider/
#    └── gitscaffold/)
# 3. From within the 'gitscaffold' directory, export your API keys and run the script:
#    export OPENAI_API_KEY="your-openai-key"
#    export GEMINI_API_KEY="your-gemini-key" # This is for the action, not aider itself
#    bash ./run_aider_on_gitscaffold.sh
#
#    Note: You might need to make the script executable first:
#    chmod +x ./run_aider_on_gitscaffold.sh

# --- Configuration ---
AIDER_DIR="../aider"
AIDER_MAIN_MODULE="aider.main"
RUN_DURATION="2h"
# Using a powerful model is recommended for complex tasks.
AIDER_MODEL="gpt-4-turbo"

# --- Aider Prompt ---
# This prompt is designed to be run in a loop. Aider will check the project state
# and work on the next incomplete task.
PROMPT='Your goal is to integrate the `google-github-actions/run-gemini-cli` GitHub Action into this `gitscaffold` project. This will empower `gitscaffold` to use Google'\''s Gemini models for automated tasks. The integration should be robust and well-documented. `gitscaffold` is being integrated with `vibe-kanban` (a manager for AI agents), so this feature should be implemented with high quality.

Please follow this checklist. In each iteration, review the current state of the repository and proceed with the next incomplete step.

**Project Checklist:**

1.  **[ ] Create GitHub Action Workflow:**
    *   **File:** `.github/workflows/gemini-assistant.yml`
    *   **Action:** If this file doesn'\''t exist, create it. It must use `google-github-actions/run-gemini-cli@main`.
    *   **Configuration:**
        *   Trigger on `issue_comment` and `pull_request_review_comment` where the comment body contains `@gemini-cli`.
        *   Use `secrets.GITHUB_TOKEN` for GitHub permissions.
        *   Use `secrets.GEMINI_API_KEY` to authenticate with the Gemini API.
    *   **Goal:** The action should act as an on-demand assistant, callable from PRs and issues.

2.  **[ ] Create `GEMINI.md` Configuration File:**
    *   **File:** `GEMINI.md`
    *   **Action:** If this file doesn'\''t exist, create it.
    *   **Content:** Populate it with project-specific context for Gemini. Describe that `gitscaffold` is a tool written in Go for scaffolding new Go projects with proper git repository structure. Mention its key commands and purpose.

3.  **[ ] Enhance `gitscaffold` to include the action:**
    *   **Goal:** Modify the `gitscaffold` tool to optionally include the new workflow and `GEMINI.md` files when generating a new project.
    *   **Action:** Identify the core scaffolding logic in the Go source code. Add a new command-line flag, such as `--with-gemini-action`, to control this feature. Implement the logic to copy `gemini-assistant.yml` and `GEMINI.md` into the new project when this flag is used.

4.  **[ ] Add Tests for the new feature:**
    *   **Goal:** Ensure the new scaffolding option works correctly.
    *   **Action:** Add a test case that executes `gitscaffold` with the `--with-gemini-action` flag. The test should then verify that `.github/workflows/gemini-assistant.yml` and `GEMINI.md` are present and correct in the scaffolded output directory.

5.  **[ ] Update Documentation:**
    *   **File:** `README.md`
    *   **Action:** Add a new section to the `README.md`.
    *   **Content:** Document the new Gemini integration feature. Explain how to use the `--with-gemini-action` flag and the requirement to set the `GEMINI_API_KEY` secret on the target repository for the action to work.

After completing a step, please re-evaluate the checklist and move to the next one. If all tasks are completed, please confirm that the work is done and then you can stop.
'

# --- Sanity Checks ---
if [ ! -d "$AIDER_DIR" ]; then
  echo "Error: Aider directory not found at '$AIDER_DIR'."
  echo "Please ensure your 'aider' and 'gitscaffold' directories are siblings."
  exit 1
fi

if [ -z "$OPENAI_API_KEY" ]; then
  echo "Error: OPENAI_API_KEY is not set."
  echo "Please export your OpenAI API key before running the script."
  exit 1
fi

# --- Run Aider ---
echo "Starting Aider to work on the gitscaffold project..."
echo "This will run for $RUN_DURATION. Press Ctrl+C to stop earlier."

# Set PYTHONPATH to include the aider project directory so modules can be found
export PYTHONPATH="${AIDER_DIR}:${PYTHONPATH}"

# Execute aider from the gitscaffold directory
python -m "$AIDER_MAIN_MODULE" \                                                                                                                                                                                                                     
  --message "$PROMPT" \                                                                                                                                                                                                                              
  --run-until "$RUN_DURATION" \                                                                                                                                                                                                                      
  --model "$AIDER_MODEL" \                                                                                                                                                                                                                           
  --continuous \                                                                                                                                                                                                                                     
  --yes 

echo "Aider has finished its session."
