"""Run management commands: runs, prune, get, diff, trace, status, etc. (Phase 25.4)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..protocol.schemas import RunRecord, RunStatus
from ..orchestration.events import new_run_id, now

from ._app import console, err_console
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    WORKSPACE_FLAG,
    _out,
    _setup_logging,
    _workspace,
)
from ._subapps import runs_app


@runs_app.callback(invoke_without_command=True)
def runs(
    ctx: typer.Context,
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List stored run records."""
    if ctx.invoked_subcommand is not None:
        return
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run_ids = store.list_runs()
    run_list = [r for rid in run_ids if (r := store.load(rid)) is not None]
    _out(ok([r.model_dump() for r in run_list]), json_output)


@runs_app.command("prune")
def runs_prune(
    workspace: Optional[str] = WORKSPACE_FLAG,
    keep: int = typer.Option(20, "--keep", min=0, help="Number of newest traces to keep"),
    older_than: Optional[int] = typer.Option(
        None, "--older-than", min=1, help="Only delete traces older than N days"
    ),
    yes: bool = typer.Option(False, "--yes", help="Delete files instead of dry-run"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Prune oldest workspace trace files beyond --keep."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    trace_dir = ws / ".arc" / "traces"
    store = JsonlTraceStore(trace_dir)
    victims = store.prune(keep=keep, dry_run=not yes, older_than_days=older_than)
    payload = {
        "workspace": str(ws),
        "trace_dir": str(trace_dir),
        "keep": keep,
        "older_than_days": older_than,
        "dry_run": not yes,
        "deleted": [] if not yes else [str(path) for path in victims],
        "would_delete": [str(path) for path in victims] if not yes else [],
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("get")
def runs_get(
    run_id: str = typer.Argument(..., help="Run ID to load"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Load one stored run record."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(run_record.model_dump(), workspace=str(ws)), json_output)


@runs_app.command("diff")
def runs_diff(
    run_a: str = typer.Argument(..., help="First run ID"),
    run_b: str = typer.Argument(..., help="Second run ID"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Compare two stored run records."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore
    from ..evals.diff import diff_runs

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    rec_a = store.load(run_a)
    rec_b = store.load(run_b)
    if rec_a is None or rec_b is None:
        missing = [r for r, rec in [(run_a, rec_a), (run_b, rec_b)] if rec is None]
        _out(
            err(ArcErrorCode.RUN_NOT_FOUND, f"Run(s) not found: {', '.join(missing)}"), json_output
        )
        raise typer.Exit(1)
    result = diff_runs(rec_a, rec_b)
    _out(ok(result.model_dump(), workspace=str(ws)), json_output)


@runs_app.command("trace")
def runs_trace(
    run_id: str = typer.Argument(..., help="Run ID to inspect"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    tail: int = typer.Option(20, "--tail", min=0, help="Number of trace lines to return"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Return trace file metadata and optional tail lines for one run."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    path = store.trace_path(run_id)
    if not path.exists():
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Trace not found: {run_id}"), json_output)
        raise typer.Exit(1)
    lines = path.read_text().splitlines()
    payload = {
        "run_id": run_id,
        "trace_path": str(path),
        "line_count": len(lines),
        "tail": lines[-tail:] if tail else [],
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("status")
def runs_status(
    run_id: str = typer.Argument(..., help="Run ID to check"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show status of a stored run record."""
    _setup_logging(debug)
    from ..storage.indexed_store import IndexedTraceStore

    ws = _workspace(workspace)
    store = IndexedTraceStore(trace_dir=ws / ".arc" / "traces", db_path=ws / ".arc" / "arc.db")
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    payload = {
        "run_id": run_record.id,
        "status": run_record.status.value,
        "workflow_id": run_record.workflow_id,
        "runtime": run_record.runtime,
        "started_at": run_record.started_at,
        "ended_at": run_record.ended_at,
        "event_count": len(run_record.events),
        "audit_path": run_record.audit_path,
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("delete")
def runs_delete(
    run_id: str = typer.Argument(..., help="Run ID to delete"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete a stored run record and its trace file."""
    _setup_logging(debug)
    from ..storage.indexed_store import IndexedTraceStore

    ws = _workspace(workspace)
    store = IndexedTraceStore(trace_dir=ws / ".arc" / "traces", db_path=ws / ".arc" / "arc.db")
    trace_path = store.trace_path(run_id)
    if not trace_path.exists():
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    trace_path.unlink()
    store.sqlite.delete_run(run_id)
    payload = {"deleted_run_id": run_id, "trace_path": str(trace_path)}
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("export")
def runs_export(
    run_id: str = typer.Argument(..., help="Run ID to export"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export a run record as JSON."""
    _setup_logging(debug)
    from ..storage.indexed_store import IndexedTraceStore

    ws = _workspace(workspace)
    store = IndexedTraceStore(trace_dir=ws / ".arc" / "traces", db_path=ws / ".arc" / "arc.db")
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(run_record.model_dump(), workspace=str(ws)), json_output)


@runs_app.command("import")
def runs_import(
    path: str = typer.Argument(..., help="Path to exported run JSON"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Import a run record JSON into the workspace trace store."""
    _setup_logging(debug)
    import json

    from ..protocol.schemas import RunRecord
    from ..storage.indexed_store import IndexedTraceStore

    ws = _workspace(workspace)
    source = Path(path).expanduser().resolve()
    if not source.exists():
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Import file not found: {source}"), json_output)
        raise typer.Exit(1)
    try:
        run_record = RunRecord.model_validate(json.loads(source.read_text()))
    except Exception as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid run export: {exc}"), json_output)
        raise typer.Exit(1)
    store = IndexedTraceStore(trace_dir=ws / ".arc" / "traces", db_path=ws / ".arc" / "arc.db")
    store.init()
    store.save(run_record)
    _out(ok({"imported_run_id": run_record.id}, workspace=str(ws)), json_output)


@runs_app.command("replay")
def runs_replay(
    run_id: str = typer.Argument(..., help="Run ID to replay from stored trace"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Replay stored trace events without re-executing the runtime."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    payload = {
        "run_id": run_record.id,
        "event_count": len(run_record.events),
        "events": [event.model_dump() for event in run_record.events],
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("backfill")
def runs_backfill(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Backfill SQLite index from existing JSONL traces. Idempotent."""
    _setup_logging(debug)
    from ..storage.indexed_store import IndexedTraceStore

    ws = _workspace(workspace)
    store = IndexedTraceStore(trace_dir=ws / ".arc" / "traces", db_path=ws / ".arc" / "arc.db")
    store.init()
    indexed, skipped, failed = store.backfill_index()
    payload = {"indexed": indexed, "skipped": skipped, "failed": failed}
    _out(ok(payload, workspace=str(ws)), json_output)
    if not json_output and failed > 0:
        err_console.print(f"[yellow]Warning: {failed} trace(s) failed to index[/yellow]")


@runs_app.command("search")
def runs_search(
    workflow: Optional[str] = typer.Option(None, "--workflow", "-f", help="Filter by workflow ID"),
    runtime: Optional[str] = typer.Option(None, "--runtime", "-r", help="Filter by runtime"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum results"),
    offset: int = typer.Option(0, "--offset", "-o", help="Result offset"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Search runs using the SQLite index."""
    _setup_logging(debug)
    from ..storage.sqlite import SqliteStore

    ws = _workspace(workspace)
    db_path = ws / ".arc" / "arc.db"
    if not db_path.exists():
        _out(
            err(
                ArcErrorCode.INVALID_INPUT, "SQLite index not found. Run 'arc runs backfill' first."
            ),
            json_output,
        )
        raise typer.Exit(1)
    store = SqliteStore(db_path)
    results = store.list_runs(
        status=status, runtime=runtime, workflow_id=workflow, limit=limit, offset=offset
    )
    total = store.count_runs()
    payload = {
        "results": results,
        "count": len(results),
        "total_indexed": total,
        "filters": {"workflow": workflow, "runtime": runtime, "status": status},
    }
    _out(ok(payload, workspace=str(ws)), json_output)
    if not json_output:
        if not results:
            console.print("[dim]No matching runs found.[/dim]")
            return
        table = Table(title=f"Runs ({len(results)} of {total} indexed)")
        table.add_column("Run ID")
        table.add_column("Workflow")
        table.add_column("Runtime")
        table.add_column("Status")
        table.add_column("Started")
        for run in results:
            table.add_row(
                run["id"][:12],
                run.get("workflow_id", "")[:20],
                run.get("runtime", ""),
                run.get("status", ""),
                run.get("started_at", "")[:19],
            )
        console.print(table)


@runs_app.command("fork")
def runs_fork(
    run_id: str = typer.Argument(..., help="Run ID to fork"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Fork a stored run into a new run record with a fresh ID."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    source = store.load(run_id)
    if source is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    new_id = new_run_id(prefix="fork")
    fork_events = [
        event for event in source.events if event.type in {"RUN_STARTED", "STEP_STARTED"}
    ]
    if not fork_events:
        fork_events = source.events[:1] if source.events else []
    fork_record = RunRecord(
        id=new_id,
        workflow_id=source.workflow_id,
        runtime=source.runtime,
        status=RunStatus.PENDING,
        started_at=now(),
        events=fork_events,
        metadata={
            **source.metadata,
            "forked_from": run_id,
            "forked_at": now(),
            "original_status": source.status.value,
        },
    )
    store.save(fork_record)
    payload = {
        "fork_id": new_id,
        "source_id": run_id,
        "workflow_id": source.workflow_id,
        "runtime": source.runtime,
        "event_count": len(fork_events),
        "source_event_count": len(source.events),
        "status": "pending",
        "metadata": fork_record.metadata,
    }
    _out(ok(payload, workspace=str(ws)), json_output)
    if not json_output:
        console.print(f"[green]Fork created:[/green] {new_id}")
        console.print(
            f"  Source: {run_id} ({source.status.value})  Workflow: {source.workflow_id}  Runtime: {source.runtime}"
        )
        console.print(f"  Events: {len(fork_events)} (of {len(source.events)} source events)")
    source.metadata["forked_to"] = source.metadata.get("forked_to", []) + [new_id]
    store.save(source)


@runs_app.command("links")
def runs_links(
    run_id: str = typer.Argument(..., help="Run ID to get cross-linked event chains for"),
    filter: Optional[str] = typer.Option(None, "--filter", help="Filter link type"),
    stable_id: Optional[str] = typer.Option(
        None, "--stable-id", help="Specific stable ID to look up"
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Get cross-linked event chains for a run by stable ID."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore
    from ..orchestration.cross_linker import CrossLinker

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    linker = CrossLinker()
    linker.index_all(run_record.events)
    if stable_id:
        node = linker.get_node_chain(stable_id) if filter in (None, "node_id") else []
        msg = linker.get_message_chain(stable_id) if filter in (None, "message_id") else []
        tc = linker.get_tool_call_chain(stable_id) if filter in (None, "tool_call_id") else []
        ev = linker.get_evidence_events(stable_id) if filter in (None, "evidence_id") else []
        payload = {
            "node_chains": {stable_id: [e.model_dump() for e in node]},
            "message_chains": {stable_id: [e.model_dump() for e in msg]},
            "tool_call_chains": {stable_id: [e.model_dump() for e in tc]},
            "evidence_chains": {stable_id: [e.model_dump() for e in ev]},
            "has_stable_ids": linker.has_stable_ids(),
            "stable_id_count": 1,
        }
    else:
        ids = linker.get_run_event_ids()
        node_chains, message_chains, tool_call_chains, evidence_chains = {}, {}, {}, {}
        for sid in ids:
            if filter in (None, "node_id"):
                chain = linker.get_node_chain(sid)
                if chain:
                    node_chains[sid] = [e.model_dump() for e in chain]
            if filter in (None, "message_id"):
                chain = linker.get_message_chain(sid)
                if chain:
                    message_chains[sid] = [e.model_dump() for e in chain]
            if filter in (None, "tool_call_id"):
                chain = linker.get_tool_call_chain(sid)
                if chain:
                    tool_call_chains[sid] = [e.model_dump() for e in chain]
            if filter in (None, "evidence_id"):
                chain = linker.get_evidence_events(sid)
                if chain:
                    evidence_chains[sid] = [e.model_dump() for e in chain]
        payload = {
            "node_chains": node_chains,
            "message_chains": message_chains,
            "tool_call_chains": tool_call_chains,
            "evidence_chains": evidence_chains,
            "has_stable_ids": linker.has_stable_ids(),
            "stable_id_count": len(ids),
        }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("contract")
def runs_contract(
    run_id: str = typer.Argument(..., help="Run ID to show contract for"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show the run contract for a stored run."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    contract = store.load_contract(run_id)
    if contract is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Contract not found for run: {run_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(contract.model_dump(), workspace=str(ws)), json_output)
    if not json_output:
        console.print(f"[bold]Run Contract:[/bold] {contract.contract_id}")
        console.print(f"  Status: {contract.status.value}  Objective: {contract.objective}")
        console.print(f"  Runtime: {contract.runtime}  Mode: {contract.mode}")


@runs_app.command("budget")
def runs_budget(
    run_id: str = typer.Argument(..., help="Run ID to show budget and usage for"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show budget and usage information for a run."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    budget = run_record.metadata.get("budget", {})
    usage = run_record.metadata.get("usage", {})

    def _dim(source: dict[str, object], key: str) -> dict[str, object]:
        if key not in source:
            return {"status": "absent"}
        raw = source[key]
        if not isinstance(raw, (int, float)) or isinstance(raw, bool):
            return {"status": "degraded", "raw": raw, "reason": "non_numeric"}
        if raw < 0:
            return {"status": "degraded", "raw": raw, "reason": "negative_value"}
        return {"status": "available", "value": raw}

    usage_report = {
        "tokens": _dim(usage, "total_tokens")
        if isinstance(usage, dict)
        else {"status": "degraded", "raw": usage, "reason": "malformed_usage"},
        "cost_usd": _dim(usage, "total_cost")
        if isinstance(usage, dict)
        else {"status": "degraded", "raw": usage, "reason": "malformed_usage"},
        "latency_ms": _dim(usage, "latency_ms")
        if isinstance(usage, dict)
        else {"status": "degraded", "raw": usage, "reason": "malformed_usage"},
    }
    payload = {
        "run_id": run_id,
        "budget": budget
        if isinstance(budget, dict)
        else {"status": "degraded", "raw": budget, "reason": "malformed_budget"},
        "usage": usage_report,
    }
    _out(ok(payload, workspace=str(ws)), json_output)
    if not json_output:
        console.print(f"[bold]Budget & Usage:[/bold] {run_id}")
        if not isinstance(budget, dict) or not budget:
            console.print("  [dim]No budget constraints recorded[/dim]")
        else:
            if "max_tokens" in budget:
                console.print(f"  Max Tokens: {budget['max_tokens']}")
            if "max_cost" in budget:
                console.print(f"  Max Cost:   ${budget['max_cost']:.4f}")


@runs_app.command("autopsy")
def runs_autopsy(
    run_id: str = typer.Argument(..., help="Run ID to show autopsy for"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show failure autopsy for a failed run."""
    _setup_logging(debug)
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    autopsy = store.load_autopsy(run_id)
    if autopsy is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Autopsy not found for run: {run_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(autopsy.model_dump(by_alias=True), workspace=str(ws)), json_output)
    if not json_output:
        console.print(f"[bold]Failure Autopsy:[/bold] {autopsy.run_id}")
        console.print(
            f"  Probable cause: {autopsy.probable_cause}  Confidence: {autopsy.confidence}"
        )
