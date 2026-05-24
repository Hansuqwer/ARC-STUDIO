"""Tests: Event schema registry (ADR-004).

Tests the event type registry, validation, and ``create_event()``.
"""

from __future__ import annotations

from agent_runtime_cockpit.protocol.events import (
    CURRENT_SCHEMA_VERSION,
    EVENT_TYPES,
    create_event,
    validate_event_data,
)
from agent_runtime_cockpit.protocol.schemas import RunEvent


class TestEventTypeRegistry:
    """The EVENT_TYPES registry contains all expected types."""

    def test_registry_contains_run_lifecycle_events(self):
        for ev in ("RUN_STARTED", "RUN_COMPLETED", "RUN_FAILED", "RUN_CANCELLED"):
            assert ev in EVENT_TYPES, f"Missing event: {ev}"

    def test_registry_contains_step_events(self):
        for ev in ("STEP_STARTED", "STEP_COMPLETED", "STEP_FAILED"):
            assert ev in EVENT_TYPES

    def test_registry_contains_tool_call_events(self):
        for ev in (
            "TOOL_CALL",
            "TOOL_CALL_START",
            "TOOL_CALL_ARGS",
            "TOOL_CALL_END",
            "TOOL_CALL_RESULT",
            "TOOL_CALL_ERROR",
            "TOOL_END",
        ):
            assert ev in EVENT_TYPES

    def test_registry_contains_message_events(self):
        for ev in (
            "MESSAGE",
            "MESSAGE_CHUNK",
            "TEXT_MESSAGE_START",
            "TEXT_MESSAGE_CONTENT",
            "TEXT_MESSAGE_END",
            "TEXT_MESSAGE_CHUNK",
        ):
            assert ev in EVENT_TYPES

    def test_registry_contains_state_and_fallback(self):
        for ev in ("STATE_SNAPSHOT", "RAW", "CUSTOM"):
            assert ev in EVENT_TYPES

    def test_registry_contains_swarmgraph_insight_events(self):
        for ev in ("SWARMGRAPH_TOPOLOGY", "SWARMGRAPH_CONSENSUS", "SWARMGRAPH_COST"):
            assert ev in EVENT_TYPES

    def test_registry_contains_hitl_events(self):
        for ev in ("HITL_PROMPT", "HITL_RESPONSE", "HITL_TIMEOUT"):
            assert ev in EVENT_TYPES

    def test_registry_contains_contract_lifecycle_events(self):
        for ev in (
            "CONTRACT_PROPOSED",
            "CONTRACT_ACCEPTED",
            "CONTRACT_FULFILLED",
            "CONTRACT_VIOLATED",
        ):
            assert ev in EVENT_TYPES

    def test_registry_contains_cockpit_primitive_events(self):
        for ev in ("RECEIPT_GENERATED", "FAILURE_AUTOPSY_GENERATED", "EVIDENCE_REF_CREATED"):
            assert ev in EVENT_TYPES

    def test_registry_contains_agent_and_handoff_events(self):
        for ev in ("AGENT_START", "AGENT_END", "HANDOFF"):
            assert ev in EVENT_TYPES

    def test_registry_contains_node_and_text_chunk_events(self):
        for ev in ("NODE_STARTED", "NODE_UPDATE", "NODE_FAILED", "TEXT_MESSAGE_CHUNK"):
            assert ev in EVENT_TYPES

    def test_all_types_have_correct_default_version(self):
        for name, typedef in EVENT_TYPES.items():
            assert typedef.version == CURRENT_SCHEMA_VERSION, (
                f"{name} has version {typedef.version}, expected {CURRENT_SCHEMA_VERSION}"
            )


class TestValidateEventData:
    """validate_event_data checks required fields."""

    def test_valid_event_returns_no_errors(self):
        errors = validate_event_data("RUN_STARTED", {"workflow_id": "wf", "runtime": "sg"})
        assert errors == []

    def test_missing_required_field_returns_error(self):
        errors = validate_event_data("RUN_STARTED", {"runtime": "sg"})
        assert len(errors) >= 1
        assert "workflow_id" in errors[0]

    def test_unknown_event_type_returns_error(self):
        errors = validate_event_data("UNKNOWN_EVENT", {})
        assert len(errors) >= 1
        assert "Unknown" in errors[0]

    def test_all_required_fields_present_is_valid(self):
        errors = validate_event_data("TOOL_CALL", {"tool_call_id": "tc1", "tool_name": "search"})
        assert errors == []

    def test_handoff_requires_both_agents(self):
        errors = validate_event_data("HANDOFF", {"from_agent": "a"})
        assert len(errors) >= 1
        assert "to_agent" in errors[0]

    def test_swarmgraph_topology_requires_nodes_and_edges(self):
        errors = validate_event_data("SWARMGRAPH_TOPOLOGY", {"nodes": []})
        assert len(errors) >= 1
        assert "edges" in errors[0]

    def test_swarmgraph_consensus_requires_votes(self):
        errors = validate_event_data("SWARMGRAPH_CONSENSUS", {"decision": "approve"})
        assert len(errors) >= 1
        assert "votes" in errors[0]


