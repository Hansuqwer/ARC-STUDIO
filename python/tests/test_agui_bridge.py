"""Tests: AG-UI bridge — event mapping."""
from agent_runtime_cockpit.web.agui_bridge import to_agui, from_agui, ARC_TO_AGUI
from agent_runtime_cockpit.protocol.schemas import RunEvent


class TestAguiBridge:
    def _make_event(self, type_: str, seq: int = 0) -> RunEvent:
        return RunEvent(
            type=type_,
            timestamp="2025-01-01T00:00:00Z",
            run_id="run-test",
            sequence=seq,
            data={"node": "agent"},
        )

    def test_run_started_maps_to_agui(self):
        event = self._make_event("RUN_STARTED")
        result = to_agui(event)
        assert result["type"] == "RunStarted"
        assert result["runId"] == "run-test"
        assert result["sequence"] == 0
        assert result["_arc_type"] == "RUN_STARTED"

    def test_node_started_maps(self):
        event = self._make_event("NODE_STARTED", seq=1)
        result = to_agui(event)
        assert result["type"] == "StepStarted"

    def test_unknown_type_passthrough(self):
        event = self._make_event("CUSTOM_ARC_EVENT")
        result = to_agui(event)
        assert result["type"] == "CUSTOM_ARC_EVENT"  # passthrough

    def test_roundtrip_from_agui(self):
        event = self._make_event("NODE_COMPLETED")
        agui = to_agui(event)
        restored = from_agui(agui)
        assert restored.run_id == event.run_id
        assert restored.sequence == event.sequence

    def test_all_arc_types_mapped(self):
        # All defined mappings must produce non-empty AG-UI types
        for arc_type, agui_type in ARC_TO_AGUI.items():
            assert agui_type, f"Empty AG-UI type for {arc_type}"

    def test_event_data_preserved(self):
        event = RunEvent(
            type="NODE_COMPLETED", timestamp="2025-01-01T00:00:00Z",
            run_id="r1", sequence=2, data={"node": "writer", "output": "draft done"}
        )
        result = to_agui(event)
        assert result.get("node") == "writer"
        assert result.get("output") == "draft done"
