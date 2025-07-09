# GitScaffold Project Roadmap

A tool to manage GitHub projects using declarative roadmap files, with AI-powered issue enrichment and creation.

## Milestones

- **v0.1 Foundation (CLI & Basic Parsing)** — 2025-08-01
- **v0.2 GitHub Integration** — 2025-09-01
- **v0.3 AI Features (Extraction & Enrichment)** — 2025-10-01
- **v0.4 Advanced Features & Usability** — 2025-11-01
- **v1.0 Stable Release** — 2025-12-01
- **Post v1.0 Enhancements** — 2026-01-01

## Features

### Core CLI Framework

Setup basic CLI structure and command handling for gitscaffold.  
**Milestone:** v0.1 Foundation (CLI & Basic Parsing)  
**Labels:** core, cli

#### Implement main CLI group using Click

Establish the main entry point and command structure for the CLI using the Click library. This will be based on `scaffold/cli.py` and `gitscaffold.py`.

#### Implement `init` command

Develop an `init` command that can initialize a project in multiple ways:
- Generate a template `ROADMAP.md` file for users to fill out.
- From an existing `ROADMAP.md` or `README.md`, create a new GitHub repository and bootstrap it with issues.

**Tests:**
- Test `init` with no arguments creates `ROADMAP.md` in the current directory.
- Test `init --create-repo` successfully creates a new repository on GitHub.
- Test `init --from-readme` correctly parses a `README.md` and creates issues.

### Roadmap Parsing and Validation

Implement logic to parse roadmap files (Markdown) and validate their structure and content.  
**Milestone:** v0.1 Foundation (CLI & Basic Parsing)  
**Labels:** core, parser, validator

#### Implement Markdown parser for roadmap

Create parsing functions for roadmap files, supporting Markdown format. Based on `scaffold/parser.py::parse_markdown`.

#### Implement Pydantic models for validation

Define Pydantic models for roadmap elements (Roadmap, Milestone, Feature, Task) to ensure data integrity. Based on `scaffold/validator.py`.

### GitHub Integration

Develop functionality to interact with the GitHub API for creating and managing milestones and issues.  
**Milestone:** v0.2 GitHub Integration  
**Labels:** core, github


#### Wrap `gh` CLI for core GitHub operations

Integrate with the `gh` CLI to leverage its robust functionality for core operations like listing, creating, and deleting issues. This will provide a reliable foundation and reduce the need to re-implement complex API interactions.

**Tests:**
- Verify that core commands (e.g., `issue list`) call the `gh` subprocess.
- Test for graceful failure when the `gh` CLI is not installed on the system.

#### Implement GitHub client wrapper

Create a robust client for GitHub API interactions, encapsulating PyGitHub calls for functionality not covered by the `gh` CLI wrapper. Based on `scaffold/github.py::GitHubClient`.

#### Implement `create` command

Build the `create` command to process a roadmap file and create corresponding milestones and issues on GitHub. Based on `scaffold/cli.py::create`.

#### Implement `setup` command

Port and integrate the `setup` command functionality for initializing a repository with predefined labels and milestones. Based on `gitscaffold.py::setup` and `scripts/github_setup.py`.

**Tests:**
- Mock GitHub API: Test `gitscaffold setup` creates all predefined labels from `scripts/github_setup.py::RECOMMENDED_LABELS`.
- Mock GitHub API: Test `gitscaffold setup` creates all predefined milestones from `scripts/github_setup.py::MILESTONES`.
- Test idempotency: running `setup` multiple times should not create duplicate labels/milestones.

#### Implement `delete-closed` command

Port and integrate the `delete-closed` command. Based on `gitscaffold.py::delete-closed`.


#### Implement `delete` command

Provide a general-purpose `delete` command to remove (or close) GitHub issues, wrapping `gh` or using the API directly.
Tasks:
- Investigate support for issue deletion vs. closure in the GitHub CLI and API.
- Build `gitscaffold delete` with confirmation prompts and a `--yes` override.
- Support both single-issue and bulk-deletion modes.
- Add safety tests to prevent accidental deletion of active issues.


