# Dispatching AI Agents for Issue Processing

The `gitscaffold process-issues` command allows you to sequentially process a list of issues using an AI agent. Currently, it supports `aider` and `gemini` agents. This document provides detailed instructions on how to use this functionality.

## Prerequisites

Before dispatching the agents, ensure you have the following:

### GitHub Token
A GitHub Personal Access Token (PAT) is required for `gitscaffold` to interact with your GitHub repository. This token should have at least `repo` or `issues` scope.

You can set your GitHub token in one of the following ways:
- As an environment variable: `export GITHUB_TOKEN="YOUR_GITHUB_PAT"`
- Using the `gitscaffold config` command: `gitscaffold config set GITHUB_TOKEN YOUR_GITHUB_PAT`

### AI API Keys

#### OpenAI (for `aider` agent)
If you plan to use the `aider` agent, you will need an OpenAI API key.
- As an environment variable: `export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"`
- Using the `gitscaffold config` command: `gitscaffold config set OPENAI_API_KEY YOUR_OPENAI_API_KEY`

#### Google Gemini (for `gemini` agent)
If you plan to use the `gemini` agent, you will need a Google Gemini API key.
- As an environment variable: `export GEMINI_API_KEY="YOUR_GEMINI_API_KEY"`
- Using the `gitscaffold config` command: `gitscaffold config set GEMINI_API_KEY YOUR_GEMINI_API_KEY`

### Aider CLI (for `aider` agent)
Ensure the `aider` CLI tool is installed and accessible in your system's PATH. If not, you can install it via pip:
```bash
pip install aider-chat
```

## Usage

The `process-issues` command takes an issues file as input, where each line represents a single issue to be processed.

```bash
gitscaffold process-issues <issues_file> --agent <agent_name> [OPTIONS]
```

- `<issues_file>`: Path to a text file containing one issue description per line.
- `--agent <agent_name>`: Specifies the AI agent to use. Choose between `aider` or `gemini`.

### Options

- `--results-dir <directory>`: (Optional) Directory to save detailed logs for each processed issue. Defaults to `results`.
- `--timeout <seconds>`: (Optional) Timeout in seconds for each agent process. Defaults to `300` seconds.

## Examples

### Example Issues File (`my_issues.txt`)

Create a file named `my_issues.txt` with the following content:

```
Fix the bug in calculator.py where division by zero causes a crash.
Implement a new feature to add a square root function to calculator.py.
Refactor the add function in calculator.py to improve readability.
```

### Dispatching with Aider

To process the issues in `my_issues.txt` using the `aider` agent:

```bash
gitscaffold process-issues my_issues.txt --agent aider
```

**Expected Behavior (Aider):**
- For each issue, `gitscaffold` will invoke the `aider` CLI with the issue description.
- `aider` will attempt to generate and apply code changes to resolve the issue.
- `aider` will automatically commit changes to your Git repository.
- Logs for each issue processing will be saved in the `results/` directory (or your specified `--results-dir`).
- You will see success or failure messages in your console for each issue.

### Dispatching with Gemini

To process the issues in `my_issues.txt` using the `gemini` agent:

```bash
gitscaffold process-issues my_issues.txt --agent gemini
```

**Expected Behavior (Gemini):**
- For each issue, `gitscaffold` will:
    1. Read the content of all Python files in the current working directory to provide context to the Gemini API.
    2. Call the Gemini API with the issue description and file contents to generate code changes.
    3. Parse the response from Gemini, identify file changes, and apply them to your local files.
    4. Automatically stage and commit the changes to your Git repository with a commit message like `fix: <issue_description>`.
- Logs for each issue processing will be saved in the `results/` directory (or your specified `--results-dir`).
- You will see success or failure messages in your console for each issue, along with messages indicating file modifications and Git commits.

## Important Notes

- **Git Repository:** Ensure you are running these commands within a Git repository, as both agents will attempt to commit changes.
- **Review Changes:** Always review the changes made by the AI agents. While they strive for accuracy, manual verification is crucial.
- **Idempotency:** Running the same issue multiple times might result in redundant commits if the issue is not fully resolved or if the agent generates the same changes again.
- **Timeout:** If an agent takes longer than the specified `--timeout` to process an issue, its process will be terminated.