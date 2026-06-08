"""B2P-09 / L-H1: run-scoped budget enforcement via ContextVar (wired at the run effect boundary)."""

from __future__ import annotations

import inspect
from decimal import Decimal

import pytest

from agent_runtime_cockpit.adapters._shared import budget_checkpoint
from agent_runtime_cockpit.budget import BudgetExceeded
from agent_runtime_cockpit.budget.runtime_context import (
    current_run_budget_enforcer,
    run_budget_scope,
)
from agent_runtime_cockpit.budget.schema import (
    BudgetCap,
    BudgetConfig,
    BudgetEnforcer,
    BudgetScope,
    BudgetState,
)


def _exhausted_enforcer() -> BudgetEnforcer:
    # An already-exhausted budget: prior SESSION spend recorded over a tiny cap, so even a
    # zero-cost pre-run check (current + 0 > cap) interrupts.
    state = BudgetState()
    state.session.add(Decimal("1.00"))
    return BudgetEnforcer(
        BudgetConfig(
            first_launch_confirmed=True,
            caps=[BudgetCap(scope=BudgetScope.SESSION, amount_usd=Decimal("0.000001"))],
        ),
        state,
    )


def test_default_scope_is_none_and_checkpoint_is_noop() -> None:
    assert current_run_budget_enforcer() is None
    # No scope active → budget_checkpoint(None, …) is a pure no-op (default runs unaffected).
    budget_checkpoint(
        None, Decimal("999"), provider_id="run:auto", run_active=False, workflow_active=False
    )


def test_run_budget_scope_blocks_exhausted_run_at_boundary() -> None:
    # With a run-budget scope holding an exhausted enforcer, the shared gate (called with no explicit
    # enforcer, as the executor does) resolves it from the ContextVar and raises — the run interrupt.
    with run_budget_scope(_exhausted_enforcer()):
        assert current_run_budget_enforcer() is not None
        with pytest.raises(BudgetExceeded):
            budget_checkpoint(
                None, Decimal("0"), provider_id="run:auto", run_active=False, workflow_active=False
            )
    # scope exits cleanly
    assert current_run_budget_enforcer() is None


def test_executor_run_path_calls_budget_checkpoint_at_boundary() -> None:
    # Lock the wiring: _execute_run gates the run via budget_checkpoint before the adapter runs.
    from agent_runtime_cockpit.tasks.executor import TaskExecutor

    src = inspect.getsource(TaskExecutor._execute_run)
    assert "budget_checkpoint(" in src
    assert src.index("budget_checkpoint(") < src.index("run_workflow(")  # gate precedes the effect
