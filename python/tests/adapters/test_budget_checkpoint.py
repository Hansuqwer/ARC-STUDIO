"""B2P-09a: shared adapter effect-boundary budget gate."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent_runtime_cockpit.adapters._shared import budget_checkpoint
from agent_runtime_cockpit.budget import BudgetExceeded


class _FakeEnforcer:
    def __init__(self, raise_exc: Exception | None = None) -> None:
        self.calls: list[tuple] = []
        self._raise = raise_exc

    def preflight(self, cost, *, provider_id, run_active, workflow_active) -> None:
        self.calls.append((cost, provider_id, run_active, workflow_active))
        if self._raise is not None:
            raise self._raise


def test_none_enforcer_is_noop() -> None:
    # Must not raise — adapters call it unconditionally; budget disabled => pass-through.
    budget_checkpoint(None, 1.23, provider_id="anthropic")


def test_delegates_to_preflight_with_decimal_cost() -> None:
    fake = _FakeEnforcer()
    budget_checkpoint(fake, 0.5, provider_id="openai", run_active=True, workflow_active=False)
    assert fake.calls == [(Decimal("0.5"), "openai", True, False)]


def test_exhaustion_interrupt_propagates() -> None:
    from agent_runtime_cockpit.budget import BudgetScope

    exc = BudgetExceeded(BudgetScope.RUN, Decimal("1"), Decimal("1"), Decimal("2"), None)
    fake = _FakeEnforcer(raise_exc=exc)
    with pytest.raises(BudgetExceeded):
        budget_checkpoint(fake, 5.0, provider_id="openai")


def test_real_enforcer_exhaustion_interrupt() -> None:
    """B2P-09b: with a REAL BudgetEnforcer over its cap, the shared gate raises BudgetExceeded."""
    from agent_runtime_cockpit.budget import BudgetConfig, BudgetEnforcer, BudgetState

    enforcer = BudgetEnforcer(BudgetConfig(first_launch_confirmed=True, caps=[]), BudgetState())
    # Drive any positive estimate over the cap (mirrors tests/unit/test_budget_preflight_estimator.py).
    enforcer._config.effective_cap = lambda *a, **kw: Decimal("0.000001")  # type: ignore[attr-defined]
    with pytest.raises(BudgetExceeded):
        budget_checkpoint(enforcer, 5.0, provider_id="anthropic")


def test_real_enforcer_under_cap_passes() -> None:
    from agent_runtime_cockpit.budget import BudgetConfig, BudgetEnforcer, BudgetState

    enforcer = BudgetEnforcer(BudgetConfig(first_launch_confirmed=True, caps=[]), BudgetState())
    enforcer._config.effective_cap = lambda *a, **kw: Decimal("1000")  # type: ignore[attr-defined]
    budget_checkpoint(enforcer, 0.001, provider_id="anthropic")  # must not raise
