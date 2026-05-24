"""Tests: CapabilityNegotiation — pure-function capability matching."""

from __future__ import annotations

from agent_runtime_cockpit.orchestration.capability_negotiation import (
    CapabilityNegotiation,
)
from agent_runtime_cockpit.protocol.capabilities import (
    ExecutionMode,
    RuntimeCapabilities,
    SupportLevel,
)


class TestSatisfies:
    """satisfies() checks single capability set against a required profile."""

    def test_empty_required_passes(self):
        caps = RuntimeCapabilities()
        satisfied, reasons = CapabilityNegotiation.satisfies(caps, {})
        assert satisfied is True
        assert reasons == []

    def test_bool_capability_satisfied(self):
        caps = RuntimeCapabilities(can_run=True, can_trace=True)
        satisfied, reasons = CapabilityNegotiation.satisfies(
            caps,
            {"can_run": True, "can_trace": True},
        )
        assert satisfied is True

    def test_bool_capability_missing(self):
        caps = RuntimeCapabilities(can_run=False)
        satisfied, reasons = CapabilityNegotiation.satisfies(
            caps,
            {"can_run": True},
        )
        assert satisfied is False
        assert any("can_run" in r for r in reasons)

    def test_str_capability_satisfied(self):
        caps = RuntimeCapabilities(support_level=SupportLevel.STABLE)
        satisfied, reasons = CapabilityNegotiation.satisfies(
            caps,
            {"support_level": "stable"},
        )
        assert satisfied is True

    def test_str_capability_mismatch(self):
        caps = RuntimeCapabilities(support_level=SupportLevel.ALPHA)
        satisfied, reasons = CapabilityNegotiation.satisfies(
            caps,
            {"support_level": "stable"},
        )
        assert satisfied is False

    def test_list_capability_satisfied(self):
        caps = RuntimeCapabilities(
            execution_modes=[ExecutionMode.STANDALONE, ExecutionMode.ADOPTION],
        )
        satisfied, reasons = CapabilityNegotiation.satisfies(
            caps,
            {"execution_modes": ["adoption"]},
        )
        assert satisfied is True

    def test_list_capability_not_satisfied(self):
        caps = RuntimeCapabilities(
            execution_modes=[ExecutionMode.STANDALONE],
        )
        satisfied, reasons = CapabilityNegotiation.satisfies(
            caps,
            {"execution_modes": ["adoption"]},
        )
        assert satisfied is False

    def test_unknown_capability_key(self):
        caps = RuntimeCapabilities()
        satisfied, reasons = CapabilityNegotiation.satisfies(
            caps,
            {"nonexistent_field": True},
        )
        assert satisfied is False
        assert any("not found" in r for r in reasons)


class TestBestMatch:
    """best_match() selects the best runtime from candidates."""

    def test_exact_match_returns_first(self):
        candidates = [
            ("alpha", RuntimeCapabilities(can_run=True)),
            ("beta", RuntimeCapabilities(can_run=True)),
        ]
        best_id, reasons = CapabilityNegotiation.best_match(
            candidates,
            {"can_run": True},
        )
        assert best_id == "alpha"
        assert reasons == []

    def test_no_match_returns_best(self):
        candidates = [
            ("alpha", RuntimeCapabilities(can_run=False, can_trace=True)),
            ("beta", RuntimeCapabilities(can_run=False, can_trace=False)),
        ]
        best_id, reasons = CapabilityNegotiation.best_match(
            candidates,
            {"can_run": True},
        )
        assert best_id == "alpha"
        assert any("can_run" in r for r in reasons)

    def test_empty_candidates(self):
        best_id, reasons = CapabilityNegotiation.best_match(
            [],
            {"can_run": True},
        )
        assert best_id is None
        assert reasons == []


class TestCockpitPrimitiveProfile:
    """cockpit_primitive_profile() builds profiles for cockpit features."""

    def test_empty_profile(self):
        profile = CapabilityNegotiation.cockpit_primitive_profile()
        assert profile == {}

    def test_contract_profile(self):
        profile = CapabilityNegotiation.cockpit_primitive_profile(
            emit_contract=True,
        )
        assert profile == {"can_emit_contract": True}

    def test_all_primitives(self):
        profile = CapabilityNegotiation.cockpit_primitive_profile(
            emit_contract=True,
            emit_receipt=True,
            emit_autopsy=True,
            emit_evidence=True,
            require_stable_ids=True,
        )
        assert profile == {
            "can_emit_contract": True,
            "can_emit_receipt": True,
            "can_emit_autopsy": True,
            "can_emit_evidence": True,
            "has_stable_ids": True,
        }

    def test_profile_matches_capabilities(self):
        caps = RuntimeCapabilities(
            can_emit_contract=True,
            can_emit_receipt=True,
            can_emit_autopsy=True,
            can_emit_evidence=True,
            has_stable_ids=True,
        )
        profile = CapabilityNegotiation.cockpit_primitive_profile(
            emit_contract=True,
            emit_receipt=True,
            emit_autopsy=True,
            emit_evidence=True,
            require_stable_ids=True,
        )
        satisfied, reasons = CapabilityNegotiation.satisfies(caps, profile)
        assert satisfied is True
        assert reasons == []

    def test_profile_missing_stable_ids(self):
        caps = RuntimeCapabilities(
            can_emit_contract=True,
            has_stable_ids=False,
        )
        profile = CapabilityNegotiation.cockpit_primitive_profile(
            emit_contract=True,
            require_stable_ids=True,
        )
        satisfied, reasons = CapabilityNegotiation.satisfies(caps, profile)
        assert satisfied is False
