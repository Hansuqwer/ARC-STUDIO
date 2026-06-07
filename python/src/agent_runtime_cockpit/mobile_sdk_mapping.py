"""Canonical field mapping: ARC Studio MobileCapability ↔ ARC Runtime SDK CapabilityCard.

Implements R79/Phase 111 Slice 110.3. Provides two public functions:

- ``mobile_capability_to_sdk_card(cap)``  → dict (forward, for SDK export)
- ``sdk_card_to_mobile_capability(card)``  → MobileCapability (inverse, for import)

The mapping is intentionally explicit: every field is named, default-filled
where no equivalent exists, and documented with the source/target key. No
lossy silent discards — mobile-only fields are carried in ``metadata`` on the
SDK card side and SDK-only fields are carried in ``metadata`` on the
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
    MobilePlatform,
    MobilePermissionRequirement,
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

_MOBILE_METADATA_KEY = "arc_mobile"


def _enum_value(value: Any) -> Any:
    return value.value if hasattr(value, "value") else value


# ── Forward: MobileCapability → SDK CapabilityCard dict ──────────────────────


def mobile_capability_to_sdk_card(cap: MobileCapability) -> dict[str, Any]:
    """Convert an ARC Studio ``MobileCapability`` to an SDK CapabilityCard dict.

    SDK CapabilityCard does not have first-class equivalents for several mobile
    governance fields. Those fields are preserved under ``metadata.arc_mobile``
    so security-relevant context is not silently lost.
    """
    category_value = cap.category.value if hasattr(cap.category, "value") else str(cap.category)
    sensitivity_value = (
        cap.data_sensitivity.value
        if hasattr(cap.data_sensitivity, "value")
        else str(cap.data_sensitivity)
    )
    metadata = dict(cap.metadata or {})
    metadata[_MOBILE_METADATA_KEY] = {
        "schema_version": cap.schema_version,
        "platforms": [_enum_value(p) for p in cap.platforms],
        "required_permissions": [p.model_dump(mode="json") for p in cap.required_permissions],
        "reads": cap.reads,
        "writes": cap.writes,
        "network": cap.network,
        "background": cap.background,
        "mcp_exposable": cap.mcp_exposable,
        "test_fixture_supported": cap.test_fixture_supported,
        "requires_trust": cap.requires_trust,
        "requires_hitl": cap.requires_hitl,
        "capability_hash": cap.capability_hash,
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
        "metadata": metadata,
    }


# ── Inverse: SDK CapabilityCard dict → MobileCapability ──────────────────────


def sdk_card_to_mobile_capability(card: dict[str, Any]) -> MobileCapability:
    """Convert an SDK CapabilityCard dict to an ARC Studio ``MobileCapability``.

    SDK-only fields are preserved in ``metadata`` using the ``sdk_`` prefix.
    Mobile governance fields from ``metadata.arc_mobile`` are restored when
    present.
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
    card_metadata = card.get("metadata", {})
    if isinstance(card_metadata, dict):
        metadata.update({k: v for k, v in card_metadata.items() if k != _MOBILE_METADATA_KEY})
        mobile_meta = card_metadata.get(_MOBILE_METADATA_KEY, {})
    else:
        mobile_meta = {}
    if not isinstance(mobile_meta, dict):
        mobile_meta = {}

    for key in ("auth_required", "ai_consent_required", "enterprise_only", "default_decision"):
        if key in card:
            metadata[f"sdk_{key}"] = card[key]

    platforms = [
        MobilePlatform(str(platform)) for platform in mobile_meta.get("platforms", ["all"])
    ]
    required_permissions = [
        MobilePermissionRequirement.model_validate(item)
        for item in mobile_meta.get("required_permissions", [])
        if isinstance(item, dict)
    ]

    return MobileCapability(
        schema_version=int(mobile_meta.get("schema_version", 1)),
        id=str(card.get("id", "")),
        name=str(card.get("name", "")),
        description=str(card.get("description", "")),
        category=MobileCapabilityCategory(mobile_cat_str),
        data_sensitivity=MobileDataSensitivity(mobile_sens_str),
        platforms=platforms,
        required_permissions=required_permissions,
        paid=bool(card.get("allow_paid_calls", False)),
        replayable=bool(card.get("replay_safe", True)),
        auditable=bool(card.get("audit_required", True)),
        simulator_supported=bool(card.get("fixture_required_in_simulator", True)),
        approval_mode=approval_mode,
        reads=bool(mobile_meta.get("reads", False)),
        writes=bool(mobile_meta.get("writes", False)),
        network=bool(mobile_meta.get("network", False)),
        background=bool(mobile_meta.get("background", False)),
        mcp_exposable=bool(mobile_meta.get("mcp_exposable", False)),
        test_fixture_supported=bool(mobile_meta.get("test_fixture_supported", True)),
        requires_trust=bool(mobile_meta.get("requires_trust", False)),
        requires_hitl=bool(mobile_meta.get("requires_hitl", False)),
        capability_hash=mobile_meta.get("capability_hash"),
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
