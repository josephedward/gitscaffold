# Shared Context

## Completed: AI-First Extraction

 **Purpose:** Centralized plan and coordination notes for implementing AI-first extraction in gitscaffold.

 ## Created Files
 - **usage.md**: User-facing workflow documentation.
 - **shared_context.md**: This coordination document.

 ## Objective
 Make AI extraction the default for unstructured Markdown roadmaps (`.md` files) in `diff` and `sync` commands:
 1. **Diff Command**
    - Detect `.md` file input and automatically invoke `extract_issues_from_markdown`.
    - Use `get_openai_api_key()` to load or prompt for the key from `.env` or environment.
    - Emit prominent warnings about the importance of protecting API keys.
 2. **Sync Command**
    - For Markdown roadmaps with no structured sections, auto-extract features/tasks via AI.
    - Integrate extracted issues into the same validation and creation flow.
    - Prompt for or load OpenAI key as above.

 ## Additional Requirements
 - Prompt user if `OPENAI_API_KEY` is missing, save it to `.env`, then re-run.
 - Warn users about secrets in logs (e.g., never print API keys).

 ## Planned Code Changes
 - Update `scaffold/cli.py`:
    * Rework `diff()` to default to AI extraction for `.md`, dropping manual `--ai` flag requirement.
    * Enhance `sync()` to fallback to AI extraction when structured parsing yields no items.
    * Call `get_openai_api_key()` at start and log warnings.
 - Adjust tests:
    * Add unit tests mocking AI extraction path in `diff` and `sync`.
    * Ensure prompting logic for missing keys is covered.

 ## Next Steps
 1. Implement the code changes outlined above. [✓]
 2. Write tests for the new AI-default paths. [✓]
 3. Update `usage.md` to describe AI-first behavior and key management. [✓]
 4. Run `pytest` to verify all scenarios pass. [✓]
 5. Release a new patch version (e.g., 0.1.13). [✓]

## Progress Summary

- Implementation of AI-first default behavior in `diff` and `sync`: Completed
- Added and updated tests for AI extraction and fallback paths: Completed
- Updated documentation (`usage.md`, CLI help text) to highlight default AI-first behavior and `--no-ai` flag: Completed
- Version bumped to `0.1.13`; patch release ready: Completed

## Discussion: AI-First Default Behavior
### Problem
- The built-in markdown parser often finds 0 items in free-form `.md` roadmaps, causing `diff` to mark all GitHub issues as extra and `sync` to do nothing.
- Users must remember to pass `--ai` (for diff) or `--ai-enrich` (for sync) to leverage AI, which is inconsistent and error-prone.

### Proposed Solution
1. **Default to AI extraction** whenever a roadmap is a Markdown file with no structured milestones/features:
   - In `diff`, detect `.md` input, run structured parser first; if no items, automatically prompt:
     "No structured roadmap items found. Try AI-powered extraction? [y/N]"
     - On confirmation, call `extract_issues_from_markdown` and proceed.
   - In `sync`, after structured parse yields no features/tasks, similarly prompt and extract.
2. **Unify flags**:
   - Remove `--ai` flag from `diff` (AI becomes implicit).
   - Add a global `--no-ai` flag to disable AI fallback when desired.
   - In `sync`, repurpose `--ai-enrich` strictly for enrichment; AI extraction implicit for Markdown.
3. **Key management & warnings**:
   - Use `get_openai_api_key()` to load or prompt/save key from `.env` or env.
   - Emit clear warnings about protecting API keys (never log them).

### Files to Modify
- **scaffold/cli.py**: Update `diff()` and `sync()` commands to implement AI-first fallback and flag changes.
- **tests/test_cli_diff.py**: Add tests for Markdown diff with AI fallback and `--no-ai` disable.
- **tests/test_cli_sync.py**: Add tests for Markdown sync creating issues via AI extraction.

### Implementation Steps
1. Code changes in `scaffold/cli.py`:
   - Refactor argument definitions: remove `--ai` from `diff`, add `--no-ai` to both commands.
   - During execution, check file extension and structured parse result, prompt for AI fallback.
2. Update unit tests:
   - Mock `extract_issues_from_markdown` to return a known set of titles.
   - Verify `diff docs/roadmap.md` triggers AI path by default and lists extracted items.
   - Verify `gitscaffold sync docs/roadmap.md` with AI creates correct issue creation messages.
3. Manual smoke test using a simple `.md` with headings to confirm behavior.
4. Update `usage.md` and README to reflect new default AI behavior and `--no-ai` option.
5. Ensure CI and pre-commit hooks pass; adjust configuration if necessary.

 **Date:** 2025-07-30
