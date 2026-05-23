"""
Tests for PolicyBypassWarning model and PolicyBypassReason enum (Phase 22.1).
"""

import json
import pytest
from datetime import datetime, timezone

from agent_runtime_cockpit.protocol._bypass import (
    PolicyBypassWarning,
    PolicyBypassReason,
)


def test_policy_bypass_warning_construction():
    """Test 1: Basic construction of PolicyBypassWarning."""
    warning = PolicyBypassWarning(
        type="POLICY_BYPASS_WARNING",
        timestamp=datetime.now(timezone.utc).isoformat(),
        run_id="run_123",
        sequence=1,
        policy_id="trust_gate",
        bypass_reason=PolicyBypassReason.UNKNOWN_PROVIDER_PLUGIN,
        surface="provider_call",
        surface_identifier="custom_provider.execute",
        suggested_remediation="Instrument the custom provider with enforcement hooks",
    )

    assert warning.type == "POLICY_BYPASS_WARNING"
    assert warning.run_id == "run_123"
    assert warning.sequence == 1
    assert warning.policy_id == "trust_gate"
    assert warning.bypass_reason == PolicyBypassReason.UNKNOWN_PROVIDER_PLUGIN
    assert warning.surface == "provider_call"
    assert warning.surface_identifier == "custom_provider.execute"
    assert warning.schema_version == 2


def test_policy_bypass_warning_validation_rejects_unknown_reason():
    """Test 2: Validation rejects unknown bypass reason."""
    with pytest.raises(ValueError, match="Input should be"):
        PolicyBypassWarning(
            type="POLICY_BYPASS_WARNING",
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id="run_123",
            sequence=1,
            policy_id="trust_gate",
            bypass_reason="invalid_reason",  # Not a valid PolicyBypassReason
            surface="provider_call",
            surface_identifier="custom_provider.execute",
            suggested_remediation="Fix the issue",
        )


def test_policy_bypass_warning_json_round_trip():
    """Test 3: JSON serialization and deserialization round-trip."""
    original = PolicyBypassWarning(
        type="POLICY_BYPASS_WARNING",
        timestamp="2026-05-23T08:00:00Z",
        run_id="run_456",
        parent_run_id="run_parent_123",
        sequence=5,
        policy_id="network_gate",
        bypass_reason=PolicyBypassReason.CUSTOM_HTTP_CLIENT,
        surface="network_access",
        surface_identifier="requests.Session.custom",
        suggested_remediation="Use the instrumented HTTP client wrapper",
    )

    # Serialize to JSON
    json_str = original.model_dump_json()
    json_dict = json.loads(json_str)

    # Deserialize back
    restored = PolicyBypassWarning.model_validate(json_dict)

    # Verify all fields match
    assert restored.type == original.type
    assert restored.timestamp == original.timestamp
    assert restored.run_id == original.run_id
    assert restored.parent_run_id == original.parent_run_id
    assert restored.sequence == original.sequence
    assert restored.policy_id == original.policy_id
    assert restored.bypass_reason == original.bypass_reason
    assert restored.surface == original.surface
    assert restored.surface_identifier == original.surface_identifier
    assert restored.suggested_remediation == original.suggested_remediation


def test_policy_bypass_reason_enum_coverage():
    """Test 4: All PolicyBypassReason enum values are valid."""
    # Verify all 5 enum values exist and are valid
    reasons = [
        PolicyBypassReason.UNKNOWN_PROVIDER_PLUGIN,
        PolicyBypassReason.CUSTOM_HTTP_CLIENT,
        PolicyBypassReason.CUSTOM_SUBPROCESS_RUNNER,
        PolicyBypassReason.UNINSTRUMENTED_TOOL,
        PolicyBypassReason.UPSTREAM_BYPASSED_BOUNDARY,
    ]

    # Verify each reason can be used in a warning
    for reason in reasons:
        warning = PolicyBypassWarning(
            type="POLICY_BYPASS_WARNING",
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id="run_test",
            sequence=1,
            policy_id="test_policy",
            bypass_reason=reason,
            surface="test_surface",
            surface_identifier="test.identifier",
            suggested_remediation="Test remediation",
        )
        assert warning.bypass_reason == reason

    # Verify we have exactly 5 enum values
    assert len(PolicyBypassReason) == 5


def test_policy_bypass_warning_payload_completeness():
    """Test 5: All required and optional fields are present."""
    # Test with all fields (including optional parent_run_id)
    complete_warning = PolicyBypassWarning(
        type="POLICY_BYPASS_WARNING",
        timestamp="2026-05-23T08:00:00Z",
        run_id="run_789",
        parent_run_id="run_parent_456",
        sequence=10,
        policy_id="shell_gate",
        bypass_reason=PolicyBypassReason.UNINSTRUMENTED_TOOL,
        surface="subprocess_spawn",
        surface_identifier="subprocess.Popen.custom",
        suggested_remediation="Use the instrumented subprocess wrapper",
    )

    # Verify all fields are accessible
    assert complete_warning.schema_version == 2
    assert complete_warning.type == "POLICY_BYPASS_WARNING"
    assert complete_warning.timestamp == "2026-05-23T08:00:00Z"
    assert complete_warning.run_id == "run_789"
    assert complete_warning.parent_run_id == "run_parent_456"
    assert complete_warning.sequence == 10
    assert complete_warning.policy_id == "shell_gate"
    assert complete_warning.bypass_reason == PolicyBypassReason.UNINSTRUMENTED_TOOL
    assert complete_warning.surface == "subprocess_spawn"
    assert complete_warning.surface_identifier == "subprocess.Popen.custom"
    assert complete_warning.suggested_remediation == "Use the instrumented subprocess wrapper"

    # Test without optional parent_run_id
    minimal_warning = PolicyBypassWarning(
        type="POLICY_BYPASS_WARNING",
        timestamp="2026-05-23T08:00:00Z",
        run_id="run_999",
        sequence=1,
        policy_id="test_policy",
        bypass_reason=PolicyBypassReason.UPSTREAM_BYPASSED_BOUNDARY,
        surface="test_surface",
        surface_identifier="test.identifier",
        suggested_remediation="Test remediation",
    )

    assert minimal_warning.parent_run_id is None
