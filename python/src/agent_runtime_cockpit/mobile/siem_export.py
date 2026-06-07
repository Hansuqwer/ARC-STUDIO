"""SIEM export for ARC Mobile Runtime traces (Phase 12).

Renders a tamper-evident MobileTrace to SIEM-ingestable formats:
- **CEF** (ArcSight Common Event Format) — one event per line.
- **JSON** — structured records with trace metadata.

Redaction is preserved by construction: events carry ``payload_hash`` (never raw payloads),
and event ``metadata`` is exported as sorted KEY NAMES only (values are never emitted), so
no secret material leaves the device. Deterministic + offline (no network).
"""

from __future__ import annotations

import json
from typing import Any

from .recorder import MobileRuntimeEvent, MobileTrace

CEF_VERSION = 0
CEF_VENDOR = "ARC"
CEF_PRODUCT = "MobileRuntime"

# Severity 0-10: a denial is more interesting to a SOC than an allowed mock action.
_SEV_DENY = 7
_SEV_ALLOW = 3


def _cef_escape_header(value: str) -> str:
    return value.replace("\\", "\\\\").replace("|", "\\|")


def _cef_escape_ext(value: str) -> str:
    return value.replace("\\", "\\\\").replace("=", "\\=").replace("\n", "\\n")


def _metadata_keys(event: MobileRuntimeEvent) -> str:
    """Key names only — never metadata values (redaction)."""
    return ",".join(sorted(event.metadata.keys()))


def event_to_cef(event: MobileRuntimeEvent) -> str:
    """Render one event as a CEF line (payload hash-only; metadata keys only)."""
    severity = _SEV_ALLOW if event.allowed else _SEV_DENY
    header = "|".join(
        [
            f"CEF:{CEF_VERSION}",
            _cef_escape_header(CEF_VENDOR),
            _cef_escape_header(CEF_PRODUCT),
            _cef_escape_header(str(event.schema_version)),
            _cef_escape_header(event.event_type),
            _cef_escape_header(event.event_type),
            str(severity),
        ]
    )
    ext_pairs: list[tuple[str, str]] = [
        ("rt", event.timestamp),
        ("externalId", event.event_id),
        ("act", "allowed" if event.allowed else "denied"),
        ("cn1Label", "sequence"),
        ("cn1", str(event.sequence)),
        ("cs1Label", "planId"),
        ("cs1", event.plan_id),
        ("cs2Label", "capabilityId"),
        ("cs2", event.capability_id or ""),
        ("cs3Label", "payloadHash"),
        ("cs3", event.payload_hash),
        ("cs4Label", "eventHash"),
        ("cs4", event.event_hash),
        ("cs5Label", "prevEventHash"),
        ("cs5", event.prev_event_hash),
        ("cs6Label", "metadataKeys"),
        ("cs6", _metadata_keys(event)),
        ("arcMock", str(event.mock).lower()),
    ]
    extension = " ".join(f"{k}={_cef_escape_ext(v)}" for k, v in ext_pairs)
    return f"{header}|{extension}"


def export_trace_cef(trace: MobileTrace) -> str:
    """Export an entire trace as newline-joined CEF lines (deterministic, sequence order)."""
    events = sorted(trace.events, key=lambda e: e.sequence)
    return "\n".join(event_to_cef(e) for e in events)


def export_trace_json(trace: MobileTrace) -> dict[str, Any]:
    """Export a trace as a structured JSON record (payloads hash-only, metadata keys only)."""
    events = sorted(trace.events, key=lambda e: e.sequence)
    return {
        "format": "arc-mobile-siem/1",
        "simulator_preview": True,
        "plan_id": trace.plan_id,
        "trace_hash": trace.trace_hash,
        "event_count": len(events),
        "events": [
            {
                "event_id": e.event_id,
                "event_type": e.event_type,
                "timestamp": e.timestamp,
                "sequence": e.sequence,
                "plan_id": e.plan_id,
                "capability_id": e.capability_id,
                "allowed": e.allowed,
                "mock": e.mock,
                "payload_hash": e.payload_hash,
                "event_hash": e.event_hash,
                "prev_event_hash": e.prev_event_hash,
                "metadata_keys": sorted(e.metadata.keys()),
            }
            for e in events
        ],
    }


def export_trace(trace: MobileTrace, fmt: str = "json") -> str:
    """Export a trace as a string in the given format ('cef' or 'json')."""
    fmt = fmt.lower()
    if fmt == "cef":
        return export_trace_cef(trace)
    if fmt == "json":
        return json.dumps(export_trace_json(trace), sort_keys=True, indent=2)
    raise ValueError(f"unknown SIEM format {fmt!r}; expected 'cef' or 'json'")
