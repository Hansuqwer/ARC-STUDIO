"""Regression guard for P1. Capture the event type parity between Python and fixtures."""

from __future__ import annotations

import json
import re
from pathlib import Path

from agent_runtime_cockpit.protocol.event_envelope import ArcEnvelope
from agent_runtime_cockpit.protocol.events import EVENT_TYPES
from agent_runtime_cockpit.schemas.audit_events import AuditEventType

FIXTURE_DIR = Path(__file__).resolve().parents[3] / "protocol" / "fixtures" / "run-event"
REPO_ROOT = Path(__file__).resolve().parents[3]
TS_PROTOCOL_SRC = REPO_ROOT / "packages" / "arc-protocol-ts" / "src"


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


def test_typed_ts_run_event_types_are_known_python_event_types() -> None:
    source = (TS_PROTOCOL_SRC / "run-events.ts").read_text(encoding="utf-8")
    block = re.search(r"export const KNOWN_RUN_EVENT_TYPES = \[(.*?)\] as const", source, re.S)
    assert block is not None
    ts_types = set(re.findall(r"'([A-Z_]+)'", block.group(1)))
    py_types = set(EVENT_TYPES)
    assert ts_types <= py_types | {"RAW"}


def test_audit_event_discriminators_match_typescript() -> None:
    source = (TS_PROTOCOL_SRC / "audit-events.ts").read_text(encoding="utf-8")
    ts_types = set(re.findall(r"'([A-Z_]+)'", source.split("export type AuditEventSeverity")[0]))
    py_types = {item.value for item in AuditEventType}
    assert ts_types == py_types


def test_envelope_required_fields_match_typescript() -> None:
    source = (TS_PROTOCOL_SRC / "arc-protocol-types.ts").read_text(encoding="utf-8")
    block = re.search(r"export interface ArcEnvelope.*?\{(.*?)\n\}", source, re.S)
    assert block is not None
    ts_fields = {
        match.group(1) for match in re.finditer(r"^\s+([a-zA-Z_]+):", block.group(1), re.M)
    }
    assert ts_fields == set(ArcEnvelope.model_fields)
