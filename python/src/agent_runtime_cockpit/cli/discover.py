"""Discovery commands: runtimes, workflows, schemas (Phase 25.3)."""

from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from ..adapters.registry import default_registry
from ..orchestration import runtime_router
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._app import app, console, err_console
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    WORKSPACE_FLAG,
    _out,
    _setup_logging,
    _workspace,
)


@app.command()
def runtimes(
    workspace: Optional[str] = WORKSPACE_FLAG,
    capabilities: bool = typer.Option(
        False, "--capabilities", help="List all adapter capability reports"
    ),
    diff_from: Optional[str] = typer.Option(
        None, "--diff-from", help="Source runtime ID for capability diff"
    ),
    diff_to: Optional[str] = typer.Option(
        None, "--diff-to", help="Target runtime ID for capability diff"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List detected runtimes in a workspace."""
    _setup_logging(debug)
    ws = _workspace(workspace)

    if diff_from and diff_to:
        from ..protocol.capability_snapshot import diff_capabilities, snapshot_capabilities

        registry = default_registry()
        from_adapter = registry.get(diff_from)
        to_adapter = registry.get(diff_to)
        if from_adapter is None:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Unknown runtime: {diff_from}"), json_output)
            return
        if to_adapter is None:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Unknown runtime: {diff_to}"), json_output)
            return
        before_caps = from_adapter.capabilities()
        after_caps = to_adapter.capabilities()
        before_snap = snapshot_capabilities(diff_from, before_caps)
        after_snap = snapshot_capabilities(diff_to, after_caps)
        diff = diff_capabilities(diff_to, before_snap, after_snap)
        payload = diff.model_dump()
        _out(ok(payload, workspace=str(ws)), json_output)
        return

    if capabilities:
        reports = runtime_router.list_runtimes(ws)
        payload = {
            "workspace": str(ws),
            "auto_priority": list(runtime_router.AUTO_PRIORITY),
            "runtimes": [report.model_dump() for report in reports],
        }
        if json_output:
            _out(ok(payload, workspace=str(ws)), json_output)
            return
        console.print(f"workspace: {ws}")
        console.print(f"auto priority: {' > '.join(runtime_router.AUTO_PRIORITY)}")
        table = Table(title="Runtime Capabilities")
        table.add_column("Runtime")
        table.add_column("Detected")
        table.add_column("Can Run")
        table.add_column("Paid")
        table.add_column("Availability")
        table.add_column("Reason")
        for report in reports:
            table.add_row(
                report.runtime_id,
                "yes" if report.detected else "no",
                "yes" if report.can_run else "no",
                "yes" if report.requires_paid_calls else "no",
                report.availability,
                (report.reason or "")[:80],
            )
        console.print(table)
        return
    registry = default_registry()
    detected = registry.detect_all(ws)
    envelope = ok([r.model_dump() for r in detected], workspace=str(ws))
    _out(envelope, json_output)


@app.command()
def workflows(
    workspace: Optional[str] = WORKSPACE_FLAG,
    runtime: Optional[str] = typer.Option(None, "--runtime", "-r"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List detected workflows in a workspace."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    registry = default_registry()
    detected = registry.detect_all(ws)
    results = []
    for rt in detected:
        if runtime and rt.adapter != runtime:
            continue
        adapter = registry.get(rt.adapter)
        if adapter and adapter.capabilities().can_export_workflow:
            try:
                wfs = adapter.export_workflow(ws)
                results.extend(w.model_dump() for w in wfs)
            except Exception as e:
                err_console.print(
                    f"[yellow]Warning: {rt.adapter} workflow export failed: {e}[/yellow]"
                )

    _out(ok(results, workspace=str(ws)), json_output)


@app.command()
def schemas(
    workspace: Optional[str] = WORKSPACE_FLAG,
    runtime: Optional[str] = typer.Option(None, "--runtime", "-r"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List detected schemas in a workspace."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    registry = default_registry()
    detected = registry.detect_all(ws)
    results = []
    for rt in detected:
        if runtime and rt.adapter != runtime:
            continue
        adapter = registry.get(rt.adapter)
        if adapter and adapter.capabilities().can_export_schema:
            try:
                ss = adapter.export_schemas(ws)
                results.extend(s.model_dump_api() for s in ss)
            except Exception as e:
                err_console.print(
                    f"[yellow]Warning: {rt.adapter} schema export failed: {e}[/yellow]"
                )

    _out(ok(results, workspace=str(ws)), json_output)
