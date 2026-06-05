"""Tests for R-UX4 theme registry: 5+ themes, select, cycle, aliases, env precedence."""

from __future__ import annotations

from agent_runtime_cockpit.tui.theme import (
    HIGH_CONTRAST_THEME,
    MONO_THEME,
    ThemeManager,
    resolve_theme_name,
    theme_names,
)


def test_all_themes_registered():
    names = theme_names()
    for expected in ["dark", "light", "mocha", "latte", "high-contrast", "mono"]:
        assert expected in names


def test_select_by_name(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ARC_THEME", raising=False)
    tm = ThemeManager()
    t = tm.select("mocha")
    assert t is not None
    assert tm.current.name == "mocha"


def test_select_alias(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ARC_THEME", raising=False)
    tm = ThemeManager()
    assert tm.select("catppuccin-latte") is not None
    assert tm.current.name == "latte"
    assert tm.select("a11y") is not None
    assert tm.current.name == "high-contrast"


def test_select_unknown_returns_none_and_keeps_current(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ARC_THEME", raising=False)
    tm = ThemeManager()
    before = tm.current.name
    assert tm.select("nope-not-a-theme") is None
    assert tm.current.name == before


def test_cycle_visits_every_theme(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ARC_THEME", raising=False)
    tm = ThemeManager()
    seen = {tm.current.name}
    for _ in range(len(theme_names())):
        seen.add(tm.cycle().name)
    assert seen == set(theme_names())


def test_arc_theme_env_selects_named(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("ARC_THEME", "mocha")
    tm = ThemeManager()
    assert tm.current.name == "mocha"


def test_no_color_selects_mono(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    tm = ThemeManager()
    assert tm.is_no_color
    assert tm.current.name == "mono"
    assert MONO_THEME.no_color is True


def test_high_contrast_palette():
    assert HIGH_CONTRAST_THEME.background == "#000000"
    assert HIGH_CONTRAST_THEME.foreground == "#ffffff"


def test_resolve_theme_name():
    assert resolve_theme_name("MOCHA") == "mocha"
    assert resolve_theme_name("catppuccin") == "mocha"
    assert resolve_theme_name("monochrome") == "mono"
    assert resolve_theme_name("garbage") is None


def test_toggle_still_dark_light(monkeypatch):
    """Back-compat: toggle() must still flip dark<->light only."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ARC_THEME", raising=False)
    tm = ThemeManager()
    assert tm.current.name == "dark"
    assert tm.toggle().name == "light"
    assert tm.toggle().name == "dark"
