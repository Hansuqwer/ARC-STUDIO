"""Sandbox CLI commands."""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Optional

import typer

from ..config.loader import load_config
from ..isolation.base import IsolationProvider
from ..isolation.microvm import (
    MicroVMIsolationProvider,
    build_microvm_run_plan,
    firecracker_proof_gates,
    generate_firecracker_exec_artifacts,
    generate_firecracker_proof_artifacts,
)
from ..isolation.selector import build_execution_provider, resolve_isolation_backend
from ..isolation.subprocess import SubprocessIsolationProvider
from ..isolation.vz_provider import (
    VZNoNetworkProof,
    generate_vz_exec_init_artifacts,
    generate_vz_proof_artifacts,
    vz_public_exec_gates,
)
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
    attach_microvm_audit_contract_fields,
    compact_sandbox_audit_events,
    container_preflight,
    decide,
    landlock_preflight,
    ensure_workspace_cwd,
    get_sandbox_audit_event,
    CommandRuleVerdict,
    add_command_rule,
    interpret_exit_code,
    list_command_rules,
    list_sandbox_audit_events,
    list_sandbox_policies,
    remove_command_rule,
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

log = logging.getLogger(__name__)


def _policy(name: str, workspace: Path) -> SandboxPolicy:
    try:
        return resolve_sandbox_policy(name, workspace)
    except (KeyError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc


def _persist_audit_safely(audit: dict) -> dict:
    """Persist a sandbox audit event without ever fail-opening on write error.

    The decision (allow/deny) has already been made by the caller; this only
    records it. If the audit log cannot be written we log the failure and mark
    the event, but the security decision still stands — a broken audit sink must
    never turn a denial into an allow.
    """
    try:
        audit_path = persist_sandbox_audit_event(audit)
        audit["audit_path"] = str(audit_path)
    except OSError as exc:
        log.error("sandbox audit persistence failed: %s", exc)
        audit["audit_path"] = None
        audit["audit_persisted"] = False
    return audit


def _persist_sandbox_denial(
    *,
    command: list[str],
    cwd: Path,
    decision,
    provider: str,
    started_at: str,
    reason: str,
    reason_code=None,
) -> dict:
    update: dict = {
        "allowed": False,
        "reason": reason,
        "approval_required": False,
        "approved": False,
    }
    if reason_code is not None:
        update["reason_code"] = reason_code
    denied = decision.model_copy(update=update)
    audit = build_audit_event(
        command=command,
        cwd=cwd,
        decision=denied,
        provider=provider,
        started_at=started_at,
        ended_at=utc_now(),
        exit_code=None,
        stdout_truncated=False,
        stderr_truncated=False,
        redaction_applied=False,
    )
    return _persist_audit_safely(audit)


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
            landlock_preflight(),
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
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Prune old sandbox audit events (events file only; chain is preserved)."""
    _sandbox_audit_compact_impl(before, keep, audit_dir, json_output, debug, yes)


@sandbox_audit_app.command("compact")
def sandbox_audit_compact_nested(
    before: Optional[str] = typer.Option(
        None, "--before", help="ISO timestamp; prune events before this"
    ),
    keep: int = typer.Option(1000, "--keep", help="Keep newest N events when --before omitted"),
    audit_dir: Optional[str] = typer.Option(None, "--audit-dir", help="Sandbox audit directory"),
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Prune old sandbox audit events (events file only; chain is preserved)."""
    _sandbox_audit_compact_impl(before, keep, audit_dir, json_output, debug, yes)


def _sandbox_audit_compact_impl(
    before: Optional[str],
    keep: int,
    audit_dir: Optional[str],
    json_output: bool,
    debug: bool,
    yes: bool = False,
) -> None:
    _setup_logging(debug)
    # Destructive: rewrites the sandbox audit events file. Confirmation-gated.
    if not yes:
        if json_output:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Refusing to prune sandbox audit events without --yes in JSON mode.",
                    details={"code": "CONFIRMATION_REQUIRED"},
                ),
                json_output,
            )
            raise typer.Exit(2)
        target = f"before {before}" if before else f"all but the newest {keep}"
        if not typer.confirm(
            f"Prune sandbox audit events ({target})? The events file is rewritten "
            "(the hash chain is preserved)."
        ):
            _out(ok({"ok": True, "cancelled": True, "pruned": 0}), json_output)
            raise typer.Exit(0)
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


