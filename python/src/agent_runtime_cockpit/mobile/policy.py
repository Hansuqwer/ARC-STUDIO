"""Fail-closed policy decisions for mobile capabilities and plans."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .models import MobileActionPlan, MobileCapability, MobileDataSensitivity
from .simulator import simulate_action_plan
from .validation import validate_action_plan, validate_capability


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


def explain_capability_policy(capability: MobileCapability) -> MobilePolicyDecision:
    report = validate_capability(capability)
    denied_rules = [finding.rule for finding in report.errors]
    sensitive = capability.data_sensitivity in (
        MobileDataSensitivity.HIGH,
        MobileDataSensitivity.CRITICAL,
    )
    approval_required = capability.approval_mode.value in {"required", "blocking"} or sensitive
    if denied_rules:
        return MobilePolicyDecision(
            allowed=False,
            approval_required=approval_required,
            capability_id=capability.id,
            reason="capability denied by mobile policy",
            denied_rules=denied_rules,
            required_approvals=[capability.id] if approval_required else [],
            mcp_exposable=capability.mcp_exposable,
        )
    if capability.mcp_exposable:
        return MobilePolicyDecision(
            allowed=False,
            approval_required=True,
            capability_id=capability.id,
            reason="MCP exposure is denied in the mobile MVP",
            denied_rules=["mcp_exposure_denied"],
            required_approvals=[capability.id],
            mcp_exposable=True,
        )
    return MobilePolicyDecision(
        allowed=True,
        approval_required=approval_required,
        capability_id=capability.id,
        reason="mock simulator capability allowed"
        if not approval_required
        else "mock simulator capability requires approval",
        required_approvals=[capability.id] if approval_required else [],
    )


def explain_plan_policy(
    plan: MobileActionPlan, capabilities: list[MobileCapability]
) -> MobilePolicyDecision:
    validation = validate_action_plan(plan, capabilities)
    simulation = simulate_action_plan(plan, capabilities)
    denied_rules = [finding.rule for finding in validation.errors]
    approval_required = bool(simulation.requires_approvals)
    allowed = validation.ok and simulation.overall_allowed
    return MobilePolicyDecision(
        allowed=allowed,
        approval_required=approval_required,
        plan_id=plan.plan_id,
        reason="plan allowed in mock simulator" if allowed else "plan denied by mobile policy",
        denied_rules=denied_rules or list(simulation.blocked_steps),
        required_approvals=list(simulation.requires_approvals),
    )
