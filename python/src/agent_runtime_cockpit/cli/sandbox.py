"""Sandbox CLI commands."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Optional

import typer

from ..isolation.microvm import MicroVMIsolationProvider
from ..isolation.subprocess import SubprocessIsolationProvider
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..security.sandbox import (
    SandboxPolicy,
    SandboxResult,
    approve_command_token,
    approve_decision,
    approve_decision_with_token,
    build_audit_event,
    decide,
    ensure_workspace_cwd,
    list_sandbox_audit_events,
    list_sandbox_policies,
    persist_sandbox_audit_event,
    revoke_approval_token,
    prune_expired_approvals,
    render_lima_template,
    resolve_sandbox_policy,
    utc_now,
    validate_command_paths,
    validate_sandbox_policy_config,
    verify_sandbox_audit,
)
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import policy_app, sandbox_app


def _policy(name: str, workspace: Path) -> SandboxPolicy:
    try:
        return resolve_sandbox_policy(name, workspace)
    except (KeyError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@sandbox_app.command("doctor")
def sandbox_doctor(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Report sandbox and microVM provider preflight state."""
    _setup_logging(debug)
    subprocess_provider = SubprocessIsolationProvider()
    microvm_provider = MicroVMIsolationProvider()
    data = {
        "providers": [
            subprocess_provider.describe(),
            microvm_provider.describe(),
        ]
    }
    _out(ok(data), json_output)


