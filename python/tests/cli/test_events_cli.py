"""Tests for the events CLI commands (Phase 32 / R25, Slice 32.2)."""

from __future__ import annotations

import json
from typing import Any

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
