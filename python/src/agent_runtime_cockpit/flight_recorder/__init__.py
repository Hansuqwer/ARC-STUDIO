"""Local Agent Flight Recorder — always-on, local-first, bounded, crash-safe.

Public surface:
    FlightRecorder   — primary recorder object
    FlightEvent      — immutable typed event
    FlightSegment    — segment metadata
    FlightIndex      — cross-run index
    FlightRecorderConfig — configuration

Event types defined in models.py.
Storage layer in segments.py + index.py.
Redaction in redaction.py.
Verification in verify.py.
Retention in retention.py.
Export bundle in export.py.

Hard constraints (enforced here and in each submodule):
- No network I/O.
- No subprocess / process execution.
- No model calls.
- No MCP server startup.
- No unauthenticated local server.
- Redaction before persistence.
- Fail closed on malformed sensitive records.
- Bounded retention enforced.
- Segment files are crash-safe (append-only JSONL + atomic meta).
"""

from __future__ import annotations

from .models import (
    SCHEMA_VERSION,
    EventType,
    FlightEvent,
    FlightExportBundle,
    FlightIndex,
    FlightRecorderConfig,
    FlightSegment,
    FlightVerificationReport,
    RedactionSummary,
    RetentionPolicy,
    RunEntry,
    SegmentRef,
)
from .recorder import FlightRecorder

__all__ = [
    "SCHEMA_VERSION",
    "EventType",
    "FlightEvent",
    "FlightExportBundle",
    "FlightIndex",
    "FlightRecorder",
    "FlightRecorderConfig",
    "FlightSegment",
    "FlightVerificationReport",
    "RedactionSummary",
    "RetentionPolicy",
    "RunEntry",
    "SegmentRef",
]
