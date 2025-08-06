#!/usr/bin/env python

import shlex

import click
from scaffold.cli import cli


@click.command()
def main():
    """
    Run the scaffold CLI in a read-eval-print loop (REPL).

    This provides an interactive shell for running scaffold commands without
    re-invoking the program.
    """
    click.echo("Starting scaffold REPL. Type 'exit' or 'quit' or press Ctrl-D to end.")

    while True:
        command = ''
        try:
            command = input("scaffold> ")
        except EOFError:
            click.echo()  # newline
            break

        if command.strip().lower() in ["exit", "quit"]:
            break

        if not command.strip():
            continue

        args = shlex.split(command)

        try:
            cli.main(args, standalone_mode=False)
        except click.exceptions.Exit as e:
            if e.exit_code != 0:
                # Click already prints error messages for non-zero exits
                # so we just continue the loop
                pass
        except Exception as e:
            click.echo(f"An unexpected error occurred: {e}", err=True)

    click.echo("Exiting REPL.")


if __name__ == "__main__":
    main()
