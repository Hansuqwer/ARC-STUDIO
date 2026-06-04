"""Tests for protocol/capability_card_events.py."""

from __future__ import annotations

from agent_runtime_cockpit.protocol.capability_card_events import (
    CapabilityCardDecisionData,
    CapabilityCardDecisionEvent,
)
from agent_runtime_cockpit.protocol.typed_events import is_known_event, parse_typed_event


class TestCapabilityCardDecisionEvent:
    def test_roundtrip(self):
        event = CapabilityCardDecisionEvent(
            schema_version=2,
            type="CAPABILITY_CARD_DECISION",
            timestamp="2026-06-04T12:00:00Z",
            run_id="run-001",
            sequence=1,
            data=CapabilityCardDecisionData(
                action="mcp_tool_dispatch",
                decision="deny",
                reason="capability_card_not_found",
                mode="strict",
                card_id="card-1",
                correlation_id="abc123def456",
            ),
        )
        d = event.model_dump()
        assert d["type"] == "CAPABILITY_CARD_DECISION"
        assert d["data"]["decision"] == "deny"
        assert d["data"]["correlation_id"] == "abc123def456"

    def test_parse_typed_event(self):
        raw = {
            "schema_version": 2,
            "type": "CAPABILITY_CARD_DECISION",
            "timestamp": "2026-06-04T12:00:00Z",
            "run_id": "run-002",
            "sequence": 2,
            "data": {
                "action": "run_workflow",
                "decision": "allow",
                "reason": "ok",
                "mode": "warn",
            },
        }
        event = parse_typed_event(raw)
        assert isinstance(event, CapabilityCardDecisionEvent)
        assert is_known_event(event)

    def test_extra_fields_ignored(self):
        event = CapabilityCardDecisionEvent(
            schema_version=2,
            type="CAPABILITY_CARD_DECISION",
            timestamp="2026-06-04T12:00:00Z",
            run_id="run-003",
            sequence=3,
            data=CapabilityCardDecisionData(
                action="test",
                decision="warn",
                reason="ok",
                mode="off",
                extra_field="ignored",  # type: ignore[call-arg]
            ),
        )
        assert event.data.action == "test"
