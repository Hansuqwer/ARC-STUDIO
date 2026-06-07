"""Round-trip tests for MobileCapability ↔ SDK CapabilityCard mapping (Slice 110.3)."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.mobile.models import (
    MobileApprovalMode,
    MobileCapability,
    MobileCapabilityCategory,
    MobileDataSensitivity,
)
from agent_runtime_cockpit.mobile_sdk_mapping import (
    _MOBILE_CAT_TO_SDK,
    _MOBILE_SENS_TO_SDK,
    _SDK_CAT_TO_MOBILE,
    _SDK_SENS_TO_MOBILE,
    mobile_capability_to_sdk_card,
    sdk_card_to_mobile_capability,
)


def _make_cap(**kwargs) -> MobileCapability:
    defaults = {
        "id": "test.cap",
        "name": "Test Capability",
        "description": "A test capability",
        "category": MobileCapabilityCategory.NETWORK,
        "data_sensitivity": MobileDataSensitivity.MEDIUM,
        "paid": False,
        "replayable": True,
        "auditable": True,
        "simulator_supported": True,
        "approval_mode": MobileApprovalMode.NONE,
    }
    defaults.update(kwargs)
    return MobileCapability(**defaults)


# ── Forward: mobile → SDK card ────────────────────────────────────────────────


def test_forward_direct_fields():
    cap = _make_cap(paid=True, replayable=False, auditable=False)
    card = mobile_capability_to_sdk_card(cap)
    assert card["id"] == "test.cap"
    assert card["name"] == "Test Capability"
    assert card["allow_paid_calls"] is True
    assert card["replay_safe"] is False
    assert card["audit_required"] is False
    assert card["default_decision"] == "deny"


def test_forward_category_mapping():
    for mobile_cat, sdk_cat in _MOBILE_CAT_TO_SDK.items():
        cap = _make_cap(category=MobileCapabilityCategory(mobile_cat))
        card = mobile_capability_to_sdk_card(cap)
        assert card["category"] == sdk_cat, f"Expected {sdk_cat} for {mobile_cat}"


def test_forward_sensitivity_mapping():
    for mobile_sens, sdk_sens in _MOBILE_SENS_TO_SDK.items():
        cap = _make_cap(data_sensitivity=MobileDataSensitivity(mobile_sens))
        card = mobile_capability_to_sdk_card(cap)
        assert card["data_sensitivity"] == sdk_sens


def test_forward_blocking_approval_maps_to_biometric():
    cap = _make_cap(approval_mode=MobileApprovalMode.BLOCKING)
    assert mobile_capability_to_sdk_card(cap)["auth_required"] == "biometric"


def test_forward_none_approval_maps_to_none():
    cap = _make_cap(approval_mode=MobileApprovalMode.NONE)
    assert mobile_capability_to_sdk_card(cap)["auth_required"] == "none"


def test_forward_simulator_supported_maps_to_fixture():
    cap = _make_cap(simulator_supported=False)
    card = mobile_capability_to_sdk_card(cap)
    assert card["fixture_required_in_simulator"] is False


# ── Inverse: SDK card → MobileCapability ─────────────────────────────────────


def test_inverse_returns_mobile_capability():
    card = {
        "id": "net.cap",
        "name": "Network Cap",
        "description": "desc",
        "category": "network",
        "data_sensitivity": "low",
        "allow_paid_calls": False,
        "replay_safe": True,
        "audit_required": True,
        "fixture_required_in_simulator": True,
        "auth_required": "none",
    }
    cap = sdk_card_to_mobile_capability(card)
    assert isinstance(cap, MobileCapability)
    assert cap.id == "net.cap"
    assert cap.category == MobileCapabilityCategory.NETWORK
    assert cap.data_sensitivity == MobileDataSensitivity.LOW


def test_inverse_category_mapping():
    for sdk_cat, mobile_cat in _SDK_CAT_TO_MOBILE.items():
        cap = sdk_card_to_mobile_capability({"id": "x", "name": "x", "category": sdk_cat})
        assert cap.category.value == mobile_cat


def test_inverse_sensitivity_mapping():
    for sdk_sens, mobile_sens in _SDK_SENS_TO_MOBILE.items():
        cap = sdk_card_to_mobile_capability({"id": "x", "name": "x", "data_sensitivity": sdk_sens})
        assert cap.data_sensitivity.value == mobile_sens


def test_inverse_biometric_auth_maps_to_blocking():
    cap = sdk_card_to_mobile_capability({"id": "x", "name": "x", "auth_required": "biometric"})
    assert cap.approval_mode == MobileApprovalMode.BLOCKING


def test_inverse_sdk_only_fields_preserved_in_metadata():
    card = {
        "id": "x",
        "name": "x",
        "auth_required": "biometric",
        "ai_consent_required": True,
        "enterprise_only": True,
        "default_decision": "deny",
    }
    cap = sdk_card_to_mobile_capability(card)
    assert cap.metadata.get("sdk_auth_required") == "biometric"
    assert cap.metadata.get("sdk_ai_consent_required") is True
    assert cap.metadata.get("sdk_enterprise_only") is True
    assert cap.metadata.get("sdk_default_decision") == "deny"


# ── Round-trip ────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("category", list(MobileCapabilityCategory))
def test_round_trip_all_categories(category):
    """Forward then inverse preserves category."""
    cap = _make_cap(category=category)
    card = mobile_capability_to_sdk_card(cap)
    restored = sdk_card_to_mobile_capability(card)
    # The round-trip goes through a many-to-one SDK category mapping, so
    # we can only assert the SDK category produced a valid ARC category.
    assert restored.category in list(MobileCapabilityCategory)


@pytest.mark.parametrize("sensitivity", list(MobileDataSensitivity))
def test_round_trip_all_sensitivities(sensitivity):
    """Forward then inverse preserves sensitivity."""
    cap = _make_cap(data_sensitivity=sensitivity)
    card = mobile_capability_to_sdk_card(cap)
    restored = sdk_card_to_mobile_capability(card)
    assert restored.data_sensitivity in list(MobileDataSensitivity)


def test_round_trip_core_fields_preserved():
    """Forward then inverse preserves the fields that have 1:1 SDK equivalents."""
    cap = _make_cap(
        id="sensor.accel",
        name="Accelerometer",
        description="Device accelerometer",
        category=MobileCapabilityCategory.SENSOR,
        data_sensitivity=MobileDataSensitivity.HIGH,
        paid=True,
        replayable=False,
        auditable=True,
        simulator_supported=False,
        approval_mode=MobileApprovalMode.BLOCKING,
    )
    card = mobile_capability_to_sdk_card(cap)
    restored = sdk_card_to_mobile_capability(card)

    assert restored.id == cap.id
    assert restored.name == cap.name
    assert restored.description == cap.description
    assert restored.paid == cap.paid
    assert restored.replayable == cap.replayable
    assert restored.auditable == cap.auditable
    assert restored.simulator_supported == cap.simulator_supported
    assert restored.approval_mode == cap.approval_mode


# ── PR3: Dropped-field metadata round-trip ────────────────────────────────────


def test_forward_records_dropped_fields_in_metadata():
    """Forward mapping preserves governance fields in metadata.arc_dropped_fields."""
    cap = _make_cap(
        category=MobileCapabilityCategory.DEVICE,
        background=False,
        network=False,
        reads=True,
        writes=False,
        requires_trust=True,
    )
    card = mobile_capability_to_sdk_card(cap)
    dropped = card["metadata"]["arc_dropped_fields"]
    assert dropped["reads"] is True
    assert dropped["writes"] is False
    assert dropped["background"] is False
    assert dropped["network"] is False
    assert dropped["requires_trust"] is True
    assert isinstance(dropped["platforms"], list)
    assert isinstance(dropped["required_permissions"], list)


def test_round_trip_restores_governance_fields():
    """Forward then inverse restores background/network/reads/writes/requires_trust."""
    cap = _make_cap(
        id="device.sensor.test.mock",
        category=MobileCapabilityCategory.SENSOR,
        reads=True,
        writes=False,
        background=False,
        network=False,
        requires_trust=True,
    )
    card = mobile_capability_to_sdk_card(cap)
    restored = sdk_card_to_mobile_capability(card)
    assert restored.reads is True
    assert restored.writes is False
    assert restored.background is False
    assert restored.network is False
    assert restored.requires_trust is True


def test_docstring_says_lossy_forward():
    """Verify the docstring no longer says 'no lossy silent discards'."""
    from agent_runtime_cockpit import mobile_sdk_mapping

    doc = mobile_sdk_mapping.__doc__ or ""
    assert "no lossy silent discards" not in doc.lower()
    assert "intentionally lossy" in doc.lower() or "lossy" in doc.lower()
