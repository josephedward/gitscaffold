<!-- Auto-generated markdown roadmap based on ROADMAP.yml -->
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

Develop the `init` command to generate a template roadmap file. This is based on the functionality in `gitscaffold.py::init`.

### Roadmap Parsing and Validation

Implement logic to parse roadmap files (YAML/Markdown) and validate their structure and content.  
**Milestone:** v0.1 Foundation (CLI & Basic Parsing)  
**Labels:** core, parser, validator

#### Implement Markdown/YAML parser for roadmap

Create parsing functions for roadmap files, supporting both Markdown and YAML formats. Based on `scaffold/parser.py::parse_roadmap` and `parse_markdown`.

#### Implement Pydantic models for validation

Define Pydantic models for roadmap elements (Roadmap, Milestone, Feature, Task) to ensure data integrity. Based on `scaffold/validator.py`.

### GitHub Integration

Develop functionality to interact with the GitHub API for creating and managing milestones and issues.  
**Milestone:** v0.2 GitHub Integration  
**Labels:** core, github

#### Implement GitHub client wrapper

Create a robust client for GitHub API interactions, encapsulating PyGitHub calls. Based on `scaffold/github.py::GitHubClient`.

#### Implement `create` command

Build the `create` command to process a roadmap file and create corresponding milestones and issues on GitHub. Based on `scaffold/cli.py::create`.

#### Implement `setup-repository` command

Create a new GitHub repository from a roadmap file and populate it with issues. Based on `scaffold/cli.py::setup_repository`.

#### Implement `delete-closed` command

Port and integrate the `delete-closed` command. Based on `gitscaffold.py::delete-closed`.

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

#### Implement `import-md` command

Port and integrate the `import-md` command for importing issues from an unstructured Markdown file, using AI to generate titles and descriptions. Based on `scaffold/cli.py::import_md_command`.

#### Implement `enrich` command

Port and integrate the `enrich` command for AI-powered enrichment of issues. Based on `gitscaffold.py::enrich` and `scripts/enrich.py`.

### Workflow and Productivity Features

Add commands to help users identify and focus on their next tasks.  
**Milestone:** v0.4 Advanced Features & Usability  
**Labels:** usability, cli

#### Implement `next` command

Create a `next` command to show next action items from the earliest active milestone. Based on `scaffold/cli.py::next_command`.

#### Implement `next-task` command

Create a `next-task` command to show the next open task for the current roadmap phase. Based on `scaffold/cli.py::next_task`.

#### Enhance `diff` command

Enhance the `diff` command to include issue numbers and state in its output, and allow filtering by issue state.

#### Implement `deduplicate-issues` command

Create a `deduplicate-issues` command to find and close duplicate open issues. Based on `scaffold/cli.py::deduplicate_issues_command`.

#### Implement `cleanup-issue-titles` command

Create a `cleanup-issue-titles` command to sanitize issue titles by removing leading markdown characters. Based on `scaffold/cli.py::cleanup_issue_titles_command`.

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

Provide a detailed specification of the roadmap file structure (YAML/Markdown).

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

Allow users to define default settings in a configuration file (`~/.gitscaffold/config.yml` or `.gitscaffold.yml`).

#### Basic plugin system

Design and implement a plugin system allowing users to extend `gitscaffold` with custom logic.

### User Interface (Potential Future Direction)

Explore the possibility of a graphical user interface for roadmap management.  
**Milestone:** Post v1.0 Enhancements  
**Labels:** ui, future-scope

#### Research UI options and design mockups

Investigate suitable UI frameworks and create initial design mockups.

#### Develop a prototype UI

Implement a minimal viable product for the UI, focusing on roadmap visualization and basic editing.

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