"""Plan CLI commands for Plan/Apply/Review loop (Phase 75).

Provides ``arc plan explain`` to show what a command or sequence of
commands would do under the sandbox policy, including classification,
file intents, approval requirements, and known/unknown cost/risk.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Optional

import typer

from ..config.loader import load_config
from ..isolation.selector import build_execution_provider, resolve_isolation_backend
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..security.plan import (
    PlanApplyResult,
    approve_plan,
    build_plan,
    build_plan_apply_event,
    load_plan_record,
    persist_plan_audit_event,
    persist_plan_event,
    persist_plan_record,
    sandbox_result_from_isolation,
    verify_plan_approval,
)
from ..security.sandbox import (
    CommandClassification,
    approve_decision_with_token,
    decide,
    ensure_workspace_cwd,
    resolve_sandbox_policy,
    utc_now,
    validate_command_paths,
)
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import plan_app

DIRECT_CONFIRMATION = "APPLY DIRECT COMMAND"


@plan_app.command(
    "explain",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def plan_explain(
    ctx: typer.Context,
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Explain what a command or sequence would do under the sandbox policy.

    Returns a plan envelope with classification, file intents, sandbox
    decisions, approval requirements, and known/unknown cost/risk estimates.
    No commands are executed.
    """
    _setup_logging(debug)
    ws = _workspace(workspace)
    raw_args = list(ctx.args)

    if not raw_args:
        _out(err(ArcErrorCode.INVALID_INPUT, "missing command"), json_output)
        raise typer.Exit(2)

    try:
        policy_model = resolve_sandbox_policy(policy, ws)
    except (KeyError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)

    commands = _parse_command_sequence(raw_args)
    plan = build_plan(commands, policy_model)
    audit_path = persist_plan_audit_event(plan, ws)
    plan_path = persist_plan_record(plan, ws)

    payload = plan.model_dump(mode="json")
    payload["audit_path"] = str(audit_path)
    payload["plan_path"] = str(plan_path)
    _out(ok(payload, workspace=str(ws)), json_output)


