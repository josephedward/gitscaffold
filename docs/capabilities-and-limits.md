# Gitscaffold Capabilities and Limits

This document states, as precisely as possible, what Gitscaffold can and cannot do based on the current codebase.

## Supported Inputs
- Structured roadmap: Markdown with sections like “## Milestones”, “## Features”, “### Feature Title”, and optional task sections; also supports YAML/JSON roadmaps.
- Unstructured Markdown: Can extract issues via AI (OpenAI or Gemini) when enabled or prompted.
- Roadmap write-back: Writes Markdown via `write_roadmap` (checkbox tasks, basic metadata lines). JSON/YAML write-back is not supported.

## Authentication and Providers
- GitHub: Requires a PAT. Reads from `GITHUB_TOKEN` (env/.env/config) or prompts. Most commands need `repo`/`issues` scopes; `delete-closed` additionally uses GraphQL.
- AI: Optional. OpenAI (`OPENAI_API_KEY`) and/or Gemini (`GEMINI_API_KEY`). Used for extraction and enrichment. Network and provider availability required.
- gh CLI: Optional. Some helpers wrap `gh` if installed or bootstrapped by `gitscaffold gh install`.

## Core Commands

### setup
- CAN: Create a sample `ROADMAP.md` and stub `.env` entries for tokens.
- CANNOT: Create a new GitHub repository; install `gh` or dependencies automatically.

### sync ROADMAP_FILE --repo owner/repo [--ai|--no-ai] [--ai-enrich] [--dry-run] [--yes] [--update-local]
- CAN: Parse roadmap; create missing milestones/issues; attach labels/assignees/milestones on creation; optionally AI-enrich bodies; preview with `--dry-run`.
- CAN: Fallback to AI extraction for unstructured Markdown (prompted unless `--no-ai`; forced with `--ai`).
- CAN: Update local roadmap from GitHub with `--update-local` (adds GH-only items; marks closed tasks as completed).
- CANNOT: Update existing GitHub issues to match roadmap (titles, labels, bodies, milestones are not reconciled).
- CANNOT: Delete/close “extra” issues on GitHub; only creates missing ones.
- CANNOT: Guarantee idempotency if titles change on GitHub; matching is primarily by exact title string (open issues).

### diff ROADMAP_FILE --repo owner/repo [--no-ai]
- CAN: Show titles present in roadmap but missing on GitHub, and vice versa.
- CAN: Prompt to create missing issues.
- CANNOT: Create missing milestones before creating issues. If an issue uses a non-existent milestone, creation may fail.
- CANNOT: Close or delete extra issues.

### next [--repo owner/repo] [-f ROADMAP.md]
- CAN: Show open issues in the earliest active milestone (by due date). If none, picks a random open issue. If no open issues, falls back to a local roadmap task.
- CANNOT: Prioritize by labels/assignees or custom rules; does not open the browser; does not consider Projects/Boards.

### delete-closed [--repo owner/repo] [--dry-run] [-y]
- CAN: Permanently delete all CLOSED issues via GraphQL. Supports dry-run and confirmation prompts.
- CANNOT: Undo deletions; act on OPEN issues; selectively delete by filters (other than closed state).

### sanitize [--repo owner/repo] [--dry-run] [-y]
- CAN: Remove leading header markers (e.g., `#`) from issue titles in bulk.
- CANNOT: Apply custom renaming rules or normalize other naming conventions.

### deduplicate [--repo owner/repo] [--dry-run] [-y]
- CAN: Find open issues with duplicate titles and close the newer ones.
- CANNOT: Merge comments/bodies; add cross-links; handle “near-duplicate” fuzzy matches.

### enrich issue|batch
- CAN: Generate enriched issue bodies using roadmap context; operate on one issue or batch; CSV export and interactive approvals supported.
- CANNOT: Change titles/labels/milestones; guarantee deterministic output; operate without valid AI keys/provider.

### import-md REPO MARKDOWN_FILE [--ai-provider openai|gemini] [--dry-run] [-y]
- CAN: Extract issues from a free-form Markdown file using AI and create them in the repo.
- CANNOT: Preserve hierarchy or metadata beyond title/body; guarantee perfect extraction; run without AI key.

### gh group (install/which/version/issue-list/create/close)
- CAN: Bootstrap `gh`; list/create/close issues via `gh` wrappers.
- CANNOT: Replace all PyGithub-backed features; wrappers are limited to the listed subcommands.

### scripts / ops
- CAN: Install and run bundled maintenance scripts (bash-based) like repo aggregation/archival and branch cleanup.
- CANNOT: Run natively on Windows PowerShell without adaptation; guarantee safety in destructive operations without careful flags.

### start-demo / start-api
- CAN: Attempt to run a Streamlit demo or a FastAPI app if present in the expected paths.
- CANNOT: Work in this repo by default (apps not included); install `streamlit`/`uvicorn` automatically.

### assistant [args] / assistant process-issues
- CAN: Passthrough to the external `aider` CLI; process a list of issues sequentially and log outputs.
- CANNOT: Run without `aider` installed; integrate natively with aider’s internals beyond subprocess invocation.

## Data Model and Mapping
- Features and tasks are modeled as separate GitHub issues. Parent-child is a convention using a body line: `Parent issue: #<number>`; no native GitHub linked-issue relationship is created.
- Title matching is strict (exact string). Existing checks and creations primarily consider OPEN issues; closed issues are not treated as existing and may be recreated.
- Labels/assignees/milestones are applied on creation if provided in the roadmap. Labels are not created/managed; they should already exist in the repository. Milestones are created in `sync` but not in `diff`.

## Performance and Parsing
- Uses a Python Markdown parser; optionally uses `mdparser` (Rust) if found in PATH for faster parsing. Falls back automatically to Python if `mdparser` is unavailable.
- Large repos/roadmaps may be slow due to API pagination and round trips.

## Non‑Goals and Known Gaps
- No bidirectional canonical sync: existing issues are not updated to match the roadmap; “extra” issues are not closed automatically.
- No automatic label or project management; no board/Project sync beyond the experimental `vibe` commands.
- No deterministic AI outputs; privacy and cost considerations apply when AI features are used.
- `next-task` is mentioned in README but not implemented in the CLI; rely on `next` for now.

## Good Practices
- Use `--dry-run` before destructive/bulk operations.
- Prefer structured roadmaps for predictability; disable AI with `--no-ai` if not desired.
- Create labels and milestones in the repo ahead of time if using `diff` creation flow; or use `sync` which creates milestones first.
- Pin tool versions in CI and standardize whether to use `gh` or PyGithub for consistency.
