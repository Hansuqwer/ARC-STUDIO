"""Generate Capability Cards from runtime adapters.

This module provides functions to convert RuntimeAdapter instances and
CapabilityReport into CapabilityCard instances.

Design rules:
- One card per runtime adapter (entity_type: runtime_adapter)
- Preserve adapter ID and version in provenance
- Use RuntimeCapabilities and CapabilityReport for capability flags
- Never execute workflows or make network calls
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ..adapters.base import CapabilityReport, RuntimeAdapter

from .hashing import card_hash
from .models import (
    ApprovalMode,
    AuditLevel,
    AuditProfile,
    CapabilityCard,
    CapabilityProvenance,
    CapabilitySet,
    EntityType,
    HitlRequirement,
    ReplayProfile,
    RiskLevel,
    TrustLevel,
    TrustProfile,
)


def card_from_adapter(
    adapter: RuntimeAdapter,
    *,
    workspace: Optional[Path] = None,
) -> CapabilityCard:
    """Generate a CapabilityCard from a RuntimeAdapter.

    Args:
        adapter: The RuntimeAdapter instance to convert.
        workspace: Optional workspace for capability report.

    Returns:
        A CapabilityCard representing the adapter's capabilities.
    """
    # Get capabilities and capability report
    caps = adapter.capabilities()
    report = adapter.capability_report(workspace or Path.cwd()) if workspace else None

    # Build capability flags
    card_caps = CapabilitySet(
        can_read=caps.can_inspect,
        can_execute=caps.can_run,
        can_emit_events=caps.can_stream_events,
        can_replay=caps.can_replay,
        can_network=False,  # Adapters don't make network calls directly
    )

    # Determine risk level from capability report
    risk_level = RiskLevel.LOW
    if report:
        if report.requires_paid_calls:
            risk_level = RiskLevel.MEDIUM
        if not report.can_run and report.detected:
            risk_level = RiskLevel.HIGH
        if report.availability in ("paid_calls_blocked", "missing_dependency"):
            risk_level = RiskLevel.HIGH

    # Derive trust profile
    trust = TrustProfile(
        requires_workspace_trust=True,
        trust_level=TrustLevel.WORKSPACE,
        hitl_requirement=HitlRequirement.NONE,
        approval_mode=ApprovalMode.NONE,
    )

    # Adapters don't require audit by default
    audit = AuditProfile(
        audit_required=False,
        audit_level=AuditLevel.NONE,
    )

    # Build provenance
    provenance = CapabilityProvenance(
        source_type="adapter",
        adapter_id=adapter.adapter_id,
        adapter_name=adapter.adapter_name,
    )

    # Build permissions
    permissions: list[tuple[str, str, str]] = []
    if caps.can_inspect:
        permissions.append(("adapter.inspect", "Inspect workspace", "allow"))
    if caps.can_run:
        permissions.append(("adapter.run", "Execute workflow", "deny"))
    if caps.can_stream_events:
        permissions.append(("adapter.stream_events", "Stream run events", "allow"))

    # Build metadata
    metadata: dict[str, Any] = {
        "adapter_id": adapter.adapter_id,
        "adapter_name": adapter.adapter_name,
        "runtime": getattr(caps, "runtime", adapter.adapter_id),
    }

    if report:
        metadata.update(
            {
                "detected": report.detected,
                "can_run": report.can_run,
                "availability": report.availability,
                "requires_paid_calls": report.requires_paid_calls,
                "detected_artifacts": report.detected_artifacts,
                "version": report.version,
                "test_level": report.test_level,
            }
        )

    # Build card
    card = CapabilityCard(
        id=f"adapter-{adapter.adapter_id}",
        name=adapter.adapter_name,
        entity_type=EntityType.RUNTIME_ADAPTER,
        description=f"Runtime adapter '{adapter.adapter_id}' for {adapter.adapter_name}",
        capabilities=card_caps,
        permissions=[
            {"kind": p[0], "required": False, "reason": p[1], "default_decision": p[2]}
            for p in permissions
        ],
        trust=trust,
        audit=audit,
        replay=ReplayProfile(
            replayable=caps.can_replay,
            deterministic=False,
            non_replayable_reasons=["runtime_non_deterministic"] if not caps.can_replay else [],
        ),
        risk_level=risk_level,
        provenance=provenance,
        metadata=metadata,
        requires_review=risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
    )

    # Compute hash
    card.card_hash = card_hash(card)

    return card


def card_from_capability_report(report: CapabilityReport) -> CapabilityCard:
    """Generate a CapabilityCard from a CapabilityReport.

    This is useful when you have a report but not the full adapter instance.

    Args:
        report: The CapabilityReport to convert.

    Returns:
        A CapabilityCard representing the reported capabilities.
    """
    # Build capability flags
    card_caps = CapabilitySet(
        can_read=report.detected,
        can_execute=report.can_run,
        can_emit_events=report.can_emit_contract or report.can_emit_receipt,
        can_replay=False,  # Not in CapabilityReport
    )

    # Determine risk level
    risk_level = RiskLevel.LOW
    if report.requires_paid_calls:
        risk_level = RiskLevel.MEDIUM
    if not report.can_run and report.detected:
        risk_level = RiskLevel.HIGH
    if report.availability in ("paid_calls_blocked", "missing_dependency"):
        risk_level = RiskLevel.HIGH

    # Derive trust profile
    trust = TrustProfile(
        requires_workspace_trust=True,
        trust_level=TrustLevel.WORKSPACE,
        hitl_requirement=HitlRequirement.NONE,
        approval_mode=ApprovalMode.NONE,
    )

    # Build provenance
    provenance = CapabilityProvenance(
        source_type="adapter",
        adapter_id=report.runtime_id,
    )

    # Build metadata
    metadata = {
        "detected": report.detected,
        "can_run": report.can_run,
        "availability": report.availability,
        "requires_paid_calls": report.requires_paid_calls,
        "detected_artifacts": report.detected_artifacts,
        "version": report.version,
        "test_level": report.test_level,
        "fake_offline_supported": report.fake_offline_supported,
        "local_real_gated": report.local_real_gated,
        "local_real_available": report.local_real_available,
        "provider_backed": report.provider_backed,
    }

    # Build card
    card = CapabilityCard(
        id=f"adapter-{report.runtime_id}",
        name=report.runtime_id,
        entity_type=EntityType.RUNTIME_ADAPTER,
        description=f"Runtime adapter report for '{report.runtime_id}'",
        capabilities=card_caps,
        trust=trust,
        provenance=provenance,
        metadata=metadata,
        requires_review=risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL),
    )

    # Compute hash
    card.card_hash = card_hash(card)

    return card


def cards_from_adapters(
    adapters: list[RuntimeAdapter],
    *,
    workspace: Optional[Path] = None,
) -> list[CapabilityCard]:
    """Generate CapabilityCards from a list of RuntimeAdapters.

    Args:
        adapters: List of RuntimeAdapter instances.
        workspace: Optional workspace root.

    Returns:
        List of CapabilityCards for all adapters.
    """
    return [card_from_adapter(adapter, workspace=workspace) for adapter in adapters]
