# Gitscaffold Weaknesses

This document candidly outlines major limitations, tradeoffs, and risks.

## External Dependencies and Limits
- Requires GitHub and (optionally) OpenAI APIs; subject to outages and rate limits.
- Dual backends (`gh` CLI vs PyGithub) can behave differently; path/versions may drift.
- Network access is required for most operations; offline workflows are limited.

## AI Accuracy and Privacy
- AI extraction can be noisy: hallucinated tasks, missed context, or duplicates.
- Non-deterministic outputs make reproducibility harder across runs.
- Sending content to third-party AI providers raises privacy/compliance concerns.
- AI usage adds latency and cost; quotas/limits can throttle workflows.

## Destructive and Bulk Operations
- `delete-closed` is irreversible; mistakes cannot be undone via the tool.
- `sanitize` and `deduplicate` perform mass edits/closures that may require manual cleanup if misapplied.
- Confirmation prompts help but don’t eliminate human error.

## Diff/Sync Heuristics
- Matching between roadmap items and GitHub issues relies heavily on titles/labels.
- Renames or significant edits can produce false positives/negatives during `diff`/`sync`.
- Idempotency has edge cases when issues are edited directly on GitHub outside the expected conventions.

## Roadmap Assumptions
- Best results require the structured roadmap format; unstructured docs depend on AI quality.
- Complex nesting, cross-file references, or custom metadata schemas have limited support.
- Mapping advanced milestone/workflow states into GitHub is opinionated and may not fit every team.

## Performance and Scale
- Large roadmaps or repositories can be slow due to API pagination and round-trips.
- Optional Rust parser (`mdparser`) improves Markdown speed but adds toolchain complexity.
- No prebuilt binaries for all platforms; building Rust components may be a barrier.

## Platform and Environment Constraints
- Some bundled scripts assume POSIX shells; Windows users may need PowerShell rewrites.
- `gh` is not installed automatically for local use; environment drift can cause surprises.

## Error Handling and UX
- API errors may surface as verbose tracebacks; limited friendly remediation guidance.
- Conflict resolution during sync is basic; complex merge policies aren’t supported.

## Testing and Support Boundaries
- End-to-end tests depend on live GitHub tokens and environment setup.
- Experimental integrations (e.g., Vibe Kanban, Gemini) are not production-hardened.

## When It May Not Be a Fit
- Strict data governance prohibits sending content to external AI services.
- Teams on non-GitHub platforms (GitLab, Jira) or with heavily customized workflows.
- Projects requiring deterministic, audited planning artifacts without AI variability.
- Extremely large enterprise repos needing specialized sync/replication guarantees.

## Mitigations and Workarounds
- Use `--dry-run` and review diffs before applying changes.
- Prefer the structured roadmap format for determinism; disable AI with `--no-ai`.
- Limit token scopes; store credentials securely; avoid sending sensitive content to AI.
- Pin a single backend (`--use-gh-cli` or PyGithub) and standardize tool versions in CI.
- Consider vendoring or prebuilding `mdparser` where performance matters.
- Backup or snapshot issues prior to bulk operations (e.g., via exports or reports).

