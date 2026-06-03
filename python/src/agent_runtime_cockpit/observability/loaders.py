"""Load ARC trace artifacts for observability export.

Supports:
- JSONL file path (--trace-file): parse line-by-line, tolerating corrupt lines
- RunRecord from storage (if workspace set)
- Optional IR JSON, policy JSON

Never executes, never calls models, never opens network connections.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)


class LoadedTrace(BaseModel):
    run_id: Optional[str] = None
    workflow_id: Optional[str] = None
    runtime: Optional[str] = None
    status: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    events: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}
    skipped_lines: int = 0
    source_file: Optional[str] = None


def load_trace_file(path: str | Path) -> LoadedTrace:
    """Load a JSONL trace file. Tolerates partial/corrupt lines with a warning.

    The file may be:
    - A RunRecord as JSON on the first line (storage/jsonl.py format)
    - Raw RunEvents as one JSON object per line
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Trace file not found: {path}")

    lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
    if not lines:
        return LoadedTrace(source_file=str(p))

    skipped = 0
    # Try first line as RunRecord
    try:
        first = json.loads(lines[0])
        if "events" in first and "id" in first:
            # It's a RunRecord
            events = [e for e in first.get("events", []) if isinstance(e, dict)]
            return LoadedTrace(
                run_id=first.get("id"),
                workflow_id=first.get("workflow_id"),
                runtime=first.get("runtime"),
                status=first.get("status"),
                started_at=first.get("started_at"),
                ended_at=first.get("ended_at"),
                events=events,
                metadata=first.get("metadata") or {},
                source_file=str(p),
            )
    except (json.JSONDecodeError, KeyError):
        pass

    # Fall back: each line is a RunEvent
    events: list[dict[str, Any]] = []
    run_id: Optional[str] = None
    for i, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
            if isinstance(obj, dict):
                if run_id is None:
                    run_id = obj.get("run_id")
                events.append(obj)
        except json.JSONDecodeError:
            log.warning("Skipping corrupt JSONL line %d in %s", i + 1, p.name)
            skipped += 1

    return LoadedTrace(
        run_id=run_id,
        events=events,
        skipped_lines=skipped,
        source_file=str(p),
    )


def load_ir_json(path: str | Path) -> Optional[dict[str, Any]]:
    """Load an IR graph JSON file. Returns None on error."""
    try:
        return json.loads(Path(path).read_text())
    except Exception as exc:
        log.warning("Could not load IR JSON %s: %s", path, exc)
        return None


def load_policy_json(path: str | Path) -> Optional[dict[str, Any]]:
    """Load a policy report JSON file. Returns None on error."""
    try:
        return json.loads(Path(path).read_text())
    except Exception as exc:
        log.warning("Could not load policy JSON %s: %s", path, exc)
        return None
