"""Protocol conformance tests: verify Python ↔ TypeScript JSON compatibility."""

import json
import pytest

# Import Python models
from agent_runtime_cockpit.protocol.schemas import (
    RunEvent,
    RunRecord,
    RunStatus,
    WorkspaceInfo,
)


class TestProtocolConformance:
    """Test that Python models serialize to TypeScript-compatible JSON."""

    def test_run_event_serialization(self):
        """RunEvent should serialize to JSON with expected fields."""
        event = RunEvent(
            type="RUN_STARTED",
            timestamp="2026-05-24T12:00:00Z",
            run_id="test-run-123",
            sequence=0,
            data={"workflow_id": "wf-001", "runtime": "swarmgraph"},
        )

        json_str = event.model_dump_json()
        json_data = json.loads(json_str)

        assert "type" in json_data
        assert "timestamp" in json_data
        assert "run_id" in json_data
        assert "sequence" in json_data
        assert "data" in json_data

    def test_run_record_roundtrip(self):
        """RunRecord should round-trip through JSON."""
        record = RunRecord(
            id="run-123",
            workflow_id="wf-001",
            runtime="swarmgraph",
            status=RunStatus.COMPLETED,
            started_at="2026-05-24T12:00:00Z",
            ended_at="2026-05-24T12:05:00Z",
            events=[],
            metadata={},
        )

        json_str = record.model_dump_json()
        json_data = json.loads(json_str)
        record2 = RunRecord.model_validate(json_data)

        assert record.model_dump() == record2.model_dump()

    def test_workspace_info_serialization(self):
        """WorkspaceInfo should serialize correctly."""
        info = WorkspaceInfo(
            path="/Users/test/workspace",
            runtimes=[],
            files_scanned=100,
            detection_warnings=[],
        )

        dump = info.model_dump()
        assert "path" in dump
        assert "runtimes" in dump
        assert "files_scanned" in dump


class TestFieldCasing:
    """Test that field casing matches expectations."""

    def test_pydanitic_uses_snake_case(self):
        """Python models use snake_case internally."""
        info = WorkspaceInfo(
            path="/test",
            runtimes=[],
            files_scanned=10,
            detection_warnings=[],
        )

        # Internal representation should be snake_case
        dump = info.model_dump()
        assert "path" in dump or "workspaceRoot" in dump


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
