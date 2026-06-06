"""Shared helpers used by multiple runtime adapters."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator

from ..protocol.schemas import RunEvent


def make_event(run_id: str, sequence: int, event_type: str, data: dict) -> RunEvent:
    """Construct a RunEvent with the current UTC timestamp."""
    return RunEvent(
        type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        run_id=run_id,
        sequence=sequence,
        data=data,
    )


@contextmanager
def workspace_import_path(workspace: Path) -> Iterator[None]:
    """Temporarily add workspace (and workspace/src) to sys.path."""
    added: list[str] = []
    for candidate in (workspace, workspace / "src"):
        if candidate.exists():
            value = str(candidate.resolve())
            if value not in sys.path:
                sys.path.insert(0, value)
                added.append(value)
    try:
        yield
    finally:
        for value in added:
            try:
                sys.path.remove(value)
            except ValueError:
                pass
