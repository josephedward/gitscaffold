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

 Add `--ai` for AI-assisted extraction on Markdown files.

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