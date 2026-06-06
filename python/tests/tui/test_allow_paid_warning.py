"""Tests for allow_paid_warning property on DataStore."""

from agent_runtime_cockpit.tui.data import DataStore


def _store(**kwargs) -> DataStore:
    return DataStore(workspace="/tmp", **kwargs)


def test_warning_when_allow_paid_true_no_budget():
    """Warning triggers when allow_paid=True AND wallet_budget_usd=0 (exhausted/zeroed)."""
    store = _store()
    store.allow_paid = True
    store.wallet_budget_usd = 0.0
    warning = store.allow_paid_warning
    assert warning is not None
    assert "budget" in warning.lower() or "wallet" in warning.lower()


def test_no_warning_when_budget_set():
    """No warning when a positive budget is set."""
    store = _store()
    store.allow_paid = True
    store.wallet_budget_usd = 5.0
    assert store.allow_paid_warning is None


def test_no_warning_when_allow_paid_false():
    """No warning when allow_paid=False."""
    store = _store()
    store.allow_paid = False
    store.wallet_budget_usd = 0.0
    assert store.allow_paid_warning is None
