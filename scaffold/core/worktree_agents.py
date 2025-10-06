import subprocess
import click
from pathlib import Path
from typing import Optional, List, Dict
import os
import time

from .worktree import list_worktrees, add_worktree
from .worktree_config import _load_config, CONFIG_FILE_NAME

def _get_worktree_path(branch_name: str) -> Optional[Path]:
    worktrees = list_worktrees()
    for wt in worktrees:
        if wt.get("branch") == branch_name:
            return Path(wt["path"])
    return None

def setup_agents(branches: Optional[str]):
    """Sets up worktrees and agent configurations for specified branches."""
    config = _load_config()
    if not config:
        click.secho(f"Error: Config file '{CONFIG_FILE_NAME}' not found. Run 'gitscaffold source worktree config init'.", fg='red')
        return

    if not branches:
        click.secho("No branches specified for agent setup.", fg='yellow')
        return

    branch_list = [b.strip() for b in branches.split(',') if b.strip()]

    for branch in branch_list:
        click.echo(f"Setting up agent for branch: {branch}")
        worktree_path = _get_worktree_path(branch)
        if not worktree_path:
            click.secho(f"Worktree for branch '{branch}' not found. Creating...", fg='yellow')
            add_worktree(branch=branch, create_new=False) # Assuming branch already exists in main repo
            worktree_path = _get_worktree_path(branch)
            if not worktree_path:
                click.secho(f"Failed to create worktree for branch '{branch}'. Skipping agent setup.", fg='red')
                continue
        
        # Apply post-create hooks from config
        post_create_hooks = config.get("worktree", {}).get("post_create_hooks", [])
        for hook in post_create_hooks:
            hook_type = hook.get("type")
            if hook_type == "copy":
                from_path = Path(worktree_path.parent.parent) / hook.get("from")
                to_path = worktree_path / hook.get("to")
                if from_path.exists():
                    click.echo(f"  Copying {from_path} to {to_path}...")
                    try:
                        subprocess.run(["cp", str(from_path), str(to_path)], check=True, capture_output=True)
                        click.secho(f"  Copied {from_path.name} to {to_path.name}.", fg='green')
                    except Exception as e:
                        click.secho(f"  Error copying file: {e}", fg='red')
                else:
                    click.secho(f"  Warning: Source file for copy hook not found: {from_path}", fg='yellow')
            elif hook_type == "command":
                command = hook.get("command")
                if command:
                    click.echo(f"  Running command: {command} in {worktree_path}...")
                    try:
                        subprocess.run(command, shell=True, check=True, cwd=worktree_path, capture_output=True)
                        click.secho(f"  Command executed successfully.", fg='green')
                    except Exception as e:
                        click.secho(f"  Error running command: {e}", fg='red')

    click.secho("Agent setup complete.", fg='green')

def start_agent(branch: str, agent_name: str):
    """Starts an AI agent in the specified worktree."""
    config = _load_config()
    agent_config = config.get("agents", {}).get(agent_name)

    if not agent_config:
        click.secho(f"Error: Agent '{agent_name}' not configured in '{CONFIG_FILE_NAME}'.", fg='red')
        return

    worktree_path = _get_worktree_path(branch)
    if not worktree_path:
        click.secho(f"Error: Worktree for branch '{branch}' not found.", fg='red')
        return

    command = agent_config.get("command")
    if not command:
        click.secho(f"Error: Command for agent '{agent_name}' not specified in config.", fg='red')
        return

    click.echo(f"Starting agent '{agent_name}' in worktree '{branch}' at '{worktree_path}'...")
    try:
        # Run in background
        process = subprocess.Popen(command, shell=True, cwd=worktree_path, preexec_fn=os.setsid)
        click.secho(f"Agent '{agent_name}' started with PID {process.pid} in worktree '{branch}'.", fg='green')
        # Store PID for status/kill
        # This is a simple in-memory store, for persistence, it would need to be written to a file
        if not hasattr(start_agent, "running_agents"):
            start_agent.running_agents = {}
        start_agent.running_agents[f"{branch}-{agent_name}"] = process.pid
    except Exception as e:
        click.secho(f"Error starting agent: {e}", fg='red')

def agent_status():
    """Reports the status of running agents in worktrees."""
    if not hasattr(start_agent, "running_agents") or not start_agent.running_agents:
        click.secho("No agents are currently running.", fg='yellow')
        return

    click.echo("Running agents:")
    for agent_id, pid in start_agent.running_agents.items():
        try:
            os.kill(pid, 0) # Check if process is still running
            click.echo(f"  - {agent_id}: PID {pid} (Running)", fg='green')
        except OSError:
            click.echo(f"  - {agent_id}: PID {pid} (Stopped/Dead)", fg='red')
            del start_agent.running_agents[agent_id] # Clean up dead process

def kill_agent(branch: str):
    """Stops the agent running in the specified worktree."""
    if not hasattr(start_agent, "running_agents") or not start_agent.running_agents:
        click.secho("No agents are currently running.", fg='yellow')
        return

    agent_found = False
    for agent_id, pid in list(start_agent.running_agents.items()):
        if agent_id.startswith(f"{branch}-"):
            click.echo(f"Attempting to stop agent with PID {pid} for worktree '{branch}'...")
            try:
                os.killpg(os.getpgid(pid), 9) # Send SIGKILL to process group
                click.secho(f"Agent for worktree '{branch}' (PID {pid}) stopped.", fg='green')
                del start_agent.running_agents[agent_id]
                agent_found = True
            except OSError as e:
                click.secho(f"Error stopping agent with PID {pid}: {e}", fg='red')
    
    if not agent_found:
        click.secho(f"No running agent found for worktree '{branch}'.", fg='yellow')
