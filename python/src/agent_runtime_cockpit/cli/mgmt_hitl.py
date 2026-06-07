"""ARC hitl management commands (split from mgmt.py — CR-026)."""

from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

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
from ._subapps import hitl_app


@hitl_app.command("pending")
def hitl_pending(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List pending workspace-local HITL prompts with single-use tokens."""
    _setup_logging(debug)
    from ..audit.hitl_store import get_token, list_prompts

    ws = _workspace(workspace)
    prompts = list_prompts(ws)
    results = []
    for prompt in prompts:
        token = get_token(ws, prompt.hitl_id)
        entry = prompt.model_dump()
        entry["token"] = token
        results.append(entry)
    _out(ok(results, workspace=str(ws)), json_output)
    if not json_output:
        if not results:
            console.print("[dim]No pending HITL prompts.[/dim]")
            return
        table = Table(title="Pending HITL Prompts")
        table.add_column("HITL ID")
        table.add_column("Run ID")
        table.add_column("Token")
        for r in results:
            table.add_row(r["hitl_id"][:12], r["run_id"][:12], r.get("token", "")[:8] + "...")
        console.print(table)


@hitl_app.command("respond")
def hitl_respond(
    hitl_id: str = typer.Argument(..., help="Pending HITL prompt ID"),
    decision: str = typer.Option(..., "--decision", help="approve | reject | modify | skip"),
    token: str = typer.Option(..., "--token", "-t", help="Single-use decision token"),
    notes: str = typer.Option("", "--notes", help="Operator notes"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Respond to a pending workspace-local HITL prompt.

    Requires the single-use token from 'arc hitl pending'.
    """
    _setup_logging(debug)
    from ..audit.hitl import HitlDecision
    from ..audit.hitl_store import respond

    ws = _workspace(workspace)
    try:
        parsed = HitlDecision(decision)
    except ValueError:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid HITL decision: {decision}"), json_output)
        raise typer.Exit(1)
    response = respond(ws, hitl_id, parsed, token=token, notes=notes)
    if response is None:
        _out(
            err(
                ArcErrorCode.RUN_NOT_FOUND,
                f"HITL prompt not found, expired, already responded, or token mismatch: {hitl_id}",
            ),
            json_output,
        )
        raise typer.Exit(1)
    _out(ok(response.model_dump(), workspace=str(ws)), json_output)
    if not json_output:
        console.print(f"[green]HITL {decision} recorded for {hitl_id[:12]}[/green]")


@hitl_app.command("approve")
def hitl_approve(
    hitl_id: str = typer.Argument(..., help="Pending HITL prompt ID"),
    token: str = typer.Option(..., "--token", "-t", help="Single-use decision token"),
    notes: str = typer.Option("", "--notes", help="Operator notes"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Approve a pending workspace-local HITL prompt."""
    hitl_respond(hitl_id, "approve", token, notes, workspace, json_output, debug)


@hitl_app.command("reject")
def hitl_reject(
    hitl_id: str = typer.Argument(..., help="Pending HITL prompt ID"),
    token: str = typer.Option(..., "--token", "-t", help="Single-use decision token"),
    notes: str = typer.Option("", "--notes", help="Operator notes"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Reject a pending workspace-local HITL prompt."""
    hitl_respond(hitl_id, "reject", token, notes, workspace, json_output, debug)
