 # Usage Guide for Gitscaffold

 ## Overview

 Gitscaffold is a CLI tool to manage GitHub issues and milestones from structured or unstructured roadmaps. This document describes an ideal end-to-end workflow:

 1. Define your roadmap (features, tasks, milestones).
 2. Sync your roadmap with GitHub (create/update issues & milestones).
 3. Add new tasks or features to your roadmap.
 4. Resync to reflect changes.
 5. Use diff & next commands to review and navigate your work.
 6. Cleanup, sanitize, and deduplicate as needed.
 7. Run tests to ensure everything is working.

 ## Prerequisites

 - Install gitscaffold:

   ```sh
   pip install -e .
   ```

 - Configure environment variables for authentication:

   ```sh
   export GITHUB_TOKEN="your_github_token"
   export OPENAI_API_KEY="your_openai_api_key"
   ```

 - Ensure a `.env` file is in your `.gitignore` if you store tokens locally:

   ```text
   GITHUB_TOKEN=your_github_token
   OPENAI_API_KEY=your_openai_api_key
   ```

 ## 1. Create or Update Your Roadmap

 ### JSON-based Roadmap

 Create a `roadmap.json` file with content like:

 ```json
 {
   "name": "Test Project Sync",
   "description": "A test project for sync functionality.",
   "milestones": [
     {"name": "M1: Setup", "due_date": "2025-01-01"}
   ],
   "features": [
     {
       "title": "Feature A: Core Logic",
       "description": "Implement the core logic.",
       "milestone": "M1: Setup",
       "labels": ["enhancement","core"],
       "tasks": [
         {"title":"Task A.1: Design","description":"Design the core logic.","labels":["design"]},
         {"title":"Task A.2: Implement","description":"Implement the core logic.","labels":["implementation"]}
       ]
     }
   ]
 }
 ```

 ### Markdown-based Roadmap

 Alternatively, use unstructured Markdown with AI extraction, e.g., `demo/example_roadmap.md`:

 ```markdown
 # DemoProject

 Quick smoke test

 ## MVP (2099-12-31)

 ### Hello World

 Just a test
 ```

 To import Markdown, use:

 ```sh
 gitscaffold import-md YOUR_REPO demo/example_roadmap.md --heading-level 1
 ```

 ## 2. Initial Sync

 Run the `sync` command to compare your roadmap with GitHub and create missing milestones and issues:

 ```sh
 gitscaffold sync roadmap.json --repo owner/repo
 ```

 You'll be prompted to confirm before creating any items.

 ## 3. Add New Tasks or Features

 Edit `roadmap.json` or your Markdown file to add new features or tasks. For example:

 - In `roadmap.json`, add another feature under `"features"`.
 - In Markdown, add another heading or list item.

 Save your file.

 ## 4. Resync

 Run `sync` again:

 ```sh
 gitscaffold sync roadmap.json --repo owner/repo
 ```

 Gitscaffold will detect new items and prompt to create them.

 ## 5. Preview Changes with Dry Run & Diff

 - Dry run without creating:

   ```sh
   gitscaffold sync roadmap.json --repo owner/repo --dry-run
   ```

 - Compare local roadmap vs GitHub issues:

   ```sh
   gitscaffold diff roadmap.json --repo owner/repo
   ```

 AI-powered extraction is automatic for Markdown files. Use `--no-ai` to disable AI fallback.

 ## 6. Navigate Your Work

 - Show next action items:

   ```sh
   gitscaffold next --repo owner/repo
   ```

 - Show next task:

   ```sh
   gitscaffold next-task roadmap.json --repo owner/repo
   ```

 ## 7. Cleanup & Maintenance

 - Delete closed issues:

   ```sh
   gitscaffold delete-closed --repo owner/repo
   ```

 - Sanitize titles:

   ```sh
   gitscaffold sanitize --repo owner/repo --dry-run
   ```

 - Deduplicate issues:

   ```sh
   gitscaffold deduplicate --repo owner/repo
   ```

 ## 8. Testing the Workflow

 Run tests to verify functionality:

 ```sh
 pytest tests/test_cli_sync.py
 pytest tests/test_cli_diff.py
 pytest tests/test_cli_next.py
 ```

 Ensure all tests pass to confirm the workflow is functional.

 ## 9. Continuous Integration

 Use `scripts/audit.sh` to run a sequence of commands:

 ```sh
 bash scripts/audit.sh
 ```

 Integrate into GitHub Actions or other CI pipelines as needed.

