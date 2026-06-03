"""Tests for flight_recorder.verify — segment integrity verification."""

from __future__ import annotations

import json
from pathlib import Path


from agent_runtime_cockpit.flight_recorder import FlightRecorder, FlightRecorderConfig
from agent_runtime_cockpit.flight_recorder import index as _index
from agent_runtime_cockpit.flight_recorder.models import EventType, SegmentRef
from agent_runtime_cockpit.flight_recorder.verify import verify


def _make_recorder(tmp_path: Path) -> FlightRecorder:
    cfg = FlightRecorderConfig(
        base_dir=str(tmp_path / ".arc" / "flight"),
        max_segment_bytes=1024 * 1024,
    )
    return FlightRecorder(config=cfg)


class TestVerify:
    def test_verify_empty_index_ok(self, tmp_path):
        cfg = FlightRecorderConfig(base_dir=str(tmp_path / ".arc" / "flight"))
        base = Path(cfg.base_dir)
        report = verify(base)
        assert report.ok is True
        assert report.checked_segments == 0

    def test_verify_clean_run_passes(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-verify-clean")
        recorder.record("run-verify-clean", EventType.IR_COMPILED, payload={"x": 1})
        recorder.record("run-verify-clean", EventType.POLICY_EVALUATED, payload={"risk": "low"})
        recorder.stop_run("run-verify-clean")

        base = Path(recorder._config.base_dir)
        report = verify(base)
        assert report.ok is True
        assert len(report.corrupt_segments) == 0
        assert len(report.missing_segments) == 0

    def test_verify_sets_last_verified_at(self, tmp_path):
        cfg = FlightRecorderConfig(base_dir=str(tmp_path / ".arc" / "flight"))
        base = Path(cfg.base_dir)
        base.mkdir(parents=True, exist_ok=True)
        verify(base)
        idx = _index.load_index(base)
        assert idx.last_verified_at is not None

    def test_verify_detects_tampered_event_hash(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-tamper")
        recorder.record("run-tamper", EventType.IR_COMPILED, payload={"x": 1})
        recorder.stop_run("run-tamper")

        # Tamper with the events file
        base = Path(recorder._config.base_dir)
        seg_dir = base / "segments" / "run-tamper"
        events_files = list(seg_dir.glob("*.events.jsonl"))
        assert events_files

        # Rewrite with modified hash
        content = events_files[0].read_text()
        lines = content.splitlines()
        data = json.loads(lines[0])
        data["hash"] = "a" * 64  # tampered hash
        lines[0] = json.dumps(data)
        events_files[0].write_text("\n".join(lines) + "\n")

        report = verify(base)
        assert not report.ok
        assert len(report.corrupt_segments) > 0

    def test_verify_detects_missing_events_file(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-missing")
        recorder.record("run-missing", EventType.IR_COMPILED, payload={})
        recorder.stop_run("run-missing")

        # Delete the events file
        base = Path(recorder._config.base_dir)
        seg_dir = base / "segments" / "run-missing"
        for f in seg_dir.glob("*.events.jsonl"):
            f.unlink()

        report = verify(base)
        assert not report.ok
        assert len(report.missing_segments) > 0

    def test_verify_hash_chain_valid_for_single_segment(self, tmp_path):
        recorder = _make_recorder(tmp_path)
        recorder.start_run("run-chain")
        recorder.record("run-chain", EventType.IR_COMPILED, payload={})
        recorder.stop_run("run-chain")

        base = Path(recorder._config.base_dir)
        report = verify(base)
        assert report.hash_chain_valid is True

    def test_verify_tolerates_empty_segment(self, tmp_path):
        """A segment with 0 events (e.g., just opened then crashed) should not crash verify."""
        cfg = FlightRecorderConfig(base_dir=str(tmp_path / ".arc" / "flight"))
        base = Path(cfg.base_dir)

        # Manually add a segment ref with an empty events file
        (base / "segments" / "run-empty").mkdir(parents=True)
        events_path = base / "segments" / "run-empty" / "segment-000000.events.jsonl"
        meta_path = base / "segments" / "run-empty" / "segment-000000.meta.json"
        events_path.write_text("")  # empty
        meta_path.write_text(
            json.dumps(
                {
                    "segment_id": "seg-empty",
                    "run_id": "run-empty",
                    "created_at": "2026-06-03T10:00:00Z",
                    "closed_at": "2026-06-03T10:01:00Z",
                    "segment_hash": "",
                    "previous_segment_hash": "GENESIS",
                    "events_path": str(events_path),
                    "meta_path": str(meta_path),
                    "event_count": 0,
                }
            )
        )

        ref = SegmentRef(
            segment_id="seg-empty",
            run_id="run-empty",
            created_at="2026-06-03T10:00:00Z",
            closed_at="2026-06-03T10:01:00Z",
            events_path=str(events_path),
            meta_path=str(meta_path),
        )
        _index.add_segment_ref(base, ref)

        report = verify(base)
        # Should complete without exception
        assert isinstance(report.ok, bool)
