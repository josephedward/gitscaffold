 # Shared Context: Vibe-Kanban Integration

 **Purpose:**
 Coordinate the integration between `gitscaffold` and the [Vibe-Kanban](https://github.com/BloopAI/vibe-kanban) project to enable seamless synchronization of GitHub issues with Vibe-Kanban boards.

 ## Objective
 - Allow users to import GitHub issues (and milestones) into Vibe-Kanban as cards and columns.
 - Enable exporting Vibe-Kanban board state back to GitHub (issues, comments, labels).
 - Provide CLI commands and/or GitHub Actions workflows to automate synchronization.

 ## Proposed Integration Approach
 1. **Review Vibe-Kanban API and CLI**
    - Identify available commands or library entry points for creating/updating boards, columns, and cards.
    - Determine authentication mechanism and configuration.
 2. **Design gitscaffold Subcommands**
    - `gitscaffold vibe-kanban import --repo <org/repo> [--board <name>]`: pull issues and push to Vibe-Kanban.
    - `gitscaffold vibe-kanban export --board <name> --repo <org/repo>`: pull Vibe-Kanban state and sync back to GitHub.
    - Support flags: `--dry-run`, `--config <file>`, `--no-ai`/`--ai-enrich` where applicable.
 3. **Configuration and Secrets**
    - Use existing `get_github_token()` and `get_openai_api_key()` if enriching descriptions.
    - Add `get_vibe_kanban_token()` for board authentication if required.

 ## Files to Modify / Create
 - `scaffold/cli.py`: Add a new `vibe-kanban` command group with `import` and `export` subcommands.
 - `scaffold/vibe_kanban.py`: New module to wrap Vibe-Kanban API/CLI calls.
 - `tests/test_cli_vibe_kanban.py`: Unit tests mocking interaction with Vibe-Kanban.
 - `docs/integration_vibe-kanban.md`: Detailed user guide and examples for the integration.

 ## Implementation Steps
 1. Clone the Vibe-Kanban repository into `integrations/vibe-kanban` and explore its API (completed).
 2. Scaffold the `vibe_kanban.py` module with placeholder functions:
    - `list_boards()`, `create_board()`, `list_columns(board_id)`, `create_column(board_id)`, `list_cards(column_id)`, `create_card(column_id, issue)`.
 3. Implement CLI commands in `scaffold/cli.py` to invoke `vibe_kanban` functions.
 4. Write unit tests in `tests/test_cli_vibe_kanban.py`, mocking `vibe_kanban` module.
 5. Add documentation in `docs/integration_vibe-kanban.md` with examples and workflow.
 6. Perform manual end-to-end smoke test with a sample GitHub repo and a test board.

 ## Next Steps
 1. Explore the Vibe-Kanban codebase to confirm API capabilities.
 2. Sketch out data model mappings between GitHub issues and Vibe-Kanban cards.
 3. Begin coding the `vibe_kanban.py` wrapper and CLI commands.
 4. Coordinate further changes in this shared context document as progress is made.

 **Date:** 2025-08-06