`gitscaffold` helps manage software projects by keeping a local `ROADMAP.md` file in sync with GitHub issues. This guide outlines a typical workflow.

## 1. Setup

First, you need to set up your environment and project.

### Environment Setup

1.  **GitHub Token:** `gitscaffold` needs a GitHub personal access token to interact with the API. You can create one from your GitHub developer settings. It needs `repo` scope.
    You can set it as an environment variable:
    ```bash
    export GITHUB_TOKEN="your_token_here"
    ```
    `gitscaffold` will automatically pick it up.

2.  **(Optional) OpenAI API Key:** For AI-powered features like `enrich` or `import-md`, you'll need an OpenAI API key, which can be set as `OPENAI_API_KEY`.

### Project Initialization

In your project's root directory, run:
```bash
gitscaffold setup
```
This command creates a `ROADMAP.md` file with a basic template.

## 2. The `ROADMAP.md` File

`ROADMAP.md` is a markdown file where you define your project's structure. It consists of:

*   **Milestones:** High-level goals, often with due dates. Represented by `##` headers.
*   **Features:** Collections of tasks. Represented by `###` headers.
*   **Tasks:** Individual work items. Represented by markdown checklist items `- [ ]`.

Here is an example `ROADMAP.md`:

```markdown
# Test Project

This is a test project roadmap.

## M1: Foundation

- [ ] Task 1: Set up project structure
- [ ] Task 2: Initial dependencies

### Feature A: Core Auth

- [ ] Sub-task A1
- [ ] Sub-task A2

## M2: API

- [ ] Task 3: Define API endpoints

### Feature B: User Profiles

- [ ] Sub-task B1
```

## 3. Standard Workflow

Here's how you can use `gitscaffold` in your day-to-day development.

### Step 1: Define Work in `ROADMAP.md`

Before starting a new feature or a batch of work, open `ROADMAP.md` and add your milestones, features, and tasks. For example, you might add a new feature to the "M2: API" milestone:

```markdown
## M2: API

- [ ] Task 3: Define API endpoints

### Feature B: User Profiles

- [ ] Sub-task B1

### Feature C: Payments

- [ ] Integrate Stripe
- [ ] Add payment endpoint
```

### Step 2: Sync Roadmap to GitHub

Once you've updated your roadmap, sync it with your GitHub repository to create issues.

```bash
gitscaffold sync --repo your_org/your_repo
```

This command will:
*   Parse your `ROADMAP.md`.
*   Create GitHub milestones for any `##` headers that don't exist.
*   Create GitHub issues for each task (`- [ ]`) that doesn't already exist.
*   Issues are automatically labeled with their feature (`Feature C: Payments`) and assigned to the correct milestone (`M2: API`).

Run with `--dry-run` first to see what changes will be made without actually making them.

### Step 3: Check for Differences

At any time, you can see the differences between your local `ROADMAP.md` and the state of your GitHub issues.

```bash
gitscaffold diff --repo your_org/your_repo
```

This is useful for seeing:
*   Tasks in `ROADMAP.md` that haven't been created as issues yet.
*   Issues on GitHub that are not (or no longer) in `ROADMAP.md`.

### Step 4: See What's Next

To get a quick summary of the current priorities, use the `next` command:

```bash
gitscaffold next --repo your_org/your_repo
```

This command shows the currently active milestone (based on due dates) and the open, unassigned issues within it, helping your team decide what to work on next.

This covers the basics of the workflow. For more advanced commands and options, run `gitscaffold --help`.
