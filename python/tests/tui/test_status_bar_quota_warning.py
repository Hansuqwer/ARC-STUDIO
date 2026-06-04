"""Tests for QuotaWarning consumer in status bar — R-01."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from agent_runtime_cockpit.tui.data import DataStore
from agent_runtime_cockpit.tui.theme import Theme, ThemeManager
from agent_runtime_cockpit.tui.widgets.status_bar import StatusBar


@dataclass
class _FakeWarning:
    usage_pct: float
    dimension: str = "session"
    limit: float = 10.0
    current: float = 0.0


def _bar(*, warnings: list = None, no_color: bool = False) -> StatusBar:
    ds = DataStore(seed=0)
    ds.workspace = Path("/tmp")
    ds.quota_warnings = warnings or []
    tm = ThemeManager()
    if no_color:
        tm._current = Theme(name="nocolor", no_color=True)
    return StatusBar(ds, tm)


class TestStatusBarQuotaWarning:
    def test_warn_event_renders_amber_chip(self):
        out = _bar(warnings=[_FakeWarning(usage_pct=0.85)]).render()
        assert "⚠" in out

    def test_critical_event_renders_red_chip(self):
        out = _bar(warnings=[_FakeWarning(usage_pct=1.0)]).render()
        assert "🛑" in out

    def test_no_color_renders_text_tags(self):
        out = _bar(warnings=[_FakeWarning(usage_pct=0.85)], no_color=True).render()
        assert "[WARN]" in out

    def test_no_color_critical_renders_text_tags(self):
        out = _bar(warnings=[_FakeWarning(usage_pct=1.0)], no_color=True).render()
        assert "[CRITICAL]" in out

    def test_no_warnings_no_warning_str(self):
        out = _bar(warnings=[]).render()
        assert "⚠" not in out
        assert "🛑" not in out
        assert "[WARN]" not in out
        assert "[CRITICAL]" not in out

    def test_multiple_warnings_shows_latest(self):
        out = _bar(
            warnings=[
                _FakeWarning(usage_pct=0.85),
                _FakeWarning(usage_pct=1.0),
            ]
        ).render()
        # Latest is pct=1.0, so red
        assert "🛑" in out
