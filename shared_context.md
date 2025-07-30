# Agent Coordination Context

This file is intended to help multiple agents (and humans) understand the context of ongoing work.

## Project Status

- `usage.md` has been created to document the standard user workflow.
- This `shared_context.md` file is used to track ongoing tasks.

## Current Task

**Request:** Ensure the workflow described in `usage.md` is covered by testing.

**My Plan:**

1.  **Create an end-to-end workflow test script:** `scripts/test_workflow.sh`.
    - This script will act as an integration test, simulating the user journey described in `usage.md`.
    - It will require `GITHUB_TOKEN` and `TEST_REPO` environment variables to run against a real test repository on GitHub.
2.  **The script will perform the following actions:**
    - Use `demo/example_roadmap.md` as a starting point.
    - Run `gitscaffold import-md` to populate the repo.
    - Create a new roadmap file `temp_roadmap.md` and add more tasks.
    - Run `gitscaffold sync` to create the new items.
    - Run `gitscaffold diff` to check the state.
    - Run `gitscaffold next` to check priorities.
    - Run cleanup commands like `gitscaffold delete-closed`.
    - The script will echo its progress and fail on any command failures.
3.  **Update this `shared_context.md` file** to reflect the plan and completion.

## Next Steps for Agents

- **Testing agents:**
  - Run the new `scripts/test_workflow.sh` script to validate the end-to-end workflow.
  - Review existing `pytest` tests to ensure full coverage of individual command features.
- **CI agents:**
  - Integrate `scripts/test_workflow.sh` into the CI pipeline. This will likely require setting up a test repository and secrets for `GITHUB_TOKEN`.
- **Documentation agents:**
  - Update `usage.md` or other documentation to mention this new test script.
