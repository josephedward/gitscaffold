 # Shared Context

 **Purpose:** Provide shared information for multiple agents working on this project.

 ## Created Files

 - **usage.md**: A comprehensive user guide describing the ideal workflow for using gitscaffold.
 - **shared_context.md**: This file, containing the shared context.

 ## Plan

 1. Create **usage.md** at the project root to describe the standard gitscaffold workflow.
 2. Reference existing examples:
    - `demo/example_roadmap.md` for Markdown-based roadmap example.
    - `tests/test_cli_sync.py` for JSON-based roadmap example and CLI tests.
 3. Include commands for key steps:
    - Syncing (`sync`, `--dry-run`, `diff`).
    - Navigation (`next`, `next-task`).
    - Maintenance (`delete-closed`, `sanitize`, `deduplicate`).
 4. Add instructions to run tests to validate functionality.

 ## Next Steps for Agents

 - Documentation agents: Review and refine **usage.md** content.
 - Development agents: Verify CLI commands behave as documented.
 - Testing agents: Run the `pytest` suite and manual smoke tests using demo files.
 - CI agents: Integrate this workflow into CI pipelines (e.g., via `scripts/audit.sh` or GitHub Actions).

 ## References

 - `README.md`
 - `docs/integration_test.md`
 - `tests/test_cli_sync.py`
 - `demo/example_roadmap.md`

 **Date:** 2025-07-30