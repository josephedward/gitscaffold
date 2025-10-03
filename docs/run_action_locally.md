# Run GitHub Actions Locally

`gitscaffold` now provides a command to run your GitHub Actions workflows locally using `nektos/act`.
This allows for faster testing and debugging of your workflows without needing to push changes to GitHub.

## Prerequisites

This feature relies on `nektos/act`, a powerful tool for running GitHub Actions locally. You need to install `act` on your system before using this `gitscaffold` command.

### Installing `nektos/act`

Follow the official `nektos/act` installation instructions. Here are common methods:

*   **macOS (using Homebrew):**
    ```bash
    brew install act
    ```
*   **Linux (using `curl`):**
    ```bash
    curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash
    ```
*   **Windows (using Chocolatey):**
    ```bash
    choco install act
    ```
    (You might need to install Chocolatey first if you don't have it.)

For more detailed and up-to-date installation instructions, please refer to the official `nektos/act` GitHub repository: [https://github.com/nektos/act](https://github.com/nektos/act)

## Usage

To run a GitHub Action locally, use the `gitscaffold run-action-locally` command:

```bash
gitscaffold run-action-locally [OPTIONS]
```

### Options

*   `--workflow-file`, `-W`: Path to the workflow file (e.g., `.github/workflows/ci.yml`).
*   `--event`, `-e`: The event that triggered the workflow (e.g., `push`, `pull_request`, `workflow_dispatch`). Defaults to `workflow_dispatch`.
*   `--job`, `-j`: Run a specific job within the workflow.
*   `--dry-run`: Perform a dry run, showing the `act` command that would be executed without actually running it.

### Examples

1.  **Run a specific workflow file:**
    ```bash
    gitscaffold run-action-locally -W .github/workflows/ci.yml
    ```

2.  **Run a workflow triggered by a `push` event:**
    ```bash
    gitscaffold run-action-locally -W .github/workflows/release.yml -e push
    ```

3.  **Run a specific job within a workflow:**
    ```bash
    gitscaffold run-action-locally -W .github/workflows/test-and-update-coverage.yml -j build
    ```

4.  **Perform a dry run to see the `act` command:**
    ```bash
    gitscaffold run-action-locally -W .github/workflows/ci.yml --dry-run
    ```

If `act` is not found in your PATH, `gitscaffold` will provide instructions on how to install it.
