from __future__ import annotations

import json
import shlex
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from agent_runtime_cockpit.security.sandbox import (
    SandboxDecision,
    decide,
    resolve_sandbox_policy,
    validate_command_paths,
)

from .aliases import get_alias
from .pipeline import ChainOperator, parse_command_chain
from .session import ChatSession
from .slash_commands import CommandResult, SlashCommandHandler


class BatchErrorMode(str, Enum):
    FAIL_FAST = "fail-fast"
    CONTINUE_ON_ERROR = "continue-on-error"


class BatchCommandType(str, Enum):
    SLASH = "slash"
    SANDBOX = "sandbox"
    DENIED = "denied"
    INVALID = "invalid"


class BatchSegmentPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_no: int
    index: int
    operator_before: str
    raw: str
    expanded: str
    command_type: BatchCommandType
    alias_chain: list[str] = Field(default_factory=list)
    allowed: bool
    reason: str = ""
    sandbox_command: list[str] | None = None
    sandbox_decision: dict[str, Any] | None = None


class BatchPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str = Field(default_factory=lambda: f"b-{uuid.uuid4().hex[:12]}")
    policy: str = "local-safe"
    workspace: str
    segments: list[BatchSegmentPlan]


class BatchSegmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_no: int
    index: int
    command: str
    state: str
    output: str = ""
    reason: str = ""
    skipped: bool = False


class BatchRunResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    batch_id: str
    policy: str
    error_mode: BatchErrorMode
    started_at: str
    ended_at: str
    results: list[BatchSegmentResult]
    ok: bool


def build_batch_plan(
    text: str, *, policy: str = "local-safe", workspace: Path | None = None
) -> BatchPlan:
    ws = (workspace or Path.cwd()).resolve()
    sandbox_policy = resolve_sandbox_policy(policy, ws)
    planned: list[BatchSegmentPlan] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        raw = raw_line.strip()
        if not raw or raw.startswith("#"):
            continue
        try:
            segments = parse_command_chain(raw)
        except ValueError as exc:
            planned.append(
                BatchSegmentPlan(
                    line_no=line_no,
                    index=0,
                    operator_before=ChainOperator.NONE.value,
                    raw=raw,
                    expanded=raw,
                    command_type=BatchCommandType.INVALID,
                    allowed=False,
                    reason=str(exc),
                )
            )
            continue
        for index, segment in enumerate(segments):
            expanded, chain = expand_aliases(segment.command, workspace=ws)
            plan = _plan_segment(
                line_no=line_no,
                index=index,
                operator_before=segment.operator_before,
                raw=segment.command,
                expanded=expanded,
                alias_chain=chain,
                policy=sandbox_policy,
            )
            planned.append(plan)
    return BatchPlan(policy=policy, workspace=str(ws), segments=planned)


def expand_aliases(command: str, *, workspace: Path, max_depth: int = 5) -> tuple[str, list[str]]:
    current = command.strip()
    chain: list[str] = []
    for _ in range(max_depth):
        parts = shlex.split(current)
        if len(parts) >= 2 and parts[0] == "/alias" and parts[1] == "run":
            item = get_alias(parts[2], workspace) if len(parts) >= 3 else None
            if item is None:
                return current, chain
            chain.append(f"{item.name} ({item.scope}) -> {item.command}")
            current = item.command
            continue
        break
    else:
        raise ValueError("alias expansion depth exceeded")
    return current, chain


