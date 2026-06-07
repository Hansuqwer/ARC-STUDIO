"""CR-009: the transcript re-renders the last assistant block in place as it streams.

DataStore.append_to_last mutates the last assistant entry's content without
changing the entry count, so the new-entries poll never re-renders it. The
Transcript now tracks that block and refreshes it on growth.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from agent_runtime_cockpit.tui.data import DataStore
from agent_runtime_cockpit.tui.widgets.markdown_block import MarkdownBlock
from agent_runtime_cockpit.tui.widgets.transcript import Transcript


def test_markdown_block_update_body_rerenders():
    block = MarkdownBlock("hello", no_color=True)
    assert block.render() == "hello"
    block.update_body("hello world")
    assert block._body == "hello world"
    assert block.render() == "hello world"


def _streaming_transcript(initial: str) -> tuple[Transcript, DataStore]:
    data = DataStore()
    data.add_entry("assistant", initial)
    t = Transcript.__new__(Transcript)  # bypass mount; exercise the logic directly
    t.data = data
    t._auto_scroll = False
    t._last_block = MagicMock()
    t._last_block_index = 0
    t._last_block_text = initial
    return t, data


def test_transcript_refreshes_streaming_block_on_growth():
    t, data = _streaming_transcript("partial")
    data.entries[0].content = "partial more"
    t._refresh_streaming_block()
    t._last_block.update_body.assert_called_once_with("partial more")


def test_transcript_no_refresh_when_unchanged():
    t, _data = _streaming_transcript("stable")
    t._refresh_streaming_block()
    t._last_block.update_body.assert_not_called()


def test_append_to_last_then_refresh_reflects_each_delta():
    t, data = _streaming_transcript("")
    data.append_to_last(" delta1")
    t._refresh_streaming_block()
    t._last_block.update_body.assert_called_with(" delta1")
    data.append_to_last(" delta2")
    t._refresh_streaming_block()
    t._last_block.update_body.assert_called_with(" delta1 delta2")


def test_refresh_is_noop_without_tracked_block():
    t, _data = _streaming_transcript("x")
    t._last_block = None
    # Must not raise when nothing is being streamed.
    t._refresh_streaming_block()
