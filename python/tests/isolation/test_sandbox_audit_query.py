"""Phase 33 tests: parse_relative_time, list_sandbox_audit_events time filters,
compact_sandbox_audit_events, and CLI audit-query command."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.security.sandbox import (
    compact_sandbox_audit_events,
    list_sandbox_audit_events,
    parse_relative_time,
    utc_now,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _make_event(
    started_at: str, classification: str = "read_only", provider: str = "subprocess"
) -> dict:
    return {
        "audit_id": f"sandbox-{started_at}",
        "type": "SANDBOX_COMMAND",
        "command": ["ls"],
        "cwd": "/workspace",
        "classification": classification,
        "decision": {
            "allowed": True,
            "classification": classification,
            "reason": "read-only command",
            "policy": "local-safe",
            "approval_required": False,
            "approved": False,
        },
        "policy": "local-safe",
        "provider": provider,
        "allowed": True,
        "reason": "read-only command",
        "started_at": started_at,
        "ended_at": started_at,
        "exit_code": 0,
        "stdout_truncated": False,
        "stderr_truncated": False,
        "redaction_applied": False,
    }


def _write_events(audit_dir: Path, events: list[dict]) -> None:
    audit_dir.mkdir(parents=True, exist_ok=True)
    events_path = audit_dir / "sandbox.events.jsonl"
    with events_path.open("w", encoding="utf-8") as fp:
        for event in events:
            fp.write(json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n")


# ---------------------------------------------------------------------------
# 1-5: parse_relative_time
# ---------------------------------------------------------------------------


def test_parse_relative_time_hours():
    """parse_relative_time('1h') returns a valid ISO string earlier than now."""
    now = datetime.now(timezone.utc)
    result = parse_relative_time("1h")
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    assert parsed < now
    diff = now - parsed
    # Should be approximately 1 hour (within ±5 seconds)
    assert 3590 <= diff.total_seconds() <= 3610


def test_parse_relative_time_minutes():
    """parse_relative_time('30m') returns a valid ISO string earlier than now."""
    now = datetime.now(timezone.utc)
    result = parse_relative_time("30m")
    assert result.endswith("Z") or "+" in result or result[-6] in "+-"
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    assert parsed < now
    diff = now - parsed
    assert 1790 <= diff.total_seconds() <= 1810


def test_parse_relative_time_days():
    """parse_relative_time('7d') returns a valid ISO string earlier than now."""
    now = datetime.now(timezone.utc)
    result = parse_relative_time("7d")
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    assert parsed < now
    diff = now - parsed
    # Approximately 7 days in seconds (604800 ±5s)
    assert 604790 <= diff.total_seconds() <= 604810


def test_parse_relative_time_iso_passthrough():
    """parse_relative_time with an ISO string returns it unchanged."""
    iso = "2026-01-01T00:00:00Z"
    assert parse_relative_time(iso) == iso


def test_parse_relative_time_now():
    """parse_relative_time('now') returns a current ISO string close to now."""
    now = datetime.now(timezone.utc)
    result = parse_relative_time("now")
    parsed = datetime.fromisoformat(result.replace("Z", "+00:00"))
    diff = abs((now - parsed).total_seconds())
    assert diff < 5


# ---------------------------------------------------------------------------
# 6-8: list_sandbox_audit_events time filters
# ---------------------------------------------------------------------------


def test_list_audit_events_since_filter(tmp_path):
    """since filter returns only events at or after the cutoff."""
    audit_dir = tmp_path / "audit"
    events = [
        _make_event("2026-01-01T00:00:00Z"),
        _make_event("2026-06-01T00:00:00Z"),
        _make_event("2026-12-01T00:00:00Z"),
    ]
    _write_events(audit_dir, events)

    result = list_sandbox_audit_events(audit_dir, since="2026-06-01T00:00:00Z", limit=-1)
    assert result["count"] == 2
    returned_ids = {e["audit_id"] for e in result["events"]}
    assert "sandbox-2026-06-01T00:00:00Z" in returned_ids
    assert "sandbox-2026-12-01T00:00:00Z" in returned_ids
    assert "sandbox-2026-01-01T00:00:00Z" not in returned_ids


def test_list_audit_events_until_filter(tmp_path):
    """until filter returns only events at or before the cutoff."""
    audit_dir = tmp_path / "audit"
    events = [
        _make_event("2026-01-01T00:00:00Z"),
        _make_event("2026-06-01T00:00:00Z"),
        _make_event("2026-12-01T00:00:00Z"),
    ]
    _write_events(audit_dir, events)

    result = list_sandbox_audit_events(audit_dir, until="2026-06-01T00:00:00Z", limit=-1)
    assert result["count"] == 2
    returned_ids = {e["audit_id"] for e in result["events"]}
    assert "sandbox-2026-01-01T00:00:00Z" in returned_ids
    assert "sandbox-2026-06-01T00:00:00Z" in returned_ids
    assert "sandbox-2026-12-01T00:00:00Z" not in returned_ids


def test_list_audit_events_since_and_until_range(tmp_path):
    """since and until together return only events in the given range."""
    audit_dir = tmp_path / "audit"
    events = [
        _make_event("2026-01-01T00:00:00Z"),
        _make_event("2026-03-01T00:00:00Z"),
        _make_event("2026-06-01T00:00:00Z"),
        _make_event("2026-12-01T00:00:00Z"),
    ]
    _write_events(audit_dir, events)

    result = list_sandbox_audit_events(
        audit_dir,
        since="2026-03-01T00:00:00Z",
        until="2026-06-01T00:00:00Z",
        limit=-1,
    )
    assert result["count"] == 2
    returned_ids = {e["audit_id"] for e in result["events"]}
    assert "sandbox-2026-03-01T00:00:00Z" in returned_ids
    assert "sandbox-2026-06-01T00:00:00Z" in returned_ids


# ---------------------------------------------------------------------------
# 9-11: compact_sandbox_audit_events
# ---------------------------------------------------------------------------


def test_compact_keep_newest(tmp_path):
    """compact with keep=2 on 5 events keeps the 2 newest."""
    audit_dir = tmp_path / "audit"
    events = [
        _make_event("2026-01-01T00:00:00Z"),
        _make_event("2026-02-01T00:00:00Z"),
        _make_event("2026-03-01T00:00:00Z"),
        _make_event("2026-04-01T00:00:00Z"),
        _make_event("2026-05-01T00:00:00Z"),
    ]
    _write_events(audit_dir, events)

    result = compact_sandbox_audit_events(keep=2, audit_dir=audit_dir)
    assert result["compacted"] == 3
    assert result["remaining"] == 2

    # Verify the file actually has 2 events (the newest two)
    events_path = audit_dir / "sandbox.events.jsonl"
    kept = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
    assert len(kept) == 2
    ids = {e["audit_id"] for e in kept}
    assert "sandbox-2026-04-01T00:00:00Z" in ids
    assert "sandbox-2026-05-01T00:00:00Z" in ids


def test_compact_before_prunes_older_events(tmp_path):
    """compact with before= removes events whose started_at < before."""
    audit_dir = tmp_path / "audit"
    events = [
        _make_event("2026-01-01T00:00:00Z"),
        _make_event("2026-03-01T00:00:00Z"),
        _make_event("2026-06-01T00:00:00Z"),
    ]
    _write_events(audit_dir, events)

    result = compact_sandbox_audit_events(before="2026-03-01T00:00:00Z", audit_dir=audit_dir)
    assert result["compacted"] == 1
    assert result["remaining"] == 2

    events_path = audit_dir / "sandbox.events.jsonl"
    kept = [json.loads(line) for line in events_path.read_text().splitlines() if line.strip()]
    ids = {e["audit_id"] for e in kept}
    assert "sandbox-2026-01-01T00:00:00Z" not in ids
    assert "sandbox-2026-03-01T00:00:00Z" in ids
    assert "sandbox-2026-06-01T00:00:00Z" in ids


def test_compact_missing_events_file(tmp_path):
    """compact on missing events file returns remaining=0, compacted=0."""
    audit_dir = tmp_path / "empty-audit"
    audit_dir.mkdir()

    result = compact_sandbox_audit_events(audit_dir=audit_dir)
    assert result["compacted"] == 0
    assert result["remaining"] == 0
    assert "events_path" in result


# ---------------------------------------------------------------------------
# 12: CLI audit-query outputs valid JSON with ok=true
# ---------------------------------------------------------------------------


def test_cli_audit_query_json_valid(tmp_path, monkeypatch):
    """arc sandbox audit-query --json --classification read_only outputs ok=true JSON."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ARC_SANDBOX_AUDIT_DIR", str(tmp_path / "audit"))

    # Write a couple of events so there's something to query
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir()
    event = _make_event(utc_now(), classification="read_only")
    (audit_dir / "sandbox.events.jsonl").write_text(
        json.dumps(event, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        [
            "sandbox",
            "audit-query",
            "--json",
            "--classification",
            "read_only",
        ],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert "events" in payload["data"]
    assert payload["data"]["count"] >= 1
    # All returned events must be read_only
    for ev in payload["data"]["events"]:
        assert ev["classification"] == "read_only"
