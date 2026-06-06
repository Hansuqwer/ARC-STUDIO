"""Tests for allow_paid_warning property on DataStore."""

from agent_runtime_cockpit.tui.data import DataStore


def _store(**kwargs) -> DataStore:
    return DataStore(workspace="/tmp", **kwargs)


def test_warning_when_allow_paid_true_no_budget():
    store = _store()
    store.allow_paid = True
    store.wallet_budget_usd = None
    warning = store.allow_paid_warning
    assert warning is not None
    assert "budget" in warning.lower() or "wallet" in warning.lower()


def test_no_warning_when_budget_set():
    store = _store()
    store.allow_paid = True
    store.wallet_budget_usd = 5.0
    assert store.allow_paid_warning is None


def test_no_warning_when_allow_paid_false():
    store = _store()
    store.allow_paid = False
    store.wallet_budget_usd = None
    assert store.allow_paid_warning is None
