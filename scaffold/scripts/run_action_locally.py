import subprocess
import sys
import os
import argparse

def check_act_installed():
    try:
        subprocess.run(["act", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def install_act_instructions():
    print("Error: 'act' (nektos/act) is not installed or not found in your PATH.")
    print("Please install 'act' to use this feature.")
    print("\nInstallation instructions:")
    print("  macOS (Homebrew): brew install act")
    print("  Linux (curl): curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash")
    print("  Windows (Chocolatey): choco install act")
    print("For more details, visit: https://github.com/nektos/act")

def run_action_locally(workflow_file: str, event: str = "workflow_dispatch", job: str = None, dry_run: bool = False):
    if not check_act_installed():
        install_act_instructions()
        return 1 # Indicate failure to the caller

    command = ["act"]

    if workflow_file:
        command.extend(["-W", workflow_file])

    if event:
        command.append(event)

    if job:
        command.extend(["-j", job])

    if dry_run:
        command.append("--dryrun")
        print(f"Dry run: The command that would be executed is: {' '.join(command)}")
        return 0 # Dry run is successful if it gets this far

    print(f"Running GitHub Action locally with command: {' '.join(command)}")
    try:
        subprocess.run(command, check=True, text=True, cwd=os.getcwd())
        return 0
    except subprocess.CalledProcessError as e:
        print(f"Error running 'act': {e}", file=sys.stderr)
        print(f"Stdout: {e.stdout}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        return e.returncode
    except FileNotFoundError:
        install_act_instructions()
        return 1

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run GitHub Actions locally using nektos/act.")
    parser.add_argument("--workflow-file", "-W", help="Path to the workflow file (e.g., .github/workflows/ci.yml).")
    parser.add_argument("--event", "-e", default="workflow_dispatch",
                        help="The event that triggered the workflow (e.g., push, pull_request, workflow_dispatch). Defaults to 'workflow_dispatch'.")
    parser.add_argument("--job", "-j", help="Run a specific job within the workflow.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Perform a dry run, showing the command that would be executed without actually running it.")

    args = parser.parse_args()

    exit_code = run_action_locally(
        workflow_file=args.workflow_file,
        event=args.event,
        job=args.job,
        dry_run=args.dry_run
    )
    sys.exit(exit_code)