### AI-Powered Features

Integrate AI/LLM capabilities for extracting issues from Markdown and enriching issue descriptions.  
**Milestone:** v0.3 AI Features (Extraction & Enrichment)  
**Labels:** ai, enhancement

#### Implement API key management for AI

Securely retrieve and manage API keys for AI services. Based on `scaffold/ai.py::_get_api_key`.

#### Implement issue extraction from Markdown

Use an LLM to parse unstructured Markdown and extract potential issues. Based on `scaffold/ai.py::extract_issues_from_markdown`.

#### Implement issue description enrichment

Use an LLM to enhance or generate issue descriptions based on a title and context. Based on `scaffold/ai.py::enrich_issue_description`.

#### Integrate AI extraction into `create` command

Add an `--ai-extract` option to the `create` command to use LLM-based issue extraction from a Markdown roadmap. Link to `scaffold/cli.py::create`.

#### Integrate AI enrichment into `create` command

Add an `--ai-enrich` option to the `create` command to use LLM-based description enrichment. Link to `scaffold/cli.py::create`.


#### Implement `enrich` command

Port and integrate the `enrich` command for AI-powered enrichment of issues. Based on `gitscaffold.py::enrich` and `scripts/enrich.py`.

#### Implement `find-issue` command with natural language

Create a `find-issue` command that uses an LLM to search for a GitHub issue based on a natural language query. This will involve fetching issues, creating embeddings for their content, and performing a semantic search to find the most relevant results.

**Tests:**
- Mock LLM/GitHub: Test with a query that should clearly match a specific issue title or body.
- Test with a query that has no obvious matches to ensure it returns no results or a helpful message.
- Verify that issue embeddings can be cached to improve performance on subsequent searches.

#### Implement `create-one` command for single-issue creation

Develop a command to create a single issue from a title, with an option to auto-generate and enrich the description using an LLM based on context from the roadmap.

**Tests:**
- Test creating a simple issue with just a title.
- Mock LLM: Test that the `--enrich` flag successfully generates and applies an issue body.
- Verify that standard options like `--label` and `--milestone` can be passed and are applied correctly.

### Workflow and Productivity Features

Add commands to help users identify and focus on their next tasks.  
**Milestone:** v0.4 Advanced Features & Usability  
**Labels:** usability, cli

#### Implement `next` command

Create a `next` command to show next action items from the earliest active milestone. Based on `scaffold/cli.py::next_command`.
#### Implement `next-task` command

Create a `next-task` command to show the next open task for the current roadmap phase. Based on `scaffold/cli.py::next_task`.
#### Implement `deduplicate-issues` command

Create a `deduplicate-issues` command to find and close duplicate open issues, based on title matching. Based on `scaffold/cli.py::deduplicate_command`.
**Tests:**
- Test `gitscaffold deduplicate-issues --dry-run` to list duplicates.
- Confirm `gitscaffold deduplicate-issues` closes duplicates when applied.
#### Implement `cleanup-issue-titles` command

Create a `cleanup-issue-titles` command to sanitize issue titles by removing leading markdown characters. Based on `scaffold/cli.py::sanitize_command`.
**Tests:**
- Test `gitscaffold sanitize --dry-run` to preview title changes.
- Confirm `gitscaffold sanitize` applies cleaned titles correctly.


#### Enhance `diff` command

Enhance the `diff` command to include issue numbers and state in its output, and allow filtering by issue state.



### Testing Framework and Coverage

Establish and maintain a comprehensive testing suite for the application.  
**Milestone:** v0.4 Advanced Features & Usability  
**Labels:** testing, quality

#### Setup Pytest environment and fixtures

Configure Pytest with necessary plugins and shared fixtures (e.g., for mocking GitHub API, LLM API).

#### Develop unit tests for parser module

Write unit tests for all functions in `scaffold/parser.py`.

#### Develop unit tests for validator module

Write unit tests for Pydantic models and validation logic in `scaffold/validator.py`.

