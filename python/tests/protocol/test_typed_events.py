"""Tests for discriminated RunEvent union types (Phase 22)."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.protocol.typed_events import (
    RunStartedEvent,
    RunCompletedEvent,
    StepStartedEvent,
    ToolCallResultEvent,
    HitlPromptEvent,
    SwarmGraphTopologyEvent,
    RawEvent,
    UnknownEvent,
    is_run_started,
    is_run_completed,
    is_tool_call_result,
    is_known_event,
    parse_typed_event,
)


class TestTypedEventConstruction:
    """Test construction of typed event variants."""

    def test_run_started_event(self):
        """Construct RUN_STARTED event with typed payload."""
        event = RunStartedEvent(
            type="RUN_STARTED",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-001",
            sequence=0,
            data={
                "workflow_id": "wf-test",
                "runtime": "swarmgraph",
                "profile_id": "default",
            },
        )
        assert event.type == "RUN_STARTED"
        assert event.data.workflow_id == "wf-test"
        assert event.data.runtime == "swarmgraph"
        assert event.data.profile_id == "default"

    def test_run_completed_event(self):
        """Construct RUN_COMPLETED event with typed payload."""
        event = RunCompletedEvent(
            type="RUN_COMPLETED",
            timestamp="2026-05-22T10:01:00Z",
            run_id="run-001",
            sequence=10,
            data={"duration_ms": 60000, "output": {"result": "success"}},
        )
        assert event.type == "RUN_COMPLETED"
        assert event.data.duration_ms == 60000
        assert event.data.output == {"result": "success"}

    def test_step_started_event(self):
        """Construct STEP_STARTED event with typed payload."""
        event = StepStartedEvent(
            type="STEP_STARTED",
            timestamp="2026-05-22T10:00:10Z",
            run_id="run-001",
            sequence=1,
            data={"step_id": "s1", "step_name": "load_data", "step_type": "data"},
        )
        assert event.type == "STEP_STARTED"
        assert event.data.step_id == "s1"
        assert event.data.step_name == "load_data"

    def test_tool_call_result_event(self):
        """Construct TOOL_CALL_RESULT event with typed payload."""
        event = ToolCallResultEvent(
            type="TOOL_CALL_RESULT",
            timestamp="2026-05-22T10:00:20Z",
            run_id="run-001",
            sequence=2,
            data={"tool_call_id": "tc1", "result": {"status": "ok", "data": [1, 2, 3]}},
        )
        assert event.type == "TOOL_CALL_RESULT"
        assert event.data.tool_call_id == "tc1"
        assert event.data.result == {"status": "ok", "data": [1, 2, 3]}

    def test_hitl_prompt_event(self):
        """Construct HITL_PROMPT event with typed payload."""
        event = HitlPromptEvent(
            type="HITL_PROMPT",
            timestamp="2026-05-22T10:00:30Z",
            run_id="run-001",
            sequence=3,
            data={
                "hitl_id": "hitl-1",
                "step_id": "s2",
                "prompt_text": "Approve this action?",
                "options": ["approve", "reject"],
                "timeout_seconds": 300,
            },
        )
        assert event.type == "HITL_PROMPT"
        assert event.data.hitl_id == "hitl-1"
        assert event.data.options == ["approve", "reject"]

    def test_unknown_event(self):
        """Construct UnknownEvent for untyped event types."""
        event = UnknownEvent(
            type="CUSTOM_EVENT",
            timestamp="2026-05-22T10:00:40Z",
            run_id="run-001",
            sequence=4,
            data={"custom_field": "value"},
        )
        assert event.type == "CUSTOM_EVENT"
        assert event.data["custom_field"] == "value"


class TestTypeGuards:
    """Test type guard functions for event narrowing."""

    def test_is_run_started(self):
        """Type guard correctly identifies RUN_STARTED events."""
        event = RunStartedEvent(
            type="RUN_STARTED",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-001",
            sequence=0,
            data={"workflow_id": "wf-test", "runtime": "swarmgraph"},
        )
        assert is_run_started(event) is True

        other_event = RunCompletedEvent(
            type="RUN_COMPLETED",
            timestamp="2026-05-22T10:01:00Z",
            run_id="run-001",
            sequence=1,
            data={"duration_ms": 1000},
        )
        assert is_run_started(other_event) is False

    def test_is_run_completed(self):
        """Type guard correctly identifies RUN_COMPLETED events."""
        event = RunCompletedEvent(
            type="RUN_COMPLETED",
            timestamp="2026-05-22T10:01:00Z",
            run_id="run-001",
            sequence=1,
            data={"duration_ms": 1000},
        )
        assert is_run_completed(event) is True

    def test_is_tool_call_result(self):
        """Type guard correctly identifies TOOL_CALL_RESULT events."""
        event = ToolCallResultEvent(
            type="TOOL_CALL_RESULT",
            timestamp="2026-05-22T10:00:20Z",
            run_id="run-001",
            sequence=2,
            data={"tool_call_id": "tc1", "result": "ok"},
        )
        assert is_tool_call_result(event) is True

    def test_is_known_event(self):
        """Type guard distinguishes known from unknown events."""
        known = RunStartedEvent(
            type="RUN_STARTED",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-001",
            sequence=0,
            data={"workflow_id": "wf-test", "runtime": "swarmgraph"},
        )
        assert is_known_event(known) is True

        unknown = UnknownEvent(
            type="CUSTOM_EVENT",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-001",
            sequence=0,
            data={},
        )
        assert is_known_event(unknown) is False


class TestEventParsing:
    """Test parsing raw event dicts into typed events."""

    def test_parse_run_started(self):
        """Parse raw dict into RUN_STARTED event."""
        raw = {
            "schema_version": 2,
            "type": "RUN_STARTED",
            "timestamp": "2026-05-22T10:00:00Z",
            "run_id": "run-001",
            "sequence": 0,
            "data": {"workflow_id": "wf-test", "runtime": "swarmgraph"},
        }
        event = parse_typed_event(raw)
        assert isinstance(event, RunStartedEvent)
        assert event.data.workflow_id == "wf-test"

    def test_parse_run_completed(self):
        """Parse raw dict into RUN_COMPLETED event."""
        raw = {
            "schema_version": 2,
            "type": "RUN_COMPLETED",
            "timestamp": "2026-05-22T10:01:00Z",
            "run_id": "run-001",
            "sequence": 10,
            "data": {"duration_ms": 60000},
        }
        event = parse_typed_event(raw)
        assert isinstance(event, RunCompletedEvent)
        assert event.data.duration_ms == 60000

    def test_parse_unknown_event_type(self):
        """Parse unknown event type into UnknownEvent."""
        raw = {
            "schema_version": 2,
            "type": "CUSTOM_EVENT",
            "timestamp": "2026-05-22T10:00:00Z",
            "run_id": "run-001",
            "sequence": 0,
            "data": {"custom_field": "value"},
        }
        event = parse_typed_event(raw)
        assert isinstance(event, UnknownEvent)
        assert event.type == "CUSTOM_EVENT"
        assert event.data["custom_field"] == "value"

    def test_parse_invalid_event(self):
        """Parse invalid event raises ValueError."""
        raw = {"invalid": "event"}
        with pytest.raises(ValueError, match="missing or invalid type field"):
            parse_typed_event(raw)


class TestBackwardCompatibility:
    """Test backward compatibility with existing RunEvent usage."""

    def test_typed_event_has_same_fields_as_old_runevent(self):
        """Typed events have same base fields as old RunEvent."""
        event = RunStartedEvent(
            type="RUN_STARTED",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-001",
            sequence=0,
            data={"workflow_id": "wf-test", "runtime": "swarmgraph"},
        )
        # All base fields present
        assert hasattr(event, "schema_version")
        assert hasattr(event, "type")
        assert hasattr(event, "timestamp")
        assert hasattr(event, "run_id")
        assert hasattr(event, "sequence")
        assert hasattr(event, "data")

    def test_typed_event_serializes_to_same_format(self):
        """Typed events serialize to same JSON format as old RunEvent."""
        event = RunStartedEvent(
            type="RUN_STARTED",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-001",
            sequence=0,
            data={"workflow_id": "wf-test", "runtime": "swarmgraph"},
        )
        serialized = event.model_dump()
        assert serialized["type"] == "RUN_STARTED"
        assert serialized["run_id"] == "run-001"
        assert serialized["data"]["workflow_id"] == "wf-test"


class TestSwarmGraphEvents:
    """Test SwarmGraph-specific event types."""

    def test_swarmgraph_topology_event(self):
        """Construct SWARMGRAPH_TOPOLOGY event."""
        event = SwarmGraphTopologyEvent(
            type="SWARMGRAPH_TOPOLOGY",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-001",
            sequence=0,
            data={
                "nodes": [{"id": "n1", "type": "worker"}],
                "edges": [{"from": "n1", "to": "n2"}],
                "strategy": "consensus",
            },
        )
        assert event.type == "SWARMGRAPH_TOPOLOGY"
        assert len(event.data.nodes) == 1
        assert len(event.data.edges) == 1


class TestRawEventFallback:
    """Test RAW event fallback for unknown event types."""

    def test_raw_event_construction(self):
        """Construct RAW event with arbitrary payload."""
        event = RawEvent(
            type="RAW",
            timestamp="2026-05-22T10:00:00Z",
            run_id="run-001",
            sequence=0,
            data={"raw": {"unknown": "data"}, "source": "external"},
        )
        assert event.type == "RAW"
        assert event.data.raw == {"unknown": "data"}
        assert event.data.source == "external"
