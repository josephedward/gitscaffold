    #!/usr/bin/env bash
    set -euxo pipefail

    # ──────────────────────────────────────────────────────────────────────────────
    # run-aider-integration.sh
    #
    # Run the local Aider CLI continuously against this repo (gitscaffold)
    # for 2 hours to integrate and test the google-github-actions/run-gemini-cli Action.
    # -----------------------------------------------------------------------------

    # Compute paths
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
    AIDER_DIR="$(cd "${REPO_ROOT}/../aider" && pwd)"

    echo "Installing local Aider from: $AIDER_DIR"
    python3 -m pip install -e "$AIDER_DIR"
    # Ensure the local Aider package is preferred over any globally installed copy
    export PYTHONPATH="$AIDER_DIR:${PYTHONPATH:-}"

    PROMPT_FILE="$REPO_ROOT/.aider-integration-prompt.txt"
    echo "Writing integration prompt to $PROMPT_FILE"
    tee "$PROMPT_FILE" > /dev/null << 'EOF'
    We want to integrate the Google GitHub Action 'google-github-actions/run-gemini-cli'
    into this repository (gitscaffold), so that every push or pull-request runs our
    local Aider CLI via Gemini/OpenAI and updates the codebase as needed.

    Please:
    1) Create a workflow file at .github/workflows/run-gemini.yml that triggers on:
         - push to main
         - pull_request targeting main

    2) In that workflow, after checkout, install Aider via:
           python3 -m pip install -e ../aider
       and export your keys from secrets:
           OPENAI_API_KEY, GEMINI_API_KEY
       then run:
           python3 -m aider \
             --message-file .aider-integration-prompt.txt \
             --continuous --delay 10 --run-until 2h

    3) Add basic smoke tests under tests/ or ci/ that verify:
       • .github/workflows/run-gemini.yml parses correctly
       • (Optional) use act or Docker to simulate the Action locally

    4) Update README.md to document:
       • The new workflow path
       • Required GitHub secrets: OPENAI_API_KEY, GEMINI_API_KEY
       • How to run Aider locally for manual testing

    5) Each loop iteration should commit incremental fixes to CI/workflow/tests until
       a non-erroring 2-hour dry-run passes.

    Only modify files in .github/, tests/, ci/ or docs/ as needed.
    EOF

    echo "Prompt written, launching continuous Aider run for 2 hours..."
    cd "$REPO_ROOT"
    # Invoke Aider via the Python module entrypoint, picking up the local source
    python3 -m aider.main \
      --message-file "$PROMPT_FILE" \
      --continuous \
      --delay 10 \
      --run-until 2h

    echo "Continuous run complete."
