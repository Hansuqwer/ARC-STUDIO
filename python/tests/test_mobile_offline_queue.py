"""Tests for T6 (Phase 8): OfflineQueue — durable, TTL/retention, hash-only."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from agent_runtime_cockpit.mobile import OfflineQueue, QueueEntry

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_enqueue_is_hash_only() -> None:
    q = OfflineQueue()
    e = q.enqueue("device.camera.capture.mock", {"secret": "RAW-PAYLOAD-XYZ"}, now=T0)
    assert isinstance(e, QueueEntry)
    assert e.payload_hash and len(e.payload_hash) == 64
    # no raw payload retained on the entry
    assert "RAW-PAYLOAD-XYZ" not in str(e.as_dict())


def test_no_raw_payload_at_rest(tmp_path) -> None:
    path = tmp_path / "q.json"
    q = OfflineQueue(path=path)
    q.enqueue("app.memory.write.mock", {"secret": "DO-NOT-PERSIST-RAW"}, now=T0)
    raw = path.read_text(encoding="utf-8")
    assert "DO-NOT-PERSIST-RAW" not in raw
    assert "payload_hash" in raw


def test_durable_reload(tmp_path) -> None:
    path = tmp_path / "q.json"
    q = OfflineQueue(path=path)
    q.enqueue("a", {"x": 1}, now=T0)
    q.enqueue("b", {"y": 2}, now=T0)
    reloaded = OfflineQueue(path=path)
    assert len(reloaded) == 2


def test_ttl_expiry_deterministic() -> None:
    q = OfflineQueue()
    q.enqueue("a", {"x": 1}, ttl_seconds=60, now=T0)
    q.enqueue("b", {"y": 2}, ttl_seconds=600, now=T0)
    later = T0 + timedelta(seconds=120)
    assert q.gc(now=later) == 1  # first entry expired
    assert len(q) == 1
    assert q.pending(now=later)[0].capability_id == "b"


def test_flush_drops_expired_returns_ready() -> None:
    q = OfflineQueue()
    q.enqueue("a", {"x": 1}, ttl_seconds=60, now=T0)
    q.enqueue("b", {"y": 2}, ttl_seconds=600, now=T0)
    ready = q.flush(now=T0 + timedelta(seconds=120))
    assert [e.capability_id for e in ready] == ["b"]
    assert len(q) == 0


def test_bounded_retention_fifo_eviction() -> None:
    q = OfflineQueue(max_entries=3)
    for i in range(5):
        q.enqueue(f"cap{i}", {"i": i}, now=T0)
    assert len(q) == 3
    assert [e.capability_id for e in q.pending(now=T0)] == ["cap2", "cap3", "cap4"]


def test_integrity_verify() -> None:
    q = OfflineQueue()
    payload = {"k": "v", "n": 7}
    e = q.enqueue("a", payload, now=T0)
    assert q.verify(e, payload) is True
    assert q.verify(e, {"k": "v", "n": 8}) is False
