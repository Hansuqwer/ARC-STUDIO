"""Capability snapshot and degradation manifest validation.

Compares runtime capability snapshots across switches and validates
that cockpit primitives (contracts, receipts, evidence, stable IDs)
are correctly advertised.

Produces TrustDiff when capabilities change in ways that affect trust
boundaries.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, Field

from .capabilities import RuntimeCapabilities


class CapabilitySnapshot(BaseModel):
    """Frozen snapshot of a runtime's capabilities at a point in time."""

    schema_version: int = 1
    runtime_id: str
    snapshot_id: str
    capabilities: RuntimeCapabilities
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = Field(default_factory=dict)


class CapabilityDiff(BaseModel):
    """Diff between two capability snapshots."""

    schema_version: int = 1
    diff_id: str
    runtime_id: str
    before_snapshot_id: str
    after_snapshot_id: str
    added_capabilities: list[str] = Field(default_factory=list)
    removed_capabilities: list[str] = Field(default_factory=list)
    changed_flags: dict[str, dict] = Field(default_factory=dict)
    requires_confirmation: bool = False
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DegradationValidation(BaseModel):
    """Validation result for a runtime's capability claims vs actual behavior."""

    schema_version: int = 1
    runtime_id: str
    validation_id: str
    is_valid: bool
    claimed_capabilities: list[str] = Field(default_factory=list)
    actual_capabilities: list[str] = Field(default_factory=list)
    missing_capabilities: list[str] = Field(default_factory=list)
    false_claims: list[str] = Field(default_factory=list)
    degradation_level: str = "none"  # none, partial, severe
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Cockpit primitive flags that affect graph linkage
# ---------------------------------------------------------------------------

COCKPIT_PRIMITIVE_FLAGS = [
    "can_emit_contract",
    "can_emit_receipt",
    "can_emit_autopsy",
    "can_emit_evidence",
    "has_stable_ids",
]

TRUST_SENSITIVE_FLAGS = [
    "can_run",
    "requires_paid_calls",
    "requires_shell",
    "requires_secrets",
    "requires_network",
]


def snapshot_capabilities(runtime_id: str, caps: RuntimeCapabilities) -> CapabilitySnapshot:
    """Create a frozen snapshot of current runtime capabilities."""
    from ..protocol.stable_ids import generate_stable_id

    snapshot_id = generate_stable_id("session")
    return CapabilitySnapshot(
        runtime_id=runtime_id,
        snapshot_id=snapshot_id,
        capabilities=caps,
    )


def diff_capabilities(
    runtime_id: str,
    before: CapabilitySnapshot,
    after: CapabilitySnapshot,
) -> CapabilityDiff:
    """Compare two capability snapshots and produce a diff."""
    from ..protocol.stable_ids import generate_stable_id

    diff_id = generate_stable_id("decision")

    added = []
    removed = []
    changed = {}

    before_dict = before.capabilities.model_dump()
    after_dict = after.capabilities.model_dump()

    for key in set(list(before_dict.keys()) + list(after_dict.keys())):
        if key in ("schema_version",):
            continue
        before_val = before_dict.get(key)
        after_val = after_dict.get(key)
        if before_val != after_val:
            changed[key] = {"before": before_val, "after": after_val}
            if isinstance(before_val, bool) and isinstance(after_val, bool):
                if after_val and not before_val:
                    added.append(key)
                elif not after_val and before_val:
                    removed.append(key)

    # Determine if confirmation is needed
    requires_confirmation = any(flag in added or flag in removed for flag in TRUST_SENSITIVE_FLAGS)

    return CapabilityDiff(
        diff_id=diff_id,
        runtime_id=runtime_id,
        before_snapshot_id=before.snapshot_id,
        after_snapshot_id=after.snapshot_id,
        added_capabilities=added,
        removed_capabilities=removed,
        changed_flags=changed,
        requires_confirmation=requires_confirmation,
    )


def validate_capability_claims(
    runtime_id: str,
    caps: RuntimeCapabilities,
    actual_behavior: dict,
) -> DegradationValidation:
    """Validate that a runtime's claimed capabilities match actual behavior.

    Args:
        runtime_id: The runtime identifier.
        caps: The runtime's declared capabilities.
        actual_behavior: Observed behavior from actual runs, e.g.:
            {
                "emitted_contracts": True,
                "emitted_receipts": False,
                "has_stable_ids_in_events": True,
                "emitted_evidence": False,
            }

    Returns:
        DegradationValidation with validation results.

    """
    from ..protocol.stable_ids import generate_stable_id

    validation_id = generate_stable_id("decision")

    claimed = []
    actual = []
    missing = []
    false_claims = []

    # Check cockpit primitive flags
    flag_to_behavior_key = {
        "can_emit_contract": "emitted_contracts",
        "can_emit_receipt": "emitted_receipts",
        "can_emit_autopsy": "emitted_autopsies",
        "can_emit_evidence": "emitted_evidence",
        "has_stable_ids": "has_stable_ids_in_events",
    }

    for flag, behavior_key in flag_to_behavior_key.items():
        claimed_value = getattr(caps, flag, False)
        actual_value = actual_behavior.get(behavior_key, False)

        if claimed_value:
            claimed.append(flag)
        if actual_value:
            actual.append(flag)
        if claimed_value and not actual_value:
            false_claims.append(flag)
        if not claimed_value and actual_value:
            missing.append(flag)

    # Determine degradation level
    critical_false = [f for f in false_claims if f in ("has_stable_ids", "can_emit_evidence")]
    if len(critical_false) >= 2:
        degradation_level = "severe"
    elif false_claims:
        degradation_level = "partial"
    else:
        degradation_level = "none"

    is_valid = len(false_claims) == 0

    return DegradationValidation(
        runtime_id=runtime_id,
        validation_id=validation_id,
        is_valid=is_valid,
        claimed_capabilities=claimed,
        actual_capabilities=actual,
        missing_capabilities=missing,
        false_claims=false_claims,
        degradation_level=degradation_level,
    )


def get_cockpit_readiness(caps: RuntimeCapabilities) -> dict:
    """Return a summary of cockpit primitive readiness."""
    return {
        "contracts": caps.can_emit_contract,
        "receipts": caps.can_emit_receipt,
        "autopsies": caps.can_emit_autopsy,
        "evidence": caps.can_emit_evidence,
        "stable_ids": caps.has_stable_ids,
        "graph_linkage_available": caps.has_stable_ids and caps.can_emit_evidence,
        "cross_surface_linking": caps.has_stable_ids,
    }
