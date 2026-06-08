"""Shared helpers used by multiple runtime adapters."""

from __future__ import annotations

import sys
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator

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


def budget_checkpoint(
    enforcer: Any,
    estimated_cost_usd: Any,
    *,
    provider_id: str,
    run_active: bool = True,
    workflow_active: bool = True,
) -> None:
    """Shared adapter effect-boundary budget gate (B2P-09a).

    Adapters call this immediately before a cost-incurring effect. With a `BudgetEnforcer` present
    it runs `preflight`, which raises `BudgetExceeded` (real-time exhaustion interrupt) or
    `ConfirmationRequired`. A ``None`` enforcer is a no-op (budget disabled / fake-offline runs),
    so adapters can call it unconditionally at every effect boundary.
    """
    if enforcer is None:
        return
    cost = (
        estimated_cost_usd
        if isinstance(estimated_cost_usd, Decimal)
        else Decimal(str(estimated_cost_usd))
    )
    enforcer.preflight(
        cost,
        provider_id=provider_id,
        run_active=run_active,
        workflow_active=workflow_active,
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
