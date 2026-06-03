"""Tests for flight_recorder.retention — prune / dry-run / apply."""

from __future__ import annotations

from pathlib import Path


from agent_runtime_cockpit.flight_recorder import FlightRecorderConfig
from agent_runtime_cockpit.flight_recorder import index as _index
from agent_runtime_cockpit.flight_recorder.models import (
    FlightIndex,
    SegmentRef,
)
from agent_runtime_cockpit.flight_recorder.retention import (
    compute_prunable_segments,
    prune,
    _safe_to_delete,
)


def _make_closed_ref(segment_id: str, run_id: str, created_at: str, base_dir: Path) -> SegmentRef:
    events_path = base_dir / "segments" / run_id / f"{segment_id}.events.jsonl"
    meta_path = base_dir / "segments" / run_id / f"{segment_id}.meta.json"
    events_path.parent.mkdir(parents=True, exist_ok=True)
    events_path.write_text('{"x":1}\n')
    meta_path.write_text("{}")
    return SegmentRef(
        segment_id=segment_id,
        run_id=run_id,
        created_at=created_at,
        closed_at="2026-06-03T11:00:00Z",
        events_path=str(events_path),
        meta_path=str(meta_path),
    )


class TestDryRun:
    def test_dry_run_does_not_delete(self, tmp_path):
        base = tmp_path / ".arc" / "flight"
        cfg = FlightRecorderConfig(base_dir=str(base), max_segments=1)

        ref1 = _make_closed_ref("seg-1", "run-1", "2026-06-01T10:00:00Z", base)
        ref2 = _make_closed_ref("seg-2", "run-2", "2026-06-02T10:00:00Z", base)
        idx = FlightIndex(segments=[ref1, ref2])
        _index.save_index(base, idx)

        result = prune(base, cfg, active_run_ids=set(), dry_run=True)
        assert result["dry_run"] is True
        assert result["applied"] is False

        # Files should still exist
        assert Path(ref1.events_path).exists()

    def test_dry_run_reports_prunable(self, tmp_path):
        base = tmp_path / ".arc" / "flight"
        cfg = FlightRecorderConfig(base_dir=str(base), max_segments=1)

        ref1 = _make_closed_ref("seg-old", "run-1", "2026-06-01T10:00:00Z", base)
        ref2 = _make_closed_ref("seg-new", "run-2", "2026-06-03T10:00:00Z", base)
        idx = FlightIndex(segments=[ref1, ref2])
        _index.save_index(base, idx)

        result = prune(base, cfg, active_run_ids=set(), dry_run=True)
        assert result["prunable_segments"] >= 1


class TestApply:
    def test_apply_deletes_oldest(self, tmp_path):
        base = tmp_path / ".arc" / "flight"
        cfg = FlightRecorderConfig(base_dir=str(base), max_segments=1)

        ref1 = _make_closed_ref("seg-old-del", "run-1", "2026-05-01T10:00:00Z", base)
        ref2 = _make_closed_ref("seg-new-keep", "run-2", "2026-06-03T10:00:00Z", base)
        idx = FlightIndex(segments=[ref1, ref2])
        _index.save_index(base, idx)

        result = prune(base, cfg, active_run_ids=set(), dry_run=False)
        assert result["applied"] is True
        # seg-old should be removed, seg-new kept
        assert not Path(ref1.events_path).exists()
        assert Path(ref2.events_path).exists()

    def test_apply_updates_index(self, tmp_path):
        base = tmp_path / ".arc" / "flight"
        cfg = FlightRecorderConfig(base_dir=str(base), max_segments=1)

        ref1 = _make_closed_ref("seg-idx-del", "run-1", "2026-05-01T10:00:00Z", base)
        ref2 = _make_closed_ref("seg-idx-keep", "run-2", "2026-06-03T10:00:00Z", base)
        idx = FlightIndex(segments=[ref1, ref2])
        _index.save_index(base, idx)

        prune(base, cfg, active_run_ids=set(), dry_run=False)
        new_idx = _index.load_index(base)
        seg_ids = {s.segment_id for s in new_idx.segments}
        assert "seg-idx-del" not in seg_ids
        assert "seg-idx-keep" in seg_ids


class TestActiveRunProtection:
    def test_active_run_segments_not_pruned(self, tmp_path):
        base = tmp_path / ".arc" / "flight"
        cfg = FlightRecorderConfig(base_dir=str(base), max_segments=0)  # prune all

        ref = _make_closed_ref("seg-active", "run-active", "2026-05-01T10:00:00Z", base)
        idx = FlightIndex(segments=[ref])
        _index.save_index(base, idx)

        # Run is still active
        prune(base, cfg, active_run_ids={"run-active"}, dry_run=False)
        # Should NOT delete because run is active
        assert Path(ref.events_path).exists()


class TestSafeToDelete:
    def test_path_inside_segments_is_safe(self, tmp_path):
        base = tmp_path / ".arc" / "flight"
        p = base / "segments" / "run-1" / "segment-000000.events.jsonl"
        p.parent.mkdir(parents=True)
        p.write_text("x")
        assert _safe_to_delete(base, p)

    def test_path_outside_segments_not_safe(self, tmp_path):
        base = tmp_path / ".arc" / "flight"
        # Attempt to delete index.json — should be refused
        p = base / "index.json"
        assert not _safe_to_delete(base, p)

    def test_path_escape_not_safe(self, tmp_path):
        base = tmp_path / ".arc" / "flight"
        p = tmp_path / "important_file.txt"
        assert not _safe_to_delete(base, p)


class TestAgePruning:
    def test_old_segments_pruned_by_age(self, tmp_path):
        base = tmp_path / ".arc" / "flight"
        # max_age_days=0 means anything older than now (all)
        cfg = FlightRecorderConfig(base_dir=str(base), max_age_days=1)

        # Very old timestamp
        old_ref = _make_closed_ref("seg-ancient", "run-ancient", "2020-01-01T00:00:00Z", base)
        idx = FlightIndex(segments=[old_ref])
        _index.save_index(base, idx)

        idx_obj = _index.load_index(base)
        prunable = compute_prunable_segments(idx_obj, base, cfg, active_run_ids=set())
        assert any(s.segment_id == "seg-ancient" for s in prunable)
