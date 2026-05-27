"""Swarm memory graph research commands."""

from __future__ import annotations

import typer
from pathlib import Path

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


@memory_app.command("forget-run")
def memory_forget_run(
    run_id: str = typer.Argument(..., help="Run ID to remove from memory source links"),
    workspace: str | None = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Remove memories sourced only from a specific run."""
    from ..memory_graph.store import MemoryGraphStore

    ws = _workspace(workspace)
    snapshot = MemoryGraphStore(ws / ".arc" / "memory" / "graph.json").forget_run(run_id)
    _out(
        ok(
            {
                "run_id": run_id,
                "nodes_remaining": len(snapshot.nodes),
                "edges_remaining": len(snapshot.edges),
            },
            workspace=str(ws),
        ),
        json_output,
    )


@memory_app.command("evaluate")
def memory_evaluate(
    workspace: str | None = WORKSPACE_FLAG,
    evidence_pack: str | None = typer.Option(None, "--evidence-pack", help="Offline evidence pack"),
    min_runs: int = typer.Option(10, "--min-runs", help="Minimum sample runs required"),
    quality_delta: float | None = typer.Option(
        None, "--quality-delta", help="Measured quality delta"
    ),
    cost_delta: float | None = typer.Option(None, "--cost-delta", help="Measured cost delta"),
    json_output: bool = JSON_FLAG,
) -> None:
    """Evaluate the research gate for using memory in runtime prompts."""
    if evidence_pack:
        from ..memory_graph.evidence import evaluate_evidence_pack

        report = evaluate_evidence_pack(Path(evidence_pack), min_samples=min_runs)
        _out(ok(report.model_dump(), workspace=str(_workspace(workspace))), json_output)
        return
    from ..memory_graph.store import MemoryGraphStore, evaluate_memory_graph

    ws = _workspace(workspace)
    snapshot = MemoryGraphStore(ws / ".arc" / "memory" / "graph.json").load()
    report = evaluate_memory_graph(
        snapshot,
        min_runs=min_runs,
        quality_delta=quality_delta,
        cost_delta=cost_delta,
    )
    _out(ok(report.model_dump(), workspace=str(ws)), json_output)


evidence_app = typer.Typer(help="Offline memory evidence-pack commands")
memory_app.add_typer(evidence_app, name="evidence")


@evidence_app.command("create")
def memory_evidence_create(
    samples: str = typer.Option(..., "--samples", help="Local JSON samples file"),
    output: str = typer.Option(..., "--output", help="Output evidence pack path"),
    pack_id: str = typer.Option("local-pack", "--pack-id", help="Evidence pack ID"),
    workspace: str | None = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Create an offline evidence pack from local fixtures only."""
    from ..memory_graph.evidence import create_evidence_pack

    ws = _workspace(workspace)
    pack = create_evidence_pack(Path(samples), Path(output), pack_id=pack_id)
    _out(ok(pack.model_dump(), workspace=str(ws)), json_output)


@evidence_app.command("evaluate")
def memory_evidence_evaluate(
    pack: str = typer.Argument(..., help="Evidence pack path"),
    min_samples: int = typer.Option(10, "--min-samples", help="Minimum valid samples"),
    workspace: str | None = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Evaluate an offline evidence pack."""
    from ..memory_graph.evidence import evaluate_evidence_pack

    ws = _workspace(workspace)
    report = evaluate_evidence_pack(Path(pack), min_samples=min_samples)
    _out(ok(report.model_dump(), workspace=str(ws)), json_output)


@evidence_app.command("show")
def memory_evidence_show(
    pack: str = typer.Argument(..., help="Evidence pack path"),
    workspace: str | None = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
) -> None:
    """Show an offline evidence pack."""
    from ..memory_graph.evidence import load_evidence_pack

    ws = _workspace(workspace)
    _out(ok(load_evidence_pack(Path(pack)).model_dump(), workspace=str(ws)), json_output)
