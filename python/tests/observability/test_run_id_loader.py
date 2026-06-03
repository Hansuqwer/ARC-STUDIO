"""Tests for run-id based storage loading."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


def _make_storage(tmp_path: Path) -> Path:
    """Set up a fake .arc/traces directory with the fixture run."""
    traces_dir = tmp_path / ".arc" / "traces"
    traces_dir.mkdir(parents=True)
    shutil.copy(FIXTURES / "run-storage-001.jsonl", traces_dir / "run-storage-001.jsonl")
    return traces_dir


class TestRunIdLoader:
    def test_load_run_by_id_success(self, tmp_path):
        from agent_runtime_cockpit.observability.loaders import load_run_by_id

        storage = _make_storage(tmp_path)
        trace = load_run_by_id("run-storage-001", storage_root=storage)
        assert trace.run_id == "run-storage-001"
        assert trace.workflow_id == "wf-storage-test"
        assert trace.runtime == "swarmgraph"
        assert len(trace.events) == 3

    def test_load_run_by_id_not_found(self, tmp_path):
        from agent_runtime_cockpit.observability.loaders import RunNotFoundError, load_run_by_id

        storage = _make_storage(tmp_path)
        with pytest.raises(RunNotFoundError):
            load_run_by_id("nonexistent-run", storage_root=storage)

    def test_load_run_by_id_malformed(self, tmp_path):
        from agent_runtime_cockpit.observability.loaders import (
            RunRecordInvalidError,
            load_run_by_id,
        )

        storage = _make_storage(tmp_path)
        (storage / "bad-run.jsonl").write_text("not valid json\n")
        with pytest.raises(RunRecordInvalidError):
            load_run_by_id("bad-run", storage_root=storage)

    def test_load_run_embedded_events(self, tmp_path):
        """RunRecord with embedded events list is fully loaded."""
        from agent_runtime_cockpit.observability.loaders import load_run_by_id

        storage = _make_storage(tmp_path)
        trace = load_run_by_id("run-storage-001", storage_root=storage)
        types = [e.get("type") for e in trace.events]
        assert "run.started" in types
        assert "run.completed" in types

    def test_source_storage_not_mutated(self, tmp_path):
        """Loading must not modify the .jsonl file."""
        from agent_runtime_cockpit.observability.loaders import load_run_by_id

        storage = _make_storage(tmp_path)
        original = (storage / "run-storage-001.jsonl").read_text()
        load_run_by_id("run-storage-001", storage_root=storage)
        assert (storage / "run-storage-001.jsonl").read_text() == original

    def test_export_by_run_id_end_to_end(self, tmp_path):
        """Full export pipeline works via run ID."""
        from agent_runtime_cockpit.observability import ObservabilityExportConfig, export_trace
        from agent_runtime_cockpit.observability.loaders import load_run_by_id

        storage = _make_storage(tmp_path)
        trace = load_run_by_id("run-storage-001", storage_root=storage)
        # Use source_file to call export_trace (the loader returns the JSONL path)
        export = export_trace(
            trace.source_file,
            cfg=ObservabilityExportConfig(format="openinference-json"),
        )
        assert export.source.run_id == "run-storage-001"
        assert export.export_hash is not None
        assert len(export.spans) >= 1

    def test_mcp_event_in_loaded_run(self, tmp_path):
        """MCP events are present after loading by run ID."""
        from agent_runtime_cockpit.observability.loaders import load_run_by_id

        storage = _make_storage(tmp_path)
        trace = load_run_by_id("run-storage-001", storage_root=storage)
        mcp_events = [e for e in trace.events if "mcp" in (e.get("type") or "").lower()]
        assert len(mcp_events) == 1
        assert mcp_events[0]["data"]["manifest_hash"] == "abc123def456"
