"""Tests for flight_recorder.segments — append-only JSONL segment writing.

Covers:
  - Append event to segment.
  - Segment hash computation.
  - Hash chain across segments.
  - Partial/corrupt trailing line tolerance.
  - Crash-safe write (temp + replace).
  - Segment meta written atomically.
  - Segment rotation by size.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.flight_recorder.models import (
    EventType,
    FlightEvent,
    FlightRecorderConfig,
)
from agent_runtime_cockpit.flight_recorder.segments import (
    SegmentWriter,
    _atomic_write,
    open_segment,
    read_segment_events,
)


def _make_event(seq: int = 0, run_id: str = "run-test") -> FlightEvent:
    evt = FlightEvent(
        event_id=f"evt-{seq:04d}",
        event_type=EventType.RUN_STARTED,
        run_id=run_id,
        timestamp="2026-06-03T10:00:00Z",
        sequence=seq,
        payload={"n": seq},
    ).with_hash()
    return evt


class TestAtomicWrite:
    def test_writes_content(self, tmp_path):
        p = tmp_path / "test.json"
        _atomic_write(p, '{"hello": "world"}')
        assert p.read_text() == '{"hello": "world"}'

    def test_overwrites_existing(self, tmp_path):
        p = tmp_path / "test.json"
        _atomic_write(p, "first")
        _atomic_write(p, "second")
        assert p.read_text() == "second"

    def test_creates_parent_dirs(self, tmp_path):
        p = tmp_path / "a" / "b" / "c" / "test.json"
        _atomic_write(p, "content")
        assert p.exists()

    def test_no_tmp_file_left_on_success(self, tmp_path):
        p = tmp_path / "test.json"
        _atomic_write(p, "data")
        tmp_files = list(tmp_path.glob(".test.json.*.tmp"))
        assert tmp_files == []


class TestSegmentWriter:
    def _make_writer(self, tmp_path: Path, segment_number: int = 0) -> SegmentWriter:
        cfg = FlightRecorderConfig(
            base_dir=str(tmp_path),
            max_segment_bytes=1024 * 1024,  # 1 MiB
        )
        return open_segment(tmp_path, "run-test", segment_number, "GENESIS", cfg)

    def test_open_creates_files(self, tmp_path):
        writer = self._make_writer(tmp_path)
        assert writer._events_path.exists()
        writer.close()

    def test_append_event(self, tmp_path):
        writer = self._make_writer(tmp_path)
        evt = _make_event(seq=0)
        writer.append(evt)
        writer.close()
        events = read_segment_events(writer._events_path)
        assert len(events) == 1
        assert events[0]["event_id"] == "evt-0000"

    def test_append_multiple_events(self, tmp_path):
        writer = self._make_writer(tmp_path)
        for i in range(5):
            writer.append(_make_event(seq=i))
        writer.close()
        events = read_segment_events(writer._events_path)
        assert len(events) == 5
        assert [e["sequence"] for e in events] == list(range(5))

    def test_segment_hash_deterministic(self, tmp_path):
        writer = self._make_writer(tmp_path)
        evts = [_make_event(seq=i) for i in range(3)]
        for evt in evts:
            writer.append(evt)
        seg = writer.close()

        # Recompute manually
        hashes = ",".join(e.compute_hash() for e in evts)
        expected = hashlib.sha256(hashes.encode("utf-8")).hexdigest()
        assert seg.segment_hash == expected

    def test_segment_hash_changes_with_different_events(self, tmp_path):
        cfg = FlightRecorderConfig(base_dir=str(tmp_path), max_segment_bytes=1024 * 1024)

        w1 = open_segment(tmp_path, "run-a", 0, "GENESIS", cfg)
        w1.append(_make_event(seq=0, run_id="run-a"))
        seg1 = w1.close()

        w2 = open_segment(tmp_path, "run-b", 0, "GENESIS", cfg)
        w2.append(_make_event(seq=1, run_id="run-b"))
        seg2 = w2.close()

        assert seg1.segment_hash != seg2.segment_hash

    def test_hash_chain(self, tmp_path):
        cfg = FlightRecorderConfig(base_dir=str(tmp_path), max_segment_bytes=1024 * 1024)

        w1 = open_segment(tmp_path, "run-test", 0, "GENESIS", cfg)
        w1.append(_make_event(seq=0))
        seg1 = w1.close()

        w2 = open_segment(tmp_path, "run-test", 1, seg1.segment_hash, cfg)
        w2.append(_make_event(seq=1))
        seg2 = w2.close()

        assert seg2.previous_segment_hash == seg1.segment_hash
        assert seg1.previous_segment_hash == "GENESIS"

    def test_close_is_idempotent(self, tmp_path):
        writer = self._make_writer(tmp_path)
        writer.append(_make_event(seq=0))
        seg1 = writer.close()
        seg2 = writer.close()  # Should not raise
        assert seg1.segment_hash == seg2.segment_hash

    def test_append_to_closed_segment_raises(self, tmp_path):
        writer = self._make_writer(tmp_path)
        writer.close()
        with pytest.raises(RuntimeError, match="closed"):
            writer.append(_make_event(seq=1))

    def test_meta_file_written_atomically(self, tmp_path):
        writer = self._make_writer(tmp_path)
        writer.append(_make_event(seq=0))
        writer.close()
        meta_path = writer._meta_path
        assert meta_path.exists()
        data = json.loads(meta_path.read_text())
        assert "segment_id" in data
        assert "segment_hash" in data

    def test_is_full_false_when_small(self, tmp_path):
        writer = self._make_writer(tmp_path)
        writer.append(_make_event(seq=0))
        assert writer.is_full is False
        writer.close()

    def test_is_full_true_when_exceeds_limit(self, tmp_path):
        cfg = FlightRecorderConfig(base_dir=str(tmp_path), max_segment_bytes=1)  # 1 byte
        w = open_segment(tmp_path, "run-test", 0, "GENESIS", cfg)
        w.append(_make_event(seq=0))
        assert w.is_full is True
        w.close()


class TestReadSegmentEvents:
    def test_reads_valid_jsonl(self, tmp_path):
        p = tmp_path / "events.jsonl"
        p.write_text('{"a": 1}\n{"b": 2}\n')
        events = read_segment_events(p)
        assert len(events) == 2

    def test_tolerates_corrupt_trailing_line(self, tmp_path):
        """Crash mid-write: last line is partial JSON — should be skipped."""
        p = tmp_path / "events.jsonl"
        p.write_text('{"a": 1}\n{"b": 2}\n{"c": incomplte...')
        events = read_segment_events(p)
        assert len(events) == 2  # Corrupt line skipped

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.jsonl"
        p.write_text("")
        assert read_segment_events(p) == []

    def test_missing_file_returns_empty(self, tmp_path):
        p = tmp_path / "nonexistent.jsonl"
        assert read_segment_events(p) == []

    def test_blank_lines_skipped(self, tmp_path):
        p = tmp_path / "events.jsonl"
        p.write_text('{"a": 1}\n\n\n{"b": 2}\n\n')
        events = read_segment_events(p)
        assert len(events) == 2