@sandbox_app.command("firecracker-gates")
def sandbox_firecracker_gates(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Report Firecracker real-host proof gates; does not boot a VM."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    _out(ok(firecracker_proof_gates(), workspace=str(ws)), json_output)


@sandbox_app.command("vz-artifacts")
def sandbox_vz_artifacts(
    output: str = typer.Option(..., "--output", help="Output directory for VZ proof artifacts"),
    kernel: Optional[str] = typer.Option(
        None, "--kernel", help="ARM64 Linux kernel to copy into the proof artifact set"
    ),
    initrd: Optional[str] = typer.Option(
        None, "--initrd", help="VZ proof initrd to copy into the proof artifact set"
    ),
    build_runner: bool = typer.Option(
        False,
        "--build-runner",
        help="Compile/sign the local Swift VZ runner into the artifact set",
    ),
    exec_init: bool = typer.Option(
        False,
        "--exec-init",
        help="Write the reviewable ARC VZ guest exec-init contract; no downloads",
    ),
    pack_initrd: bool = typer.Option(
        False,
        "--pack-initrd",
        help="With --exec-init, package a minimal initrd using local BusyBox and cpio",
    ),
    busybox: Optional[str] = typer.Option(
        None,
        "--busybox",
        help="Local executable BusyBox path for --exec-init --pack-initrd",
    ),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate VZ proof artifact provenance; does not boot a VM."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    if pack_initrd and not exec_init:
        _out(err(ArcErrorCode.INVALID_INPUT, "--pack-initrd requires --exec-init"), json_output)
        raise typer.Exit(2)
    report = (
        generate_vz_exec_init_artifacts(
            Path(output).expanduser(),
            pack_initrd=pack_initrd,
            busybox_path=Path(busybox).expanduser() if busybox else None,
        )
        if exec_init
        else generate_vz_proof_artifacts(
            Path(output).expanduser(),
            kernel_path=Path(kernel).expanduser() if kernel else None,
            initrd_path=Path(initrd).expanduser() if initrd else None,
            build_runner=build_runner,
        )
    )
    _out(ok(report.model_dump(mode="json"), workspace=str(ws)), json_output)


@sandbox_app.command(
    "run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def sandbox_run(
    ctx: typer.Context,
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
    provider: Optional[str] = typer.Option(
        None,
        "--provider",
        help="Isolation backend override (auto, none, subprocess, docker, microvm); "
        "defaults to the configured execution.isolation backend",
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
        provider = resolve_isolation_backend(load_config(ws), override=provider)
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
        audit = _persist_sandbox_denial(
            command=command,
            cwd=cwd,
            decision=decision,
            provider=provider,
            started_at=started_at,
            reason=str(exc),
            reason_code=getattr(exc, "reason_code", None),
        )
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                str(exc),
                details={"audit_path": audit["audit_path"], "audit_id": audit["audit_id"]},
            ),
            json_output,
        )
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
            audit = _persist_audit_safely(audit)
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
        ended_at = utc_now()
        audit = build_audit_event(
            command=command,
            cwd=cwd,
            decision=decision,
            provider="subprocess",
            started_at=started_at,
            ended_at=ended_at,
            exit_code=stream_result.exit_code,
            stdout_truncated=stream_result.stdout_truncated,
            stderr_truncated=stream_result.stderr_truncated,
            redaction_applied=stream_result.redaction_applied,
        )
        audit = _persist_audit_safely(audit)
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
        import platform as _platform

        vz_gates = (
            vz_public_exec_gates()
            if provider == "microvm" and _platform.system() == "Darwin"
            else {}
        )
        attach_microvm_audit_contract_fields(
            audit,
            microvm_provider="vz" if vz_gates.get("microvm_provider") == "vz" else None,
            platform_name=str(vz_gates.get("platform")) if vz_gates else None,
            lifecycle=["preflight"],
            lifecycle_errors=[str(exc)],
            network_proof_passed=False,
            teardown_attempted=False,
            gates=vz_gates.get("gates") if vz_gates else None,
            artifact_manifest_path=vz_gates.get("manifest_path") if vz_gates else None,
            artifact_hashes=vz_gates.get("artifact_hashes") if vz_gates else None,
            public_execution_enabled=False,
        )
        audit = _persist_audit_safely(audit)
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    ended_at = utc_now()
    result_decision = decision
    if iso.provider == "microvm" and iso.exit_code != 0:
        result_decision = decision.model_copy(
            update={
                "allowed": False,
                "reason": iso.stderr or "microVM proof failed",
                "approval_required": False,
                "approved": False,
            }
        )
    audit = build_audit_event(
        command=command,
        cwd=cwd,
        decision=result_decision,
        provider=iso.provider if iso.provider != "unknown" else provider,
        started_at=started_at,
        ended_at=ended_at,
        exit_code=iso.exit_code,
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
    )
    if iso.provider == "microvm":
        attach_microvm_audit_contract_fields(
            audit,
            microvm_provider=iso.metadata.get("microvm_provider"),
            platform_name=iso.metadata.get("platform"),
            lifecycle=iso.metadata.get("lifecycle", []),
            lifecycle_errors=iso.metadata.get("lifecycle_errors", []),
            network_proof_passed=bool(iso.metadata.get("network_proof_passed", False)),
            workspace_proof_passed=iso.metadata.get("workspace_proof_passed"),
            proof_markers=iso.metadata.get("proof_markers"),
            teardown_attempted=bool(iso.metadata.get("teardown_attempted", False)),
            teardown_ok=iso.metadata.get("teardown_ok"),
            gate=str(iso.metadata.get("gate", "ARC_MICROVM_EXEC_ENABLED=1")),
            gates=iso.metadata.get("gates"),
            artifact_manifest_path=iso.metadata.get("artifact_manifest_path"),
            artifact_hashes=iso.metadata.get("artifact_hashes"),
            public_execution_enabled=bool(iso.metadata.get("public_execution_enabled", False)),
        )
    audit = _persist_audit_safely(audit)
    is_error, exit_note = interpret_exit_code(command, iso.exit_code)
    result = SandboxResult(
        command=command,
        cwd=str(cwd),
        classification=decision.classification,
        decision=result_decision,
        provider=iso.provider if iso.provider != "unknown" else provider,
        exit_code=iso.exit_code,
        stdout=iso.stdout,
        stderr=iso.stderr,
        duration_ms=iso.duration_ms,
        timed_out=iso.killed and iso.kill_reason == "timeout",
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
        is_error=is_error,
        exit_note=exit_note,
        audit_event=audit,
    )
    _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
    # Preserve the real process exit code for the caller, but only when the
    # command-aware interpreter considers it a genuine error (PR-A). A benign
    # nonzero exit (e.g. grep "no matches") returns success.
    if iso.exit_code not in (0, None) and is_error:
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
) -> IsolationProvider:
    return build_execution_provider(
        name,
        workspace_root=ws,
        env_allowlist=frozenset(policy_model.env_allowlist),
        max_output_bytes=policy_model.max_output_bytes,
        read_write_workspace=read_write_workspace,
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


# ---------------------------------------------------------------------------
# PR-E: policy rule management commands
# ---------------------------------------------------------------------------


@policy_app.command("rule-add")
def policy_rule_add(
    pattern: str = typer.Option(..., "--pattern", help="Command glob pattern, e.g. 'git *'"),
    verdict: str = typer.Option(..., "--verdict", help="allow | deny | ask"),
    comment: str = typer.Option("", "--comment", help="Optional human note"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Add an explicit command rule (allow/deny/ask) to the rule store.

    Rules are evaluated before classification; first match wins.

    Examples:
      arc policy rule-add --pattern 'git *' --verdict allow
      arc policy rule-add --pattern 'curl *' --verdict deny --comment 'no network'
    """
    _setup_logging(debug)
    try:
        v = CommandRuleVerdict(verdict.lower())
    except ValueError:
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"invalid verdict {verdict!r}; use allow/deny/ask"),
            json_output,
        )
        raise typer.Exit(2)
    rule = add_command_rule(pattern=pattern, verdict=v, comment=comment)
    _out(ok(rule.model_dump(mode="json")), json_output)


@policy_app.command("rule-list")
def policy_rule_list(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List all persisted command rules in evaluation order."""
    _setup_logging(debug)
    rules = list_command_rules()
    _out(
        ok({"rules": [r.model_dump(mode="json") for r in rules], "count": len(rules)}), json_output
    )


@policy_app.command("rule-remove")
def policy_rule_remove(
    pattern: str = typer.Option(..., "--pattern", help="Pattern to remove (exact match)"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Remove all command rules matching the given pattern exactly."""
    _setup_logging(debug)
    result = remove_command_rule(pattern=pattern)
    _out(ok(result), json_output)


@policy_app.command("template-list")
def policy_template_list(
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List available policy templates (R97)."""
    _setup_logging(debug)
    from ..security.policy_templates import list_templates

    templates = list_templates(category=category)
    payload = {
        "count": len(templates),
        "category_filter": category,
        "templates": [t.to_dict() for t in templates],
    }
    _out(ok(payload), json_output)


@policy_app.command("template-show")
def policy_template_show(
    template_id: str = typer.Argument(..., help="Template ID to show"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show details of a policy template (R97)."""
    _setup_logging(debug)
    from ..security.policy_templates import load_template

    try:
        template = load_template(template_id)
        _out(ok(template.to_dict()), json_output)
    except FileNotFoundError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1)


@policy_app.command("template-validate")
def policy_template_validate(
    template_id: str = typer.Argument(..., help="Template ID to validate"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Validate a policy template (R97)."""
    _setup_logging(debug)
    from ..security.policy_templates import validate_template

    result = validate_template(template_id)
    if result["ok"]:
        _out(ok(result), json_output)
    else:
        _out(err(ArcErrorCode.INVALID_INPUT, result.get("error", "Validation failed")), json_output)
        raise typer.Exit(1)


@policy_app.command("template-apply")
def policy_template_apply(
    template_id: str = typer.Argument(..., help="Template ID to apply"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    yes: bool = typer.Option(False, "--yes", help="Skip the confirmation prompt"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Apply a policy template to a workspace (R97).

    Writes a .arc/profile.yaml file. Does NOT execute any code.
    Requires --yes in JSON mode (confirmation-gated mutating action).
    """
    _setup_logging(debug)
    from ..security.policy_templates import apply_template

    ws = _workspace(workspace)
    if json_output and not yes:
        _out(
            err(
                ArcErrorCode.PERMISSION_DENIED,
                "Refusing to apply policy template in JSON mode without --yes.",
            ),
            json_output,
        )
        raise typer.Exit(1)

    if not yes:
        typer.confirm(f"Apply policy template '{template_id}' to {ws}?", abort=True)

    result = apply_template(template_id, ws)
    if result["ok"]:
        _out(ok(result), json_output)
    else:
        _out(err(ArcErrorCode.INVALID_INPUT, result.get("error", "Apply failed")), json_output)
        raise typer.Exit(1)
