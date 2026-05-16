from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities, SupportLevel
from agent_runtime_cockpit.protocol.capability_snapshot import (
    COCKPIT_PRIMITIVE_FLAGS,
    TRUST_SENSITIVE_FLAGS,
    diff_capabilities,
    get_cockpit_readiness,
    snapshot_capabilities,
    validate_capability_claims,
)


class TestSnapshotCapabilities:
    def test_creates_snapshot(self):
        caps = RuntimeCapabilities(
            support_level=SupportLevel.STABLE,
            can_run=True,
            can_emit_contract=True,
            has_stable_ids=True,
        )
        snap = snapshot_capabilities("swarmgraph", caps)
        assert snap.runtime_id == "swarmgraph"
        assert snap.snapshot_id.startswith("sess_")
        assert snap.capabilities.can_run is True
        assert snap.capabilities.can_emit_contract is True
        assert snap.capabilities.has_stable_ids is True

    def test_snapshot_has_timestamp(self):
        caps = RuntimeCapabilities()
        snap = snapshot_capabilities("test", caps)
        assert snap.timestamp is not None
        assert "T" in snap.timestamp


class TestDiffCapabilities:
    def test_no_diff_for_identical(self):
        caps = RuntimeCapabilities(can_run=True, has_stable_ids=True)
        before = snapshot_capabilities("test", caps)
        after = snapshot_capabilities("test", caps)
        diff = diff_capabilities("test", before, after)
        assert len(diff.added_capabilities) == 0
        assert len(diff.removed_capabilities) == 0
        assert diff.requires_confirmation is False

    def test_detects_added_capability(self):
        before_caps = RuntimeCapabilities(can_run=False)
        after_caps = RuntimeCapabilities(can_run=True)
        before = snapshot_capabilities("test", before_caps)
        after = snapshot_capabilities("test", after_caps)
        diff = diff_capabilities("test", before, after)
        assert "can_run" in diff.added_capabilities
        assert diff.requires_confirmation is True

    def test_detects_removed_capability(self):
        before_caps = RuntimeCapabilities(can_emit_contract=True)
        after_caps = RuntimeCapabilities(can_emit_contract=False)
        before = snapshot_capabilities("test", before_caps)
        after = snapshot_capabilities("test", after_caps)
        diff = diff_capabilities("test", before, after)
        assert "can_emit_contract" in diff.removed_capabilities

    def test_detects_changed_flags(self):
        before_caps = RuntimeCapabilities(has_stable_ids=False)
        after_caps = RuntimeCapabilities(has_stable_ids=True)
        before = snapshot_capabilities("test", before_caps)
        after = snapshot_capabilities("test", after_caps)
        diff = diff_capabilities("test", before, after)
        assert "has_stable_ids" in diff.changed_flags
        assert diff.changed_flags["has_stable_ids"]["before"] is False
        assert diff.changed_flags["has_stable_ids"]["after"] is True

    def test_trust_sensitive_flags_require_confirmation(self):
        before_caps = RuntimeCapabilities(requires_paid_calls=False)
        after_caps = RuntimeCapabilities(requires_paid_calls=True)
        before = snapshot_capabilities("test", before_caps)
        after = snapshot_capabilities("test", after_caps)
        diff = diff_capabilities("test", before, after)
        assert diff.requires_confirmation is True

    def test_non_trust_change_no_confirmation(self):
        before_caps = RuntimeCapabilities(can_inspect=False)
        after_caps = RuntimeCapabilities(can_inspect=True)
        before = snapshot_capabilities("test", before_caps)
        after = snapshot_capabilities("test", after_caps)
        diff = diff_capabilities("test", before, after)
        assert diff.requires_confirmation is False


