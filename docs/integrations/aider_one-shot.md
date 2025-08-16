# Aider One-Shot Issue Processing

`gitscaffold` provides a powerful integration with the `aider` AI coding assistant to automate the resolution of GitHub issues. The `process-issues` command allows you to process a list of issues in a disciplined, one-shot manner.

## How it Works

The command reads a text file where each line represents a task or an issue to be addressed. It then iterates through each line and invokes `aider` in a separate, non-interactive "one-shot" session for each task.

This approach is useful for:

-   **Batch Processing:** Applying a set of refactorings or fixes across your codebase.
-   **Atomic Changes:** Ensuring each issue is addressed in a separate, auto-committed change, making for a clean and reviewable git history.
-   **Unattended Execution:** Running a series of coding tasks without manual intervention for each one.

## Usage

1.  **Create an issues file:**
    Create a text file (e.g., `tasks.txt`) with one issue description per line:

    ```text
    tasks.txt
    -----------
    Refactor the User model to use composition instead of inheritance.
    Add unit tests for the authentication service.
    Update dependencies and resolve any vulnerabilities.
    ```

2.  **Run the command:**
    Invoke `gitscaffold` to process the file:

    ```bash
    gitscaffold process-issues tasks.txt
    ```

    `gitscaffold` will then call `aider` for each line in `tasks.txt`. Aider will attempt to complete the task and commit the changes if successful.

### Command Options

-   `--results-dir <directory>`: Specify a directory to save logs for each Aider run. Defaults to `results/`.
-   `--timeout <seconds>`: Set a timeout for each individual Aider process. Defaults to 300 seconds.

This disciplined, one-shot approach to issue processing with Aider enables a new level of automation in your development workflow.