class TestCreateEvent:
    """create_event produces validated RunEvent instances."""

    def test_creates_valid_event(self):
        ev = create_event("run-1", 0, "RUN_STARTED", {"workflow_id": "wf", "runtime": "sg"})
        assert isinstance(ev, RunEvent)
        assert ev.type == "RUN_STARTED"
        assert ev.run_id == "run-1"
        assert ev.sequence == 0
        assert ev.schema_version == CURRENT_SCHEMA_VERSION
        assert ev.data["workflow_id"] == "wf"

    def test_raises_on_unknown_type(self):
        import pytest

        with pytest.raises(ValueError, match="Unknown"):
            create_event("run-1", 0, "NOT_A_REAL_TYPE", {})

    def test_raises_on_missing_required_field(self):
        import pytest

        with pytest.raises(ValueError, match="required"):
            create_event("run-1", 0, "RUN_STARTED", {})

    def test_stores_timestamp(self):
        ev = create_event("run-1", 0, "RUN_STARTED", {"workflow_id": "wf", "runtime": "sg"})
        assert isinstance(ev.timestamp, str)
        assert "T" in ev.timestamp  # ISO-8601 format

    def test_tooll_call_event_validates(self):
        ev = create_event("run-1", 1, "TOOL_CALL", {"tool_call_id": "tc1", "tool_name": "search"})
        assert ev.type == "TOOL_CALL"
        assert ev.schema_version == CURRENT_SCHEMA_VERSION
        assert ev.data["tool_call_id"] == "tc1"

    def test_contract_proposed_event(self):
        ev = create_event(
            "run-1", 2, "CONTRACT_PROPOSED", {"contract": {"id": "c1", "terms": "do x"}}
        )
        assert ev.type == "CONTRACT_PROPOSED"
        assert ev.data["contract"]["id"] == "c1"

    def test_contract_accepted_event(self):
        ev = create_event("run-1", 3, "CONTRACT_ACCEPTED", {"contract_id": "c1"})
        assert ev.type == "CONTRACT_ACCEPTED"

    def test_contract_fulfilled_event(self):
        ev = create_event(
            "run-1", 4, "CONTRACT_FULFILLED", {"contract_id": "c1", "run_id": "run-1"}
        )
        assert ev.type == "CONTRACT_FULFILLED"

    def test_contract_violated_event(self):
        ev = create_event(
            "run-1",
            5,
            "CONTRACT_VIOLATED",
            {"contract_id": "c1", "run_id": "run-1", "reason": "budget exceeded"},
        )
        assert ev.type == "CONTRACT_VIOLATED"

    def test_receipt_generated_event(self):
        ev = create_event(
            "run-1", 6, "RECEIPT_GENERATED", {"receipt": {"id": "r1", "total_ms": 1500}}
        )
        assert ev.type == "RECEIPT_GENERATED"

    def test_failure_autopsy_generated_event(self):
        ev = create_event(
            "run-1",
            7,
            "FAILURE_AUTOPSY_GENERATED",
            {"autopsy": {"cause": "timeout", "suggestion": "increase timeout"}},
        )
        assert ev.type == "FAILURE_AUTOPSY_GENERATED"

    def test_evidence_ref_created_event(self):
        ev = create_event(
            "run-1",
            8,
            "EVIDENCE_REF_CREATED",
            {
                "evidence_ref": {
                    "evidence_id": "ev_abcdefghijklmnopqrst123456",
                    "kind": "file",
                    "target": "log.txt",
                }
            },
        )
        assert ev.type == "EVIDENCE_REF_CREATED"

    def test_event_with_node_id_optional_field(self):
        """Stable ID fields (node_id, message_id, etc.) are optional and accepted."""
        ev = create_event(
            "run-1",
            9,
            "RUN_STARTED",
            {
                "workflow_id": "wf",
                "runtime": "sg",
                "node_id": "node_abc",
            },
        )
        assert ev.data["node_id"] == "node_abc"

    def test_event_with_all_stable_ids(self):
        """Events can carry all stable ID fields simultaneously."""
        ev = create_event(
            "run-1",
            10,
            "MESSAGE",
            {
                "text": "hello",
                "node_id": "n1",
                "message_id": "m1",
                "tool_call_id": "t1",
            },
        )
        assert ev.data["node_id"] == "n1"
        assert ev.data["message_id"] == "m1"
        assert ev.data["tool_call_id"] == "t1"

    def test_swarmgraph_topology_event_accepts_nodes_and_edges(self):
        ev = create_event(
            "run-1",
            11,
            "SWARMGRAPH_TOPOLOGY",
            {
                "nodes": [{"id": "queen", "label": "Queen"}],
                "edges": [{"source": "queen", "target": "worker-1"}],
            },
        )
        assert ev.type == "SWARMGRAPH_TOPOLOGY"
        assert ev.data["nodes"][0]["id"] == "queen"
        assert ev.data["edges"][0]["target"] == "worker-1"

    def test_swarmgraph_consensus_event_accepts_votes_and_metadata(self):
        ev = create_event(
            "run-1",
            12,
            "SWARMGRAPH_CONSENSUS",
            {
                "votes": [{"voter": "worker-1", "vote": "approve"}],
                "decision": "approve",
                "strategy": "majority",
                "voters": ["worker-1"],
                "confidence": 0.9,
                "consensus_reached": True,
                "task_id": "task-1",
            },
        )
        assert ev.type == "SWARMGRAPH_CONSENSUS"
        assert ev.data["votes"][0]["vote"] == "approve"
        assert ev.data["consensus_reached"] is True

    def test_swarmgraph_cost_event_accepts_all_optional_fields(self):
        ev = create_event(
            "run-1",
            13,
            "SWARMGRAPH_COST",
            {
                "provider": "openai",
                "model": "gpt-4o",
                "promptTokens": 600,
                "completionTokens": 600,
                "totalCost": 0.012,
                "totalTokens": 1200,
                "currency": "USD",
                "source": "langgraph+swarmgraph",
                "items": [{"model": "gpt-4o", "tokens": 1200, "cost": 0.012}],
                "runtime": "swarmgraph",
                "measured": "2026-05-19T12:00:00.000000+00:00",
            },
        )
        assert ev.type == "SWARMGRAPH_COST"
        assert ev.data["provider"] == "openai"
        assert ev.data["model"] == "gpt-4o"
        assert ev.data["promptTokens"] == 600
        assert ev.data["completionTokens"] == 600
        assert ev.data["totalCost"] == 0.012
        assert ev.data["totalTokens"] == 1200
        assert ev.data["source"] == "langgraph+swarmgraph"
        assert ev.data["measured"] == "2026-05-19T12:00:00.000000+00:00"

    def test_swarmgraph_cost_event_allows_empty_payload(self):
        ev = create_event("run-1", 14, "SWARMGRAPH_COST", {})
        assert ev.type == "SWARMGRAPH_COST"
        assert ev.data == {}

    def test_swarmgraph_cost_event_partial_fields(self):
        """Cost event with only some fields populated is valid."""
        ev = create_event(
            "run-1",
            15,
            "SWARMGRAPH_COST",
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "promptTokens": 300,
                "completionTokens": 150,
            },
        )
        assert ev.type == "SWARMGRAPH_COST"
        assert ev.data["provider"] == "openai"
        assert ev.data["model"] == "gpt-4o-mini"
        assert ev.data["promptTokens"] == 300
        assert ev.data["completionTokens"] == 150
        assert "totalCost" not in ev.data
        assert "totalTokens" not in ev.data

    def test_swarmgraph_cost_event_malformed_types_still_valid_as_optional(self):
        """Schema does not enforce types; malformed data passes optional-field check."""
        ev = create_event(
            "run-1",
            16,
            "SWARMGRAPH_COST",
            {
                "totalCost": "not-a-number",
                "model": 42,
                "promptTokens": None,
            },
        )
        assert ev.type == "SWARMGRAPH_COST"
        assert ev.data["totalCost"] == "not-a-number"
        assert ev.data["model"] == 42
        assert ev.data["promptTokens"] is None

    def test_swarmgraph_topology_event_rejects_missing_edges(self):
        import pytest

        with pytest.raises(ValueError, match="required"):
            create_event("run-1", 17, "SWARMGRAPH_TOPOLOGY", {"nodes": []})

    def test_swarmgraph_consensus_event_rejects_missing_votes(self):
        import pytest

        with pytest.raises(ValueError, match="required"):
            create_event("run-1", 18, "SWARMGRAPH_CONSENSUS", {"decision": "approve"})


