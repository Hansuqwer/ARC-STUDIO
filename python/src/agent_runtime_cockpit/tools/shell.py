"""Sandboxed shell command tool for coding agents."""

from __future__ import annotations

import asyncio
import concurrent.futures
import os
import shlex
from pathlib import Path
from typing import Any, Coroutine, TypeVar

from pydantic import BaseModel, Field

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken
from agent_runtime_cockpit.isolation.subprocess import SubprocessIsolationProvider
from agent_runtime_cockpit.security.sandbox import (
    SandboxPolicy,
    classify_command,
    build_audit_event,
    decide,
    ensure_workspace_cwd,
    persist_sandbox_audit_event,
    utc_now,
    validate_command_paths,
)
from agent_runtime_cockpit.security.trust import TRUST_DB, ensure_trusted
from agent_runtime_cockpit.tools.protocol import ToolResult

T = TypeVar("T")


class BashArgs(BaseModel):
    command: str = Field(
        description="Single command string parsed with shlex.split; no shell is used"
    )


def _run_coro_sync(coro: Coroutine[Any, Any, T]) -> T:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        return executor.submit(asyncio.run, coro).result()


class BashTool:
    """Run argv through SubprocessIsolationProvider under SandboxPolicy."""

    name = "bash"
    description = (
        "Run a sandboxed command in the workspace. Read-only/workspace-write only; no shell."
    )
    output_trust_level = "untrusted"
    args_schema = BashArgs
    output_byte_limit = 65536

    def __init__(
        self,
        workspace_root: Path | None = None,
        policy: SandboxPolicy | None = None,
        trust_db: Path = TRUST_DB,
    ) -> None:
        root = (workspace_root or Path.cwd()).resolve()
        self.policy = policy or SandboxPolicy(workspace_root=root)
        self.workspace_root = self.policy.workspace_root.resolve()
        self.output_byte_limit = self.policy.max_output_bytes
        self.trust_db = trust_db

    def execute(self, args: BashArgs, cancellation_token: CancellationToken) -> ToolResult:
        cancellation_token.raise_if_cancelled()
        started_at = utc_now()
        command = shlex.split(args.command)
        cwd = ensure_workspace_cwd(Path.cwd(), self.workspace_root)
        decision = decide(command, self.policy)
        workspace_interpreter_allowed = _workspace_interpreter_gate(command, self.workspace_root)
        if workspace_interpreter_allowed:
            decision = decision.model_copy(
                update={
                    "allowed": True,
                    "classification": classify_command(command),
                    "reason": "explicit workspace interpreter gate",
                    "approval_required": False,
                }
            )
        try:
            ensure_trusted(self.workspace_root, trust_db=self.trust_db, allow_if_no_db=True)
        except Exception as exc:  # noqa: BLE001 - tool errors are returned to model.
            decision = decision.model_copy(update={"allowed": False, "reason": str(exc)})
        if not workspace_interpreter_allowed:
            try:
                validate_command_paths(command, self.policy)
            except ValueError as exc:
                decision = decision.model_copy(update={"allowed": False, "reason": str(exc)})
        if not decision.allowed:
            audit = build_audit_event(
                command=command,
                cwd=cwd,
                decision=decision,
                provider="subprocess",
                started_at=started_at,
                ended_at=utc_now(),
                exit_code=None,
                stdout_truncated=False,
                stderr_truncated=False,
                redaction_applied=False,
            )
            _persist(audit)
            return ToolResult(
                content={
                    "error": decision.reason,
                    "allowed": False,
                    "classification": decision.classification.value,
                }
            )
        provider = SubprocessIsolationProvider(
            safe_env_keys=frozenset(self.policy.env_allowlist),
            workspace_root=self.workspace_root,
            max_output_bytes=self.policy.max_output_bytes,
        )
        iso = _run_coro_sync(
            provider.execute(command, cwd=cwd, timeout_seconds=self.policy.timeout_seconds)
        )
        audit = build_audit_event(
            command=command,
            cwd=cwd,
            decision=decision,
            provider=iso.provider,
            started_at=started_at,
            ended_at=utc_now(),
            exit_code=iso.exit_code,
            stdout_truncated=iso.stdout_truncated,
            stderr_truncated=iso.stderr_truncated,
            redaction_applied=iso.redaction_applied,
        )
        _persist(audit)
        return ToolResult(
            content={
                "exit_code": iso.exit_code,
                "stdout": iso.stdout,
                "stderr": iso.stderr,
                "timed_out": iso.killed and iso.kill_reason == "timeout",
            }
        )


def _persist(audit: dict[str, Any]) -> None:
    try:
        persist_sandbox_audit_event(audit)
    except Exception:
        return


def _workspace_interpreter_gate(command: list[str], workspace_root: Path) -> bool:
    if os.environ.get("ARC_AGENT_ALLOW_WORKSPACE_INTERPRETER") != "1":
        return False
    if len(command) != 2 or Path(command[0]).name not in {"python", "python3"}:
        return False
    script = Path(command[1])
    if not script.is_absolute():
        script = workspace_root / script
    try:
        return script.resolve(strict=False).is_relative_to(workspace_root.resolve())
    except OSError:
        return False
