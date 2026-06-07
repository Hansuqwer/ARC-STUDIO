"""Tests for Phase 128: CommandPalette detail pane updates on highlight."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from agent_runtime_cockpit.cli_repl.commands import CommandDef
from agent_runtime_cockpit.tui.widgets.command_palette import CommandPalette


@pytest.mark.asyncio
async def test_detail_pane_updates_on_highlight():
    """Detail pane shows usage and examples when a command with usage is highlighted."""
    from textual.widgets import ListItem, ListView

    cmd = CommandDef(
        name="foo",
        help_text="Does foo things",
        category="session",
        handler=MagicMock(),
        usage="Usage: /foo <arg>",
        examples=["example1", "example2", "example3"],
    )

    palette = CommandPalette()
    palette._cmds = [cmd]

    item = ListItem(id="pal-foo")
    highlighted = ListView.Highlighted(list_view=MagicMock(), item=item)

    mock_static = MagicMock()
    palette.query_one = MagicMock(return_value=mock_static)

    palette.on_list_view_highlighted(highlighted)

    mock_static.update.assert_called_once()
    call_arg = mock_static.update.call_args[0][0]
    assert "Usage: /foo" in call_arg
    # Only first 2 examples
    assert "example1" in call_arg
    assert "example2" in call_arg
    assert "example3" not in call_arg


@pytest.mark.asyncio
async def test_detail_pane_empty_when_no_usage():
    """Detail pane shows only help_text when usage and examples are empty."""
    from textual.widgets import ListItem, ListView

    cmd = CommandDef(
        name="bar",
        help_text="Does bar things",
        category="session",
        handler=MagicMock(),
        usage="",
        examples=[],
    )

    palette = CommandPalette()
    palette._cmds = [cmd]

    item = ListItem(id="pal-bar")
    highlighted = ListView.Highlighted(list_view=MagicMock(), item=item)

    mock_static = MagicMock()
    palette.query_one = MagicMock(return_value=mock_static)

    palette.on_list_view_highlighted(highlighted)

    mock_static.update.assert_called_once()
    call_arg = mock_static.update.call_args[0][0]
    assert "Does bar things" in call_arg
    # No usage line, no examples — only help_text
    assert call_arg.strip() == "Does bar things"


@pytest.mark.asyncio
async def test_palette_populates_on_mount_with_fresh_registry():
    """CR-023: opening the palette before any other registry consumer has run
    still shows commands — on_mount builds the (idempotent) registry rather than
    reading a possibly-empty global singleton."""
    from textual.app import App

    from agent_runtime_cockpit.cli_repl.commands import reset_registry
    from agent_runtime_cockpit.tui.widgets.command_palette import CommandPalette

    reset_registry()  # simulate fresh launch: global registry is empty
    palette = CommandPalette()

    class _Harness(App):
        async def on_mount(self) -> None:
            await self.push_screen(palette)

    app = _Harness()
    async with app.run_test(size=(80, 40)) as pilot:
        await pilot.pause()
        assert len(palette._cmds) > 0, "palette should list commands even on first open"
