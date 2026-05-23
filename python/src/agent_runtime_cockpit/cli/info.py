"""Info commands: version, health, status, inspect, bug-report (Phase 25.2)."""

from __future__ import annotations

import os
import sys
from typing import Optional

from rich.table import Table

from .. import __version__ as arc_version
from ..protocol.event_envelope import ok
from ..workspace import iter_workspace_files

from ._app import app, console
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    WORKSPACE_FLAG,
    _out,
    _setup_logging,
    _workspace,
)


@app.command()
def version(
    json_output: bool = JSON_FLAG,
) -> None:
    """Print ARC version information."""
    data = {
        "version": arc_version,
        "python": sys.version.split()[0],
        "platform": sys.platform,
    }
    envelope = ok(data)
    _out(envelope, json_output)


@app.command()
def health(
    json_output: bool = JSON_FLAG,
) -> None:
    """Check ARC daemon and environment health."""
    import time

    t0 = time.time()

    checks: list[dict] = []
    all_ok = True

    daemon_host = os.environ.get("ARC_DAEMON_HOST", "127.0.0.1")
    daemon_port = os.environ.get("ARC_DAEMON_PORT", "7777")
    try:
        # enforcement: not-applicable - Internal daemon health check, not user-triggered network access
        import urllib.request

        # enforcement: not-applicable - Internal daemon health check (same as above)
        req = urllib.request.Request(f"http://{daemon_host}:{daemon_port}/health")
        with urllib.request.urlopen(req, timeout=2) as resp:
            daemon_ok = resp.status == 200
            if not daemon_ok:
                all_ok = False
            checks.append(
                {
                    "check": "daemon",
                    "ok": daemon_ok,
                    "status": resp.status if daemon_ok else "unhealthy",
                }
            )
    except Exception as exc:
        all_ok = False
        checks.append(
            {
                "check": "daemon",
                "ok": False,
                "status": f"unreachable: {type(exc).__name__}",
            }
        )

    checks.append({"check": "python", "ok": True, "version": sys.version.split()[0]})
    checks.append({"check": "cli", "ok": True, "version": arc_version})

    data = {"ok": all_ok, "checks": checks}
    envelope = ok(data, duration_ms=(time.time() - t0) * 1000)
    _out(envelope, json_output)


@app.command()
def status(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show ARC workspace and runtime status overview."""
    import time

    _setup_logging(debug)
    ws = _workspace(workspace)
    t0 = time.time()

    from ..adapters.registry import default_registry

    registry = default_registry()
    runtimes = registry.detect_all(ws)
    runtime_list = []
    for rt in runtimes:
        adapter = registry.get(rt.adapter)
        if adapter is not None:
            report = adapter.capability_report(ws)
            runtime_list.append(
                {
                    "id": rt.adapter,
                    "detected": True,
                    "can_run": report.can_run,
                    "paid": report.requires_paid_calls,
                }
            )
        else:
            runtime_list.append(
                {
                    "id": rt.adapter,
                    "detected": True,
                    "can_run": False,
                    "note": "adapter not found in registry",
                }
            )

    from ..storage.jsonl import JsonlTraceStore

    store = JsonlTraceStore(ws / ".arc" / "traces")
    trace_ids = store.list_runs()

    py_files = len(list(ws.rglob("*.py"))) if ws.is_dir() else 0

    data = {
        "workspace": str(ws),
        "runtimes": runtime_list,
        "runtime_count": len(runtime_list),
        "trace_count": len(trace_ids),
        "python_files": py_files,
    }
    envelope = ok(data, workspace=str(ws), duration_ms=(time.time() - t0) * 1000)
    _out(envelope, json_output)


@app.command()
def inspect(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Inspect a workspace and detect agent runtimes."""
    import time

    _setup_logging(debug)
    ws = _workspace(workspace)
    t0 = time.time()

    from ..adapters.registry import default_registry
    from ..protocol.schemas import WorkspaceInfo

    registry = default_registry()
    runtimes = registry.detect_all(ws)

    py_count = len(list(iter_workspace_files(ws, (".py",))))
    ts_count = len(list(iter_workspace_files(ws, (".ts",))))

    info = WorkspaceInfo(
        path=str(ws),
        runtimes=runtimes,
        files_scanned=py_count + ts_count,
        detection_warnings=[] if runtimes else ["No runtimes detected"],
    )

    envelope = ok(info.model_dump(), workspace=str(ws), duration_ms=(time.time() - t0) * 1000)
    _out(envelope, json_output)

    if not json_output:
        table = Table(title="Detected Runtimes")
        table.add_column("ID")
        table.add_column("Adapter")
        table.add_column("Confidence")
        table.add_column("Evidence")
        for r in runtimes:
            table.add_row(r.id, r.adapter, r.confidence, " | ".join(r.evidence[:2]))
        console.print(table)
        console.print(f"[dim]Files scanned: {info.files_scanned}[/dim]")


@app.command("bug-report")
def bug_report(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Collect diagnostic information for a bug report.

    Gathers environment, runtime, storage, and config info.
    All secrets are redacted.
    """
    _setup_logging(debug)
    from ..config.loader import load_config
    from ..provider_action import redacted_diagnostics

    ws = _workspace(workspace)
    config = load_config(workspace=ws)
    traces_dir = ws / ".arc" / "traces"
    db_path = ws / ".arc" / "arc.db"
    trace_count = len(list(traces_dir.glob("*.jsonl"))) if traces_dir.exists() else 0
    indexed_count = 0
    if db_path.exists():
        from ..storage.sqlite import SqliteStore

        indexed_count = SqliteStore(db_path).count_runs()
    payload = {
        "arc_version": arc_version,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "workspace": str(ws),
        "traces": trace_count,
        "indexed_runs": indexed_count,
        "config": {
            "version": config.version,
            "runtime_default": config.runtime.default,
            "isolation": config.execution.isolation,
        },
        "providers": redacted_diagnostics(os.environ),
    }
    _out(ok(payload), json_output)
