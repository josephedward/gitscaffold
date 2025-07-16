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
- Implement `sync` command
  - Process roadmap file and create milestones/issues (`scaffold/cli.py::sync`)
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
- Integrate AI extraction/enrichment into `sync` command (`scaffold/cli.py::sync`)
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

- Rename generic GitHub Action workflow file
  - Move `.github/workflows/action.yml` to `.github/workflows/setup.yml` and update its `name` field for clarity.
  - Tests: Verify manual dispatch (`workflow_dispatch`) works; confirm updated workflow name in Actions UI.

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
