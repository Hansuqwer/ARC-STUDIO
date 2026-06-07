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
