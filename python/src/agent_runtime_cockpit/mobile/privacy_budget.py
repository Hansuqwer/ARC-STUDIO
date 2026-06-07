"""Privacy budget ledger for ARC Mobile Runtime.

Tallies capability reads, writes, and sensitive data classes declared in a
manifest or action plan. Pure analysis — no execution, no network, no OS calls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import MobileRuntimeManifest, MobileDataSensitivity


@dataclass
class PrivacyBudget:
    """Tallied privacy budget from a manifest's declared capabilities."""

    manifest_id: str
    total_capabilities: int = 0
    read_capabilities: int = 0
    write_capabilities: int = 0
    network_capabilities: int = 0
    background_capabilities: int = 0
    sensitive_classes: list[str] = field(default_factory=list)
    critical_capabilities: list[str] = field(default_factory=list)
    high_capabilities: list[str] = field(default_factory=list)
    approval_required_count: int = 0
    hitl_required_count: int = 0
    mcp_exposable_count: int = 0
    simulator_mode: bool = True
    advisory: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "advisory": self.advisory,
            "manifest_id": self.manifest_id,
            "simulator_mode": self.simulator_mode,
            "total_capabilities": self.total_capabilities,
            "read_capabilities": self.read_capabilities,
            "write_capabilities": self.write_capabilities,
            "network_capabilities": self.network_capabilities,
            "background_capabilities": self.background_capabilities,
            "sensitive_classes": self.sensitive_classes,
            "critical_capabilities": self.critical_capabilities,
            "high_capabilities": self.high_capabilities,
            "approval_required_count": self.approval_required_count,
            "hitl_required_count": self.hitl_required_count,
            "mcp_exposable_count": self.mcp_exposable_count,
        }


def compute_privacy_budget(manifest: MobileRuntimeManifest) -> PrivacyBudget:
    """Compute a PrivacyBudget from a manifest's declared capabilities."""
    budget = PrivacyBudget(
        manifest_id=manifest.id,
        simulator_mode=manifest.simulator_mode,
    )
    seen_classes: set[str] = set()

    for cap in manifest.capabilities:
        budget.total_capabilities += 1
        if cap.reads:
            budget.read_capabilities += 1
        if cap.writes:
            budget.write_capabilities += 1
        if cap.network:
            budget.network_capabilities += 1
        if cap.background:
            budget.background_capabilities += 1
        if cap.mcp_exposable:
            budget.mcp_exposable_count += 1
        if cap.requires_hitl:
            budget.hitl_required_count += 1
        if cap.approval_mode.value in ("required", "blocking"):
            budget.approval_required_count += 1

        sens = cap.data_sensitivity.value
        if sens == MobileDataSensitivity.CRITICAL.value:
            budget.critical_capabilities.append(cap.id)
            if sens not in seen_classes:
                budget.sensitive_classes.append(sens)
                seen_classes.add(sens)
        elif sens == MobileDataSensitivity.HIGH.value:
            budget.high_capabilities.append(cap.id)
            if sens not in seen_classes:
                budget.sensitive_classes.append(sens)
                seen_classes.add(sens)
        elif sens in ("medium", "low"):
            if sens not in seen_classes:
                budget.sensitive_classes.append(sens)
                seen_classes.add(sens)

    return budget


# ── Data-egress guard (Phase 8) ──────────────────────────────────────────────
# Deterministic, budget-bound accounting for *simulated* egress. This performs no
# network I/O; it decides allow/deny for declared egress so a flow that would exceed
# its byte budget (overall or per data class) is blocked before it could ever run.
# Security decision is deterministic — no LLM, no probabilistic judgement.

_CRITICAL = MobileDataSensitivity.CRITICAL.value


@dataclass
class EgressDecision:
    """The deterministic verdict for a single egress request."""

    allowed: bool
    classification: str
    byte_cost: int
    reason: str
    remaining_bytes: int
    deterministic: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "classification": self.classification,
            "byte_cost": self.byte_cost,
            "reason": self.reason,
            "remaining_bytes": self.remaining_bytes,
            "deterministic": self.deterministic,
        }


class EgressGuard:
    """Budget-bound egress guard. Denies (deterministically) when an egress would exceed
    the overall byte budget, a per-classification limit, or touches a blocked class.

    Blocked classes (default: ``critical``) never egress in simulator preview. ``check``
    is pure (no state change); ``record`` applies the cost only when allowed.
    """

    def __init__(
        self,
        budget_bytes: int,
        per_class_limits: dict[str, int] | None = None,
        blocked_classifications: set[str] | None = None,
    ) -> None:
        if budget_bytes < 0:
            raise ValueError("budget_bytes must be >= 0")
        self.budget_bytes = budget_bytes
        self.per_class_limits = dict(per_class_limits or {})
        self.blocked_classifications = (
            {_CRITICAL} if blocked_classifications is None else set(blocked_classifications)
        )
        self._used_total = 0
        self._used_by_class: dict[str, int] = {}

    def _classification(self, classification: MobileDataSensitivity | str) -> str:
        return (
            classification.value
            if isinstance(classification, MobileDataSensitivity)
            else str(classification)
        )

    def check(self, byte_cost: int, classification: MobileDataSensitivity | str) -> EgressDecision:
        cls = self._classification(classification)
        remaining = self.budget_bytes - self._used_total
        if byte_cost < 0:
            return EgressDecision(False, cls, byte_cost, "negative byte_cost", remaining)
        if cls in self.blocked_classifications:
            return EgressDecision(
                False, cls, byte_cost, f"classification '{cls}' is blocked from egress", remaining
            )
        if self._used_total + byte_cost > self.budget_bytes:
            return EgressDecision(False, cls, byte_cost, "over overall egress budget", remaining)
        limit = self.per_class_limits.get(cls)
        if limit is not None and self._used_by_class.get(cls, 0) + byte_cost > limit:
            return EgressDecision(
                False, cls, byte_cost, f"over per-class budget for '{cls}'", remaining
            )
        return EgressDecision(True, cls, byte_cost, "within budget", remaining - byte_cost)

    def record(self, byte_cost: int, classification: MobileDataSensitivity | str) -> EgressDecision:
        decision = self.check(byte_cost, classification)
        if decision.allowed:
            self._used_total += byte_cost
            self._used_by_class[decision.classification] = (
                self._used_by_class.get(decision.classification, 0) + byte_cost
            )
        return decision

    def usage(self) -> dict[str, Any]:
        return {
            "budget_bytes": self.budget_bytes,
            "used_total": self._used_total,
            "remaining_bytes": self.budget_bytes - self._used_total,
            "used_by_class": dict(self._used_by_class),
            "blocked_classifications": sorted(self.blocked_classifications),
        }
