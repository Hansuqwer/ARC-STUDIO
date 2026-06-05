"""Bounded deterministic edit -> sandboxed test -> repair loop."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..config.loader import load_config
from ..isolation.selector import build_execution_provider, resolve_isolation_backend
from .edit_loop import apply_edit_plan
from .sandbox import (
    build_audit_event,
    decide,
    ensure_workspace_cwd,
    persist_sandbox_audit_event,
    resolve_sandbox_policy,
    utc_now,
    validate_command_paths,
)


class RepairAttempt(BaseModel):
    step: Literal["test", "edit", "repair"]
    ok: bool
    reason: str
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


class RepairLoopResult(BaseModel):
    version: Literal[1] = 1
    ok: bool
    stopped_reason: str
    attempts: list[RepairAttempt] = Field(default_factory=list)
    transaction_id: str | None = None
    audit_events: list[dict[str, Any]] = Field(default_factory=list)


def _run_test(
    workspace_root: Path, command: list[str], policy_name: str
) -> tuple[RepairAttempt, dict[str, Any]]:
    policy = resolve_sandbox_policy(policy_name, workspace_root)
    cwd = ensure_workspace_cwd(workspace_root, workspace_root)
    decision = decide(command, policy)
    started = utc_now()
    if not decision.allowed:
        ended = utc_now()
        audit = build_audit_event(
            command=command,
            cwd=cwd,
            decision=decision,
            provider="subprocess",
            started_at=started,
            ended_at=ended,
            exit_code=None,
            stdout_truncated=False,
            stderr_truncated=False,
            redaction_applied=False,
        )
        audit_path = persist_sandbox_audit_event(audit)
        audit["audit_path"] = str(audit_path)
        return RepairAttempt(step="test", ok=False, reason=decision.reason), audit
    validate_command_paths(command, policy)
    iso = asyncio.run(
        build_execution_provider(
            resolve_isolation_backend(load_config(workspace_root)),
            workspace_root=workspace_root,
            env_allowlist=frozenset(policy.env_allowlist),
            max_output_bytes=policy.max_output_bytes,
        ).execute(command, cwd=cwd, timeout_seconds=policy.timeout_seconds)
    )
    ended = utc_now()
    audit = build_audit_event(
        command=command,
        cwd=cwd,
        decision=decision,
        provider=iso.provider,
        started_at=started,
        ended_at=ended,
        exit_code=iso.exit_code,
        stdout_truncated=iso.stdout_truncated,
        stderr_truncated=iso.stderr_truncated,
        redaction_applied=iso.redaction_applied,
    )
    audit_path = persist_sandbox_audit_event(audit)
    audit["audit_path"] = str(audit_path)
    return (
        RepairAttempt(
            step="test",
            ok=iso.exit_code == 0,
            reason="passed" if iso.exit_code == 0 else "failed",
            exit_code=iso.exit_code,
            stdout=iso.stdout,
            stderr=iso.stderr,
        ),
        audit,
    )


def run_deterministic_repair_loop(
    *,
    workspace_root: Path,
    path: str,
    initial_content: str,
    repair_content: str,
    test_command: list[str],
    policy_name: str = "local-safe",
    max_attempts: int = 2,
) -> RepairLoopResult:
    """Run a bounded local fixture repair loop; no model/provider call."""
    attempts: list[RepairAttempt] = []
    audits: list[dict[str, Any]] = []
    apply_initial = apply_edit_plan(
        path_arg=path,
        content=initial_content,
        workspace_root=workspace_root,
        policy_name=policy_name,
        approved=True,
    )
    attempts.append(
        RepairAttempt(
            step="edit", ok=bool(apply_initial["applied"]), reason=apply_initial["reason"]
        )
    )
    if not apply_initial["applied"]:
        return RepairLoopResult(ok=False, stopped_reason="initial_edit_denied", attempts=attempts)
    last_txn = apply_initial.get("transaction_id")
    for index in range(max_attempts):
        test, audit = _run_test(workspace_root, test_command, policy_name)
        attempts.append(test)
        audits.append(audit)
        if not test.ok and audit.get("allowed") is False:
            return RepairLoopResult(
                ok=False,
                stopped_reason="sandbox_denied",
                attempts=attempts,
                transaction_id=last_txn,
                audit_events=audits,
            )
        if test.ok:
            return RepairLoopResult(
                ok=True,
                stopped_reason="passed",
                attempts=attempts,
                transaction_id=last_txn,
                audit_events=audits,
            )
        if index >= max_attempts - 1:
            return RepairLoopResult(
                ok=False,
                stopped_reason="retry_limit",
                attempts=attempts,
                transaction_id=last_txn,
                audit_events=audits,
            )
        repair = apply_edit_plan(
            path_arg=path,
            content=repair_content,
            workspace_root=workspace_root,
            policy_name=policy_name,
            approved=True,
        )
        attempts.append(
            RepairAttempt(step="repair", ok=bool(repair["applied"]), reason=repair["reason"])
        )
        last_txn = repair.get("transaction_id")
        if not repair["applied"]:
            return RepairLoopResult(
                ok=False,
                stopped_reason="repair_denied",
                attempts=attempts,
                transaction_id=last_txn,
                audit_events=audits,
            )
    return RepairLoopResult(
        ok=False,
        stopped_reason="retry_limit",
        attempts=attempts,
        transaction_id=last_txn,
        audit_events=audits,
    )
