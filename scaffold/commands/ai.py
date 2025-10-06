import click


@click.group(name='ai', help='AI assistants and integrations.')
def ai():
    pass


# Map legacy groups under unified AI umbrella when available
try:
    from scaffold.cli import assistant as legacy_assistant_group  # type: ignore
    ai.add_command(legacy_assistant_group, name='aider')
except Exception:
    pass
try:
    from scaffold.cli import vibe as legacy_vibe_group  # type: ignore
    ai.add_command(legacy_vibe_group, name='vibe')
except Exception:
    pass
try:
    from scaffold.cli import enrich as legacy_enrich_group  # type: ignore
    ai.add_command(legacy_enrich_group, name='enrich')
except Exception:
    pass
