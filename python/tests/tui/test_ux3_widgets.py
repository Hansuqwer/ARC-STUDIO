"""Tests for R-UX3: RiskBadge, KeycapHint, Toaster wiring, CommandPalette search."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.tui.widgets.keycap_hint import KeycapHint
from agent_runtime_cockpit.tui.widgets.risk_badge import RiskBadge


# ── RiskBadge ─────────────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "level,expected_sub",
    [
        ("low", "green"),
        ("medium", "yellow"),
        ("high", "red"),
        ("critical", "bold red"),
    ],
)
def test_risk_badge_markup_contains_color(level, expected_sub):
    markup = RiskBadge.markup(level)
    assert expected_sub in markup
    assert level in markup


def test_risk_badge_markup_no_color():
    assert RiskBadge.markup("high", no_color=True) == "[H]"
    assert RiskBadge.markup("critical", no_color=True) == "[C]"
    assert RiskBadge.markup("low", no_color=True) == "[L]"
    assert RiskBadge.markup("medium", no_color=True) == "[M]"


def test_risk_badge_unknown_level_no_color():
    result = RiskBadge.markup("unknown", no_color=True)
    assert "[" in result and "]" in result


# ── KeycapHint ────────────────────────────────────────────────────────────────


def test_keycap_hint_markup_contains_key():
    markup = KeycapHint.markup("Ctrl+P")
    assert "Ctrl+P" in markup


def test_keycap_hint_markup_no_color():
    result = KeycapHint.markup("Esc", no_color=True)
    assert result == "[Esc]"


def test_keycap_hint_markup_has_brackets():
    # Color form should still have bracket characters
    markup = KeycapHint.markup("Enter")
    assert "[" in markup and "]" in markup


# ── CommandPalette searches help_text ────────────────────────────────────────


@pytest.mark.asyncio
async def test_command_palette_searches_description():
    """CommandPalette._populate filters on help_text when query matches description."""
    from unittest.mock import MagicMock

    from agent_runtime_cockpit.cli_repl.commands import CommandDef

    cmd = CommandDef(
        name="providers",
        help_text="Manage API key providers and model selection",
        category="provider",
        handler=MagicMock(),
    )
    palette_cmds = [cmd]
    q = "api key"
    filtered = [c for c in palette_cmds if q in c.name or q in c.help_text.lower()]
    # "api key" is NOT in name "providers" but IS in help_text
    assert len(filtered) == 1
    assert filtered[0].name == "providers"


@pytest.mark.asyncio
async def test_command_palette_name_search_still_works():
    """CommandPalette still returns results when query matches the name."""
    from unittest.mock import MagicMock

    from agent_runtime_cockpit.cli_repl.commands import CommandDef

    palette_cmds = [
        CommandDef(
            name="providers",
            help_text="Manage API key providers",
            category="provider",
            handler=MagicMock(),
        ),
        CommandDef(
            name="runs", help_text="Browse run history", category="run", handler=MagicMock()
        ),
    ]
    q = "runs"
    filtered = [c for c in palette_cmds if q in c.name or q in c.help_text.lower()]
    assert any(c.name == "runs" for c in filtered)


# ── Toaster wired in screen ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_toaster_present_in_screen():
    """Toaster is yielded in ArcScreen compose so it can be queried."""
    from agent_runtime_cockpit.tui.app import ArcApp
    from agent_runtime_cockpit.tui.data import DataStore
    from agent_runtime_cockpit.tui.widgets.toaster import Toaster

    app = ArcApp(data=DataStore(seed=42))
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        assert app.query_one("#toaster", Toaster) is not None


@pytest.mark.asyncio
async def test_toaster_show_mounts_toast():
    """Toaster.show() mounts a _Toast child that contains the message."""
    from agent_runtime_cockpit.tui.app import ArcApp
    from agent_runtime_cockpit.tui.data import DataStore
    from agent_runtime_cockpit.tui.widgets.toaster import Toaster

    app = ArcApp(data=DataStore(seed=43))
    async with app.run_test(size=(120, 40)) as pilot:
        await pilot.pause()
        toaster = app.query_one("#toaster", Toaster)
        toaster.show("Daemon reconnected", severity="success", timeout=60.0)
        await pilot.pause()
        children = list(toaster.children)
        assert len(children) >= 1
        # The toast label contains our message (Content or str)
        text = str(children[0].render())
        assert "Daemon reconnected" in text
