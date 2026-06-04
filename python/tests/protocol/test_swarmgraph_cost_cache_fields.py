"""R-03: SwarmGraphCostData cache field round-trip tests."""

from __future__ import annotations

from agent_runtime_cockpit.protocol.typed_events import SwarmGraphCostEvent


def test_swarmgraph_cost_event_round_trips_cache_fields() -> None:
    raw = {
        "schema_version": 2,
        "type": "SWARMGRAPH_COST",
        "timestamp": "2026-01-01T00:00:00Z",
        "run_id": "r-1",
        "sequence": 1,
        "data": {
            "provider": "anthropic",
            "model": "claude-3-haiku",
            "cache_read_input_tokens": 48012,
            "cache_creation_input_tokens": 1200,
        },
    }
    event = SwarmGraphCostEvent.model_validate(raw)
    assert event.data.cache_read_input_tokens == 48012
    assert event.data.cache_creation_input_tokens == 1200


def test_swarmgraph_cost_event_legacy_payload_parses_without_cache_fields() -> None:
    """Older events without cache fields parse cleanly (forward-compat)."""
    raw = {
        "schema_version": 2,
        "type": "SWARMGRAPH_COST",
        "timestamp": "2026-01-01T00:00:00Z",
        "run_id": "r-2",
        "sequence": 1,
        "data": {"provider": "openai", "totalCost": 0.01, "totalTokens": 500},
    }
    event = SwarmGraphCostEvent.model_validate(raw)
    assert event.data.cache_read_input_tokens is None
    assert event.data.cache_creation_input_tokens is None