class TestValidateCapabilityClaims:
    def test_valid_claims(self):
        caps = RuntimeCapabilities(
            can_emit_contract=True,
            has_stable_ids=True,
        )
        actual = {
            "emitted_contracts": True,
            "has_stable_ids_in_events": True,
        }
        result = validate_capability_claims("test", caps, actual)
        assert result.is_valid is True
        assert len(result.false_claims) == 0
        assert result.degradation_level == "none"

    def test_false_claim_detected(self):
        caps = RuntimeCapabilities(
            can_emit_contract=True,
            has_stable_ids=True,
        )
        actual = {
            "emitted_contracts": False,
            "has_stable_ids_in_events": True,
        }
        result = validate_capability_claims("test", caps, actual)
        assert result.is_valid is False
        assert "can_emit_contract" in result.false_claims

    def test_severe_degradation(self):
        caps = RuntimeCapabilities(
            has_stable_ids=True,
            can_emit_evidence=True,
        )
        actual = {
            "has_stable_ids_in_events": False,
            "emitted_evidence": False,
        }
        result = validate_capability_claims("test", caps, actual)
        assert result.degradation_level == "severe"
        assert result.is_valid is False

    def test_partial_degradation(self):
        caps = RuntimeCapabilities(can_emit_receipt=True)
        actual = {"emitted_receipts": False}
        result = validate_capability_claims("test", caps, actual)
        assert result.degradation_level == "partial"

    def test_no_degradation(self):
        caps = RuntimeCapabilities()
        actual = {}
        result = validate_capability_claims("test", caps, actual)
        assert result.degradation_level == "none"
        assert result.is_valid is True

    def test_has_validation_id(self):
        caps = RuntimeCapabilities()
        result = validate_capability_claims("test", caps, {})
        assert result.validation_id.startswith("dec_")


class TestGetCockpitReadiness:
    def test_all_ready(self):
        caps = RuntimeCapabilities(
            can_emit_contract=True,
            can_emit_receipt=True,
            can_emit_autopsy=True,
            can_emit_evidence=True,
            has_stable_ids=True,
        )
        readiness = get_cockpit_readiness(caps)
        assert readiness["contracts"] is True
        assert readiness["receipts"] is True
        assert readiness["stable_ids"] is True
        assert readiness["graph_linkage_available"] is True
        assert readiness["cross_surface_linking"] is True

    def test_no_stable_ids(self):
        caps = RuntimeCapabilities(
            can_emit_evidence=True,
            has_stable_ids=False,
        )
        readiness = get_cockpit_readiness(caps)
        assert readiness["stable_ids"] is False
        assert readiness["graph_linkage_available"] is False
        assert readiness["cross_surface_linking"] is False

    def test_partial_readiness(self):
        caps = RuntimeCapabilities(
            can_emit_contract=True,
            can_emit_receipt=False,
            has_stable_ids=True,
        )
        readiness = get_cockpit_readiness(caps)
        assert readiness["contracts"] is True
        assert readiness["receipts"] is False
        assert readiness["stable_ids"] is True


class TestCockpitPrimitiveFlags:
    def test_flags_defined(self):
        assert "can_emit_contract" in COCKPIT_PRIMITIVE_FLAGS
        assert "can_emit_receipt" in COCKPIT_PRIMITIVE_FLAGS
        assert "can_emit_autopsy" in COCKPIT_PRIMITIVE_FLAGS
        assert "can_emit_evidence" in COCKPIT_PRIMITIVE_FLAGS
        assert "has_stable_ids" in COCKPIT_PRIMITIVE_FLAGS

    def test_trust_sensitive_flags_defined(self):
        assert "can_run" in TRUST_SENSITIVE_FLAGS
        assert "requires_paid_calls" in TRUST_SENSITIVE_FLAGS
        assert "requires_shell" in TRUST_SENSITIVE_FLAGS
        assert "requires_secrets" in TRUST_SENSITIVE_FLAGS
        assert "requires_network" in TRUST_SENSITIVE_FLAGS


