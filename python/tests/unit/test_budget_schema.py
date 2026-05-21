from __future__ import annotations

from decimal import Decimal

import pytest

from agent_runtime_cockpit.budget import (
    BudgetCap,
    BudgetConfig,
    BudgetEnforcer,
    BudgetExceeded,
    BudgetScope,
    BudgetState,
    ConfirmationRequired,
)


def test_provider_day_cap_requires_provider_id() -> None:
    with pytest.raises(ValueError, match="provider_id"):
        BudgetCap(scope=BudgetScope.PROVIDER_DAY, amount_usd=Decimal("1"))
    with pytest.raises(ValueError, match="provider_id"):
        BudgetCap(scope=BudgetScope.RUN, amount_usd=Decimal("1"), provider_id="anthropic")


def test_first_launch_session_cap_is_one_dollar() -> None:
    config = BudgetConfig()
    assert config.effective_cap(BudgetScope.SESSION) == Decimal("1.00")


def test_preflight_blocks_when_run_cap_would_be_exceeded() -> None:
    config = BudgetConfig(
        first_launch_confirmed=True,
        caps=[BudgetCap(scope=BudgetScope.RUN, amount_usd=Decimal("0.10"))],
    )
    state = BudgetState()
    state.begin_run()
    enforcer = BudgetEnforcer(config, state)
    with pytest.raises(BudgetExceeded) as exc:
        enforcer.preflight(Decimal("0.11"), provider_id="anthropic", run_active=True, workflow_active=False)
    assert exc.value.scope is BudgetScope.RUN


def test_preflight_requires_confirmation_above_threshold() -> None:
    enforcer = BudgetEnforcer(BudgetConfig(), BudgetState())
    with pytest.raises(ConfirmationRequired):
        enforcer.preflight(Decimal("1.01"), provider_id="anthropic", run_active=False, workflow_active=False)


def test_record_adds_measured_cost_to_active_scopes() -> None:
    state = BudgetState()
    state.begin_run()
    state.begin_workflow()
    enforcer = BudgetEnforcer(BudgetConfig(first_launch_confirmed=True), state)
    enforcer.record(Decimal("0.25"), provider_id="anthropic", run_active=True, workflow_active=True)
    assert state.spend_for(BudgetScope.SESSION) == Decimal("0.25")
    assert state.spend_for(BudgetScope.RUN) == Decimal("0.25")
    assert state.spend_for(BudgetScope.WORKFLOW) == Decimal("0.25")
    assert state.spend_for(BudgetScope.PROVIDER_DAY, "anthropic") == Decimal("0.25")
