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

### Managing Credentials via `config`

You can now use the `config` command to persistently manage your API keys:
```bash
gitscaffold config set GITHUB_TOKEN "your_token_here"
gitscaffold config set OPENAI_API_KEY "your_key_here"
gitscaffold config list
```
By default, this stores credentials in `~/.gitscaffold/config`.

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

### High-Performance Parsing (Optional)

For significantly faster processing of Markdown files, `gitscaffold` can use a companion parser written in Rust.

**How it works**:
- If `gitscaffold` finds an executable named `mdparser` in your system's `PATH`, it will use it to parse Markdown files.
- If `mdparser` is not found, `gitscaffold` seamlessly falls back to its built-in Python parser.

**How to build and install `mdparser`**:
1.  **Install Rust**: If you don't have it, install the Rust toolchain from [rust-lang.org](https://www.rust-lang.org/tools/install).
2.  **Build the binary**: From the root of the `gitscaffold` repository, run:
    ```sh
    cargo build --manifest-path rust/mdparser/Cargo.toml --release
    ```
3.  **Install the binary**: Copy the compiled executable to a location in your `PATH`.
    ```sh
    # Example for Linux/macOS
    cp rust/mdparser/target/release/mdparser ~/.local/bin/
    ```

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

### Alternative AI Workflow: `import-md`

As an alternative to using `sync` with an unstructured file, you can use the `import-md` command. This command is specifically designed to parse a Markdown file and create GitHub issues from it using AI.

```bash
gitscaffold import-md your_org/your_repo docs/plan.md
```

This is useful for quickly converting documents like meeting notes into actionable GitHub issues.

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

### Example: Auditing the `gitscaffold` Repository Itself

A great way to see `gitscaffold` in action is to run it on its own codebase (a practice known as "dogfooding"). The `diff` command is perfect for this, as it provides a safe, read-only comparison of the project's `ROADMAP.md` against the issues in the `josephedward/gitscaffold` repository.

1.  **Run `diff` from your local clone:**
    ```sh
    # Ensure GITHUB_TOKEN is set
    gitscaffold diff ROADMAP.md --repo josephinedward/gitscaffold
    ```

2.  **Interpret the output:**
    If the local roadmap and GitHub are in sync, you'll get a success message. If not, `gitscaffold` will list the differences, showing you which tasks from the roadmap are missing as GitHub issues, and which issues exist on GitHub but aren't in the roadmap. This helps maintain alignment between your project plan and tracked work.

## 4. Maintenance Commands

`gitscaffold` provides several commands to keep your repository clean:

- `gitscaffold delete-closed`: Deletes all closed issues.
- `gitscaffold sanitize`: Removes markdown formatting from issue titles.
- `gitscaffold deduplicate`: Finds and closes duplicate open issues.
- `gitscaffold enrich issue|batch`: Enriches GitHub issues with AI-generated content based on context from your roadmap.

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
## 6. Vibe Kanban Integration (Experimental)

This integration is highly experimental and untested. For full details and examples, see the [Vibe Kanban Integration Guide](integration_vibe-kanban.md).

## 7. Troubleshooting

### `gitscaffold: command not found`

If you have successfully installed `gitscaffold` but your shell cannot find the command, the installation directory for command-line scripts is likely not in your shell's `PATH`.

1.  **Find the script location:**
    The location of installed command-line scripts depends on your environment.
    - If you are in a virtual environment, it's typically in the `bin/` subdirectory of the environment.
    - If you installed with `--user`, it's often in `~/.local/bin` (Linux/macOS).
    
    You can find your Python installation's script path by running:
    ```sh
    python -c "import sysconfig; print(sysconfig.get_path('scripts'))"
    ```

2.  **Add the location to your `PATH`:**
    Once you find the script directory, add it to your `PATH`. For example, if the scripts are in `~/.local/bin`, add this line to your shell's startup file (e.g., `~/.zshrc`, `~/.bashrc`):

    ```sh
    export PATH="$HOME/.local/bin:$PATH"
    ```

    Restart your shell or run `source ~/.zshrc` (or equivalent) for the changes to take effect.

## PR Feedback Utilities

Use the bundled GitHub CLI to fetch feedback for a specific pull request and optionally act on it:

```bash
# Print a summary of reviews and comments
gitscaffold gh pr-feedback --repo owner/repo --pr 123 --summarize

# If any review has requested changes, add a label
gitscaffold gh pr-feedback --repo owner/repo --pr 123 \
  --label-on-changes needs-changes

# Post a summary comment (dry run shown)
gitscaffold gh pr-feedback --repo owner/repo --pr 123 --comment --dry-run
```

Multiple labels can be supplied by repeating `--label-on-changes`. Add `--dry-run` to preview actions without applying changes.