def execute_batch_plan(
    plan: BatchPlan,
    *,
    session: ChatSession | None = None,
    handler: SlashCommandHandler | None = None,
    error_mode: BatchErrorMode = BatchErrorMode.FAIL_FAST,
) -> BatchRunResult:
    started = datetime.now(timezone.utc).isoformat()
    sess = session or ChatSession()
    runner = handler or SlashCommandHandler()
    results: list[BatchSegmentResult] = []
    previous: CommandResult | None = None
    for segment in plan.segments:
        previous_ok = _result_ok(previous) if previous is not None else True
        if segment.operator_before == ChainOperator.AND.value and not previous_ok:
            result = BatchSegmentResult(
                line_no=segment.line_no,
                index=segment.index,
                command=segment.expanded,
                state="skipped",
                reason="and_previous_failed",
                skipped=True,
            )
            results.append(result)
            continue
        if segment.operator_before == ChainOperator.OR.value and previous_ok:
            result = BatchSegmentResult(
                line_no=segment.line_no,
                index=segment.index,
                command=segment.expanded,
                state="skipped",
                reason="or_previous_succeeded",
                skipped=True,
            )
            results.append(result)
            continue
        if not segment.allowed:
            result = BatchSegmentResult(
                line_no=segment.line_no,
                index=segment.index,
                command=segment.expanded,
                state="denied",
                reason=segment.reason,
            )
            previous = CommandResult(state="denied", reason=segment.reason)
            results.append(result)
            if error_mode is BatchErrorMode.FAIL_FAST:
                break
            continue
        command = segment.expanded
        if segment.operator_before == ChainOperator.PIPE.value and previous is not None:
            command = f"{command} {shlex.quote(previous.output)}"
        raw = runner.handle(command, sess)
        current = (
            raw
            if isinstance(raw, CommandResult)
            else CommandResult(state="present", output=str(raw or ""))
        )
        previous = current
        results.append(
            BatchSegmentResult(
                line_no=segment.line_no,
                index=segment.index,
                command=command,
                state=current.state,
                output=current.output,
                reason=current.reason,
            )
        )
        if error_mode is BatchErrorMode.FAIL_FAST and not _result_ok(current):
            break
    ended = datetime.now(timezone.utc).isoformat()
    ok = all(item.skipped or item.state in {"present", "ok", "completed"} for item in results)
    return BatchRunResult(
        batch_id=plan.batch_id,
        policy=plan.policy,
        error_mode=error_mode,
        started_at=started,
        ended_at=ended,
        results=results,
        ok=ok,
    )


def render_plan_text(plan: BatchPlan) -> str:
    lines = [f"Batch plan: {plan.batch_id}", f"Policy: {plan.policy}", "Commands:"]
    for segment in plan.segments:
        lines.append(
            f"  {segment.line_no}.{segment.index}: {segment.expanded} "
            f"[{segment.command_type.value}] allowed={segment.allowed} {segment.reason}".rstrip()
        )
        for item in segment.alias_chain:
            lines.append(f"    alias: {item}")
        if segment.sandbox_decision:
            lines.append(f"    approval: {json.dumps(segment.sandbox_decision, sort_keys=True)}")
    return "\n".join(lines)


def _plan_segment(
    *,
    line_no: int,
    index: int,
    operator_before: ChainOperator,
    raw: str,
    expanded: str,
    alias_chain: list[str],
    policy: Any,
) -> BatchSegmentPlan:
    if not expanded.startswith("/"):
        return BatchSegmentPlan(
            line_no=line_no,
            index=index,
            operator_before=operator_before.value,
            raw=raw,
            expanded=expanded,
            command_type=BatchCommandType.DENIED,
            alias_chain=alias_chain,
            allowed=False,
            reason="batch commands must be explicit slash commands; use /sandbox run -- <argv>",
        )
    parts = shlex.split(expanded)
    if len(parts) >= 2 and parts[0] == "/sandbox" and parts[1] == "run":
        command = _sandbox_argv(parts[2:])
        decision: SandboxDecision | None = None
        reason = ""
        allowed = False
        if command:
            try:
                decision = decide(command, policy)
                validate_command_paths(command, policy)
                allowed = decision.allowed and not decision.approval_required
                reason = decision.reason
            except ValueError as exc:
                reason = str(exc)
        else:
            reason = "missing sandbox command"
        return BatchSegmentPlan(
            line_no=line_no,
            index=index,
            operator_before=operator_before.value,
            raw=raw,
            expanded=expanded,
            command_type=BatchCommandType.SANDBOX,
            alias_chain=alias_chain,
            allowed=allowed,
            reason=reason,
            sandbox_command=command,
            sandbox_decision=decision.model_dump(mode="json") if decision else None,
        )
    return BatchSegmentPlan(
        line_no=line_no,
        index=index,
        operator_before=operator_before.value,
        raw=raw,
        expanded=expanded,
        command_type=BatchCommandType.SLASH,
        alias_chain=alias_chain,
        allowed=True,
    )


def _sandbox_argv(parts: list[str]) -> list[str]:
    command: list[str] = []
    index = 0
    while index < len(parts):
        part = parts[index]
        if part == "--":
            return parts[index + 1 :]
        if part in {"--policy", "--provider"} and index + 1 < len(parts):
            index += 2
            continue
        if part.startswith("--policy=") or part.startswith("--provider="):
            index += 1
            continue
        command = parts[index:]
        break
    return command


def _result_ok(result: CommandResult | None) -> bool:
    if result is None:
        return True
    return result.state not in {"blocked", "denied", "error", "failed"}
