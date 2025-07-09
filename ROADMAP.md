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

### Milestones

Refer to the roadmap milestones defined above.

### Features

Main feature list to plan issue creation.

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

```yaml
name: GitScaffold Project Roadmap
description: A tool to manage GitHub projects using declarative roadmap files, with AI-powered issue enrichment and creation.

milestones:
  - name: v0.1 Foundation (CLI & Basic Parsing)
    due_date: 2025-08-01
  - name: v0.2 GitHub Integration
    due_date: 2025-09-01
  - name: v0.3 AI Features (Extraction & Enrichment)
    due_date: 2025-10-01
  - name: v0.4 Advanced Features & Usability
    due_date: 2025-11-01
  - name: v1.0 Stable Release
    due_date: 2025-12-01
  - name: Post v1.0 Enhancements
    due_date: 2026-01-01 # Ongoing

features:
  - title: Core CLI Framework
    description: Setup basic CLI structure and command handling for gitscaffold.
    milestone: v0.1 Foundation (CLI & Basic Parsing)
    labels: [core, cli]
    assignees: []
    tasks:
      - title: Implement main CLI group using Click
        description: Establish the main entry point and command structure for the CLI using the Click library. This will be based on `scaffold/cli.py` and `gitscaffold.py`.
        labels: [implementation]
        tests:
          - Verify basic CLI invocation (`gitscaffold --help`).
          - Test that the version option (`gitscaffold --version`) displays correctly.
          - Ensure all top-level commands are listed in help output.
      - title: Implement `init` command
        description: Develop the `init` command to generate a template roadmap file. This is based on the functionality in `gitscaffold.py::init`.
        labels: [implementation, cli]
        tests:
          - Confirm `gitscaffold init <filename>` creates a new file.
          - Validate the content of the generated file against a predefined template structure.
          - Test behavior when the output file already exists.

  - title: Roadmap Parsing and Validation
    description: Implement logic to parse roadmap files (YAML/Markdown) and validate their structure and content.
    milestone: v0.1 Foundation (CLI & Basic Parsing)
    labels: [core, parser, validator]
    assignees: []
    tasks:
      - title: Implement Markdown/YAML parser for roadmap
        description: Create parsing functions for roadmap files, supporting both Markdown and YAML formats. Based on `scaffold/parser.py::parse_roadmap` and `parse_markdown`.
        labels: [implementation, parser]
        tests:
          - Test parsing of a valid YAML roadmap file.
          - Test parsing of a valid Markdown roadmap file (if syntax differs).
          - Verify correct extraction of project name, description, milestones, features, and tasks.
          - Test error handling for malformed roadmap files (syntax errors, incorrect types).
      - title: Implement Pydantic models for validation
        description: Define Pydantic models for roadmap elements (Roadmap, Milestone, Feature, Task) to ensure data integrity. Based on `scaffold/validator.py`.
        labels: [implementation, validator]
        tests:
          - Validate a correctly structured roadmap data object.
          - Test validation failure for missing required fields (e.g., `name` in Roadmap, `title` in Feature).
          - Test validation of `due_date` formats for milestones.
          - Verify that `milestone` references in features/tasks point to defined milestones.
          - Test `check_milestone_refs` root validator specifically.

  - title: GitHub Integration
    description: Develop functionality to interact with the GitHub API for creating and managing milestones and issues.
    milestone: v0.2 GitHub Integration
    labels: [core, github]
    assignees: []
    tasks:
      - title: Implement GitHub client wrapper
        description: Create a robust client for GitHub API interactions, encapsulating PyGitHub calls. Based on `scaffold/github.py::GitHubClient`.
        labels: [implementation, api-integration]
        tests:
          - Mock GitHub API: Test client initialization with a token.
          - Mock GitHub API: Test `create_milestone` for new and existing milestones.
          - Mock GitHub API: Test `create_issue` with all parameters (title, body, assignees, labels, milestone).
          - Mock GitHub API: Test `_find_milestone` and `_find_issue` logic.
          - Mock GitHub API: Test error handling for common API errors (401, 403, 404, 422).
      - title: Implement `create` command
        description: Build the `create` command to process a roadmap file and create corresponding milestones and issues on GitHub. Based on `scaffold/cli.py::create`.
        labels: [implementation, cli]
        tests:
          - Test `gitscaffold create --dry-run` to ensure no actual API calls are made and output is as expected.
          - Mock GitHub API: Test `gitscaffold create` (actual run) for full roadmap processing.
          - Verify correct creation of milestones.
          - Verify correct creation of issues for features (and tasks, if applicable).
          - Check that assignees, labels, and milestones are correctly set on created issues.
      - title: Implement `setup` command (from gitscaffold.py)
        description: Port and integrate the `setup` command functionality for initializing a repository with predefined labels and milestones. Based on `gitscaffold.py::setup` and `scripts/github_setup.py`.
        labels: [implementation, cli, github]
        tests:
          - Mock GitHub API: Test `gitscaffold setup` creates all predefined labels from `scripts/github_setup.py::RECOMMENDED_LABELS`.
          - Mock GitHub API: Test `gitscaffold setup` creates all predefined milestones from `scripts/github_setup.py::MILESTONES`.
          - Test idempotency: running `setup` multiple times should not create duplicate labels/milestones.
      - title: Implement `delete-closed` command (from gitscaffold.py)
        description: Port and integrate the `delete-closed` command. Based on `gitscaffold.py::delete-closed`.
        labels: [implementation, cli, github]
        tests:
          - Test `gitscaffold delete-closed --dry-run`.
          - Mock GitHub API: Test `gitscaffold delete-closed` actually attempts to delete closed issues.
          - Test any specific `method` options if applicable.

  - title: AI-Powered Features
    description: Integrate AI/LLM capabilities for extracting issues from Markdown and enriching issue descriptions.
    milestone: v0.3 AI Features (Extraction & Enrichment)
    labels: [ai, enhancement]
    assignees: []
    tasks:
      - title: Implement API key management for AI
        description: Securely retrieve and manage API keys for AI services. Based on `scaffold/ai.py::_get_api_key`.
        labels: [implementation, security]
        tests:
          - Test successful API key retrieval from an environment variable.
          - Test graceful failure or clear error message if the API key is not found.
      - title: Implement issue extraction from Markdown
        description: Use an LLM to parse unstructured Markdown and extract potential issues. Based on `scaffold/ai.py::extract_issues_from_markdown`.
        labels: [implementation, ai]
        tests:
          - Mock LLM API: Test with a sample Markdown input containing identifiable issues.
          - Mock LLM API: Test with Markdown input that contains no clear issues.
          - Verify the structure of the extracted issues.
          - Test configurability of model and temperature parameters.
      - title: Implement issue description enrichment
        description: Use an LLM to enhance or generate issue descriptions based on a title and context. Based on `scaffold/ai.py::enrich_issue_description`.
        labels: [implementation, ai]
        tests:
          - Mock LLM API: Test with a simple title and empty existing body.
          - Mock LLM API: Test with a title and some existing body content to be augmented.
          - Mock LLM API: Test how different `context` inputs affect the enrichment.
      - title: Integrate AI extraction into `create` command
        description: Add an `--ai-extract` option to the `create` command to use LLM-based issue extraction from a Markdown roadmap. Link to `scaffold/cli.py::create`.
        labels: [integration, cli, ai]
        tests:
          - Test `gitscaffold create --ai-extract <markdown_file.md>` (mocking LLM and GitHub).
          - Verify that issues extracted by the AI are then processed for creation on GitHub.
      - title: Integrate AI enrichment into `create` command
        description: Add an `--ai-enrich` option to the `create` command to use LLM-based description enrichment. Link to `scaffold/cli.py::create`.
        labels: [integration, cli, ai]
        tests:
          - Test `gitscaffold create --ai-enrich <roadmap_file.yml>` (mocking LLM and GitHub).
          - Verify that issue descriptions are passed through the enrichment process before GitHub creation.
      - title: Implement `enrich` command (from gitscaffold.py)
        description: Port and integrate the `enrich` command for AI-powered enrichment of issues. Based on `gitscaffold.py::enrich` and `scripts/enrich.py`.
        labels: [implementation, cli, ai]
        tests:
          - Mock LLM/GitHub: Test `gitscaffold enrich --issue-number <num>`.
          - Mock LLM/GitHub: Test `gitscaffold enrich --batch --csv-file <file.csv>`.
          - Test interactive mode prompts and responses.
          - Test the effect of `--apply-changes` vs. dry run.

  - title: Testing Framework and Coverage
    description: Establish and maintain a comprehensive testing suite for the application.
    milestone: v0.4 Advanced Features & Usability
    labels: [testing, quality]
    assignees: []
    tasks:
      - title: Setup Pytest environment and fixtures
        description: Configure Pytest with necessary plugins, and create shared fixtures (e.g., for mocking GitHub API, LLM API, temporary file paths).
        labels: [setup, testing]
        tests:
          - Confirm `pytest` runs and discovers tests correctly.
          - Verify common fixtures (e.g., `tmp_path`) are usable.
          - Create a basic `FakeRepo` or `MockGitHubClient` fixture.
      - title: Develop unit tests for parser module
        description: Write unit tests for all functions in `scaffold/parser.py`.
        labels: [testing, unit-test]
        tests:
          - Test `parse_roadmap` with various valid and invalid YAML inputs (e.g., correct structure, top-level not a mapping).
          - Test `parse_markdown` for structured Markdown: correct extraction of global description, features from H1 headings, tasks from H2 headings, and their respective descriptions.
          - Verify correct extraction of project name, description, milestones, features, and tasks for both formats.
          - Test error handling for malformed roadmap files (syntax errors, incorrect types, file not found).
      - title: Develop unit tests for validator module
        description: Write unit tests for Pydantic models and validation logic in `scaffold/validator.py`.
        labels: [testing, unit-test]
        tests:
          - Test successful validation of `Roadmap`, `Feature`, `Task`, `Milestone` objects.
          - Test validation failures for each model with incorrect data.
          - Specifically test `check_milestone_refs` and `validate_roadmap`.
      - title: Develop unit/integration tests for GitHub client
        description: Test `scaffold/github.py` thoroughly using mocked GitHub API responses. (Refers to `tests/test_github.py` for inspiration).
        labels: [testing, unit-test, integration-test]
        tests:
          - Test all public methods of `GitHubClient`.
          - Ensure all parameters and conditional logic paths are covered.
      - title: Develop unit/integration tests for AI module
        description: Test `scaffold/ai.py` using mocked LLM API responses. (Refers to `tests/test_import_md.py` for inspiration on mocking AI).
        labels: [testing, unit-test, integration-test]
        tests:
          - Test `_get_api_key` behavior.
          - Test `extract_issues_from_markdown` with various inputs and mocked AI responses.
          - Test `enrich_issue_description` similarly.
      - title: Develop integration tests for CLI commands
        description: Create end-to-end tests for each CLI command, mocking external services (GitHub, AI). Use Click's `CliRunner`.
        labels: [testing, integration-test]
        tests:
          - Test `gitscaffold init`: check exit code, file creation, content.
          - Test `gitscaffold create`: check exit code, (mocked) API calls made.
          - Test `gitscaffold setup`: check exit code, (mocked) API calls.
          - Test `gitscaffold delete-closed`: check exit code, (mocked) API calls.
          - Test `gitscaffold enrich`: check exit code, (mocked) API calls.
      - title: Achieve and maintain target test coverage
        description: Aim for a high test coverage percentage (e.g., 85%+) and integrate coverage reporting into CI.
        labels: [quality, testing]
        tests:
          - Configure `pytest-cov` or similar.
          - CI step to report coverage, potentially fail build if coverage drops.
      - title: Implement tests for `scripts/import_md.py` (if kept separate)
        description: Ensure robust tests for the Markdown import script. Based on `tests/test_import_md.py`.
        labels: [testing, script]
        tests:
          - Test LLM call mocking and response handling.
          - Test GitHub interaction mocking (issue creation).
          - Test dry-run vs. actual creation modes.
          - Test parsing of Markdown content under different headings.

  - title: Documentation
    description: Create and maintain comprehensive documentation for users and developers.
    milestone: v0.4 Advanced Features & Usability
    labels: [documentation]
    assignees: []
    tasks:
      - title: Write comprehensive `README.md`
        description: Include project overview, features, installation instructions, quick start guide, and basic usage examples.
        labels: [documentation]
        tests:
          - Peer review of README for clarity, accuracy, and completeness.
          - Verify installation instructions work.
      - title: Document roadmap file format
        description: Provide a detailed specification of the roadmap file structure (YAML/Markdown), including all fields, their types, and whether they are required or optional.
        labels: [documentation]
        tests:
          - Review documentation against the Pydantic models and parser logic.
          - Ensure examples in documentation are valid.
      - title: Document all CLI commands and options
        description: Generate or write detailed help text and usage examples for each CLI command and all its options.
        labels: [documentation]
        tests:
          - Verify that `gitscaffold <command> --help` output is clear and matches documented options.
          - Check that all options are explained.
      - title: Create example roadmap files
        description: Develop a diverse set of example roadmap files showcasing different features and use cases. This should include examples for structured YAML, structured Markdown (similar to `docs/example_roadmap.md` and `gitscaffold init` output), and unstructured Markdown suitable for AI extraction (`import-md` command).
        labels: [documentation, example]
        tests:
          - Validate all structured example roadmaps using `gitscaffold create --dry-run`.
          - Process unstructured Markdown examples with `gitscaffold import-md --dry-run`.
      - title: Write developer documentation
        description: Include information on project structure, development setup, contribution guidelines, how to run tests, and coding conventions.
        labels: [documentation, contributing]
        tests:
          - Have a new developer try to set up the project using this documentation.

  - title: CI/CD and Release Management
    description: Automate testing, building, and publishing of the `gitscaffold` package.
    milestone: v1.0 Stable Release
    labels: [ci-cd, release]
    assignees: []
    tasks:
      - title: Setup GitHub Actions for CI
        description: Configure workflows to run linters (e.g., Ruff, Black) and execute the test suite on every push and pull request. (Partially exists with `pypi-publish.yml`, `release.yml`).
        labels: [ci, automation]
        tests:
          - Verify CI workflow triggers correctly.
          - Confirm tests and linters run and pass in CI.
      - title: Automate PyPI publishing on release
        description: Enhance or confirm GitHub Actions workflow (`.github/workflows/pypi-publish.yml`) to build and publish the package to PyPI when a new release is tagged.
        labels: [release, automation, pypi]
        tests:
          - Test publishing to TestPyPI first.
          - Verify successful publishing to official PyPI on a real release.
      - title: Automate GitHub Releases creation
        description: Enhance or confirm GitHub Actions workflow (`.github/workflows/release.yml`) to automatically create GitHub releases, potentially with generated changelogs.
        labels: [release, automation, github]
        tests:
          - Test that a new tag triggers the release creation.
          - Verify release notes are generated or attached correctly.
      - title: Standardize versioning strategy
        description: Ensure consistent version management using `scaffold/__init__.py::__version__` (and `pyproject.toml`) and potentially tools like `bumpversion` or `poetry version`.
        labels: [release, versioning]
        tests:
          - Ensure `gitscaffold --version` reflects the correct version from `scaffold/__init__.py`.
          - CI check to ensure version is updated consistently in PRs for release.
      - title: Test and Maintain GitHub Action
        description: Ensure the GitHub Action defined in `action.yml` is well-tested and maintained. This includes testing its inputs (`roadmap-file`, `repo`, `github-token`, `dry-run`, `openai-key`, `apply`) and overall functionality.
        labels: [ci, github-action, testing]
        tests:
          - Create example workflows that use the action with different input combinations.
          - Test the `--apply` input specifically for markdown imports.
          - Verify the action runs correctly with various roadmap file types.
          - Ensure the action's Docker environment (`Dockerfile`) is kept up-to-date.

  - title: Advanced Roadmap Features (Post v1.0)
    description: Introduce more sophisticated features for roadmap management.
    milestone: Post v1.0 Enhancements
    labels: [enhancement, roadmap]
    assignees: []
    tasks:
      - title: Support for task dependencies
        description: Allow tasks within a roadmap to declare dependencies on other tasks (e.g., "Task B depends on Task A").
        labels: [feature, roadmap-v2]
        tests:
          - Test parsing of new dependency syntax in roadmap files.
          - Test validation logic (e.g., prevent circular dependencies).
          - Test that issue creation order or linking (e.g., "blocks" relationship) reflects dependencies.
      - title: Support for GitHub issue templates
        description: Allow users to specify project-defined GitHub issue templates to be used when creating issues from features or tasks.
        labels: [feature, github-integration]
        tests:
          - Test parsing of template references in the roadmap.
          - Mock GitHub API: Verify that the correct template is referenced during issue creation.
      - title: Roadmap diffing and updating ("sync" command)
        description: Implement a command to compare the current state of GitHub issues/milestones with the roadmap file and report differences or apply updates.
        labels: [feature, cli, github-sync]
        tests:
          - Test diffing logic: new items in roadmap, items closed on GitHub but open in roadmap, changed titles/descriptions.
          - Test interactive prompts for applying updates.
          - Test `--apply` flag for automatic updates.
      - title: Option for sub-tasks as checklist items
        description: Provide an option (e.g., per feature or globally) to create tasks as checklist items within the body of their parent feature's issue, rather than separate issues.
        labels: [feature, github-integration, usability]
        tests:
          - Test configuration of this feature.
          - Verify correct Markdown generation for checklists in issue bodies.

  - title: Extensibility and Configuration (Post v1.0)
    description: Enhance the tool's flexibility through better configuration and a plugin architecture.
    milestone: Post v1.0 Enhancements
    labels: [enhancement, configuration, extensibility]
    assignees: []
    tasks:
      - title: Global and project-level configuration file
        description: Allow users to define default settings (e.g., GitHub repository, token path, default AI model, common labels) in a configuration file (`~/.gitscaffold/config.yml` or `.gitscaffold.yml` in project).
        labels: [feature, usability, configuration]
        tests:
          - Test loading of settings from global and project config files.
          - Test precedence (CLI options > project config > global config).
      - title: Basic plugin system
        description: Design and implement a plugin system allowing users to extend `gitscaffold` with custom logic (e.g., new roadmap formats, custom actions after issue creation).
        labels: [feature, extensibility, architecture]
        tests:
          - Test plugin discovery and loading mechanisms.
          - Create a simple example plugin and test its hook execution.

  - title: User Interface (Potential Future Direction)
    description: Explore the possibility of a graphical user interface for roadmap management.
    milestone: Post v1.0 Enhancements
    labels: [ui, future-scope]
    assignees: []
    tasks:
      - title: Research UI options and design mockups
        description: Investigate suitable UI frameworks (e.g., Streamlit, TUI with Textual, web app with Flask/FastAPI + Svelte/React) and create initial design mockups.
        labels: [design, research, ui]
        tests:
          - Gather user feedback on proposed UI concepts and mockups.
      - title: Develop a prototype UI
        description: Implement a minimal viable product for the UI, focusing on roadmap visualization and basic editing capabilities.
        labels: [implementation, ui, prototype]
        tests:
          - Test core UI functionality: loading, displaying, and modifying a simple roadmap.

  - title: Code Refactoring and Maintainability (Ongoing)
    description: Continuously improve the codebase for clarity, efficiency, and ease of maintenance.
    milestone: Post v1.0 Enhancements # Or as an ongoing activity across all milestones
    labels: [refactor, quality, technical-debt]
    assignees: []
    tasks:
      - title: Refactor `scripts/` functionalities into core CLI
        description: Systematically integrate the logic from standalone scripts (`scripts/github_setup.py`, `scripts/enrich.py`, `scripts/import_md.py`) into the main `scaffold/cli.py` as subcommands or options.
        labels: [refactor, cli, architecture]
        tests:
          - Ensure all original functionalities are preserved and accessible via the main CLI.
          - Update all relevant tests to reflect new command structures.
      - title: Consolidate `gitscaffold.py` and `scaffold/cli.py` entry points
        description: Review the two main CLI entry points (`gitscaffold.py` at root and `scaffold/cli.py`). If redundant, merge them into a single, clear entry point. Otherwise, clarify their distinct roles.
        labels: [refactor, cli, architecture]
        tests:
          - Verify all commands remain functional after refactoring.
          - Ensure `python -m scaffold` and the installed `gitscaffold` script behave consistently.
      - title: Improve error handling and user feedback
        description: Enhance error reporting with more specific, user-friendly messages and suggestions for resolving common issues.
        labels: [usability, quality, error-handling]
        tests:
          - Test various failure scenarios (e.g., invalid file paths, API errors, validation errors) and check error output.
      - title: Enforce strict code style and linting
        description: Maintain high code quality by consistently applying linters (Ruff, Black) and type checking (Mypy) in CI.
        labels: [quality, tooling, ci]
        tests:
          - CI pipeline includes steps for linting and type checking, failing the build on errors.
```
