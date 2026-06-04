"""Execution commands: serve, run (Phase 25.3)."""

from __future__ import annotations

import os
import secrets
from typing import Optional

import typer

from ..gating import GatingError
from ..orchestration import runtime_router
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._app import app, console
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    LOCAL_REAL_GATE_ENVS,
    WORKSPACE_FLAG,
    _local_real_gate_open,
    _out,
    _run_preflight,
    _setup_logging,
    _validate_runtime_mode,
    _workspace,
)


@app.command("tui")
def tui_command(
    resume: Optional[str] = typer.Option(None, "--resume", help="Session ID to resume"),
) -> None:
    """Launch the ARC Studio interactive TUI."""
    from ..tui.app import run_tui

    run_tui(resume_id=resume)


@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(7777, "--port"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Start the ARC HTTP daemon."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    _ensure_daemon_token()
    console.print(f"[bold cyan]ARC[/bold cyan] daemon starting on http://{host}:{port}")
    from ..web.server import run_server

    run_server(host=host, port=port, workspace=ws)


def _ensure_daemon_token() -> None:
    if (
        os.environ.get("ARC_DAEMON_TOKEN")
        or os.environ.get("ARC_DAEMON_ALLOW_UNAUTHENTICATED") == "1"
    ):
        return
    token = secrets.token_urlsafe(32)
    os.environ["ARC_DAEMON_TOKEN"] = token
    console.print("[yellow]ARC_DAEMON_TOKEN was unset; generated a process-local token.[/yellow]")
    console.print(f"ARC_DAEMON_TOKEN={token}")


@app.command("run")
def run_workflow(
    workflow: str = typer.Argument("wf-swarmgraph-fixture", help="Workflow ID"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    runtime: str = typer.Option(
        "auto", "--runtime", "-r", help="Runtime: auto, swarmgraph, langgraph, crewai, lmarena"
    ),
    runtime_mode: str = typer.Option(
        "fake/offline", "--runtime-mode", help="Runtime mode: fake/offline or local-real"
    ),
    prompt: Optional[str] = typer.Option(
        None, "--prompt", help="Prompt passed to runnable adapters"
    ),
    allow_paid_calls: bool = typer.Option(
        False, "--allow-paid-calls", help="Allow runtimes to make provider calls"
    ),
    profile_id: str = typer.Option("local-safe", "--profile-id", help="Run profile ID"),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Inspect run readiness without executing adapters"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Execute a workflow and return the run record."""
    import asyncio

    _setup_logging(debug)
    ws = _workspace(workspace)
    try:
        runtime_mode = _validate_runtime_mode(runtime_mode)
    except typer.BadParameter as exc:
        _out(
            err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": "INVALID_RUNTIME_MODE"}),
            json_output,
        )
        raise typer.Exit(2)
    if dry_run:
        payload = _run_preflight(
            ws, workflow, runtime.lower(), profile_id, allow_paid_calls, runtime_mode
        )
        _out(ok(payload), json_output)
        return
    if (
        runtime.lower() == "langgraph+swarmgraph"
        and runtime_mode == "local-real"
        and not _local_real_gate_open()
    ):
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                "Set ARC_REAL_RUNTIME_SMOKE=1 and ARC_LANGGRAPH_SWARMGRAPH_REAL=1 "
                "to request langgraph+swarmgraph local-real; no provider calls were made",
                details={
                    "code": "LOCAL_REAL_GATE_REQUIRED",
                    "required_env": list(LOCAL_REAL_GATE_ENVS),
                },
            ),
            json_output,
        )
        raise typer.Exit(2)
    from ..security.profiles import GatingError as ProfileGatingError
    from ..security.profiles import ProfileNotFound, enforce_profile, resolve_profile_strict

    try:
        profile = resolve_profile_strict(profile_id)
        enforce_profile(profile, runtime.lower())
    except ProfileNotFound:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Profile '{profile_id}' does not exist",
                details={"code": "UNKNOWN_PROFILE"},
            ),
            json_output,
        )
        raise typer.Exit(2)
    except ProfileGatingError as exc:
        _out(
            err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": "PROFILE_BLOCKED"}),
            json_output,
        )
        raise typer.Exit(2)
    try:
        requested_runtime = (
            [part.strip().lower() for part in runtime.split(",") if part.strip()]
            if "," in runtime
            else runtime.lower()
        )
        routed = runtime_router.resolve(ws, requested_runtime, allow_paid_calls=allow_paid_calls)
    except runtime_router.UnknownRuntime as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": exc.code}), json_output)
        raise typer.Exit(2)
    except runtime_router.RuntimeRouterError as exc:
        _out(err(ArcErrorCode.NOT_IMPLEMENTED, str(exc), details={"code": exc.code}), json_output)
        raise typer.Exit(1)

    if not json_output:
        console.print(f"[dim]Runtime:[/dim] {routed.adapter.adapter_id} ({routed.chosen_by})")

    inputs = {
        "workspace": str(ws),
        "allow_paid_calls": allow_paid_calls,
        "profile_id": profile_id,
        "runtime_mode": runtime_mode,
    }
    if prompt:
        inputs["prompt"] = prompt
    try:
        run_record = asyncio.run(routed.adapter.run_workflow(workflow, inputs))
    except GatingError as exc:
        _out(
            err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": "DUAL_GATE_REQUIRED"}),
            json_output,
        )
        raise typer.Exit(2)

    from ..storage.jsonl import JsonlTraceStore

    store = JsonlTraceStore(ws / ".arc" / "traces")
    trace_path = store.trace_path(run_record.id)
    run_record.metadata["trace_path"] = str(trace_path)
    store.save(run_record)

    _out(ok(run_record.model_dump()), json_output)
    if not json_output:
        console.print(
            f"[green]Run completed:[/green] {run_record.id} ({len(run_record.events)} events)"
        )
