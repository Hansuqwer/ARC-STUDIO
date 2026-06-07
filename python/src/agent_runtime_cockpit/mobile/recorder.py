"""Append-only trace recorder for mobile simulator events.

Timestamps use wall-clock UTC by default. Pass ``deterministic=True`` to
``events_from_report()`` / ``build_trace()`` for reproducible test output
(fixes timestamp to 2026-01-01T00:00:00Z).

Tamper-evident chain: each event carries ``prev_event_hash`` — the
``event_hash`` of the preceding event, or ``"0" * 64`` for the first event.
This means reordering or deleting events is detectable by ``verify_trace()``.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .hashing import _hash
from .models import MOBILE_SCHEMA_VERSION, MobileActionSimulationReport

_DETERMINISTIC_TS = "2026-01-01T00:00:00Z"
_ZERO_HASH = "0" * 64


class MobileRuntimeEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = MOBILE_SCHEMA_VERSION
    event_id: str
    event_type: str
    plan_id: str
    step_id: str | None = None
    capability_id: str | None = None
    timestamp: str
    sequence: int
    allowed: bool
    mock: bool = True
    payload_hash: str
    prev_event_hash: str = _ZERO_HASH  # hash of preceding event; _ZERO_HASH for first
    prev_event_hash: str = "0" * 64  # PR17: SHA-256 of preceding event; zeros for first
    event_hash: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)


class MobileTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: int = MOBILE_SCHEMA_VERSION
    plan_id: str
    events: list[MobileRuntimeEvent] = Field(default_factory=list)
    trace_hash: str = ""


def event_hash(event: MobileRuntimeEvent) -> str:
    data = event.model_dump(mode="json")
    data.pop("event_hash", None)
    return _hash(data)


def trace_hash(events: list[MobileRuntimeEvent]) -> str:
    return _hash([event.event_hash for event in events])


def verify_trace(trace: MobileTrace) -> tuple[bool, str]:
    """Verify the prev_event_hash chain and event_hashes.

    Returns (ok, message). ok=False means the trace has been tampered with.
    """
    prev_hash = _ZERO_HASH
    for event in trace.events:
        # Check prev_event_hash
        if event.prev_event_hash != prev_hash:
            return (
                False,
                f"Chain broken at sequence {event.sequence}: "
                f"expected prev_hash={prev_hash!r}, got {event.prev_event_hash!r}",
            )
        # Check event_hash
        recomputed = event_hash(event)
        if recomputed != event.event_hash:
            return (
                False,
                f"Event hash mismatch at sequence {event.sequence}: "
                f"expected {recomputed!r}, stored {event.event_hash!r}",
            )
        prev_hash = event.event_hash

    # Check trace_hash
    expected_trace_hash = trace_hash(trace.events)
    if trace.trace_hash and trace.trace_hash != expected_trace_hash:
        return False, f"Trace hash mismatch: expected {expected_trace_hash!r}"

    return True, "ok"


def events_from_report(
    report: MobileActionSimulationReport,
    *,
    deterministic: bool = False,
) -> list[MobileRuntimeEvent]:
    if deterministic:
        timestamp = _DETERMINISTIC_TS
    else:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    events: list[MobileRuntimeEvent] = []
    prev_hash = _ZERO_HASH

    for index, step in enumerate(report.steps):
        payload = {
            "plan_id": report.plan_id,
            "step_id": step.step_id,
            "capability_id": step.capability_id,
            "allowed": step.allowed,
            "mock": step.mock,
            "blocked_reason": step.blocked_reason,
            "predicted_permissions": step.predicted_permissions,
            "predicted_approvals": step.predicted_approvals,
        }
        event = MobileRuntimeEvent(
            event_id=f"evt-{report.plan_id}-{index:04d}",
            event_type="mobile.step.simulated",
            plan_id=report.plan_id,
            step_id=step.step_id,
            capability_id=step.capability_id,
            timestamp=timestamp,
            sequence=index,
            allowed=step.allowed,
            mock=step.mock,
            payload_hash=_hash(payload),
            prev_event_hash=prev_hash,
            metadata={"risk_level": report.risk_level},
        )
        event.event_hash = event_hash(event)
        prev_hash = event.event_hash
        events.append(event)
    return events


def build_trace(
    report: MobileActionSimulationReport,
    *,
    deterministic: bool = False,
) -> MobileTrace:
    events = events_from_report(report, deterministic=deterministic)
    return MobileTrace(plan_id=report.plan_id, events=events, trace_hash=trace_hash(events))


def append_trace(path: str | Path, trace: MobileTrace) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8") as handle:
        for event in trace.events:
            handle.write(json.dumps(event.model_dump(mode="json"), sort_keys=True) + "\n")
    return target


def read_trace(path: str | Path) -> MobileTrace:
    events = []
    plan_id = ""
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        event = MobileRuntimeEvent.model_validate(json.loads(line))
        events.append(event)
        plan_id = event.plan_id
    return MobileTrace(plan_id=plan_id, events=events, trace_hash=trace_hash(events))
