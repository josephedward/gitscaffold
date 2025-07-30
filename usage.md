# `gitscaffold` Usage Guide

`gitscaffold` helps manage software projects by keeping a local roadmap file in sync with GitHub issues. This guide outlines a typical workflow, including the new AI-first features for handling unstructured Markdown files.

## 1. Setup

First, you need to set up your environment and project.

### Environment Setup

1.  **GitHub Token:** `gitscaffold` needs a GitHub personal access token to interact with the API. You can create one from your GitHub developer settings with `repo` scope.
2.  **OpenAI API Key:** For AI-powered features, you'll need an OpenAI API key.

You can set these in a `.env` file in your project root, or as environment variables:

```bash
# As environment variables
export GITHUB_TOKEN="your_token_here"
export OPENAI_API_KEY="your_key_here"
```

Or in a `.env` file (which should be in your `.gitignore`):

```dotenv
GITHUB_TOKEN="your_token_here"
OPENAI_API_KEY="your_key_here"
```

If a key is missing, `gitscaffold` will prompt you for it and offer to save it to your `.env` file.

### Project Initialization

In your project's root directory, run:
```bash
gitscaffold setup
```
This command creates a structured `ROADMAP.md` file with a basic template, which is a great starting point.

## 2. The Roadmap File

You can use two types of roadmaps:

### Structured `ROADMAP.md`

This is the standard, machine-readable format. It uses `##` for milestones, `###` for features, and `- [ ]` for tasks. The `gitscaffold setup` command creates a file like this.

Example `ROADMAP.md`:
```markdown
# Test Project

## M1: Foundation
- [ ] Task 1: Set up project structure

### Feature A: Core Auth
- [ ] Sub-task A1
```

### Unstructured Markdown File

You can also use any free-form Markdown file (e.g., meeting notes, a design doc). `gitscaffold` will use AI to automatically extract tasks and features.

## 3. The Standard Workflow

### Step 1: Sync Your Roadmap with GitHub

The `sync` command creates GitHub issues and milestones from your roadmap.

```bash
# For a structured ROADMAP.md
gitscaffold sync ROADMAP.md --repo your_org/your_repo

# For an unstructured doc, e.g., docs/plan.md
gitscaffold sync docs/plan.md --repo your_org/your_repo
```

**AI-First Behavior**: If you use an unstructured Markdown file, `gitscaffold` will detect it and ask if you want to use AI to extract issues.
```
Warning: Roadmap appears to be empty or unstructured.
Would you like to use AI to extract issues from it? [Y/n]: y
```
- To **disable** this automatic AI behavior, use the `--no-ai` flag.
- To **force** AI extraction without prompt, use the `--ai` flag.
- To **enrich** issue descriptions with AI-generated content (for any roadmap type), use the `--ai-enrich` flag.

### Step 2: Check for Differences

Use the `diff` command to see what's different between your local roadmap and GitHub.

```bash
gitscaffold diff ROADMAP.md --repo your_org/your_repo
```

Like `sync`, `diff` will also automatically prompt for AI extraction when it detects an unstructured Markdown file:

- Use `--no-ai` to disable this automatic AI behavior.
- To specify your OpenAI API key directly (instead of environment or .env), use the `--openai-key` option.

### Step 3: See What's Next

To get a quick summary of current priorities, use the `next` command:
```bash
gitscaffold next --repo your_org/your_repo
```
This shows the active milestone and its open, unassigned issues.

## 4. Maintenance Commands

`gitscaffold` provides several commands to keep your repository clean:

- `gitscaffold delete-closed`: Deletes all closed issues.
- `gitscaffold sanitize`: Removes markdown formatting from issue titles.
- `gitscaffold deduplicate`: Finds and closes duplicate open issues.

Run any command with `--dry-run` to preview changes without applying them.

## 5. Testing

You can run the full test suite to ensure everything is working correctly:
```bash
pytest
```

There is also an end-to-end workflow test script:
```bash
# Set environment variables first
export GITHUB_TOKEN="..."
export TEST_REPO="your/test-repo"

./scripts/test_workflow.sh
```
This script validates the complete user journey described in this guide.

For more details on any command, run `gitscaffold <command> --help`.
