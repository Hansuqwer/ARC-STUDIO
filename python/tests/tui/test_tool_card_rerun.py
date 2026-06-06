"""Tests for ToolCard 'r' key rerun feature (Phase 129)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from textual import events

from agent_runtime_cockpit.tui.widgets.tool_card import ToolCard


def _make_entry(content: str = "output") -> MagicMock:
    entry = MagicMock()
    entry.content = content
    entry.metadata = {"status": "success", "tool_name": "my_tool"}
    return entry


def _make_theme() -> MagicMock:
    theme = MagicMock()
    theme.current.no_color = False
    return theme


def test_r_key_posts_rerun_requested() -> None:
    entry = _make_entry()
    card = ToolCard(entry=entry, theme=_make_theme())
    key_event = MagicMock(spec=events.Key)
    key_event.key = "r"

    with patch.object(card, "post_message") as mock_post:
        card.on_key(key_event)

    key_event.stop.assert_called_once()
    mock_post.assert_called_once()
    msg = mock_post.call_args[0][0]
    assert isinstance(msg, ToolCard.RerunRequested)
    assert msg.entry is entry


def test_rerun_hint_in_collapsed_render() -> None:
    entry = _make_entry("line1\nline2")
    card = ToolCard(entry=entry, theme=_make_theme())
    assert card._collapsed  # default collapsed
    output = card.render()
    assert "rerun" in output
