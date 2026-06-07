"""Tests for Phase 12c: audit-log retention/rotation."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from agent_runtime_cockpit.mobile import apply_retention, rotate_if_oversized

T0 = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _write(path, entries):
    path.write_text("".join(json.dumps(e) + "\n" for e in entries), encoding="utf-8")


def test_prune_by_age(tmp_path) -> None:
    p = tmp_path / "audit.jsonl"
    _write(
        p,
        [
            {"id": "old", "logged_at": (T0 - timedelta(days=40)).isoformat()},
            {"id": "recent", "logged_at": (T0 - timedelta(days=1)).isoformat()},
        ],
    )
    summary = apply_retention(p, max_age_seconds=30 * 86400, now=T0)
    assert summary["removed"] == 1
    remaining = [json.loads(line) for line in p.read_text().splitlines()]
    assert [e["id"] for e in remaining] == ["recent"]


def test_prune_by_count_keeps_newest(tmp_path) -> None:
    p = tmp_path / "audit.jsonl"
    _write(p, [{"id": i, "logged_at": (T0 + timedelta(seconds=i)).isoformat()} for i in range(5)])
    apply_retention(p, max_entries=2, now=T0 + timedelta(days=1))
    remaining = [json.loads(line)["id"] for line in p.read_text().splitlines()]
    assert remaining == [3, 4]


def test_entries_without_timestamp_are_kept(tmp_path) -> None:
    p = tmp_path / "audit.jsonl"
    _write(p, [{"id": "no-ts"}, {"id": "old", "logged_at": (T0 - timedelta(days=99)).isoformat()}])
    apply_retention(p, max_age_seconds=86400, now=T0)
    remaining = [json.loads(line)["id"] for line in p.read_text().splitlines()]
    assert remaining == ["no-ts"]


def test_rotation_on_oversize(tmp_path) -> None:
    p = tmp_path / "audit.jsonl"
    p.write_text("x" * 5000, encoding="utf-8")
    assert rotate_if_oversized(p, max_bytes=1000) is True
    assert p.read_text() == ""  # fresh file
    assert (tmp_path / "audit.jsonl.1").read_text() == "x" * 5000
    # under cap -> no rotation
    assert rotate_if_oversized(p, max_bytes=1000) is False


def test_missing_file_is_noop(tmp_path) -> None:
    summary = apply_retention(tmp_path / "nope.jsonl", max_entries=10, now=T0)
    assert summary == {"before": 0, "after": 0, "removed": 0}
