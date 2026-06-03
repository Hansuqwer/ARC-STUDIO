"""Safe mobile action simulator.

Pure static analysis — no native calls, no network, no OS permission requests,
no real data access. Predicts what an action plan would do.
"""

from __future__ import annotations

from .hashing import report_hash as _report_hash
from .models import (
    MobileActionPlan,
    MobileActionSimulationReport,
    MobileCapability,
    MobileSimulationStepResult,
)

_SENSITIVE_PREFIXES = (
    "device.camera",
    "device.microphone",
    "device.location",
    "device.calendar",
    "device.contacts",
    "device.photos",
    "device.health",
    "device.biometric",
)

_RISK_SCORE = {"none": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}


def simulate_action_plan(
    plan: MobileActionPlan,
    extra_capabilities: list[MobileCapability] | None = None,
) -> MobileActionSimulationReport:
    """Simulate a MobileActionPlan. Returns MobileActionSimulationReport.

    Never executes anything. Pure static prediction.
    """
    step_results: list[MobileSimulationStepResult] = []
    blocked: list[str] = []
    req_permissions: list[str] = []
    req_approvals: list[str] = []
    warnings: list[str] = []
    max_risk = 0

    # Build capability lookup (catalog + extra)
    catalog: dict[str, MobileCapability] = {}
    from .capabilities import _CATALOG

    catalog.update(_CATALOG)
    for cap in extra_capabilities or []:
        catalog[cap.id] = cap

    # Top-level blocks
    if plan.requires_background:
        warnings.append("BACKGROUND_BLOCKED: plan requires background execution (blocked in MVP)")
    if plan.requires_network:
        warnings.append("NETWORK_BLOCKED: plan requires network (blocked in MVP)")

    for step in plan.steps:
        cap = catalog.get(step.capability_id)

        if cap is None:
            step_results.append(
                MobileSimulationStepResult(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    allowed=False,
                    mock=False,
                    blocked_reason=f"Unknown capability '{step.capability_id}'",
                )
            )
            blocked.append(step.step_id)
            continue

        # Block: background
        if cap.background:
            step_results.append(
                MobileSimulationStepResult(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    allowed=False,
                    mock=step.mock,
                    blocked_reason="background execution blocked in MVP",
                )
            )
            blocked.append(step.step_id)
            continue

        # Block: network non-mock
        if cap.network and not cap.id.endswith(".mock"):
            step_results.append(
                MobileSimulationStepResult(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    allowed=False,
                    mock=step.mock,
                    blocked_reason="network capability must be mock in MVP",
                )
            )
            blocked.append(step.step_id)
            continue

        # Block: sensitive non-mock
        cid = cap.id.lower()
        if any(cid.startswith(p) for p in _SENSITIVE_PREFIXES) and not cid.endswith(".mock"):
            step_results.append(
                MobileSimulationStepResult(
                    step_id=step.step_id,
                    capability_id=step.capability_id,
                    allowed=False,
                    mock=False,
                    blocked_reason=f"sensitive capability '{cap.id}' must be mock in MVP",
                )
            )
            blocked.append(step.step_id)
            continue

        # Collect predicted permissions
        predicted_perms = [p.id for p in cap.required_permissions]
        req_permissions.extend(predicted_perms)

        # Collect predicted approvals
        predicted_approvals: list[str] = []
        if cap.approval_mode.value in ("required", "blocking"):
            predicted_approvals.append(cap.id)
            req_approvals.append(cap.id)

        # Risk
        risk = _RISK_SCORE.get(cap.data_sensitivity.value, 0)
        max_risk = max(max_risk, risk)

        step_results.append(
            MobileSimulationStepResult(
                step_id=step.step_id,
                capability_id=step.capability_id,
                allowed=True,
                mock=step.mock or cap.simulator_supported,
                predicted_permissions=predicted_perms,
                predicted_approvals=predicted_approvals,
                audit_required=cap.auditable,
                replayable=cap.replayable,
            )
        )

    risk_labels = {0: "low", 1: "low", 2: "medium", 3: "high", 4: "critical"}
    overall_allowed = not blocked and not plan.requires_background and not plan.requires_network

    report = MobileActionSimulationReport(
        plan_id=plan.plan_id,
        overall_allowed=overall_allowed,
        steps=step_results,
        blocked_steps=blocked,
        requires_permissions=list(dict.fromkeys(req_permissions)),
        requires_approvals=list(dict.fromkeys(req_approvals)),
        risk_level=risk_labels.get(max_risk, "low"),
        warnings=warnings,
    )
    report.report_hash = _report_hash(report)
    return report