class TestRunEventSchemaVersion:
    """RunEvent model carries schema_version (default 2)."""

    def test_run_event_defaults_to_version_2(self):
        from datetime import datetime, timezone

        ev = RunEvent(
            type="TEST",
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id="r1",
            sequence=0,
            data={},
        )
        assert ev.schema_version == 2

    def test_run_event_serializes_schema_version(self):
        from datetime import datetime, timezone

        ev = RunEvent(
            type="TEST",
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id="r1",
            sequence=0,
            data={},
        )
        d = ev.model_dump()
        assert "schema_version" in d
        assert d["schema_version"] == 2

    def test_run_event_custom_version(self):
        from datetime import datetime, timezone

        ev = RunEvent(
            schema_version=2,
            type="TEST",
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id="r1",
            sequence=0,
            data={},
        )
        assert ev.schema_version == 2

    def test_run_event_migrates_v1_payload_to_v2(self):
        from datetime import datetime, timezone

        ev = RunEvent(
            schema_version=1,
            type="TEST",
            timestamp=datetime.now(timezone.utc).isoformat(),
            run_id="r1",
            sequence=0,
            data={"runtime_mode": "offline"},
        )
        assert ev.schema_version == 2
        assert ev.data["runtime_mode"] == "fake"
        assert ev.data["profile_id"] == "default"
        assert ev.data["isolation_id"] == "none"
        assert ev.data["source_trust"] == "workspace"
