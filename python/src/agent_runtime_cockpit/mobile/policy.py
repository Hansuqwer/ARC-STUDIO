"""Fail-closed policy decisions for mobile capabilities and plans.

Changes (PR12):
- MobilePolicyDecision gains policy_version field.
- Decision logging to ~/.arc/audit/mobile_decisions.jsonl (append-only).
- EnterprisePolicyHook interface for future org/tenant policy extension.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from .models import MobileActionPlan, MobileCapability, MobileDataSensitivity
from .simulator import simulate_action_plan
from .validation import validate_action_plan, validate_capability

log = logging.getLogger(__name__)

MOBILE_POLICY_VERSION = "1.0.0"
_AUDIT_FILE = Path.home() / ".arc" / "audit" / "mobile_decisions.jsonl"


@runtime_checkable
class EnterprisePolicyHook(Protocol):
    """Extension point for org/tenant policy overrides.

    Implement this protocol and pass it to explain_capability_policy /
    explain_plan_policy to inject enterprise policy context.
    Returns None to defer to the default policy.
    """

    def evaluate(
        self,
        decision: "MobilePolicyDecision",
        context: dict[str, Any],
    ) -> "MobilePolicyDecision | None": ...


class MobilePolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allowed: bool
    approval_required: bool = False
    capability_id: str | None = None
    plan_id: str | None = None
    reason: str
    denied_rules: list[str] = Field(default_factory=list)
    required_approvals: list[str] = Field(default_factory=list)
    mcp_exposable: bool = False
    policy_version: str = MOBILE_POLICY_VERSION


def _log_decision(decision: MobilePolicyDecision) -> None:
    """Append decision to audit log. Best-effort: never raises."""
    try:
        _AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
        entry = decision.model_dump(mode="json")
        entry["logged_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with _AUDIT_FILE.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")
    except Exception as exc:  # noqa: BLE001
        log.debug("mobile_decisions audit log failed: %s", exc)


def explain_capability_policy(
    capability: MobileCapability,
    *,
    enterprise_hook: EnterprisePolicyHook | None = None,
    log_decision: bool = True,
) -> MobilePolicyDecision:
    report = validate_capability(capability)
    denied_rules = [finding.rule for finding in report.errors]
    sensitive = capability.data_sensitivity in (
        MobileDataSensitivity.HIGH,
        MobileDataSensitivity.CRITICAL,
    )
    approval_required = capability.approval_mode.value in {"required", "blocking"} or sensitive

    if denied_rules:
        decision = MobilePolicyDecision(
            allowed=False,
            approval_required=approval_required,
            capability_id=capability.id,
            reason="capability denied by mobile policy",
            denied_rules=denied_rules,
            required_approvals=[capability.id] if approval_required else [],
            mcp_exposable=capability.mcp_exposable,
        )
    elif capability.mcp_exposable:
        decision = MobilePolicyDecision(
            allowed=False,
            approval_required=True,
            capability_id=capability.id,
            reason="MCP exposure is denied in the mobile MVP",
            denied_rules=["mcp_exposure_denied"],
            required_approvals=[capability.id],
            mcp_exposable=True,
        )
    else:
        decision = MobilePolicyDecision(
            allowed=True,
            approval_required=approval_required,
            capability_id=capability.id,
            reason=(
                "mock simulator capability allowed"
                if not approval_required
                else "mock simulator capability requires approval"
            ),
            required_approvals=[capability.id] if approval_required else [],
        )

    if enterprise_hook is not None:
        override = enterprise_hook.evaluate(decision, {"capability_id": capability.id})
        if override is not None:
            decision = override

    if log_decision:
        _log_decision(decision)
    return decision


def explain_plan_policy(
    plan: MobileActionPlan,
    capabilities: list[MobileCapability],
    *,
    enterprise_hook: EnterprisePolicyHook | None = None,
    log_decision: bool = True,
) -> MobilePolicyDecision:
    validation = validate_action_plan(plan, capabilities)
    simulation = simulate_action_plan(plan, capabilities)
    denied_rules = [finding.rule for finding in validation.errors]
    approval_required = bool(simulation.requires_approvals)
    allowed = validation.ok and simulation.overall_allowed

    decision = MobilePolicyDecision(
        allowed=allowed,
        approval_required=approval_required,
        plan_id=plan.plan_id,
        reason="plan allowed in mock simulator" if allowed else "plan denied by mobile policy",
        denied_rules=denied_rules or list(simulation.blocked_steps),
        required_approvals=list(simulation.requires_approvals),
    )

    if enterprise_hook is not None:
        override = enterprise_hook.evaluate(decision, {"plan_id": plan.plan_id})
        if override is not None:
            decision = override

    if log_decision:
        _log_decision(decision)
    return decision
