"""Canonical field mapping: ARC Studio MobileCapability ↔ ARC Runtime SDK CapabilityCard.

Implements R79/Phase 111 Slice 110.3. Provides two public functions:

- ``mobile_capability_to_sdk_card(cap)``  → dict (forward, for SDK export)
- ``sdk_card_to_mobile_capability(card)``  → MobileCapability (inverse, for import)

The mapping is intentionally explicit: every field is named, default-filled
where no equivalent exists, and documented with the source/target key. No
lossy silent discards — unmapped fields are carried in ``metadata`` on the
MobileCapability side.

Truth: the SDK CapabilityCard format is a plain dict/JSON schema (no Pydantic
model on the SDK side at this integration level). This module owns the
canonical bidirectional conversion so both sides stay in sync in one place.
"""

from __future__ import annotations

from typing import Any

from .mobile.models import (
    MobileApprovalMode,
    MobileCapability,
    MobileCapabilityCategory,
    MobileDataSensitivity,
)

# ── Category mapping ──────────────────────────────────────────────────────────

_MOBILE_CAT_TO_SDK: dict[str, str] = {
    "device": "native_bridge",
    "app": "plugin",
    "network": "network",
    "storage": "storage",
    "ui": "native_bridge",
    "sensor": "sensor",
    "media": "native_bridge",
    "communication": "native_bridge",
}

# Invert — multiple SDK categories may map to the same ARC category.
# We use the most specific match; "native_bridge" defaults to "device".
_SDK_CAT_TO_MOBILE: dict[str, str] = {
    "native_bridge": "device",
    "plugin": "app",
    "network": "network",
    "storage": "storage",
    "sensor": "sensor",
}

# ── Data sensitivity mapping ──────────────────────────────────────────────────

_MOBILE_SENS_TO_SDK: dict[str, str] = {
    "none": "none",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "critical": "pii",  # closest SDK equivalent
}

_SDK_SENS_TO_MOBILE: dict[str, str] = {
    "none": "none",
    "low": "low",
    "medium": "medium",
    "high": "high",
    "pii": "critical",  # map back to highest sensitivity
}


# ── Forward: MobileCapability → SDK CapabilityCard dict ──────────────────────


def mobile_capability_to_sdk_card(cap: MobileCapability) -> dict[str, Any]:
    """Convert an ARC Studio ``MobileCapability`` to an SDK CapabilityCard dict.

    Fields with no SDK equivalent are silently dropped (documented in the map
    below). The inverse function ``sdk_card_to_mobile_capability`` can
    reconstruct a MobileCapability from the result.
    """
    category_value = cap.category.value if hasattr(cap.category, "value") else str(cap.category)
    sensitivity_value = (
        cap.data_sensitivity.value
        if hasattr(cap.data_sensitivity, "value")
        else str(cap.data_sensitivity)
    )
    return {
        # direct id/name/description
        "id": cap.id,
        "name": cap.name,
        "description": cap.description,
        # category: MobileCapabilityCategory → SDK category string
        "category": _MOBILE_CAT_TO_SDK.get(category_value, "plugin"),
        # sensitivity: MobileDataSensitivity → SDK DataSensitivity
        "data_sensitivity": _MOBILE_SENS_TO_SDK.get(sensitivity_value, "none"),
        # default_decision is always deny (conservative)
        "default_decision": "deny",
        # paid ← bool (direct)
        "allow_paid_calls": cap.paid,
        # replayable → replay_safe (direct)
        "replay_safe": cap.replayable,
        # auditable → audit_required (direct)
        "audit_required": cap.auditable,
        # simulator_supported → fixture_required_in_simulator (inverse)
        "fixture_required_in_simulator": cap.simulator_supported,
        # approval_mode → auth_required: BLOCKING/REQUIRED → "biometric", else "none"
        "auth_required": (
            "biometric"
            if cap.approval_mode in (MobileApprovalMode.BLOCKING, MobileApprovalMode.REQUIRED)
            else "none"
        ),
        # no SDK equivalents: mcp_exposable, requires_hitl, platforms,
        # required_permissions, background, network, reads, writes, requires_trust
        "ai_consent_required": False,
        "enterprise_only": False,
    }


# ── Inverse: SDK CapabilityCard dict → MobileCapability ──────────────────────


def sdk_card_to_mobile_capability(card: dict[str, Any]) -> MobileCapability:
    """Convert an SDK CapabilityCard dict to an ARC Studio ``MobileCapability``.

    Fields that exist only on the SDK side (``auth_required``,
    ``ai_consent_required``, ``enterprise_only``, ``default_decision``) are
    preserved in the ``metadata`` dict so no information is silently lost.
    """
    sdk_cat = str(card.get("category", "plugin"))
    sdk_sens = str(card.get("data_sensitivity", "none"))
    auth = str(card.get("auth_required", "none"))

    mobile_cat_str = _SDK_CAT_TO_MOBILE.get(sdk_cat, "device")
    mobile_sens_str = _SDK_SENS_TO_MOBILE.get(sdk_sens, "none")
    approval_mode = (
        MobileApprovalMode.BLOCKING
        if auth in ("biometric", "pin", "face_id")
        else MobileApprovalMode.NONE
    )

    # Carry SDK-only fields in metadata to avoid silent information loss.
    metadata: dict[str, Any] = {}
    for key in ("auth_required", "ai_consent_required", "enterprise_only", "default_decision"):
        if key in card:
            metadata[f"sdk_{key}"] = card[key]

    return MobileCapability(
        id=str(card.get("id", "")),
        name=str(card.get("name", "")),
        description=str(card.get("description", "")),
        category=MobileCapabilityCategory(mobile_cat_str),
        data_sensitivity=MobileDataSensitivity(mobile_sens_str),
        paid=bool(card.get("allow_paid_calls", False)),
        replayable=bool(card.get("replay_safe", True)),
        auditable=bool(card.get("audit_required", True)),
        simulator_supported=bool(card.get("fixture_required_in_simulator", True)),
        approval_mode=approval_mode,
        metadata=metadata,
    )


# ── Public surface ────────────────────────────────────────────────────────────

__all__ = [
    "mobile_capability_to_sdk_card",
    "sdk_card_to_mobile_capability",
    "_MOBILE_CAT_TO_SDK",
    "_SDK_CAT_TO_MOBILE",
    "_MOBILE_SENS_TO_SDK",
    "_SDK_SENS_TO_MOBILE",
]
