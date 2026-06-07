"""Canonical field mapping: ARC Studio MobileCapability ↔ ARC Runtime SDK CapabilityCard.

Implements R79/Phase 111 Slice 110.3. Provides two public functions:

- ``mobile_capability_to_sdk_card(cap)``  → dict (forward, for SDK export)
- ``sdk_card_to_mobile_capability(card)``  → MobileCapability (inverse, for import)

Forward direction (Mobile → SDK) is **intentionally lossy**: seven governance fields have
no equivalent in the SDK CapabilityCard schema and cannot be represented there:
  ``platforms``, ``required_permissions``, ``background``, ``network``,
  ``reads``, ``writes``, ``requires_trust``.
These values are preserved in the SDK card's ``metadata["arc_dropped_fields"]`` dict so
the inverse direction can reconstruct them without silent loss.

Inverse direction (SDK → Mobile) preserves all SDK-only fields in ``metadata`` under the
``sdk_`` prefix (``auth_required``, ``ai_consent_required``, ``enterprise_only``,
``default_decision``).

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

    Seven governance fields have no SDK equivalent and are captured in
    ``metadata["arc_dropped_fields"]`` for lossless round-tripping:
    ``platforms``, ``required_permissions``, ``background``, ``network``,
    ``reads``, ``writes``, ``requires_trust``.
    """
    category_value = cap.category.value if hasattr(cap.category, "value") else str(cap.category)
    sensitivity_value = (
        cap.data_sensitivity.value
        if hasattr(cap.data_sensitivity, "value")
        else str(cap.data_sensitivity)
    )

    # Capture governance fields that have no SDK-card equivalent
    platforms_val = [p.value if hasattr(p, "value") else str(p) for p in cap.platforms]
    perms_val = [
        {
            "id": p.id,
            "platform": p.platform.value if hasattr(p.platform, "value") else str(p.platform),
            "required": p.required,
            "mock_safe": p.mock_safe,
        }
        for p in cap.required_permissions
    ]
    arc_dropped: dict[str, Any] = {
        "platforms": platforms_val,
        "required_permissions": perms_val,
        "background": cap.background,
        "network": cap.network,
        "reads": cap.reads,
        "writes": cap.writes,
        "requires_trust": cap.requires_trust,
    }

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
        "ai_consent_required": False,
        "enterprise_only": False,
        # Governance fields with no SDK equivalent — preserved for round-trip
        "metadata": {"arc_dropped_fields": arc_dropped},
    }


# ── Inverse: SDK CapabilityCard dict → MobileCapability ──────────────────────


def sdk_card_to_mobile_capability(card: dict[str, Any]) -> MobileCapability:
    """Convert an SDK CapabilityCard dict to an ARC Studio ``MobileCapability``.

    SDK-only fields (``auth_required``, ``ai_consent_required``, ``enterprise_only``,
    ``default_decision``) are preserved in ``metadata`` under the ``sdk_`` prefix.

    If the card was produced by ``mobile_capability_to_sdk_card``, the seven
    governance fields stored in ``metadata["arc_dropped_fields"]`` are restored
    directly onto the returned ``MobileCapability``.
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

    # Restore dropped governance fields if present
    dropped: dict[str, Any] = (card.get("metadata") or {}).get("arc_dropped_fields", {})

    # Carry SDK-only fields in metadata to avoid silent information loss.
    metadata: dict[str, Any] = {}
    for key in ("auth_required", "ai_consent_required", "enterprise_only", "default_decision"):
        if key in card:
            metadata[f"sdk_{key}"] = card[key]

    from .mobile.models import MobilePermissionRequirement

    restored_permissions: list[MobilePermissionRequirement] = []
    for p in dropped.get("required_permissions", []):
        try:
            restored_permissions.append(MobilePermissionRequirement.model_validate(p))
        except Exception:
            pass

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
        # Restored governance fields
        platforms=dropped.get("platforms") or [],
        required_permissions=restored_permissions,
        background=bool(dropped.get("background", False)),
        network=bool(dropped.get("network", False)),
        reads=bool(dropped.get("reads", False)),
        writes=bool(dropped.get("writes", False)),
        requires_trust=bool(dropped.get("requires_trust", False)),
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