#### Develop unit/integration tests for GitHub client

Test `scaffold/github.py` thoroughly using mocked GitHub API responses.

#### Develop unit/integration tests for AI module

Test `scaffold/ai.py` using mocked LLM API responses.

#### Develop integration tests for CLI commands

Create end-to-end tests for each CLI command, mocking external services (GitHub, AI) using Click’s `CliRunner`.

#### Achieve and maintain target test coverage

Aim for a high test coverage percentage (85%+) and integrate coverage reporting into CI.

#### Implement tests for `scripts/import_md.py`

Ensure robust tests for the Markdown import script. Based on `tests/test_import_md.py`.

### Documentation

Create and maintain comprehensive documentation for users and developers.  
**Milestone:** v0.4 Advanced Features & Usability  
**Labels:** documentation

#### Write comprehensive `README.md`

Include project overview, features, installation instructions, quick start guide, and basic usage examples.

#### Document roadmap file format

Provide a detailed specification of the roadmap file structure (Markdown).

#### Document all CLI commands and options

Generate or write detailed help text and usage examples for each CLI command.

#### Create example roadmap files

Develop a diverse set of example roadmap files showcasing different features and use cases.

#### Write developer documentation

Include information on project structure, development setup, contribution guidelines, how to run tests, and coding conventions.

### CI/CD and Release Management

Automate testing, building, and publishing of the `gitscaffold` package.  
**Milestone:** v1.0 Stable Release  
**Labels:** ci-cd, release

#### Setup GitHub Actions for CI

Configure workflows to run linters and execute the test suite on every push and pull request.

#### Automate PyPI publishing

Set up automated publishing to PyPI when new versions are tagged.

#### Manage release notes and changelog

Maintain a changelog and automate generation of release notes.

### Advanced Roadmap Features (Post v1.0)

Introduce more sophisticated features for roadmap management.  
**Milestone:** Post v1.0 Enhancements  
**Labels:** enhancement, roadmap

#### Support for task dependencies

Allow tasks within a roadmap to declare dependencies on other tasks.

#### Support for GitHub issue templates

Allow users to specify project-defined GitHub issue templates for creation.

#### Roadmap diffing and updating (“sync” command)

Implement the `sync` command to compare a roadmap with GitHub issues and prompt to create missing ones.

#### Option for sub-tasks as checklist items

Provide an option to create tasks as checklist items within the body of their parent feature’s issue.

### Extensibility and Configuration (Post v1.0)

Enhance the tool’s flexibility through better configuration and a plugin architecture.  
**Milestone:** Post v1.0 Enhancements  
**Labels:** enhancement, configuration, extensibility

#### Global and project-level configuration file

Allow users to define default settings in a configuration file (`~/.gitscaffold/config.md` or `.gitscaffold.md`).

#### Basic plugin system

Design and implement a plugin system allowing users to extend `gitscaffold` with custom logic.

### User Interface (Potential Future Direction)

Explore the possibility of a graphical user interface for roadmap management.  
**Milestone:** Post v1.0 Enhancements  
**Labels:** ui, future-scope

#### Research UI options and design mockups

Investigate suitable UI frameworks and create initial design mockups.

#### Develop a prototype UI

Implement a minimal viable product for the UI, focusing on roadmap visualization and basic editing capabilities.

### Code Refactoring and Maintainability (Ongoing)

Continuously improve the codebase for clarity, efficiency, and ease of maintenance.  
**Milestone:** Post v1.0 Enhancements  
**Labels:** refactor, quality, technical-debt

#### Refactor `scripts/` functionalities into core CLI

Systematically integrate logic from standalone scripts into `scaffold/cli.py`.

#### Consolidate entry points

Review the two main CLI entry points and merge or clarify their roles.

#### Improve error handling and user feedback

Enhance error reporting with more specific, user-friendly messages.

#### Enforce strict code style and linting

Maintain high code quality by applying linters (Ruff, Black) and type checking (Mypy) in CI.

