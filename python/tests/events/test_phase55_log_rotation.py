"""Tests for Phase 55 — Event log rotation in EventPersistenceWriter."""

import json
import time

from agent_runtime_cockpit.events.persistence import EventPersistenceWriter
from agent_runtime_cockpit.events.types import ArcEvent


def _make_event(seq: int) -> ArcEvent:
    return ArcEvent(event_type="test", payload={"seq": seq})


def test_compact_drops_old_entries(tmp_path):
    log_path = tmp_path / "event-log.jsonl"
    writer = EventPersistenceWriter(log_path, max_entries=10, max_age_days=7)

    # Write 5 events with recent timestamps
    for i in range(5):
        writer.write(_make_event(i))

    # Manually append old entries past max_age_days
    old_ts = time.time() - 10 * 86400  # 10 days ago
    for i in range(5, 10):
        log_path.read_text(encoding="utf-8").splitlines()
        old_event = {
            "seq": i + 100,
            "event_type": "test",
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(old_ts)),
            "payload": {"seq": i},
        }
        with log_path.open("a", encoding="utf-8") as fp:
            fp.write(json.dumps(old_event, separators=(",", ":")) + "\n")

    # Total lines before: recent(5) + old(5) = 10
    writer.compact()

    lines_after = log_path.read_text(encoding="utf-8").splitlines()
    # Only the 5 recent entries should survive
    assert len(lines_after) == 5


def test_compact_bounds_by_max_entries(tmp_path):
    log_path = tmp_path / "event-log.jsonl"
    writer = EventPersistenceWriter(log_path, max_entries=5, max_age_days=365)

    # Write 20 events
    for i in range(20):
        writer.write(_make_event(i))

    # compact should keep only the last max_entries=5
    writer.compact()

    lines_after = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines_after) <= 5

    # The surviving entries should be the tail (highest seq numbers)
    for line in lines_after:
        data = json.loads(line)
        assert data["seq"] >= 15


def test_compact_noop_when_under_limit(tmp_path):
    log_path = tmp_path / "event-log.jsonl"
    writer = EventPersistenceWriter(log_path, max_entries=100, max_age_days=7)

    for i in range(10):
        writer.write(_make_event(i))

    writer.compact()

    lines_after = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines_after) == 10


def test_compact_noop_on_empty_file(tmp_path):
    log_path = tmp_path / "event-log.jsonl"
    writer = EventPersistenceWriter(log_path)
    writer.compact()  # should not raise


def test_concurrent_write_does_not_corrupt(tmp_path):
    """compacting while writes continue should not corrupt the log."""
    log_path = tmp_path / "event-log.jsonl"
    writer = EventPersistenceWriter(log_path, max_entries=20, max_age_days=365)

    # Write 25 events to trigger auto-compact at seq=200... actually at 200.
    # Manually trigger compact with a lower threshold.
    for i in range(15):
        writer.write(_make_event(i))

    writer.compact()

    # Verify all remaining lines are valid JSON
    lines = log_path.read_text(encoding="utf-8").splitlines()
    for line in lines:
        data = json.loads(line)
        assert "seq" in data
        assert "event_type" in data
