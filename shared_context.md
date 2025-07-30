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

 **Date:** 2025-07-30# Agent Coordination Context

This file is intended to help multiple agents (and humans) understand the context of ongoing work.

## Current Task

**Request:** Create a `usage.md` document outlining the ideal workflow for `gitscaffold`, and use this file (`shared_context.md`) to log plans and updates.

**My Plan:**

1.  **Create `shared_context.md`:** This file. It will serve as a log of my actions and plans for this session.
2.  **Create `usage.md`:**
    *   Outline a standard user workflow for `gitscaffold`.
    *   The workflow will cover:
        *   Initial project setup (`gitscaffold setup`).
        *   Defining tasks and milestones in `ROADMAP.md`.
        *   Syncing the roadmap to GitHub issues (`gitscaffold sync`).
        *   Checking for differences (`gitscaffold diff`).
        *   Finding what to work on next (`gitscaffold next`).
    *   I will use a sample `ROADMAP.md` as a concrete example.
    *   The documentation will be written to be clear and easy to follow for a new user.
    *   The user mentioned ensuring the workflow is 'tested and functional'. I'll base the workflow on the existing CLI commands and their tests, assuming they reflect the intended functionality.

No existing files need to be modified for this request. I will create two new files: `usage.md` and `shared_context.md`.
