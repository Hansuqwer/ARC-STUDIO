"""CR-035: ContextMeter default context limit is a modern 200k baseline."""

from __future__ import annotations

from agent_runtime_cockpit.tui.data import DataStore
from agent_runtime_cockpit.tui.theme import ThemeManager
from agent_runtime_cockpit.tui.widgets.context_meter import (
    _DEFAULT_CONTEXT_LIMIT,
    ContextMeter,
)


def test_default_context_limit_is_200k():
    assert _DEFAULT_CONTEXT_LIMIT == 200_000


def test_meter_uses_default_when_no_model_limit():
    ds = DataStore(seed=0)
    ds.total_tokens = 100_000
    ds.context_limit = 0  # no active-model limit wired → falls back to default
    out = ContextMeter(ds, ThemeManager()).render()
    assert "200000" in out
    assert "50%" in out  # 100k / 200k


def test_meter_prefers_model_limit_over_default():
    ds = DataStore(seed=0)
    ds.total_tokens = 5_000
    ds.context_limit = 10_000  # active-model limit wins
    out = ContextMeter(ds, ThemeManager()).render()
    assert "10000" in out
    assert "200000" not in out
