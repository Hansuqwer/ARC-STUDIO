"""Append-only trace recorder for mobile simulator events."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .hashing import _hash
from .models import MOBILE_SCHEMA_VERSION, MobileActionSimulationReport


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


def events_from_report(report: MobileActionSimulationReport) -> list[MobileRuntimeEvent]:
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")
    events: list[MobileRuntimeEvent] = []
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
            metadata={"risk_level": report.risk_level},
        )
        event.event_hash = event_hash(event)
        events.append(event)
    return events


def build_trace(report: MobileActionSimulationReport) -> MobileTrace:
    events = events_from_report(report)
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
