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


# ── Slash commands: /theme <name>, /theme list, /title, /statusline ──────────

import pytest  # noqa: E402


def _last_system(data) -> str:
    for entry in reversed(data.entries):
        if entry.role == "system":
            return entry.content
    return ""


@pytest.mark.asyncio
async def test_slash_theme_select(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ARC_THEME", raising=False)
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        screen = app.screen
        screen._handle_slash("/theme mocha")
        await pilot.pause()
        assert app.theme_manager.current.name == "mocha"
        assert "Theme: mocha" in _last_system(app.data)


@pytest.mark.asyncio
async def test_slash_theme_list(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.screen._handle_slash("/theme list")
        await pilot.pause()
        msg = _last_system(app.data)
        assert "Themes:" in msg and "mocha" in msg


@pytest.mark.asyncio
async def test_slash_theme_unknown(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.screen._handle_slash("/theme not-a-real-theme")
        await pilot.pause()
        # current theme unchanged; an error/system entry mentions the unknown name
        assert app.theme_manager.current.name == "dark"
        assert "not-a-real-theme" in _last_system(app.data).lower()


@pytest.mark.asyncio
async def test_slash_title(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.screen._handle_slash("/title My Session")
        await pilot.pause()
        assert app.title == "My Session"


@pytest.mark.asyncio
async def test_slash_statusline(monkeypatch):
    monkeypatch.delenv("NO_COLOR", raising=False)
    from agent_runtime_cockpit.tui.app import ArcApp

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.screen._handle_slash("/statusline")
        await pilot.pause()
        assert "Status-line slots" in _last_system(app.data)


@pytest.mark.asyncio
async def test_status_bar_no_color_has_no_dot_glyphs(monkeypatch):
    """R-UX4 a11y: daemon/stream indicators must not use ●/○ in NO_COLOR mode."""
    monkeypatch.setenv("NO_COLOR", "1")
    from pathlib import Path

    from agent_runtime_cockpit.tui.app import ArcApp
    from agent_runtime_cockpit.tui.widgets.status_bar import StatusBar

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.data.workspace = Path("/tmp")  # short path so the line isn't truncated
        app.data.daemon_online = True
        app.data.is_streaming = True
        bar = app.query_one("#status-bar", StatusBar)
        out = bar.render()
        assert "●" not in out
        assert "○" not in out
        assert "[on]" in out
        assert "streaming" in out


@pytest.mark.asyncio
async def test_status_bar_color_keeps_dot_glyph(monkeypatch):
    """Color mode still uses the ● daemon glyph (control for the NO_COLOR test)."""
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("ARC_THEME", raising=False)
    from pathlib import Path

    from agent_runtime_cockpit.tui.app import ArcApp
    from agent_runtime_cockpit.tui.widgets.status_bar import StatusBar

    app = ArcApp()
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        app.data.workspace = Path("/tmp")  # short path so the line isn't truncated
        app.data.daemon_online = True
        bar = app.query_one("#status-bar", StatusBar)
        out = bar.render()
        assert "●" in out
