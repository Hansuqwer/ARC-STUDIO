"""ARC storage management commands (split from mgmt.py — CR-026)."""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._app import console
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    WORKSPACE_FLAG,
    _out,
    _setup_logging,
    _workspace,
)
from ._subapps import storage_app


@storage_app.command("vacuum")
def storage_vacuum(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Vacuum SQLite index to reclaim space after deletions."""
    _setup_logging(debug)
    import sqlite3

    ws = _workspace(workspace)
    db_path = ws / ".arc" / "arc.db"
    if not db_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, "SQLite index not found."), json_output)
        raise typer.Exit(1)
    size_before = db_path.stat().st_size
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("VACUUM")
        size_after = db_path.stat().st_size
        saved = size_before - size_after
        payload = {
            "workspace": str(ws),
            "db_path": str(db_path),
            "size_before": size_before,
            "size_after": size_after,
            "saved_bytes": saved,
        }
        _out(ok(payload, workspace=str(ws)), json_output)
        if not json_output:
            console.print(f"[green]Vacuumed[/green] {db_path}")
            console.print(f"  Before: {size_before:,} bytes")
            console.print(f"  After: {size_after:,} bytes")
            if saved > 0:
                console.print(f"  Saved: {saved:,} bytes")
    except Exception as e:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Vacuum failed: {e}"), json_output)
        raise typer.Exit(1)


@storage_app.command("status")
def storage_status(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show storage usage statistics."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    traces_dir = ws / ".arc" / "traces"
    db_path = ws / ".arc" / "arc.db"
    goldens_dir = ws / ".arc" / "goldens"
    hitl_dir = ws / ".arc" / "hitl"

    trace_count = len(list(traces_dir.glob("*.jsonl"))) if traces_dir.exists() else 0
    trace_size = (
        sum(p.stat().st_size for p in traces_dir.glob("*.jsonl")) if traces_dir.exists() else 0
    )
    db_size = db_path.stat().st_size if db_path.exists() else 0
    golden_count = len(list(goldens_dir.glob("*.json"))) if goldens_dir.exists() else 0
    hitl_pending = (
        len(list((hitl_dir / "pending").glob("*.json"))) if (hitl_dir / "pending").exists() else 0
    )

    payload = {
        "workspace": str(ws),
        "traces": {
            "count": trace_count,
            "size_bytes": trace_size,
            "dir": str(traces_dir),
        },
        "sqlite_index": {
            "exists": db_path.exists(),
            "size_bytes": db_size,
            "path": str(db_path),
        },
        "goldens": {
            "count": golden_count,
            "dir": str(goldens_dir),
        },
        "hitl": {
            "pending": hitl_pending,
            "dir": str(hitl_dir),
        },
    }
    _out(ok(payload, workspace=str(ws)), json_output)
    if not json_output:
        console.print(f"[bold]Storage Status[/bold] — {ws}")
        console.print(f"  Traces: {trace_count} files ({trace_size:,} bytes)")
        console.print(
            f"  SQLite: {'exists' if db_path.exists() else 'not found'} ({db_size:,} bytes)"
        )
        console.print(f"  Goldens: {golden_count}")
        console.print(f"  HITL pending: {hitl_pending}")