@plan_app.command("approve")
def plan_approve(
    plan_id: str = typer.Option(..., "--plan-id", help="Persisted plan id to approve"),
    token: Optional[str] = typer.Option(
        None, "--token", help="Approval token; generated if omitted"
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Approve an existing plan record and return a scoped token."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    raw_token = token or f"plan-{uuid.uuid4().hex}"
    try:
        plan = load_plan_record(ws, plan_id)
        approval = approve_plan(plan, raw_token, ws)
    except ValueError as exc:
        event = build_plan_apply_event(
            "plan_apply_denied",
            plan_id=plan_id,
            policy="unknown",
            workspace_root=ws,
            reason=str(exc),
        )
        audit_path = persist_plan_event(event, ws)
        _out(
            err(ArcErrorCode.PERMISSION_DENIED, str(exc), {"audit_path": str(audit_path)}),
            json_output,
        )
        raise typer.Exit(3)

    event = build_plan_apply_event(
        "plan_approval_accepted",
        plan_id=plan.plan_id,
        policy=plan.policy,
        workspace_root=ws,
        reason="approval accepted",
        approval_id=approval.approval_id,
    )
    audit_path = persist_plan_event(event, ws)
    _out(
        ok(
            {
                "approved": True,
                "plan_id": plan.plan_id,
                "approval_id": approval.approval_id,
                "approval_token": raw_token,
                "audit_path": str(audit_path),
            },
            workspace=str(ws),
        ),
        json_output,
    )


@plan_app.command(
    "apply", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def plan_apply(
    ctx: typer.Context,
    plan_id: Optional[str] = typer.Option(None, "--plan-id", help="Persisted plan id to apply"),
    approval_token: Optional[str] = typer.Option(
        None, "--approval-token", help="Approval token returned by plan approve"
    ),
    policy: str = typer.Option(
        "local-safe", "--policy", help="Sandbox policy profile for direct command"
    ),
    direct: bool = typer.Option(
        False, "--direct", help="Apply direct argv instead of persisted plan"
    ),
    confirm: Optional[str] = typer.Option(
        None, "--confirm", help=f"Required direct confirmation: {DIRECT_CONFIRMATION}"
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Apply an approved plan through the sandbox path."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    raw_args = list(ctx.args)
    try:
        cwd = ensure_workspace_cwd(ws, ws)
        if direct:
            if confirm != DIRECT_CONFIRMATION:
                raise PermissionError(f"direct apply requires --confirm '{DIRECT_CONFIRMATION}'")
            if not raw_args:
                raise ValueError("missing command")
            policy_model = resolve_sandbox_policy(policy, ws)
            plan = build_plan(_parse_command_sequence(raw_args), policy_model)
            approval_id = "direct-command-override"
        else:
            if raw_args:
                raise ValueError("plan apply accepts argv only with --direct")
            if not plan_id:
                raise ValueError("--plan-id required unless --direct is used")
            plan = load_plan_record(ws, plan_id)
            policy_model = resolve_sandbox_policy(plan.policy, ws)
            approval = verify_plan_approval(plan, approval_token, ws)
            approval_id = approval.approval_id
    except PermissionError as exc:
        event = build_plan_apply_event(
            "plan_apply_denied",
            plan_id=plan_id or "direct",
            policy=policy,
            workspace_root=ws,
            reason=str(exc),
        )
        audit_path = persist_plan_event(event, ws)
        _out(
            err(ArcErrorCode.PERMISSION_DENIED, str(exc), {"audit_path": str(audit_path)}),
            json_output,
        )
        raise typer.Exit(3)
    except (KeyError, ValueError) as exc:
        event = build_plan_apply_event(
            "plan_apply_denied",
            plan_id=plan_id or "direct",
            policy=policy,
            workspace_root=ws,
            reason=str(exc),
        )
        audit_path = persist_plan_event(event, ws)
        code = (
            ArcErrorCode.PERMISSION_DENIED
            if "approval" in str(exc) or "approved plan" in str(exc)
            else ArcErrorCode.INVALID_INPUT
        )
        _out(err(code, str(exc), {"audit_path": str(audit_path)}), json_output)
        raise typer.Exit(3 if code == ArcErrorCode.PERMISSION_DENIED else 2)

    denial = _plan_static_denial(plan)
    if denial:
        event = build_plan_apply_event(
            "plan_apply_denied",
            plan_id=plan.plan_id,
            policy=plan.policy,
            workspace_root=ws,
            reason=denial,
            approval_id=approval_id,
        )
        audit_path = persist_plan_event(event, ws)
        result = PlanApplyResult(
            plan_id=plan.plan_id,
            policy=plan.policy,
            workspace_root=str(ws),
            approved=not direct,
            applied=False,
            reason=denial,
            audit_events=[{**event, "audit_path": str(audit_path)}],
        )
        _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
        raise typer.Exit(3)

    started_event = build_plan_apply_event(
        "plan_apply_attempted",
        plan_id=plan.plan_id,
        policy=plan.policy,
        workspace_root=ws,
        reason="apply attempted",
        approval_id=approval_id,
    )
    started_path = persist_plan_event(started_event, ws)
    events = [{**started_event, "audit_path": str(started_path)}]
    results = []
    provider = build_execution_provider(
        resolve_isolation_backend(load_config(ws)),
        workspace_root=ws,
        env_allowlist=frozenset(policy_model.env_allowlist),
        max_output_bytes=policy_model.max_output_bytes,
    )
    for step in plan.steps:
        command = step.command
        decision = decide(command, policy_model)
        if decision.approval_required:
            decision = approve_decision_with_token(
                token=approval_token,
                command=command,
                policy=policy_model,
                decision=decision,
            )
        if not decision.allowed:
            reason = (
                f"sandbox approval required for {decision.classification.value} command"
                if decision.approval_required
                else decision.reason
            )
            event = build_plan_apply_event(
                "plan_apply_denied",
                plan_id=plan.plan_id,
                policy=plan.policy,
                workspace_root=ws,
                reason=reason,
                approval_id=approval_id,
                command=command,
                classification=decision.classification.value,
                approval_required=decision.approval_required,
            )
            audit_path = persist_plan_event(event, ws)
            result = PlanApplyResult(
                plan_id=plan.plan_id,
                policy=plan.policy,
                workspace_root=str(ws),
                approved=not direct,
                applied=False,
                reason=reason,
                audit_events=[*events, {**event, "audit_path": str(audit_path)}],
                results=results,
            )
            _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
            raise typer.Exit(3)
        try:
            validate_command_paths(command, policy_model)
        except ValueError as exc:
            event = build_plan_apply_event(
                "plan_apply_denied",
                plan_id=plan.plan_id,
                policy=plan.policy,
                workspace_root=ws,
                reason=str(exc),
                approval_id=approval_id,
                command=command,
            )
            audit_path = persist_plan_event(event, ws)
            result = PlanApplyResult(
                plan_id=plan.plan_id,
                policy=plan.policy,
                workspace_root=str(ws),
                approved=not direct,
                applied=False,
                reason=str(exc),
                audit_events=[*events, {**event, "audit_path": str(audit_path)}],
                results=results,
            )
            _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
            raise typer.Exit(3)
        started_at = utc_now()
        iso = asyncio.run(
            provider.execute(command, cwd=cwd, timeout_seconds=policy_model.timeout_seconds)
        )
        ended_at = utc_now()
        sandbox_result = sandbox_result_from_isolation(
            command=command,
            cwd=cwd,
            decision=decision,
            provider="subprocess",
            iso=iso,
            started_at=started_at,
            ended_at=ended_at,
        )
        results.append(sandbox_result)
        if iso.exit_code != 0:
            event = build_plan_apply_event(
                "plan_apply_failed",
                plan_id=plan.plan_id,
                policy=plan.policy,
                workspace_root=ws,
                reason="command failed",
                approval_id=approval_id,
                command=command,
                exit_code=iso.exit_code,
            )
            audit_path = persist_plan_event(event, ws)
            result = PlanApplyResult(
                plan_id=plan.plan_id,
                policy=plan.policy,
                workspace_root=str(ws),
                approved=not direct,
                applied=False,
                reason="command failed",
                audit_events=[*events, {**event, "audit_path": str(audit_path)}],
                results=results,
            )
            _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
            raise typer.Exit(iso.exit_code)

    completed = build_plan_apply_event(
        "plan_apply_completed",
        plan_id=plan.plan_id,
        policy=plan.policy,
        workspace_root=ws,
        reason="apply completed",
        approval_id=approval_id,
        exit_code=0,
    )
    completed_path = persist_plan_event(completed, ws)
    events.append({**completed, "audit_path": str(completed_path)})
    result = PlanApplyResult(
        plan_id=plan.plan_id,
        policy=plan.policy,
        workspace_root=str(ws),
        approved=not direct,
        applied=True,
        reason="apply completed",
        audit_events=events,
        results=results,
    )
    _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)


def _parse_command_sequence(args: list[str]) -> list[list[str]]:
    """Parse a flat argument list into a sequence of commands.

    Commands are separated by ``--`` tokens. If no ``--`` is present,
    the entire argument list is treated as a single command.
    """
    commands: list[list[str]] = []
    current: list[str] = []
    for arg in args:
        if arg == "--":
            if current:
                commands.append(current)
            current = []
        else:
            current.append(arg)
    if current:
        commands.append(current)
    return commands


def _plan_static_denial(plan) -> str | None:
    for step in plan.steps:
        if step.classification in {
            CommandClassification.DESTRUCTIVE,
            CommandClassification.PRIVILEGED,
        }:
            return "destructive or privileged commands denied"
    return None
