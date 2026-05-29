"""Sandbox CLI commands."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer

from ..isolation.microvm import (
    MicroVMIsolationProvider,
    build_microvm_run_plan,
    generate_firecracker_exec_artifacts,
    generate_firecracker_proof_artifacts,
)
from ..isolation.subprocess import SubprocessIsolationProvider
from ..isolation.vz_provider import VZNoNetworkProof
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..runtime.streaming import stream_subprocess_events
from ..security.sandbox import (
    CommandClassification,
    SandboxPolicy,
    SandboxResult,
    apply_sandbox_policy_yaml,
    approve_command_token,
    approve_decision,
    approve_decision_with_token,
    build_audit_event,
    compact_sandbox_audit_events,
    container_preflight,
    decide,
    ensure_workspace_cwd,
    get_sandbox_audit_event,
    list_sandbox_audit_events,
    list_sandbox_policies,
    parse_relative_time,
    persist_sandbox_audit_event,
    revoke_approval_token,
    prune_expired_approvals,
    render_lima_template,
    resolve_sandbox_policy,
    utc_now,
    validate_command_paths,
    validate_sandbox_policy_config,
    validate_sandbox_policy_yaml,
    verify_sandbox_audit,
)
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import policy_app, sandbox_app, sandbox_audit_app


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
            VZNoNetworkProof().preflight(),
            container_preflight(),
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
    _sandbox_audit_verify_impl(audit_dir, json_output, debug)


@sandbox_audit_app.command("verify")
def sandbox_audit_verify_nested(
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify sandbox audit hash-chain against raw events."""
    _sandbox_audit_verify_impl(audit_dir, json_output, debug)