class TestRuntimeSwitchDiff:
    """Tests for capability diff when switching between runtimes."""

    def test_diff_between_two_runtimes(self):
        swarm_caps = RuntimeCapabilities(
            can_run=True,
            can_trace=True,
            can_emit_contract=True,
            can_emit_evidence=True,
            has_stable_ids=True,
            requires_paid_calls=True,
        )
        lang_caps = RuntimeCapabilities(
            can_run=True,
            can_trace=False,
            can_emit_contract=False,
            can_emit_evidence=False,
            has_stable_ids=False,
            requires_paid_calls=False,
        )
        before = snapshot_capabilities("swarmgraph", swarm_caps)
        after = snapshot_capabilities("langgraph", lang_caps)
        diff = diff_capabilities("langgraph", before, after)
        assert "can_trace" in diff.removed_capabilities
        assert "can_emit_contract" in diff.removed_capabilities
        assert "can_emit_evidence" in diff.removed_capabilities
        assert "has_stable_ids" in diff.removed_capabilities
        assert "requires_paid_calls" in diff.removed_capabilities
        assert diff.requires_confirmation is True

    def test_diff_widening_trust_boundary(self):
        minimal_caps = RuntimeCapabilities(
            can_run=False,
            requires_paid_calls=False,
            requires_shell=False,
            requires_secrets=False,
            requires_network=False,
        )
        full_caps = RuntimeCapabilities(
            can_run=True,
            requires_paid_calls=True,
            requires_shell=True,
            requires_secrets=True,
            requires_network=True,
        )
        before = snapshot_capabilities("stub", minimal_caps)
        after = snapshot_capabilities("swarmgraph", full_caps)
        diff = diff_capabilities("swarmgraph", before, after)
        assert diff.requires_confirmation is True
        assert "can_run" in diff.added_capabilities
        assert "requires_paid_calls" in diff.added_capabilities
        assert "requires_shell" in diff.added_capabilities
        assert "requires_secrets" in diff.added_capabilities
        assert "requires_network" in diff.added_capabilities

    def test_diff_narrowing_trust_no_confirmation(self):
        full_caps = RuntimeCapabilities(
            can_run=True,
            requires_paid_calls=True,
        )
        minimal_caps = RuntimeCapabilities(
            can_run=False,
            requires_paid_calls=False,
        )
        before = snapshot_capabilities("swarmgraph", full_caps)
        after = snapshot_capabilities("stub", minimal_caps)
        diff = diff_capabilities("stub", before, after)
        assert diff.requires_confirmation is True

    def test_diff_with_unknown_capability_values(self):
        before_caps = RuntimeCapabilities(can_inspect=False)
        after_caps = RuntimeCapabilities(can_inspect=True)
        before = snapshot_capabilities("a", before_caps)
        after = snapshot_capabilities("b", after_caps)
        diff = diff_capabilities("b", before, after)
        assert "can_inspect" in diff.changed_flags
        assert diff.changed_flags["can_inspect"]["before"] is False
        assert diff.changed_flags["can_inspect"]["after"] is True
        assert diff.requires_confirmation is False

    def test_diff_preserves_runtime_id(self):
        caps_a = RuntimeCapabilities(can_run=True)
        caps_b = RuntimeCapabilities(can_run=False)
        before = snapshot_capabilities("runtime_a", caps_a)
        after = snapshot_capabilities("runtime_b", caps_b)
        diff = diff_capabilities("runtime_b", before, after)
        assert diff.runtime_id == "runtime_b"

    def test_diff_has_valid_diff_id(self):
        caps = RuntimeCapabilities()
        before = snapshot_capabilities("x", caps)
        after = snapshot_capabilities("y", caps)
        diff = diff_capabilities("y", before, after)
        assert diff.diff_id.startswith("dec_")

    def test_diff_timestamp_present(self):
        caps = RuntimeCapabilities()
        before = snapshot_capabilities("x", caps)
        after = snapshot_capabilities("y", caps)
        diff = diff_capabilities("y", before, after)
        assert diff.timestamp is not None
        assert "T" in diff.timestamp
