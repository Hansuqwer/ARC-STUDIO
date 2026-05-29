"""Agentic edit-loop CLI commands."""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..security.edit_loop import (
    apply_edit_bundle,
    apply_edit_plan,
    approve_edit_plan,
    build_edit_bundle,
    build_edit_plan,
    edit_plan_status,
    list_edit_plan_records,
    load_edit_plan_record,
)
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import edit_app


@edit_app.command("plan")
def edit_plan(
    path: Optional[str] = typer.Option(None, "--path", help="Workspace file path"),
    content: Optional[str] = typer.Option(None, "--content", help="Replacement file content"),
    edit: list[str] = typer.Option([], "--edit", help="Bundle edit as path=text; may be repeated"),
    patch: Optional[str] = typer.Option(None, "--patch", help="Narrow unified diff for --path"),
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Preview one safety-gated file edit; no write occurs."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    try:
        if edit:
            plan = build_edit_bundle(
                edits=[_parse_edit_item(item) for item in edit],
                workspace_root=ws,
                policy_name=policy,
            )
        elif patch is not None:
            if not path:
                raise ValueError("--path required with --patch")
            plan = build_edit_bundle(
                edits=[{"path": path, "patch": patch}], workspace_root=ws, policy_name=policy
            )
        else:
            if not path or content is None:
                raise ValueError("--path and --content required")
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
    content: Optional[str] = typer.Option(None, "--content", help="Replacement file content"),
    edit: list[str] = typer.Option([], "--edit", help="Bundle edit as path=text; may be repeated"),
    patch: Optional[str] = typer.Option(None, "--patch", help="Narrow unified diff for --path"),
    plan_id: Optional[str] = typer.Option(None, "--plan-id", help="Apply saved edit plan id"),
    approval_token: Optional[str] = typer.Option(
        None, "--approval-token", help="Token from edit approve"
    ),
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
    if not path and not plan_id and not edit:
        _out(err(ArcErrorCode.INVALID_INPUT, "--path, --plan-id, or --edit required"), json_output)
        raise typer.Exit(2)
    try:
        if edit:
            result = apply_edit_bundle(
                edits=[_parse_edit_item(item) for item in edit],
                workspace_root=ws,
                policy_name=policy,
                approved=approve,
                plan_id=plan_id,
                approval_token=approval_token,
            )
        elif patch is not None:
            if not path:
                raise ValueError("--path required with --patch")
            result = apply_edit_bundle(
                edits=[{"path": path, "patch": patch}],
                workspace_root=ws,
                policy_name=policy,
                approved=approve,
                plan_id=plan_id,
                approval_token=approval_token,
            )
        else:
            if content is None:
                raise ValueError("--content required")
            result = apply_edit_plan(
                path_arg=path or "",
                content=content,
                workspace_root=ws,
                policy_name=policy,
                approved=approve,
                expected_original_hash=expected_original_hash,
                plan_id=plan_id,
                approval_token=approval_token,
            )
    except (KeyError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    _out(ok(result, workspace=str(ws)), json_output)
    if not result["applied"]:
        raise typer.Exit(3)


@edit_app.command("list")
def edit_list(
    limit: int = typer.Option(50, "--limit", help="Maximum plans to return"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List saved edit plans for IDE/CLI bridge use."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    plans = []
    for plan in list_edit_plan_records(ws, limit=limit):
        payload = plan.model_dump(mode="json")
        payload["status"] = edit_plan_status(ws, plan)
        plans.append(payload)
    _out(ok({"plans": plans, "count": len(plans)}, workspace=str(ws)), json_output)


@edit_app.command("show")
def edit_show(
    plan_id: str = typer.Option(..., "--plan-id", help="Saved edit plan id"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show one saved edit plan without replacement content."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    try:
        plan = load_edit_plan_record(ws, plan_id)
    except (OSError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    payload = plan.model_dump(mode="json")
    payload["status"] = edit_plan_status(ws, plan)
    _out(ok(payload, workspace=str(ws)), json_output)


@edit_app.command("approve")
def edit_approve(
    plan_id: str = typer.Option(..., "--plan-id", help="Saved edit plan id"),
    token: str = typer.Option(..., "--token", help="Approval token to bind"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Approve a saved edit plan by exact metadata hash."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    try:
        approval = approve_edit_plan(ws, plan_id, token)
    except (OSError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    _out(ok(approval.model_dump(mode="json"), workspace=str(ws)), json_output)


def _parse_edit_item(value: str) -> dict[str, str]:
    if "=" not in value:
        raise ValueError("--edit must use path=text")
    path, content = value.split("=", 1)
    if not path:
        raise ValueError("--edit path is empty")
    return {"path": path, "content": content}
