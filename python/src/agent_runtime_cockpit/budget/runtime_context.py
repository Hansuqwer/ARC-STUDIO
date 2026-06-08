"""Run-scoped budget enforcer context (B2P-09 / L-H1).

Routes an optional ``BudgetEnforcer`` to effect boundaries via a ``ContextVar`` — never by mutating
the frozen ``EnforcementContext`` or threading the enforcer through trace-serialized adapter params
(the two reasons per-effect budget enforcement was previously unwired). The default is ``None`` (no
enforcement), so normal runs are unaffected; a caller opts in with ``run_budget_scope(enforcer)``.

``adapters._shared.budget_checkpoint`` reads this when no explicit enforcer is passed, giving the
shared gate a real caller at the run effect boundary (see ``tasks.executor._execute_run``).
"""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import TYPE_CHECKING, Iterator, Optional

if TYPE_CHECKING:
    from .schema import BudgetEnforcer

_run_budget_enforcer: ContextVar[Optional["BudgetEnforcer"]] = ContextVar(
    "arc_run_budget_enforcer", default=None
)


def current_run_budget_enforcer() -> Optional["BudgetEnforcer"]:
    """Return the run-scoped budget enforcer, or ``None`` when budget enforcement is not active."""
    return _run_budget_enforcer.get()


@contextmanager
def run_budget_scope(enforcer: Optional["BudgetEnforcer"]) -> Iterator[None]:
    """Activate ``enforcer`` for the duration of the block (immutable; reset on exit)."""
    token = _run_budget_enforcer.set(enforcer)
    try:
        yield
    finally:
        _run_budget_enforcer.reset(token)