# GitScaffold Project Roadmap

A tool to manage GitHub projects using declarative roadmap files, with AI-powered issue enrichment and creation.

## Milestones

| Milestone                        | Due Date    |
|----------------------------------|-------------|
| v0.1 Foundation (CLI & Basic Parsing)   | 2025-08-01  |
| v0.2 GitHub Integration                | 2025-09-01  |
| v0.3 AI Features (Extraction & Enrichment) | 2025-10-01  |
| v0.4 Advanced Features & Usability         | 2025-11-01  |
| v1.0 Stable Release                       | 2025-12-01  |
| Post v1.0 Enhancements (Ongoing)          | 2026-01-01  |

## Features

### Core CLI Framework
- **Description:** Setup basic CLI structure and command handling for gitscaffold.
- **Milestone:** v0.1 Foundation (CLI & Basic Parsing)
- **Labels:** core, cli

**Tasks:**
- Implement main CLI group using Click
  - Establish entry point and command structure using Click (`scaffold/cli.py`, `gitscaffold.py`)
  - Tests:
    - Verify CLI invocation (`gitscaffold --help`)
    - Test version option (`gitscaffold --version`)
    - Ensure all top-level commands are listed in help output
- Implement `init` command
  - Develop command to generate a template roadmap file (`gitscaffold.py::init`)
  - Tests:
    - Confirm file creation
    - Validate content against template
    - Test behavior when file exists

### Roadmap Parsing and Validation
- **Description:** Parse roadmap files (Markdown) and validate structure/content.
- **Milestone:** v0.1 Foundation (CLI & Basic Parsing)
- **Labels:** core, parser, validator

**Tasks:**
- Implement Markdown/YAML parser for roadmap
  - Parsing functions for both formats (`scaffold/parser.py::parse_roadmap`, `parse_markdown`)
  - Tests:
    - Parse valid Markdown
    - Extract project fields
    - Handle malformed files
- Implement Pydantic models for validation
  - Define models for Roadmap, Milestone, Feature, Task (`scaffold/validator.py`)
  - Tests:
    - Validate correct/incorrect data
    - Test required fields and due_date format
    - Ensure milestone references are valid
    - Test `check_milestone_refs` root validator

### GitHub Integration
- **Description:** Interact with GitHub API for milestones and issues.
- **Milestone:** v0.2 GitHub Integration
- **Labels:** core, github

**Tasks:**
- Implement GitHub client wrapper
  - Encapsulate PyGitHub calls (`scaffold/github.py::GitHubClient`)
  - Tests:
    - Mock API: client init, create_milestone, create_issue, find logic, error handling
- Implement `create` command
  - Process roadmap file and create milestones/issues (`scaffold/cli.py::create`)
  - Tests:
    - Dry run and actual run
    - Verify creation of milestones/issues
    - Check assignees, labels, milestones
- Implement `setup` command
  - Initialize repo with labels/milestones (`gitscaffold.py::setup`, `scripts/github_setup.py`)
  - Tests:
    - Mock API: label/milestone creation
    - Idempotency
- Implement `delete-closed` command
  - Delete closed issues (`gitscaffold.py::delete-closed`)
  - Tests:
    - Dry run, actual deletion, method options

### AI-Powered Features
- **Description:** Integrate AI/LLM for issue extraction and enrichment.
- **Milestone:** v0.3 AI Features (Extraction & Enrichment)
- **Labels:** ai, enhancement

**Tasks:**
- Implement API key management for AI (`scaffold/ai.py::_get_api_key`)
  - Tests: retrieval, error handling
- Implement issue extraction from Markdown (`scaffold/ai.py::extract_issues_from_markdown`)
  - Tests: mock LLM API, structure, config
- Implement issue description enrichment (`scaffold/ai.py::enrich_issue_description`)
  - Tests: mock LLM API, context variations
- Integrate AI extraction/enrichment into `create` command (`scaffold/cli.py::create`)
  - Tests: mock LLM & GitHub, verify processing