@sandbox_app.command("audit-verify")
def sandbox_audit_verify(
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify sandbox audit hash-chain against raw events."""
    _setup_logging(debug)
    result = verify_sandbox_audit(Path(audit_dir).expanduser() if audit_dir else None)
    _out(ok(result), json_output)
    if not result["ok"]:
        raise typer.Exit(1)


@sandbox_app.command("audit-list")
def sandbox_audit_list(
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    allowed: Optional[bool] = typer.Option(
        None, "--allowed/--denied", help="Filter allowed or denied events"
    ),
    classification: Optional[str] = typer.Option(
        None, "--classification", help="Filter by classification"
    ),
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider"),
    limit: int = typer.Option(50, "--limit", help="Maximum events to return"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List sandbox audit events with optional filters."""
    _setup_logging(debug)
    result = list_sandbox_audit_events(
        Path(audit_dir).expanduser() if audit_dir else None,
        allowed=allowed,
        classification=classification,
        provider=provider,
        limit=limit,
    )
    _out(ok(result), json_output)


@sandbox_app.command("lima-template")
def sandbox_lima_template(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Render experimental Lima template; does not execute a VM."""
    _setup_logging(debug)
    if not __import__("os").environ.get("ARC_MICROVM_EXPERIMENTAL"):
        _out(
            err(
                ArcErrorCode.INVALID_INPUT, "Set ARC_MICROVM_EXPERIMENTAL=1 to render Lima template"
            ),
            json_output,
        )
        raise typer.Exit(2)
    ws = _workspace(workspace)
    template = render_lima_template(ws)
    _out(ok({"template": template, "execution": "not_implemented"}, workspace=str(ws)), json_output)


@sandbox_app.command(
    "run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def sandbox_run(
    ctx: typer.Context,
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    ask: bool = typer.Option(False, "--ask", help="Prompt for network/install/unknown approval"),
    approval_token: Optional[str] = typer.Option(
        None, "--approval-token", help="Use a scoped non-interactive approval token"
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run argv under the local sandbox policy."""
    _setup_logging(debug)
    command = list(ctx.args)
    ws = _workspace(workspace)
    try:
        policy_model = _policy(policy, ws)
        cwd = ensure_workspace_cwd(Path.cwd(), ws)
        decision = decide(command, policy_model)
        decision = approve_decision_with_token(
            token=approval_token, command=command, policy=policy_model, decision=decision
        )
    except (ValueError, typer.BadParameter) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    started_at = utc_now()
    ended_at = started_at
    if not command:
        _out(err(ArcErrorCode.INVALID_INPUT, "missing command"), json_output)
        raise typer.Exit(2)
    try:
        validate_command_paths(command, policy_model)
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    if not decision.allowed:
        if ask and json_output:
            _out(err(ArcErrorCode.INVALID_INPUT, "--ask requires non-JSON output"), json_output)
            raise typer.Exit(2)
        if (
            ask
            and decision.approval_required
            and typer.confirm(
                f"Approve {decision.classification.value} command under policy {policy_model.name}?",
                default=False,
            )
        ):
            decision = approve_decision(decision)
        else:
            audit = build_audit_event(
                command=command,
                cwd=cwd,
                decision=decision,
                provider="subprocess",
                started_at=started_at,
                ended_at=ended_at,
                exit_code=None,
                stdout_truncated=False,
                stderr_truncated=False,
                redaction_applied=False,
            )
            audit_path = persist_sandbox_audit_event(audit)
            audit["audit_path"] = str(audit_path)
            result = SandboxResult(
                command=command,
                cwd=str(cwd),
                classification=decision.classification,
                decision=decision,
                provider="subprocess",
                audit_event=audit,
            )
            _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
            raise typer.Exit(3)

    provider = SubprocessIsolationProvider(
        safe_env_keys=frozenset(policy_model.env_allowlist),
        workspace_root=ws,
        max_output_bytes=policy_model.max_output_bytes,
    )
    iso = asyncio.run(
        provider.execute(command, cwd=cwd, timeout_seconds=policy_model.timeout_seconds)
    )
    ended_at = utc_now()
    audit = build_audit_event(
        command=command,
        cwd=cwd,
        decision=decision,
        provider=provider.provider_id,
        started_at=started_at,
        ended_at=ended_at,
        exit_code=iso.exit_code,
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
    )
    audit_path = persist_sandbox_audit_event(audit)
    audit["audit_path"] = str(audit_path)
    result = SandboxResult(
        command=command,
        cwd=str(cwd),
        classification=decision.classification,
        decision=decision,
        provider=provider.provider_id,
        exit_code=iso.exit_code,
        stdout=iso.stdout,
        stderr=iso.stderr,
        duration_ms=iso.duration_ms,
        timed_out=iso.killed and iso.kill_reason == "timeout",
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
        audit_event=audit,
    )
    _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
    if iso.exit_code != 0:
        raise typer.Exit(iso.exit_code)


@policy_app.command(
    "explain", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def policy_explain(
    ctx: typer.Context,
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Explain sandbox decision for argv without executing it."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    policy_model = _policy(policy, ws)
    command = list(ctx.args)
    decision = decide(command, policy_model)
    try:
        validate_command_paths(command, policy_model)
    except ValueError as exc:
        decision = decision.model_copy(update={"allowed": False, "reason": str(exc)})
    _out(
        ok({"command": command, "decision": decision.model_dump(mode="json")}, workspace=str(ws)),
        json_output,
    )


@policy_app.command(
    "approve", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def policy_approve(
    ctx: typer.Context,
    token: str = typer.Option(..., "--token", help="Approval token to bind"),
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Persist scoped approval for a command token."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    command = list(ctx.args)
    if not command:
        _out(err(ArcErrorCode.INVALID_INPUT, "missing command"), json_output)
        raise typer.Exit(2)
    try:
        policy_model = _policy(policy, ws)
        approval = approve_command_token(token=token, command=command, policy=policy_model)
    except (ValueError, typer.BadParameter) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    _out(
        ok(
            {
                "approved": True,
                "policy": approval.policy,
                "classification": approval.classification.value,
                "command_hash": approval.command_hash,
                "workspace_root": approval.workspace_root,
            },
            workspace=str(ws),
        ),
        json_output,
    )


@policy_app.command("revoke")
def policy_revoke(
    token: str = typer.Option(..., "--token", help="Approval token to revoke"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Revoke all approvals for a token."""
    _setup_logging(debug)
    _out(ok(revoke_approval_token(token)), json_output)


@policy_app.command("prune")
def policy_prune(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Remove expired approvals from the store."""
    _setup_logging(debug)
    _out(ok(prune_expired_approvals()), json_output)


@policy_app.command("list")
def policy_list(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List built-in and configured sandbox policies."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    policies = [p.model_dump(mode="json") for p in list_sandbox_policies(ws)]
    _out(ok({"policies": policies}, workspace=str(ws)), json_output)


@policy_app.command("show")
def policy_show(
    name: str = typer.Argument(..., help="Policy name"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show a configured sandbox policy."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    try:
        policy = resolve_sandbox_policy(name, ws)
    except (KeyError, ValueError) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1)
    _out(ok(policy.model_dump(mode="json"), workspace=str(ws)), json_output)


@policy_app.command("validate")
def policy_validate(
    config: Optional[str] = typer.Option(None, "--config", help="Sandbox policy config path"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Validate sandbox policy config schema."""
    _setup_logging(debug)
    result = validate_sandbox_policy_config(Path(config).expanduser() if config else None)
    _out(ok(result), json_output)
    if not result["ok"]:
        raise typer.Exit(1)
