"""Agentic edit-loop CLI commands."""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..security.edit_loop import apply_edit_plan, build_edit_plan
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import edit_app


@edit_app.command("plan")
def edit_plan(
    path: str = typer.Option(..., "--path", help="Workspace file path"),
    content: str = typer.Option(..., "--content", help="Replacement file content"),
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Preview one safety-gated file edit; no write occurs."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    try:
        plan = build_edit_plan(
            path_arg=path,
            content=content,
            workspace_root=ws,
            policy_name=policy,
        )
    except (KeyError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    _out(ok(plan.model_dump(mode="json"), workspace=str(ws)), json_output)


@edit_app.command("apply")
def edit_apply(
    path: Optional[str] = typer.Option(None, "--path", help="Workspace file path"),
    content: str = typer.Option(..., "--content", help="Replacement file content"),
    plan_id: Optional[str] = typer.Option(None, "--plan-id", help="Apply saved edit plan id"),
    approve: bool = typer.Option(False, "--approve", help="Apply after preview approval"),
    expected_original_hash: Optional[str] = typer.Option(
        None,
        "--expected-original-hash",
        help="Deny if current file hash differs from prior edit plan",
    ),
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Apply one sandbox-approved file edit after explicit approval."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    if not path and not plan_id:
        _out(err(ArcErrorCode.INVALID_INPUT, "--path or --plan-id required"), json_output)
        raise typer.Exit(2)
    try:
        result = apply_edit_plan(
            path_arg=path or "",
            content=content,
            workspace_root=ws,
            policy_name=policy,
            approved=approve,
            expected_original_hash=expected_original_hash,
            plan_id=plan_id,
        )
    except (KeyError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    _out(ok(result, workspace=str(ws)), json_output)
    if not result["applied"]:
        raise typer.Exit(3)