- Implement `enrich` command (`gitscaffold.py::enrich`, `scripts/enrich.py`)
  - Tests: mock LLM/GitHub, batch, interactive, apply changes

### Testing Framework and Coverage
- **Description:** Comprehensive testing suite.
- **Milestone:** v0.4 Advanced Features & Usability
- **Labels:** testing, quality

**Tasks:**
- Setup Pytest environment and fixtures
  - Tests: pytest runs, fixtures, mock clients
- Develop unit/integration tests for all modules (`scaffold/parser.py`, `scaffold/validator.py`, `scaffold/github.py`, `scaffold/ai.py`)
  - Tests: valid/invalid inputs, error handling, coverage
- Develop integration tests for CLI commands
  - Tests: end-to-end with mocked services
- Achieve and maintain target test coverage (85%+)
  - Tests: coverage reporting in CI
- Implement tests for `scripts/import_md.py`
  - Tests: LLM/GitHub mocking, dry-run, parsing

### Documentation
- **Description:** Comprehensive user and developer documentation.
- **Milestone:** v0.4 Advanced Features & Usability
- **Labels:** documentation

**Tasks:**
- Write comprehensive `README.md`
  - Tests: peer review, install instructions
- Document roadmap file format
  - Tests: review against models, valid examples
- Document all CLI commands and options
  - Tests: help output matches docs
- Create example roadmap files
  - Tests: validate with CLI
- Write developer documentation
  - Tests: onboarding by new developer

### CI/CD and Release Management
- **Description:** Automate testing, building, and publishing.
- **Milestone:** v1.0 Stable Release
- **Labels:** ci-cd, release

**Tasks:**
- Setup GitHub Actions for CI
  - Tests: workflow triggers, tests/linters
- Automate PyPI publishing on release
  - Tests: TestPyPI, official PyPI
- Automate GitHub Releases creation
  - Tests: tag triggers, release notes
- Standardize versioning strategy
  - Tests: version consistency, CI checks
- Test and maintain GitHub Action
  - Tests: example workflows, Dockerfile maintenance

### Advanced Roadmap Features (Post v1.0)
- **Description:** Sophisticated roadmap management features.
- **Milestone:** Post v1.0 Enhancements
- **Labels:** enhancement, roadmap

**Tasks:**
- Support for task dependencies
  - Tests: parsing, validation, creation order/linking
- Support for GitHub issue templates
  - Tests: template parsing, API verification
- Roadmap diffing and updating ("sync" command)
  - Tests: diff logic, prompts, apply flag
- Option for sub-tasks as checklist items
  - Tests: configuration, Markdown generation

### Extensibility and Configuration (Post v1.0)
- **Description:** Configuration and plugin architecture.
- **Milestone:** Post v1.0 Enhancements
- **Labels:** enhancement, configuration, extensibility

**Tasks:**
- Global and project-level configuration file
  - Tests: loading, precedence
- Basic plugin system
  - Tests: discovery, example plugin

### User Interface (Potential Future Direction)
- **Description:** Graphical UI exploration.
- **Milestone:** Post v1.0 Enhancements
- **Labels:** ui, future-scope

**Tasks:**
- Research UI options and design mockups
  - Tests: user feedback
- Develop a prototype UI
  - Tests: core functionality

### Code Refactoring and Maintainability (Ongoing)
- **Description:** Ongoing code quality improvements.
- **Milestone:** Post v1.0 Enhancements (Ongoing)
- **Labels:** refactor, quality, technical-debt

**Tasks:**
- Refactor `scripts/` functionalities into core CLI
  - Tests: functionality preserved, tests updated
- Consolidate entry points (`gitscaffold.py`, `scaffold/cli.py`)
  - Tests: command functionality, consistent behavior
- Improve error handling and user feedback
  - Tests: failure scenarios, error output
- Enforce strict code style and linting
  - Tests: CI pipeline for linting/type checking

This roadmap provides a structured, test-driven plan for developing, releasing, and maintaining the GitScaffold tool, with a strong focus on extensibility, automation, and user experience.