"""Tests for emit_policy_bypass_warning helper and rate-limiting (Phase 22.1)."""

from agent_runtime_cockpit.protocol._bypass import PolicyBypassReason
from agent_runtime_cockpit.security._bypass_rate_limit import (
    get_emitted_count,
    reset_warning_state,
)
from agent_runtime_cockpit.security.enforcement import emit_policy_bypass_warning


def test_rate_limiting_deduplicates_same_surface():
    """Test that 100 calls with the same (run_id, surface_identifier) emit only 1 event."""
    # Reset state before test
    reset_warning_state()

    # Track emitted events
    emitted_events = []

    def capture_event(run_id: str, event_type: str, data: dict) -> None:
        emitted_events.append((run_id, event_type, data))

    # Call emit_policy_bypass_warning 100 times with the same (run_id, surface_identifier)
    run_id = "run_test_123"
    surface_identifier = "custom_provider.execute"

    for i in range(100):
        result = emit_policy_bypass_warning(
            run_id=run_id,
            sequence=i,
            policy_id="trust_gate",
            bypass_reason=PolicyBypassReason.UNKNOWN_PROVIDER_PLUGIN,
            surface="provider_call",
            surface_identifier=surface_identifier,
            suggested_remediation="Instrument the custom provider",
            emit_event=capture_event,
        )

        # First call should emit (return True), subsequent calls should be suppressed (return False)
        if i == 0:
            assert result is True, "First call should emit warning"
        else:
            assert result is False, f"Call {i} should be suppressed by rate-limiting"

    # Verify only 1 event was emitted
    assert len(emitted_events) == 1, f"Expected 1 event, got {len(emitted_events)}"
    assert emitted_events[0][0] == run_id
    assert emitted_events[0][1] == "POLICY_BYPASS_WARNING"

    # Verify dedup state
    assert get_emitted_count() == 1


def test_rate_limiting_allows_distinct_surfaces():
    """Test that 100 calls with distinct surface_identifiers emit 100 events."""
    # Reset state before test
    reset_warning_state()

    # Track emitted events
    emitted_events = []

    def capture_event(run_id: str, event_type: str, data: dict) -> None:
        emitted_events.append((run_id, event_type, data))

    # Call emit_policy_bypass_warning 100 times with distinct surface_identifiers
    run_id = "run_test_456"

    for i in range(100):
        surface_identifier = f"custom_provider_{i}.execute"
        result = emit_policy_bypass_warning(
            run_id=run_id,
            sequence=i,
            policy_id="trust_gate",
            bypass_reason=PolicyBypassReason.CUSTOM_HTTP_CLIENT,
            surface="provider_call",
            surface_identifier=surface_identifier,
            suggested_remediation="Use instrumented HTTP client",
            emit_event=capture_event,
        )

        # All calls should emit (return True) because surface_identifier is unique
        assert result is True, f"Call {i} should emit warning (unique surface_identifier)"

    # Verify 100 events were emitted
    assert len(emitted_events) == 100, f"Expected 100 events, got {len(emitted_events)}"

    # Verify all events are POLICY_BYPASS_WARNING
    for event in emitted_events:
        assert event[0] == run_id
        assert event[1] == "POLICY_BYPASS_WARNING"

    # Verify dedup state
    assert get_emitted_count() == 100
