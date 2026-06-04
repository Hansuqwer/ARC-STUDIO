"""Tests for TokenWallet — R-01."""

from __future__ import annotations

import concurrent.futures
import dataclasses
from decimal import Decimal

import pytest

from agent_runtime_cockpit.budget.schema import (
    BudgetConfig,
    BudgetEnforcer,
    BudgetScope,
    BudgetState,
)
from agent_runtime_cockpit.budget.wallet import TokenWallet, WalletBalance, WalletSnapshot


def _make_enforcer(
    *,
    first_launch_confirmed: bool = True,
    session_spent: Decimal = Decimal("0"),
) -> BudgetEnforcer:
    config = BudgetConfig(first_launch_confirmed=first_launch_confirmed)
    state = BudgetState()
    state.session.amount_usd = session_spent
    return BudgetEnforcer(config, state)


class TestTokenWallet:
    def test_snapshot_returns_all_scopes(self):
        enforcer = _make_enforcer()
        wallet = TokenWallet(enforcer)
        snap = wallet.snapshot()

        # PROVIDER_DAY is skipped; we get RUN, WORKFLOW, SESSION
        assert "session" in snap.balances
        assert "run" in snap.balances
        assert "workflow" in snap.balances
        assert "provider_day" not in snap.balances
        assert snap.fail_closed_reason is None

    def test_snapshot_remaining_clamped_at_zero_when_over_cap(self):
        enforcer = _make_enforcer(session_spent=Decimal("999.99"))
        wallet = TokenWallet(enforcer)
        snap = wallet.snapshot()

        bal = snap.balances["session"]
        assert bal.remaining_usd == Decimal(0)
        assert bal.spent_usd == Decimal("999.99")

    def test_snapshot_first_launch_true_when_not_confirmed(self):
        enforcer = _make_enforcer(first_launch_confirmed=False)
        wallet = TokenWallet(enforcer)
        snap = wallet.snapshot()

        assert snap.first_launch is True

    def test_snapshot_first_launch_false_when_confirmed(self):
        enforcer = _make_enforcer(first_launch_confirmed=True)
        wallet = TokenWallet(enforcer)
        snap = wallet.snapshot()

        assert snap.first_launch is False

    def test_fail_closed_on_enforcer_error(self):
        enforcer = _make_enforcer()
        wallet = TokenWallet(enforcer)

        # Replace the _config with an object whose effective_cap raises
        class _BrokenConfig:
            first_launch_confirmed = True

            def effective_cap(self, *_a, **_kw):
                raise RuntimeError("boom")

        object.__setattr__(enforcer, "_config", _BrokenConfig())
        snap = wallet.snapshot()

        assert snap.balances == {}
        assert snap.first_launch is False
        assert "RuntimeError" in (snap.fail_closed_reason or "")
        assert "boom" in (snap.fail_closed_reason or "")

    def test_snapshot_does_not_mutate_enforcer(self):
        enforcer = _make_enforcer(session_spent=Decimal("1.50"))
        original_spend = enforcer._state.session.amount_usd
        wallet = TokenWallet(enforcer)
        wallet.snapshot()
        wallet.snapshot()

        assert enforcer._state.session.amount_usd == original_spend

    def test_wallet_balance_frozen(self):
        bal = WalletBalance(
            scope=BudgetScope.SESSION,
            cap_usd=Decimal("10"),
            spent_usd=Decimal("1"),
            remaining_usd=Decimal("9"),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            bal.spent_usd = Decimal("999")  # type: ignore[misc]

    def test_snapshot_concurrent_calls(self):
        enforcer = _make_enforcer(session_spent=Decimal("2.00"))
        wallet = TokenWallet(enforcer)

        def _call(_: int) -> WalletSnapshot:
            return wallet.snapshot()

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_call, i) for i in range(32)]
            results = [f.result() for f in futures]

        # All should succeed without exception
        assert all(r.fail_closed_reason is None for r in results)
        assert all("session" in r.balances for r in results)

    def test_no_llm_import_in_wallet(self):
        """Ensure the wallet module does not import any LLM/provider modules."""
        import importlib
        import inspect

        mod = importlib.import_module("agent_runtime_cockpit.budget.wallet")
        source = inspect.getsource(mod)
        forbidden = ["openai", "anthropic", "langchain", "llm", "provider"]
        for word in forbidden:
            # Check imports only, not comments/docstrings about providers
            for line in source.splitlines():
                if line.strip().startswith(("import ", "from ")):
                    assert word not in line.lower(), f"Forbidden import containing '{word}': {line}"
