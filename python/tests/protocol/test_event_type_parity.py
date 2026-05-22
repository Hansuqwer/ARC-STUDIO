"""Regression guard for P1. Capture the event type parity between Python and fixtures."""
from __future__ import annotations

import json
from pathlib import Path

from agent_runtime_cockpit.protocol.events import EVENT_TYPES

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "protocol" / "fixtures" / "run-event"


def test_every_fixture_event_type_is_a_known_python_event_type() -> None:
    """Verify that every fixture references a known Python event type."""
    known = set(EVENT_TYPES.keys())
    missing: list[str] = []
    
    for fixture_path in FIXTURE_DIR.glob("*.json"):
        payload = json.loads(fixture_path.read_text())
        event_type = payload.get("type")
        
        if event_type not in known:
            missing.append(f"{fixture_path.name}: {event_type}")
    
    assert missing == [], f"Fixtures reference unknown Python event types: {missing}"
