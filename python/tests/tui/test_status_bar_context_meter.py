"""P0-4: context-usage meter in status bar."""

from __future__ import annotations

from agent_runtime_cockpit.tui.data import DataStore
from agent_runtime_cockpit.tui.theme import Theme, ThemeManager
from agent_runtime_cockpit.tui.widgets.status_bar import StatusBar


def _bar(total_tokens: int = 0, context_limit: int = 0, no_color: bool = False) -> StatusBar:
    ds = DataStore(seed=0)
    ds.total_tokens = total_tokens
    ds.context_limit = context_limit
    tm = ThemeManager()
    if no_color:
        tm._current = Theme(name="nocolor", no_color=True)
    bar = StatusBar(ds, tm)
    return bar


def test_renders_tokens_and_limit() -> None:
    # Use a short path so the line isn't truncated before the tok segment.
    ds = DataStore(seed=0)
    ds.total_tokens = 5000
    ds.context_limit = 10000
    # Override workspace to short path
    from pathlib import Path

    ds.workspace = Path("/tmp")
    tm = ThemeManager()
    bar = StatusBar(ds, tm)
    out = bar.render()
    assert "tok" in out
    assert "50%" in out


def test_no_limit_shows_only_count() -> None:
    out = _bar(5000, 0).render()
    assert "5000" in out
    assert "%" not in out
    assert "/" not in out.split("tok ")[1].split(" │")[0]


def test_color_tier_green() -> None:
    out = _bar(3000, 10000).render()
    assert "green" in out


def test_color_tier_yellow() -> None:
    out = _bar(7000, 10000).render()
    assert "yellow" in out


def test_color_tier_red() -> None:
    out = _bar(9000, 10000).render()
    assert "red" in out


def test_no_color_low() -> None:
    out = _bar(3000, 10000, no_color=True).render()
    assert "[low]" in out
    assert "green" not in out


def test_no_color_warn() -> None:
    out = _bar(7000, 10000, no_color=True).render()
    assert "[warn]" in out


def test_no_color_hot() -> None:
    out = _bar(9000, 10000, no_color=True).render()
    assert "[hot]" in out
