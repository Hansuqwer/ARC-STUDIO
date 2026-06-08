"""Runtime-wide confirmation enforcement for high/critical adaptive decisions (B2P-08).

Deterministic, LLM-free. When an adaptive risk assessment is high/critical (``hitl_required``),
a decision must be explicitly approved before it proceeds; otherwise it is blocked and the
enforcement is appended to a tamper-evident-style audit log. This is the canonical gate that
runtime entrypoints call so high/critical adaptive decisions cannot run without confirmation.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Risk levels that require explicit confirmation before a decision may proceed.
_CONFIRM_LEVELS = frozenset({"high", "critical"})


@dataclass(frozen=True)
class ConfirmationDecision:
    """The deterministic verdict of the adaptive-confirmation gate."""

    allowed: bool
    risk_level: str
    hitl_required: bool
    requires_confirmation: bool
    approved: bool
    reason: str
    decision_id: str = ""
    deterministic: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "risk_level": self.risk_level,
            "hitl_required": self.hitl_required,
            "requires_confirmation": self.requires_confirmation,
            "approved": self.approved,
            "reason": self.reason,
            "decision_id": self.decision_id,
            "deterministic": self.deterministic,
        }


def evaluate_confirmation(
    risk_level: str,
    hitl_required: bool,
    *,
    approved: bool = False,
    decision_id: str = "",
) -> ConfirmationDecision:
    """Deterministically decide whether a high/critical adaptive decision may proceed.

    A decision requires confirmation when it is ``hitl_required`` or its risk level is
    high/critical. Such a decision is allowed only when ``approved`` is explicitly true.
    """
    requires = bool(hitl_required) or str(risk_level).lower() in _CONFIRM_LEVELS
    if not requires:
        return ConfirmationDecision(
            allowed=True,
            risk_level=risk_level,
            hitl_required=hitl_required,
            requires_confirmation=False,
            approved=approved,
            reason="risk level does not require confirmation",
            decision_id=decision_id,
        )
    if approved:
        return ConfirmationDecision(
            allowed=True,
            risk_level=risk_level,
            hitl_required=hitl_required,
            requires_confirmation=True,
            approved=True,
            reason="high/critical decision explicitly approved",
            decision_id=decision_id,
        )
    return ConfirmationDecision(
        allowed=False,
        risk_level=risk_level,
        hitl_required=hitl_required,
        requires_confirmation=True,
        approved=False,
        reason="high/critical adaptive decision requires explicit confirmation",
        decision_id=decision_id,
    )


def persist_confirmation_audit_event(
    decision: ConfirmationDecision, workspace_root: Path | None = None
) -> Path:
    """Append the confirmation decision to the adaptive-confirmation audit log."""
    root = workspace_root or Path.cwd()
    audit_path = root / ".arc" / "audit" / "adaptive_confirmation.events.jsonl"
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "type": "adaptive_confirmation",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **decision.as_dict(),
    }
    with audit_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True) + "\n")
    return audit_path


def enforce_confirmation(
    risk_level: str,
    hitl_required: bool,
    *,
    approved: bool = False,
    decision_id: str = "",
    workspace_root: Path | None = None,
    audit: bool = True,
) -> ConfirmationDecision:
    """Evaluate the confirmation gate and (by default) audit decisions that required confirmation."""
    decision = evaluate_confirmation(
        risk_level, hitl_required, approved=approved, decision_id=decision_id
    )
    if audit and decision.requires_confirmation:
        persist_confirmation_audit_event(decision, workspace_root=workspace_root)
    return decision
