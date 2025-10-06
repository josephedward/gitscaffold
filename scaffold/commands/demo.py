import click


@click.group(name='demo', help='Demo modes and examples.')
def demo():
    pass


try:
    from scaffold.cli import start_demo as legacy_start_demo_cmd  # type: ignore
    demo.add_command(legacy_start_demo_cmd, name='streamlit')
except Exception:
    pass

@demo.command(name='examples')
def demo_examples():
    """Run example demos (stub)."""
    click.secho('Demo examples: not implemented yet', fg='yellow')
