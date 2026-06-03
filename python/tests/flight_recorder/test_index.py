"""Tests for flight_recorder.index — load/save/upsert/segments."""

from __future__ import annotations


from agent_runtime_cockpit.flight_recorder import index as _index
from agent_runtime_cockpit.flight_recorder.models import (
    FlightIndex,
    RunEntry,
    SegmentRef,
)


class TestLoadSave:
    def test_load_empty_returns_default(self, tmp_path):
        idx = _index.load_index(tmp_path)
        assert isinstance(idx, FlightIndex)
        assert idx.segments == []
        assert idx.runs == {}

    def test_save_and_load_round_trip(self, tmp_path):
        idx = FlightIndex(
            runs={"run-1": RunEntry(run_id="run-1", started_at="2026-06-03T10:00:00Z")}
        )
        _index.save_index(tmp_path, idx)
        loaded = _index.load_index(tmp_path)
        assert "run-1" in loaded.runs

    def test_corrupt_index_returns_empty(self, tmp_path):
        p = tmp_path / "index.json"
        p.write_text("NOT_VALID_JSON{{{")
        idx = _index.load_index(tmp_path)
        assert isinstance(idx, FlightIndex)
        assert idx.segments == []

    def test_index_file_written_atomically(self, tmp_path):
        idx = FlightIndex()
        _index.save_index(tmp_path, idx)
        assert (tmp_path / "index.json").exists()
        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == []


class TestUpsertRun:
    def test_upsert_adds_run(self, tmp_path):
        run = RunEntry(run_id="run-a", started_at="2026-06-03T10:00:00Z")
        _index.upsert_run(tmp_path, run)
        idx = _index.load_index(tmp_path)
        assert "run-a" in idx.runs

    def test_upsert_updates_run(self, tmp_path):
        run = RunEntry(run_id="run-b", started_at="2026-06-03T10:00:00Z", status="running")
        _index.upsert_run(tmp_path, run)
        run.status = "completed"
        _index.upsert_run(tmp_path, run)
        idx = _index.load_index(tmp_path)
        assert idx.runs["run-b"].status == "completed"


class TestAddSegmentRef:
    def _make_ref(self, segment_id: str, run_id: str = "run-1") -> SegmentRef:
        return SegmentRef(
            segment_id=segment_id,
            run_id=run_id,
            created_at="2026-06-03T10:00:00Z",
        )

    def test_add_segment(self, tmp_path):
        ref = self._make_ref("seg-1")
        _index.add_segment_ref(tmp_path, ref)
        idx = _index.load_index(tmp_path)
        assert any(s.segment_id == "seg-1" for s in idx.segments)

    def test_no_duplicates(self, tmp_path):
        ref = self._make_ref("seg-dup")
        _index.add_segment_ref(tmp_path, ref)
        _index.add_segment_ref(tmp_path, ref)
        idx = _index.load_index(tmp_path)
        count = sum(1 for s in idx.segments if s.segment_id == "seg-dup")
        assert count == 1

    def test_update_segment_ref(self, tmp_path):
        ref = self._make_ref("seg-upd")
        _index.add_segment_ref(tmp_path, ref)
        ref.event_count = 10
        _index.update_segment_ref(tmp_path, ref)
        idx = _index.load_index(tmp_path)
        updated = next(s for s in idx.segments if s.segment_id == "seg-upd")
        assert updated.event_count == 10


class TestCloseRun:
    def test_close_run_updates_status(self, tmp_path):
        run = RunEntry(run_id="run-close", started_at="2026-06-03T10:00:00Z")
        _index.upsert_run(tmp_path, run)
        _index.close_run(tmp_path, "run-close", status="failed")
        idx = _index.load_index(tmp_path)
        assert idx.runs["run-close"].status == "failed"
        assert idx.runs["run-close"].completed_at is not None


class TestSegmentsForRun:
    def test_segments_for_run_filtered(self, tmp_path):
        r1 = SegmentRef(segment_id="s1", run_id="run-x", created_at="2026-06-03T10:00:00Z")
        r2 = SegmentRef(segment_id="s2", run_id="run-y", created_at="2026-06-03T10:01:00Z")
        _index.add_segment_ref(tmp_path, r1)
        _index.add_segment_ref(tmp_path, r2)
        result = _index.segments_for_run(tmp_path, "run-x")
        assert len(result) == 1
        assert result[0].segment_id == "s1"
