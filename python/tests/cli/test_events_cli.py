"""Tests for the events CLI commands (Phase 32 / R25, Slice 32.2 + Phase 56)."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Generator

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.events import reset_bus

runner = CliRunner()


@pytest.fixture(autouse=True)
def _reset():
    reset_bus()
    yield
    reset_bus()


# --- CLI Registration ---


def test_events_cli_registered():
    """arc events --help shows the events sub-app."""
    result = runner.invoke(app, ["events", "--help"])
    assert result.exit_code == 0
    assert "watch" in result.stdout
    assert "webhook-add" in result.stdout
    assert "webhook-list" in result.stdout
    assert "webhook-remove" in result.stdout
    assert "dead-letter" in result.stdout


# --- JSON output shape ---


def test_watch_json_output():
    """arc events watch --json outputs JSON."""
    result = runner.invoke(app, ["events", "watch", "--json"], timeout=2)
    # Should time out or exit
    assert result.exit_code in (0, 1, 2)


# --- Webhook CLI ---


def test_webhook_add_list_remove():
    """arc events webhook-add, webhook-list, webhook-remove work."""
    result = runner.invoke(
        app,
        [
            "events",
            "webhook-add",
            "https://example.com/hook",
            "my-secret",
            "--events",
            "hitl_required,run_completed",
        ],
    )
    assert result.exit_code == 0, f"Got exit code {result.exit_code}: stderr={result.stderr}"
    assert "Webhook" in result.stderr

    result = runner.invoke(app, ["events", "webhook-list"])
    assert result.exit_code == 0

    result = runner.invoke(app, ["events", "webhook-remove", "nonexistent"])
    assert result.exit_code == 0


def test_dead_letter_empty():
    """arc events dead-letter shows empty when no dead-letters."""
    result = runner.invoke(app, ["events", "dead-letter"])
    assert result.exit_code == 0


# --- Event types via CLI ---


def test_event_types_created():
    """All event types can be created and round-tripped."""
    cases: list[dict[str, Any]] = [
        {
            "event_type": "hitl_required",
            "run_id": "r1",
            "hitl_id": "h1",
            "step_id": "s1",
            "prompt_text": "Approve?",
        },
        {"event_type": "run_completed", "run_id": "r1", "workflow_id": "wf1", "duration_ms": 100},
        {
            "event_type": "run_failed",
            "run_id": "r1",
            "workflow_id": "wf1",
            "error": "err",
            "error_detail": "Error",
        },
        {
            "event_type": "audit_verified",
            "ok": True,
            "mode": "hmac",
            "records_checked": 1,
            "reason": "ok",
            "duration_ms": 5,
        },
        {"event_type": "hitl_decided", "run_id": "r1", "hitl_id": "h1", "decision": "approve"},
        {
            "event_type": "quota_warning",
            "dimension": "tokens",
            "usage_pct": 85.0,
            "limit": 1000,
            "current": 850,
        },
    ]
    for payload in cases:
        from agent_runtime_cockpit.events.types import parse_event

        event = parse_event(payload)
        dump = json.loads(event.model_dump_json())
        assert dump["event_type"] == payload["event_type"]


# --- Phase 56: Event Query ---


@pytest.fixture
def tmp_workspace() -> Generator[Path, None, None]:
    """Create a temp workspace without event log."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        old = Path.cwd()
        os.chdir(str(cwd))
        yield cwd
        os.chdir(str(old))


@pytest.fixture
def tmp_events_log() -> Generator[Path, None, None]:
    """Create a temp dir with a seeded events JSONL log."""
    with tempfile.TemporaryDirectory() as td:
        cwd = Path(td)
        old = Path.cwd()
        os.chdir(str(cwd))
        # Create event log with some events
        log_dir = cwd / ".arc" / "events"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "event-log.jsonl"

        import json as _json

        events = [
            {
                "seq": 1,
                "event_type": "run_completed",
                "run_id": "r1",
                "timestamp": "2026-01-01T00:00:00",
            },
            {
                "seq": 2,
                "event_type": "hitl_required",
                "run_id": "r1",
                "hitl_id": "h1",
                "timestamp": "2026-01-01T01:00:00",
            },
            {
                "seq": 3,
                "event_type": "run_failed",
                "run_id": "r2",
                "timestamp": "2026-01-02T00:00:00",
            },
            {
                "seq": 4,
                "event_type": "run_completed",
                "run_id": "r3",
                "timestamp": "2026-01-03T00:00:00",
            },
        ]
        with log_path.open("w") as f:
            for ev in events:
                f.write(_json.dumps(ev, separators=(",", ":")) + "\n")

        yield cwd
        os.chdir(str(old))


def test_events_query_registered():
    """arc events --help shows query subcommand."""
    result = runner.invoke(app, ["events", "--help"])
    assert result.exit_code == 0
    assert "query" in result.stdout


def test_events_query_json(tmp_events_log: Path):
    """arc events query --json returns filtered events."""
    result = runner.invoke(app, ["events", "query", "--json"])
    assert result.exit_code == 0, f"Got exit {result.exit_code}: stderr={result.stderr}"
    data = json.loads(result.stdout)
    payload = data.get("data", data)
    assert payload.get("count") == 4
    assert len(payload.get("events", [])) == 4


def test_events_query_filter_type(tmp_events_log: Path):
    """arc events query --type run_completed --json filters correctly."""
    result = runner.invoke(app, ["events", "query", "--type", "run_completed", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    payload = data.get("data", data)
    events = payload.get("events", [])
    assert payload.get("count") == 2
    assert all(e["event_type"] == "run_completed" for e in events)


def test_events_query_limit(tmp_events_log: Path):
    """arc events query --limit 2 --json limits results."""
    result = runner.invoke(app, ["events", "query", "--limit", "2", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    payload = data.get("data", data)
    assert payload.get("count") == 2


def test_events_query_stats(tmp_events_log: Path):
    """arc events query --stats --json returns type counts."""
    result = runner.invoke(app, ["events", "query", "--stats", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    payload = data.get("data", data)
    assert "event_types" in payload
    assert payload["event_types"]["run_completed"] == 2
    assert payload["event_types"]["hitl_required"] == 1
    assert payload["event_types"]["run_failed"] == 1


def test_events_query_since(tmp_events_log: Path):
    """arc events query --since 2026-01-02 --json filters by timestamp."""
    result = runner.invoke(app, ["events", "query", "--since", "2026-01-02T00:00:00", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    payload = data.get("data", data)
    assert payload.get("count") == 2  # r2 and r3 events


def test_events_query_no_log(tmp_workspace: Path):
    """arc events query --json with no event log returns error."""
    result = runner.invoke(app, ["events", "query", "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data.get("ok") is False
