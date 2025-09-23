# Gitscaffold Strengths

This document highlights what Gitscaffold does especially well and when to use it.

## Core Value
- Turns Markdown roadmaps into actionable GitHub issues and milestones.
- Keeps plans and issues aligned with `sync` and `diff` workflows.
- Works as both a local CLI and a GitHub Action.

## AI-First Capabilities
- Extracts issues from unstructured Markdown using OpenAI (opt-in or prompted).
- Enriches issue descriptions for clarity and context (`enrich`).
- Supports an alternate ingestion path with `import-md` for quick conversion of notes to issues.

## Safety, Control, and UX
- `--dry-run` previews for destructive or bulk operations.
- Interactive confirmations before applying changes.
- Clear, readable plans and diffs before mutation.

## Productivity Utilities
- `delete-closed` to bulk-remove closed issues.
- `sanitize` to clean header markers from issue titles.
- `deduplicate` to find and close duplicates by title.
- `next` and `next-task` to surface immediate priorities.

## Performance and Reliability
- Optional Rust-based Markdown parser (`mdparser`) for high-speed parsing with seamless Python fallback.
- Uses GitHub CLI (`gh`) when available, while supporting a robust PyGithub backend.

## Simple Auth and Config
- Credentials via env vars, `.env`, or `gitscaffold config` with a persisted config file.
- Works well in local dev, CI, and GitHub Actions.

## Extensibility and Scripts
- Bundled helper scripts for repo maintenance (aggregation, archival, cleanup).
- Experimental integrations (e.g., Vibe Kanban, Gemini) to explore advanced workflows.

## Quality and Operations
- Tested end-to-end workflow and pytest test suite included.
- CI with coverage reporting; project actively dogfoods itself.

## Great Fit For
- Teams who plan in Markdown but execute on GitHub issues.
- Projects mixing structured and free-form docs, wanting AI assistance.
- Repos needing regular hygiene: deduplication, closed-issue cleanup, and title normalization.

