"""MCP outbound call sandbox — policy decision combining risk + policy.

Default policy: STRICT (deny high/critical).
Decisions persisted to .arc/mcp/decisions.jsonl (workspace-local).
"""

from __future__ import annotations

import itertools
import json
import time
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from .risk import RiskLevel, RiskScore, RiskSignals, scan_call_arguments, score_call


class McpPolicy(StrEnum):
    STRICT = "strict"
    PERMISSIVE = "permissive"


class McpDecision(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    WARN = "warn"


class McpCallDecision(BaseModel):
    """A sandbox decision for one MCP outbound call."""

    server_id: str
    tool_name: str
    decision: McpDecision
    risk_score: RiskScore
    policy: McpPolicy
    reason: str
    timestamp: float = Field(default_factory=time.time)
    arguments_redacted: bool = False


def decide_call(
    *,
    server_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    manifest_risk: str = "low",
    roots_violation: bool = False,
    drift: str | None = None,
    policy: McpPolicy = McpPolicy.STRICT,
) -> McpCallDecision:
    """Make a sandbox decision for an MCP outbound call."""
    inj_sev = scan_call_arguments(arguments)
    signals = RiskSignals(
        manifest_risk=manifest_risk,
        injection_severity=inj_sev,
        roots_violation=roots_violation,
        drift=drift,
    )
    risk = score_call(signals)

    if policy == McpPolicy.STRICT:
        if risk.level in (RiskLevel.CRITICAL, RiskLevel.HIGH):
            decision = McpDecision.DENY
            reason = f"risk={risk.level.value}; policy=strict; {','.join(risk.reasons)}"
        elif risk.level == RiskLevel.MEDIUM:
            decision = McpDecision.WARN
            reason = f"risk=medium; policy=strict; {','.join(risk.reasons)}"
        else:
            decision = McpDecision.ALLOW
            reason = "risk=low; policy=strict"
    else:
        # permissive: only deny critical
        if risk.level == RiskLevel.CRITICAL:
            decision = McpDecision.DENY
            reason = f"risk=critical; policy=permissive; {','.join(risk.reasons)}"
        elif risk.level in (RiskLevel.HIGH, RiskLevel.MEDIUM):
            decision = McpDecision.WARN
            reason = f"risk={risk.level.value}; policy=permissive; {','.join(risk.reasons)}"
        else:
            decision = McpDecision.ALLOW
            reason = "risk=low; policy=permissive"

    return McpCallDecision(
        server_id=server_id,
        tool_name=tool_name,
        decision=decision,
        risk_score=risk,
        policy=policy,
        reason=reason,
        arguments_redacted=arguments is not None,
    )


def persist_decision(workspace: Path, decision: McpCallDecision) -> Path:
    """Append decision to workspace-local .arc/mcp/decisions.jsonl."""
    decisions_dir = workspace / ".arc" / "mcp"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    path = decisions_dir / "decisions.jsonl"
    with path.open("a", encoding="utf-8") as fp:
        fp.write(decision.model_dump_json() + "\n")
    return path


# ── Typed MCP_CALL_DECISION run-event producer (CR-043) ──────────────────────
# The McpCallDecisionEvent protocol event was defined + registered but never written.
# These build it from a sandbox McpCallDecision and persist it to a workspace-local stream.

_DECISION_SEQ = itertools.count()


def next_decision_sequence() -> int:
    """Monotonic per-process sequence for MCP_CALL_DECISION events."""
    return next(_DECISION_SEQ)


def to_call_decision_event(
    decision: McpCallDecision,
    *,
    run_id: str,
    sequence: int,
    timestamp: str | None = None,
    correlation_id: str | None = None,
):
    """Build the typed MCP_CALL_DECISION run-event from a sandbox decision."""
    from datetime import datetime, timezone

    from ..protocol.mcp_decision_events import McpCallDecisionData, McpCallDecisionEvent

    ts = timestamp or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return McpCallDecisionEvent(
        type="MCP_CALL_DECISION",
        timestamp=ts,
        run_id=run_id,
        sequence=sequence,
        data=McpCallDecisionData(
            server_id=decision.server_id,
            tool_name=decision.tool_name,
            decision=decision.decision.value,
            risk_level=decision.risk_score.level.value,
            policy=decision.policy.value,
            reason=decision.reason,
            correlation_id=correlation_id,
        ),
    )


def persist_decision_event(workspace: Path, event) -> Path:
    """Append a typed MCP_CALL_DECISION event to .arc/mcp/decision-events.jsonl."""
    decisions_dir = workspace / ".arc" / "mcp"
    decisions_dir.mkdir(parents=True, exist_ok=True)
    path = decisions_dir / "decision-events.jsonl"
    with path.open("a", encoding="utf-8") as fp:
        fp.write(event.model_dump_json() + "\n")
    return path


def load_decisions(workspace: Path, limit: int = 50) -> list[dict[str, Any]]:
    """Load recent decisions from workspace-local decisions.jsonl."""
    path = workspace / ".arc" / "mcp" / "decisions.jsonl"
    if not path.exists():
        return []
    lines = path.read_text().strip().splitlines()
    results = []
    for line in lines[-limit:]:
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return results