def _sandbox_audit_verify_impl(audit_dir: Optional[str], json_output: bool, debug: bool) -> None:
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
    command_contains: Optional[str] = typer.Option(
        None, "--command-contains", help="Filter by argv substring"
    ),
    since: Optional[str] = typer.Option(None, "--since", help="Filter started_at >= value"),
    until: Optional[str] = typer.Option(None, "--until", help="Filter started_at <= value"),
    limit: int = typer.Option(50, "--limit", help="Maximum events to return"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List sandbox audit events with optional filters."""
    _sandbox_audit_list_impl(
        audit_dir,
        allowed,
        classification,
        provider,
        command_contains,
        since,
        until,
        limit,
        json_output,
        debug,
    )


@sandbox_audit_app.command("list")
def sandbox_audit_list_nested(
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    allowed: Optional[bool] = typer.Option(
        None, "--allowed/--denied", help="Filter allowed or denied events"
    ),
    classification: Optional[str] = typer.Option(
        None, "--classification", help="Filter by classification"
    ),
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider"),
    command_contains: Optional[str] = typer.Option(
        None, "--command-contains", help="Filter by argv substring"
    ),
    since: Optional[str] = typer.Option(None, "--since", help="Filter started_at >= value"),
    until: Optional[str] = typer.Option(None, "--until", help="Filter started_at <= value"),
    limit: int = typer.Option(50, "--limit", help="Maximum events to return"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List sandbox audit events with optional filters."""
    _sandbox_audit_list_impl(
        audit_dir,
        allowed,
        classification,
        provider,
        command_contains,
        since,
        until,
        limit,
        json_output,
        debug,
    )


def _sandbox_audit_list_impl(
    audit_dir: Optional[str],
    allowed: Optional[bool],
    classification: Optional[str],
    provider: Optional[str],
    command_contains: Optional[str],
    since: Optional[str],
    until: Optional[str],
    limit: int,
    json_output: bool,
    debug: bool,
) -> None:
    _setup_logging(debug)
    result = list_sandbox_audit_events(
        Path(audit_dir).expanduser() if audit_dir else None,
        allowed=allowed,
        classification=classification,
        provider=provider,
        command_contains=command_contains,
        since=since,
        until=until,
        limit=limit,
    )
    _out(ok(result), json_output)


@sandbox_app.command("audit-query")
def sandbox_audit_query(
    from_time: Optional[str] = typer.Option(
        None, "--from", help="Start time: ISO string or relative (e.g. 1h, 30m, 7d)"
    ),
    to_time: Optional[str] = typer.Option(
        None, "--to", help="End time: ISO string or relative (e.g. now, 30m)"
    ),
    classification: Optional[str] = typer.Option(
        None, "--classification", help="Filter by classification"
    ),
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider"),
    allowed: Optional[bool] = typer.Option(
        None, "--allowed/--denied", help="Filter allowed or denied events"
    ),
    command_contains: Optional[str] = typer.Option(
        None, "--command-contains", help="Filter by argv substring"
    ),
    limit: int = typer.Option(100, "--limit", help="Maximum events to return"),
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Rich time-range query over sandbox audit events."""
    _sandbox_audit_query_impl(
        from_time,
        to_time,
        classification,
        provider,
        allowed,
        command_contains,
        limit,
        audit_dir,
        json_output,
        debug,
    )


@sandbox_audit_app.command("query")
def sandbox_audit_query_nested(
    from_time: Optional[str] = typer.Option(
        None, "--from", help="Start time: ISO string or relative (e.g. 1h, 30m, 7d)"
    ),
    to_time: Optional[str] = typer.Option(
        None, "--to", help="End time: ISO string or relative (e.g. now, 30m)"
    ),
    classification: Optional[str] = typer.Option(
        None, "--classification", help="Filter by classification"
    ),
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider"),
    allowed: Optional[bool] = typer.Option(
        None, "--allowed/--denied", help="Filter allowed or denied events"
    ),
    command_contains: Optional[str] = typer.Option(
        None, "--command-contains", help="Filter by argv substring"
    ),
    limit: int = typer.Option(100, "--limit", help="Maximum events to return"),
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Rich time-range query over sandbox audit events."""
    _sandbox_audit_query_impl(
        from_time,
        to_time,
        classification,
        provider,
        allowed,
        command_contains,
        limit,
        audit_dir,
        json_output,
        debug,
    )


def _sandbox_audit_query_impl(
    from_time: Optional[str],
    to_time: Optional[str],
    classification: Optional[str],
    provider: Optional[str],
    allowed: Optional[bool],
    command_contains: Optional[str],
    limit: int,
    audit_dir: Optional[str],
    json_output: bool,
    debug: bool,
) -> None:
    _setup_logging(debug)
    try:
        since = parse_relative_time(from_time, strict=True) if from_time else None
        until = parse_relative_time(to_time, strict=True) if to_time else None
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2) from exc
    result = list_sandbox_audit_events(
        Path(audit_dir).expanduser() if audit_dir else None,
        allowed=allowed,
        classification=classification,
        provider=provider,
        command_contains=command_contains,
        since=since,
        until=until,
        limit=limit,
    )
    _out(ok(result), json_output)


@sandbox_app.command("audit-compact")
def sandbox_audit_compact(
    before: Optional[str] = typer.Option(
        None, "--before", help="ISO timestamp; prune events before this"
    ),
    keep: int = typer.Option(1000, "--keep", help="Keep newest N events when --before omitted"),
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Prune old sandbox audit events (events file only; chain is preserved)."""
    _sandbox_audit_compact_impl(before, keep, audit_dir, json_output, debug)


@sandbox_audit_app.command("compact")
def sandbox_audit_compact_nested(
    before: Optional[str] = typer.Option(
        None, "--before", help="ISO timestamp; prune events before this"
    ),
    keep: int = typer.Option(1000, "--keep", help="Keep newest N events when --before omitted"),
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Prune old sandbox audit events (events file only; chain is preserved)."""
    _sandbox_audit_compact_impl(before, keep, audit_dir, json_output, debug)


def _sandbox_audit_compact_impl(
    before: Optional[str],
    keep: int,
    audit_dir: Optional[str],
    json_output: bool,
    debug: bool,
) -> None:
    _setup_logging(debug)
    try:
        result = compact_sandbox_audit_events(
            before=before,
            keep=keep,
            audit_dir=Path(audit_dir).expanduser() if audit_dir else None,
        )
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2) from exc
    _out(ok(result), json_output)
    if not result.get("ok", True):
        raise typer.Exit(1)


@sandbox_app.command("audit-show")
def sandbox_audit_show(
    audit_id: str = typer.Argument(..., help="Sandbox audit event ID"),
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show one sandbox audit event by ID."""
    _sandbox_audit_show_impl(audit_id, audit_dir, json_output, debug)


@sandbox_audit_app.command("show")
def sandbox_audit_show_nested(
    audit_id: str = typer.Argument(..., help="Sandbox audit event ID"),
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show one sandbox audit event by ID."""
    _sandbox_audit_show_impl(audit_id, audit_dir, json_output, debug)


def _sandbox_audit_show_impl(
    audit_id: str, audit_dir: Optional[str], json_output: bool, debug: bool
) -> None:
    _setup_logging(debug)
    result = get_sandbox_audit_event(
        audit_id,
        Path(audit_dir).expanduser() if audit_dir else None,
    )
    _out(ok(result), json_output)
    if not result["found"]:
        raise typer.Exit(4)


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
    "microvm-plan", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def sandbox_microvm_plan(
    ctx: typer.Context,
    provider: str = typer.Option(
        "lima", "--provider", help="MicroVM plan provider: lima or firecracker"
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Render a non-executing microVM run plan."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    command = list(ctx.args)
    try:
        ensure_workspace_cwd(Path.cwd(), ws)
        plan = build_microvm_run_plan(provider, command, workspace_root=ws)
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    _out(ok(plan.model_dump(mode="json"), workspace=str(ws)), json_output)


@sandbox_app.command("firecracker-artifacts")
def sandbox_firecracker_artifacts(
    output: str = typer.Option(..., "--output", help="Output directory for proof artifacts"),
    exec_rootfs: bool = typer.Option(
        False,
        "--exec-rootfs",
        help="Generate ARC Firecracker execution init/rootfs artifacts instead of proof-only artifacts",
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate Firecracker proof or execution artifacts; does not boot a VM."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    report = (
        generate_firecracker_exec_artifacts(Path(output).expanduser())
        if exec_rootfs
        else generate_firecracker_proof_artifacts(Path(output).expanduser())
    )
    _out(ok(report.model_dump(mode="json"), workspace=str(ws)), json_output)


@sandbox_app.command(
    "run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def sandbox_run(
    ctx: typer.Context,
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    provider: str = typer.Option(
        "subprocess", "--provider", help="Isolation provider (subprocess, microvm)"
    ),
    ask: bool = typer.Option(False, "--ask", help="Prompt for network/install/unknown approval"),
    approval_token: Optional[str] = typer.Option(
        None, "--approval-token", help="Use a scoped non-interactive approval token"
    ),
    stream_json: bool = typer.Option(False, "--stream-json", help="Emit JSONL stream events"),
    cancel_after_events: Optional[int] = typer.Option(
        None, "--cancel-after-events", help="Deterministically cancel after N output events"
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
                provider=provider,
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
                provider=provider,
                audit_event=audit,
            )
            _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
            raise typer.Exit(3)

    if stream_json and provider != "subprocess":
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                "--stream-json currently supports subprocess provider only",
            ),
            json_output,
        )
        raise typer.Exit(2)
    if stream_json:
        events, stream_result = stream_subprocess_events(
            command,
            cwd=cwd,
            source="sandbox",
            timeout_seconds=policy_model.timeout_seconds,
            max_output_bytes=policy_model.max_output_bytes,
            cancel_after_events=cancel_after_events,
            safe_env_keys=frozenset(policy_model.env_allowlist),
        )
        for event in events:
            typer.echo(
                json.dumps(
                    ok(event.model_dump(mode="json"), workspace=str(ws)).model_dump(mode="json"),
                    sort_keys=True,
                )
            )
        if stream_result.terminal_event.value in {"cancelled", "timeout"}:
            raise typer.Exit(130 if stream_result.terminal_event.value == "cancelled" else 124)
        if stream_result.exit_code not in (0, None):
            raise typer.Exit(stream_result.exit_code)
        return

    try:
        iso = asyncio.run(
            _build_provider(
                provider,
                policy_model,
                ws,
                read_write_workspace=decision.classification
                == CommandClassification.WRITES_WORKSPACE,
            ).execute(command, cwd=cwd, timeout_seconds=policy_model.timeout_seconds)
        )
    except NotImplementedError as exc:
        ended_at = utc_now()
        denied = decision.model_copy(
            update={
                "allowed": False,
                "reason": str(exc),
                "approval_required": False,
                "approved": False,
            }
        )
        audit = build_audit_event(
            command=command,
            cwd=cwd,
            decision=denied,
            provider=provider,
            started_at=started_at,
            ended_at=ended_at,
            exit_code=None,
            stdout_truncated=False,
            stderr_truncated=False,
            redaction_applied=False,
        )
        audit["public_execution_enabled"] = False
        audit["contract_doc"] = "docs/adr/ADR-024-microvm-public-execution-contract.md"
        audit_path = persist_sandbox_audit_event(audit)
        audit["audit_path"] = str(audit_path)
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    ended_at = utc_now()
    audit = build_audit_event(
        command=command,
        cwd=cwd,
        decision=decision,
        provider=iso.provider if iso.provider != "unknown" else provider,
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
        provider=iso.provider if iso.provider != "unknown" else provider,
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


@sandbox_app.command(
    "inspect", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def sandbox_inspect(
    ctx: typer.Context,
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    timeout: int = typer.Option(30, "--timeout", help="Timeout in seconds"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Inspect an MCP server through the sandbox.

    The server command is classified and approved by the sandbox policy.
    Network commands are denied by default. Destructive commands are denied.
    Output is capped.
    """
    _setup_logging(debug)
    command = list(ctx.args)
    ws = _workspace(workspace)

    if not command:
        _out(err(ArcErrorCode.INVALID_INPUT, "missing server command"), json_output)
        raise typer.Exit(2)

    try:
        policy_model = _policy(policy, ws)
        decision = decide(command, policy_model)
    except (ValueError, typer.BadParameter) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)

    if not decision.allowed:
        _out(
            ok(
                {
                    "command": command,
                    "classification": decision.classification.value,
                    "decision": "denied",
                    "reason": decision.reason,
                    "policy": policy_model.name,
                },
                workspace=str(ws),
            ),
            json_output,
        )
        raise typer.Exit(3)

    try:
        from ..cli.mcp import _inspect_server

        result = _inspect_server(server_cmd=command, workspace=ws, timeout=float(timeout))
    except Exception as exc:
        _out(err(ArcErrorCode.INTERNAL_ERROR, str(exc)), json_output)
        raise typer.Exit(1)

    if "error" in result:
        _out(err(ArcErrorCode.INTERNAL_ERROR, result["error"]), json_output)
        raise typer.Exit(1)

    _out(
        ok(
            {
                "command": command,
                "classification": decision.classification.value,
                "decision": "allowed",
                "policy": policy_model.name,
                "tools": result.get("tools", []),
                "resources": result.get("resources", []),
                "prompts": result.get("prompts", []),
                "stderr": result.get("stderr"),
            },
            workspace=str(ws),
        ),
        json_output,
    )


def _build_provider(
    name: str,
    policy_model: SandboxPolicy,
    ws: Path,
    *,
    read_write_workspace: bool = False,
) -> "SubprocessIsolationProvider | MicroVMIsolationProvider":
    if name == "microvm":
        return MicroVMIsolationProvider(
            workspace_root=ws, max_output_bytes=policy_model.max_output_bytes
        )
    if name == "container":
        from ..isolation.docker_provider import SubprocessContainerProvider

        return SubprocessContainerProvider(
            workspace_root=ws,
            max_output_bytes=policy_model.max_output_bytes,
            read_write_workspace=read_write_workspace,
            safe_env_keys=frozenset(policy_model.env_allowlist),
        )
    return SubprocessIsolationProvider(
        safe_env_keys=frozenset(policy_model.env_allowlist),
        workspace_root=ws,
        max_output_bytes=policy_model.max_output_bytes,
    )


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
    try:
        policies = [p.model_dump(mode="json") for p in list_sandbox_policies(ws)]
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1) from exc
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


@policy_app.command("validate-yaml")
def policy_validate_yaml(
    file: str = typer.Option(..., "--file", help="YAML policy file to validate"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Validate a YAML sandbox policy file."""
    _setup_logging(debug)
    result = validate_sandbox_policy_yaml(Path(file).expanduser())
    _out(ok(result), json_output)
    if not result["ok"]:
        raise typer.Exit(1)


@policy_app.command("apply")
def policy_apply(
    file: str = typer.Option(..., "--file", help="YAML policy file to apply"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    target: Optional[str] = typer.Option(None, "--target", help="Override target path"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Apply a YAML policy file to the workspace .arc directory."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    result = apply_sandbox_policy_yaml(
        Path(file).expanduser(),
        ws,
        target_path=Path(target).expanduser() if target else None,
    )
    _out(ok(result), json_output)
    if not result["ok"]:
        raise typer.Exit(1)
