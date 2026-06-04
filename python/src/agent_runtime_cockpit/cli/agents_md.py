"""CLI commands for AGENTS.md workspace ingestion and SKILL.md catalog."""

from __future__ import annotations

from pathlib import Path

import typer

from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import agents_app, skills_app
from ..protocol.event_envelope import err, ok


@agents_app.command("discover")
def agents_discover(
    workspace: str = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Discover all AGENTS.md files in the workspace."""
    from ..context.agents_md import discovery

    ws = _workspace(workspace)
    entries = discovery(ws)
    data = [
        {
            "path": str(e.path.relative_to(ws)),
            "sha256": e.sha256,
            "size_bytes": e.size_bytes,
            "over_cap": e.over_cap,
            "is_override": e.is_override,
            "likely_llm_generated": e.likely_llm_generated,
        }
        for e in entries
    ]
    _out(ok({"count": len(data), "entries": data}), json_output)


@agents_app.command("nearest")
def agents_nearest(
    target: str = typer.Argument(help="File path to find nearest AGENTS.md for"),
    workspace: str = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Find the nearest AGENTS.md for a given file path."""
    from ..context.agents_md import nearest_for

    ws = _workspace(workspace)
    target_path = Path(target).resolve()
    entry = nearest_for(target_path, ws)
    if entry is None:
        _out(err("NOT_FOUND", "No AGENTS.md found for target path"), json_output)
        raise typer.Exit(1)
    _out(
        ok(
            {
                "path": str(entry.path.relative_to(ws)),
                "sha256": entry.sha256,
                "is_override": entry.is_override,
                "likely_llm_generated": entry.likely_llm_generated,
            }
        ),
        json_output,
    )


@agents_app.command("pin")
def agents_pin(
    workspace: str = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Pin current AGENTS.md state to .arc/agents-md/index.json."""
    from ..context.agents_md import pin

    ws = _workspace(workspace)
    index_path = pin(ws)
    _out(ok({"pinned": str(index_path.relative_to(ws))}), json_output)


@agents_app.command("drift")
def agents_drift(
    workspace: str = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Check for drift since last pin."""
    from ..context.agents_md import check_drift

    ws = _workspace(workspace)
    report = check_drift(ws)
    _out(
        ok(
            {
                "drifted": report.drifted,
                "added": report.added,
                "removed": report.removed,
                "changed": report.changed,
            }
        ),
        json_output,
    )


@agents_app.command("cards")
def agents_cards(
    workspace: str = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Generate Capability Cards for all discovered AGENTS.md files."""
    from ..capabilities.from_workspace import card_from_agents_md
    from ..context.agents_md import discovery

    ws = _workspace(workspace)
    entries = discovery(ws)
    cards = [card_from_agents_md(e, ws) for e in entries]
    data = [c.model_dump(mode="json") for c in cards]
    _out(ok({"count": len(data), "cards": data}), json_output)


@skills_app.command("discover")
def skills_discover(
    workspace: str = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Discover all SKILL.md files in the workspace."""
    from ..context.skill_md import discovery

    ws = _workspace(workspace)
    entries = discovery(ws)
    data = [
        {
            "path": str(e.path.relative_to(ws)),
            "sha256": e.sha256,
            "size_bytes": e.size_bytes,
            "name": e.name,
            "description": e.description,
            "frontmatter": e.frontmatter,
        }
        for e in entries
    ]
    _out(ok({"count": len(data), "entries": data}), json_output)


@skills_app.command("cards")
def skills_cards(
    workspace: str = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Generate Capability Cards for all discovered SKILL.md files."""
    from ..capabilities.from_workspace import card_from_skill
    from ..context.skill_md import discovery

    ws = _workspace(workspace)
    entries = discovery(ws)
    cards = [card_from_skill(e, ws) for e in entries]
    data = [c.model_dump(mode="json") for c in cards]
    _out(ok({"count": len(data), "cards": data}), json_output)
