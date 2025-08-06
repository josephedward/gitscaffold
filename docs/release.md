# Release Notes

## v0.1.17 (2025-08-06)
- **Fix**: Resolved an UnboundLocalError in the `sync` command by defaulting issue bodies when missing descriptions.
- **Docs**: Moved Vibe Kanban integration details to `docs/integration_vibe-kanban.md` and removed detailed examples from README.md and usage.md.
- **Cleanup**: Deleted deprecated `shared_context.md` and `shared_context_vibe-kanban.md`.
- **Feature**: Added stub `vibe list-projects` command and documented it.

## v0.1.16 (2025-07-30)
- **Feature**: The `sync --update-local` command now marks tasks as completed in the local roadmap file with `[x]` if their corresponding GitHub issue is closed.
- **Parser**: The Markdown parser now recognizes `[x]` and `[ ]` in task titles to correctly set their completion status upon reading the file.
- **Validator**: Added a `completed: bool` flag to the `Task` data model to support tracking completion status.

## v0.1.15 (2025-07-30)
- **Fix**: Corrected package configuration in `pyproject.toml` to ensure the `gitscaffold` command-line script is created upon installation.
- **Fix**: Corrected the OpenAI API client initialization in the `enrich` command, which was using a deprecated calling convention and would fail.
- **Fix**: Added retry logic for OpenAI API calls in `sync` and `diff` commands. If an invalid API key is detected, the user is prompted to enter a new one, which is then saved to `.env` for immediate use.
- **Docs**: Added a troubleshooting section to `usage.md` for the `command not found` error.

## v0.1.14 (2025-07-30)
- **Feature**: Default AI-first extraction for unstructured Markdown in `sync` and `diff` commands; use `--no-ai` to disable or `--ai` to force.
- **CLI**: Help texts updated to prominently mention `OPENAI_API_KEY` requirement and AI-first behavior.
- **Fix**: Removed duplicate missing-token/key messages and streamlined prompting flow without requiring a rerun.
- **Docs**: Trimmed duplicate blocks in `usage.md`, polished wording across README and usage guide.

## v0.1.11 (2025-07-18)
- **Feature**: Add `import-md` as a top-level command for AI-driven issue creation from unstructured markdown files.
- **Fix**: Resolve issue with duplicate `import-md` command definitions in the CLI, which caused argument parsing errors.

## Releasing

The project is automatically published to PyPI via the `Publish & Notify Release` GitHub Action when a new tag matching `v*.*.*` is pushed.

The process is:
1.  **Update Version**: Bump the `__version__` in `scaffold/__init__.py`.
2.  **Update Release Notes**: Add a new section for the release at the top of this file (`docs/release.md`).
3.  **Commit and Tag**:
    ```sh
    git add scaffold/__init__.py docs/release.md
    git commit -m "chore(release): vX.Y.Z"
    git tag vX.Y.Z
    ```
4.  **Push to GitHub**:
    ```sh
    git push origin main --tags
    ```
5.  **Monitor Workflow**: The `Publish & Notify Release` workflow will automatically trigger. Check the "Actions" tab in the repository to monitor its progress.
