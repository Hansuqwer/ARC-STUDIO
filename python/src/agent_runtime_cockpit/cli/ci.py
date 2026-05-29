"""CI guardrails and local CI orchestration CLI."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer

from ..ci_orchestration import (
    CiRunResult,
    build_ci_matrix,
    make_custom_ci_job,
    write_ci_run_artifact,
)
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..runtime.streaming import StreamEventType, stream_subprocess_events
from ..security.sandbox import (
    approve_decision_with_token,
    build_audit_event,
    decide,
    ensure_workspace_cwd,
    persist_sandbox_audit_event,
    resolve_sandbox_policy,
    utc_now,
    validate_command_paths,
)
from ._helpers import DEBUG_FLAG, JSON_FLAG, WORKSPACE_FLAG, _out, _setup_logging, _workspace
from ._subapps import ci_app


def _policy(name: str, workspace: Path):
    try:
        return resolve_sandbox_policy(name, workspace)
    except (KeyError, ValueError) as exc:
        raise typer.BadParameter(str(exc)) from exc


@ci_app.command("matrix")
def ci_matrix(
    workspace: Optional[str] = WORKSPACE_FLAG,
    include_workflows: bool = typer.Option(
        True, "--include-workflows/--no-workflows", help="Include GitHub Actions run steps"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Detect local CI/test matrix without executing jobs."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    matrix = build_ci_matrix(ws, include_workflows=include_workflows)
    _out(ok(matrix.model_dump(mode="json"), workspace=str(ws)), json_output)


@ci_app.command("run", context_settings={"allow_extra_args": True, "ignore_unknown_options": True})
def ci_run(
    ctx: typer.Context,
    job_id: Optional[str] = typer.Option(None, "--job", help="Detected matrix job id to run"),
    policy: str = typer.Option("local-safe", "--policy", help="Sandbox policy profile"),
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
    """Run one detected or explicit CI job through sandbox policy."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    explicit_command = list(ctx.args)
    if job_id and explicit_command:
        _out(err(ArcErrorCode.INVALID_INPUT, "use --job or -- <cmd>, not both"), json_output)
        raise typer.Exit(2)
    if not job_id and not explicit_command:
        _out(err(ArcErrorCode.INVALID_INPUT, "missing --job or command"), json_output)
        raise typer.Exit(2)

    matrix = build_ci_matrix(ws)
    job = make_custom_ci_job(explicit_command) if explicit_command else None
    if job is None:
        job = next((candidate for candidate in matrix.jobs if candidate.id == job_id), None)
    if job is None:
        _out(err(ArcErrorCode.INVALID_INPUT, f"unknown ci job: {job_id}"), json_output)
        raise typer.Exit(2)
    if not job.runnable:
        _out(
            err(ArcErrorCode.INVALID_INPUT, job.blocked_reason or "job is not argv-runnable"),
            json_output,
        )
        raise typer.Exit(2)

    try:
        policy_model = _policy(policy, ws)
        cwd = ensure_workspace_cwd((ws / job.cwd).resolve(), ws)
        decision = decide(job.command, policy_model)
        decision = approve_decision_with_token(
            token=approval_token, command=job.command, policy=policy_model, decision=decision
        )
        validate_command_paths(job.command, policy_model)
    except (ValueError, typer.BadParameter) as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)

    run_id = f"ci-{uuid.uuid4().hex[:12]}"
    started_at = utc_now()
    ended_at = started_at
    if not decision.allowed:
        audit = build_audit_event(
            command=job.command,
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
        result = CiRunResult(
            run_id=run_id,
            job=job,
            policy=policy_model.name,
            status="denied",
            summary=f"denied: {decision.reason}",
            decision=decision,
            audit_event=audit,
        )
        artifact_path = write_ci_run_artifact(ws, run_id, result)
        result.artifact_paths.append(str(artifact_path.relative_to(ws)))
        _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
        raise typer.Exit(3)

    events, stream_result = stream_subprocess_events(
        job.command,
        cwd=cwd,
        source="testbench",
        timeout_seconds=policy_model.timeout_seconds,
        max_output_bytes=policy_model.max_output_bytes,
        cancel_after_events=cancel_after_events,
        safe_env_keys=frozenset(policy_model.env_allowlist),
    )
    ended_at = utc_now()
    audit = build_audit_event(
        command=job.command,
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
    audit_path = persist_sandbox_audit_event(audit)
    audit["audit_path"] = str(audit_path)
    status = _ci_status(stream_result.terminal_event, stream_result.exit_code)
    result = CiRunResult(
        run_id=run_id,
        job=job,
        policy=policy_model.name,
        status=status,
        exit_code=stream_result.exit_code,
        duration_ms=stream_result.duration_ms,
        stdout=stream_result.stdout,
        stderr=stream_result.stderr,
        stdout_truncated=stream_result.stdout_truncated,
        stderr_truncated=stream_result.stderr_truncated,
        redaction_applied=stream_result.redaction_applied,
        summary=_ci_summary(status, stream_result.exit_code),
        decision=decision,
        audit_event=audit,
    )
    artifact_path = write_ci_run_artifact(ws, run_id, result)
    result.artifact_paths.append(str(artifact_path.relative_to(ws)))
    if stream_json:
        for event in events:
            typer.echo(
                json.dumps(
                    ok(event.model_dump(mode="json"), workspace=str(ws)).model_dump(mode="json"),
                    sort_keys=True,
                )
            )
        typer.echo(
            json.dumps(
                ok(result.model_dump(mode="json"), workspace=str(ws)).model_dump(mode="json"),
                sort_keys=True,
            )
        )
    else:
        _out(ok(result.model_dump(mode="json"), workspace=str(ws)), json_output)
    if status == "cancelled":
        raise typer.Exit(130)
    if status == "timeout":
        raise typer.Exit(124)
    if stream_result.exit_code not in (0, None):
        raise typer.Exit(stream_result.exit_code)


def _ci_status(event: StreamEventType, exit_code: int | None):
    if event == StreamEventType.CANCELLED:
        return "cancelled"
    if event == StreamEventType.TIMEOUT:
        return "timeout"
    if exit_code == 0:
        return "passed"
    return "failed"


def _ci_summary(status: str, exit_code: int | None) -> str:
    if status == "passed":
        return "job passed"
    if status == "failed":
        return f"job failed with exit code {exit_code}"
    return f"job {status}"


@ci_app.command("check")
def ci_check(
    workspace: Optional[str] = WORKSPACE_FLAG,
    audit_dir: Optional[str] = typer.Option(
        None, "--audit-dir", help="Path to sandbox audit directory"
    ),
    json_output: bool = JSON_FLAG,
    private: bool = typer.Option(True, "--private", help="Run checks offline, no uploads"),
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run offline CI guardrail checks (sandbox audit, policy, eval, receipts).

    Default mode is private/offline — no network calls.
    """
    _setup_logging(debug)
    ws = _workspace(workspace)

    checks: dict[str, object] = {
        "private": private,
        "advisory": True,
        "workspace": str(ws),
        "checks": {},
    }

    # 1. Sandbox audit — look for denied commands
    from ..security.sandbox import list_sandbox_audit_events

    audit_result = list_sandbox_audit_events(limit=100)
    denied_events = [e for e in audit_result.get("events", []) if e.get("allowed") is False]
    checks["checks"]["sandbox_audit"] = {
        "status": "fail" if denied_events else "pass",
        "total_events": audit_result.get("count", 0),
        "exercised": audit_result.get("count", 0) > 0,
        "denied_count": len(denied_events),
        "denied_commands": [
            {
                "command": e.get("command", []),
                "classification": e.get("classification"),
                "reason": e.get("reason"),
                "started_at": e.get("started_at"),
            }
            for e in denied_events[:20]
        ],
        "degraded": audit_result.get("degraded", False),
        "source": audit_result.get("source", "unknown"),
    }

    # 2. Policy check
    from ..security.sandbox import list_sandbox_policies, validate_sandbox_policy_config

    policies = list_sandbox_policies(ws)
    policy_validation = validate_sandbox_policy_config()
    checks["checks"]["policy"] = {
        "status": "pass" if policy_validation.get("ok", True) else "fail",
        "policy_count": len(policies),
        "policy_names": [p.name for p in policies],
        "validation_errors": policy_validation.get("errors", []),
    }

    # 3. Eval gate — check for goldens or eval artifacts
    goldens_dir = ws / ".arc" / "goldens"
    eval_dir = ws / ".arc" / "eval"
    evals_dir = ws / ".arc" / "evals"
    goldens_content: list[str] = []
    eval_content: list[str] = []
    evals_content: list[str] = []
    if goldens_dir.exists():
        goldens_content = sorted(
            str(p.relative_to(ws)) for p in goldens_dir.iterdir() if p.is_file()
        )
    if eval_dir.exists():
        eval_content = sorted(str(p.relative_to(ws)) for p in eval_dir.iterdir() if p.is_file())
    if evals_dir.exists():
        evals_content = sorted(str(p.relative_to(ws)) for p in evals_dir.iterdir() if p.is_file())
    checks["checks"]["eval"] = {
        "status": "pass" if (goldens_content or eval_content or evals_content) else "skip",
        "goldens_found": len(goldens_content),
        "eval_files_found": len(eval_content),
        "evals_files_found": len(evals_content),
        "goldens_files": goldens_content[:20],
        "eval_files": eval_content[:20],
        "evals_files": evals_content[:20],
    }

    # 4. Receipt check
    receipts_dir = ws / ".arc" / "receipts"
    receipt_files: list[str] = []
    if receipts_dir.exists():
        receipt_files = sorted(
            str(p.relative_to(ws))
            for p in receipts_dir.iterdir()
            if p.suffix in {".json", ".jsonl", ".md"}
        )
    checks["checks"]["receipt"] = {
        "status": "pass" if receipt_files else "skip",
        "receipt_count": len(receipt_files),
        "receipt_files": receipt_files[:20],
    }

    # Overall status
    all_statuses = [c.get("status", "skip") for c in checks["checks"].values()]
    overall = "fail" if "fail" in all_statuses else "pass"
    checks["overall"] = overall
    checks["checked_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    _out(ok(checks), json_output)


@ci_app.command("summary")
def ci_summary(
    workspace: Optional[str] = WORKSPACE_FLAG,
    audit_dir: Optional[str] = typer.Option(
        None, "--audit-dir", help="Path to sandbox audit directory"
    ),
    format: str = typer.Option("markdown", "--format", help="Output format: markdown or json"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate an advisory PR summary from local CI data.

    Collects audit events, policy decisions, and eval results into
    deterministic redacted output. Advisory only — no AI judgment claims.
    """
    _setup_logging(debug)
    ws = _workspace(workspace)

    from ..security.sandbox import list_sandbox_audit_events, list_sandbox_policies

    audit_events = list_sandbox_audit_events(limit=100)
    policies = list_sandbox_policies(ws)

    # Collect denied events
    denied = [e for e in audit_events.get("events", []) if e.get("allowed") is False]
    allowed = [e for e in audit_events.get("events", []) if e.get("allowed") is True]

    # Eval status
    goldens_dir = ws / ".arc" / "goldens"
    eval_dir = ws / ".arc" / "eval"
    evals_dir = ws / ".arc" / "evals"
    goldens_count = (
        len([p for p in goldens_dir.iterdir() if p.is_file()]) if goldens_dir.exists() else 0
    )
    eval_files = (
        [str(p.relative_to(ws)) for p in eval_dir.iterdir() if p.is_file()]
        if eval_dir.exists()
        else []
    )
    evals_files = (
        [str(p.relative_to(ws)) for p in evals_dir.iterdir() if p.is_file()]
        if evals_dir.exists()
        else []
    )

    # Receipt status
    receipts_dir = ws / ".arc" / "receipts"
    receipt_count = (
        len([p for p in receipts_dir.iterdir() if p.suffix in {".json", ".jsonl", ".md"}])
        if receipts_dir.exists()
        else 0
    )

    summary_data = {
        "advisory": True,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workspace": str(ws),
        "no_ai_judgment": True,
        "audit_events": {
            "total": audit_events.get("count", 0),
            "allowed": len(allowed),
            "denied": len(denied),
            "denied_commands": [
                {
                    "command": e.get("command", []),
                    "classification": e.get("classification"),
                    "reason": e.get("reason"),
                }
                for e in denied[:20]
            ],
        },
        "policies": {
            "count": len(policies),
            "names": [p.name for p in policies],
        },
        "eval": {
            "goldens_count": goldens_count,
            "eval_files": eval_files[:20],
            "evals_files": evals_files[:20],
        },
        "receipts": {
            "count": receipt_count,
        },
    }

    if format == "json" or json_output:
        _out(ok(summary_data), True)
        return

    # Markdown output
    lines: list[str] = [
        "<!-- ARC CI Summary — Advisory Only; No AI Judgment Claims -->",
        "",
        "# ARC CI Summary",
        "",
        f"> **Advisory only.** Generated at {summary_data['generated_at']}",
        f"> Workspace: `{summary_data['workspace']}`",
        "",
        "## Audit Events",
        "",
        f"- **Total events:** {summary_data['audit_events']['total']}",
        f"- **Allowed:** {summary_data['audit_events']['allowed']}",
        f"- **Denied:** {summary_data['audit_events']['denied']}",
    ]

    if summary_data["audit_events"]["denied_commands"]:
        lines.extend(
            [
                "",
                "### Denied Commands",
                "",
                "| Command | Classification | Reason |",
                "|---------|---------------|--------|",
            ]
        )
        for dc in summary_data["audit_events"]["denied_commands"]:
            cmd = (
                " ".join(str(p) for p in dc["command"])
                if isinstance(dc["command"], list)
                else str(dc["command"])
            )
            lines.append(
                f"| `{cmd[:80]}` | {dc.get('classification', '?')} | {dc.get('reason', '?')} |"
            )

    lines.extend(
        [
            "",
            "## Policies",
            "",
            f"- **Policy count:** {summary_data['policies']['count']}",
            f"- **Active policies:** {', '.join(summary_data['policies']['names'])}",
            "",
            "## Evaluation",
            "",
            f"- **Goldens found:** {summary_data['eval']['goldens_count']}",
            f"- **Eval files:** {len(summary_data['eval']['eval_files'])}",
            "",
            "## Receipts",
            "",
            f"- **Receipt count:** {summary_data['receipts']['count']}",
            "",
            "---",
            "",
            "_ARC CI guardrails (Phase 80 / R51) — deterministic, offline, advisory._",
        ]
    )

    from ._app import console

    console.print("\n".join(lines))


@ci_app.command("verify-audit")
def ci_verify_audit(
    audit_dir: str = typer.Option("", "--audit-dir", help="Path to sandbox audit directory"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    strict: bool = typer.Option(
        False, "--strict", help="If audit is invalid or missing, exit with code 1"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify sandbox audit chain integrity using existing verifier."""
    _setup_logging(debug)

    from ..security.sandbox import verify_sandbox_audit

    target_dir = Path(audit_dir).expanduser().resolve() if audit_dir else None
    result = verify_sandbox_audit(audit_dir=target_dir)
    _out(ok(result), json_output)
    if not json_output:
        from ._app import console

        color = "green" if result.get("ok") else "red"
        status = "VERIFIED" if result.get("ok") else "FAILED"
        console.print(f"Sandbox audit chain: [bold {color}]{status}[/bold {color}]")
        console.print(f"  Chain: {result.get('chain', '?')}")
        console.print(f"  Reason: {result.get('reason', '?')}")
    if not result.get("ok"):
        if strict:
            raise typer.Exit(1)
        raise typer.Exit(0)
