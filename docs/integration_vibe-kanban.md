<!--
  Experimental Vibe Kanban integration guide.
  This feature is highly experimental and untested.
-->
# Vibe Kanban Integration (Experimental)

**Highly Experimental & Untested**
This integration bridges GitHub issues managed by `gitscaffold` with a Vibe Kanban board. It is in early development and may change without notice.

Original project: https://github.com/BloopAI/vibe-kanban

## Purpose
Coordinate synchronization between GitHub issues and a Vibe Kanban board, enabling:
- Importing GitHub issues (and milestones) into Vibe Kanban as cards and columns
- Exporting Vibe Kanban state (statuses, comments, labels) back to GitHub
- Automating sync via CLI commands or GitHub Actions

## Objective
- **Push**: Mirror GitHub issues to a Vibe Kanban board
- **Pull**: Sync card status and comments back to GitHub issues

## Proposed Integration Approach
1. **Review Vibe Kanban API/CLI**: Identify commands/endpoints and authentication methods
2. **Design CLI Subcommands**:
   - `gitscaffold vibe list-projects`
   - `gitscaffold vibe push --repo <org/repo> --board <name>`
   - `gitscaffold vibe pull --repo <org/repo> --board <name> [--bidirectional]`
3. **Configure Secrets**: Use `GITHUB_TOKEN`, `OPENAI_API_KEY`; add `VIBE_KANBAN_API`, `VIBE_KANBAN_TOKEN` if needed

## Files to Modify / Create
- `scaffold/cli.py`: Add `vibe` command group with `list-projects`, `push`, `pull`
- `scaffold/vibe_kanban.py`: Implement API client methods (`list_boards`, `push_issues_to_board`, `pull_board_status`)
- `tests/test_cli_vibe.py`: Unit tests mocking the Vibe Kanban client

## Implementation Steps
1. Scaffold `scaffold/vibe_kanban.py` with placeholder methods
2. Wire up `vibe` commands in `scaffold/cli.py` to call the client
3. Write unit tests using mocks or a dummy server
4. Document examples and edge cases in this guide
5. Perform manual end-to-end smoke tests against a live Vibe Kanban server

## Next Steps
- Explore the Vibe Kanban repository for API details
- Sketch mappings between GitHub issues and Kanban cards
- Build and refine test coverage

Date: 2025-08-06