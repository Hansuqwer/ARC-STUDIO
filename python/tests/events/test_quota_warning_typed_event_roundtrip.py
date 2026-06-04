"""Protocol round-trip tests for QUOTA_WARNING typed event."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.protocol.typed_events import (
    QuotaWarningEvent,
    is_known_event,
    parse_typed_event,
)


def _raw(usage_pct: float = 0.85) -> dict:
    return {
        "schema_version": 2,
        "type": "QUOTA_WARNING",
        "timestamp": "2026-01-01T00:00:00Z",
        "run_id": "r-1",
        "sequence": 1,
        "data": {"dimension": "session", "usage_pct": usage_pct, "limit": 10.0, "current": 8.5},
    }


def test_quota_warning_round_trip() -> None:
    event = QuotaWarningEvent.model_validate(_raw())
    assert event.type == "QUOTA_WARNING"
    assert event.data.dimension == "session"
    assert event.data.usage_pct == pytest.approx(0.85)


def test_quota_warning_parse_typed_event() -> None:
    event = parse_typed_event(_raw())
    assert is_known_event(event)
    assert event.type == "QUOTA_WARNING"


def test_quota_warning_legacy_extra_fields_ignored() -> None:
    """extra='ignore' forward-compat: unknown fields don't raise."""
    raw = _raw()
    raw["data"]["future_field"] = "ignored"
    event = QuotaWarningEvent.model_validate(raw)
    assert event.data.dimension == "session"
