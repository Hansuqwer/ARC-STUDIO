"""Swarm memory graph research commands."""

from __future__ import annotations

import typer

from ..protocol.event_envelope import ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import memory_app


@memory_app.command("extract")
def memory_extract(
    workspace: str | None = WORKSPACE_FLAG,
    limit: int = typer.Option(10, "--limit", "-n", help="Max trace files to scan"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Do not persist graph"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Extract local-only research memories from stored traces."""
    from ..memory_graph.store import MemoryGraphStore, extract_memories_from_runs

    ws = _workspace(workspace)
    snapshot = extract_memories_from_runs(ws / ".arc" / "traces", limit=limit)
    if dry_run:
        payload = snapshot.model_dump()
    else:
        payload = (
            MemoryGraphStore(ws / ".arc" / "memory" / "graph.json").merge(snapshot).model_dump()
        )
    _out(ok(payload, workspace=str(ws)), json_output)


@memory_app.command("query")
def memory_query(
    query: str = typer.Argument(..., help="Search text"),
    workspace: str | None = WORKSPACE_FLAG,
    limit: int = typer.Option(20, "--limit", "-n", help="Max memories to return"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Query persisted local-only memory graph nodes."""
    from ..memory_graph.store import MemoryGraphStore

    ws = _workspace(workspace)
    nodes = MemoryGraphStore(ws / ".arc" / "memory" / "graph.json").query(query, limit=limit)
    _out(
        ok(
            {"count": len(nodes), "nodes": [node.model_dump() for node in nodes]}, workspace=str(ws)
        ),
        json_output,
    )


@memory_app.command("show")
def memory_show(
    workspace: str | None = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Show memory graph research snapshot metadata."""
    from ..memory_graph.store import MemoryGraphStore

    ws = _workspace(workspace)
    snapshot = MemoryGraphStore(ws / ".arc" / "memory" / "graph.json").load()
    _out(ok(snapshot.model_dump(), workspace=str(ws)), json_output)
