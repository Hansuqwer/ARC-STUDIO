"""Tests for P2 UX widgets: ToolCard rebuild, DiffBlock, Toaster."""

from __future__ import annotations

import pytest

from agent_runtime_cockpit.tui.data import TranscriptEntry
from agent_runtime_cockpit.tui.theme import Theme, ThemeManager
from agent_runtime_cockpit.tui.widgets.tool_card import ToolCard
from agent_runtime_cockpit.tui.widgets.diff_block import DiffBlock
from agent_runtime_cockpit.tui.widgets.toaster import Toaster, _Toast


def _tool_entry(content: str, status: str = "success", tool: str = "bash", risk: str = "") -> TranscriptEntry:
    return TranscriptEntry(
        id="test-001",
        role="tool",
        content=content,
        metadata={"status": status, "tool_name": tool, "risk": risk},
    )


def _theme() -> ThemeManager:
    return ThemeManager()


# ── ToolCard ──────────────────────────────────────────────────────────────────


def test_tool_card_starts_collapsed() -> None:
    card = ToolCard(_tool_entry("output"), _theme())
    assert card._collapsed is True


def test_tool_card_collapsed_shows_preview() -> None:
    lines = "\n".join(f"line {i}" for i in range(20))
    card = ToolCard(_tool_entry(lines), _theme())
    out = card.render()
    assert "line 0" in out
    assert "more lines" in out


def test_tool_card_expand_shows_all_lines() -> None:
    lines = "\n".join(f"line {i}" for i in range(20))
    card = ToolCard(_tool_entry(lines), _theme())
    card.toggle_collapse()  # expand
    out = card.render()
    assert "line 19" in out
    # Should not mention truncation when expanded
    assert "more lines" not in out


def test_tool_card_risk_badge_in_header() -> None:
    card = ToolCard(_tool_entry("x", risk="high"), _theme())
    out = card.render()
    assert "high" in out


def test_tool_card_no_risk_no_badge() -> None:
    card = ToolCard(_tool_entry("x", risk=""), _theme())
    out = card.render()
    # No spurious risk text when not set
    assert "low" not in out
    assert "high" not in out


def test_tool_card_no_color_uses_ascii_status() -> None:
    tm = ThemeManager()
    tm._current = Theme(name="nocolor", no_color=True)
    card = ToolCard(_tool_entry("x", status="success"), tm)
    out = card.render()
    assert "[OK]" in out or "✓" in out


# ── DiffBlock ─────────────────────────────────────────────────────────────────


SAMPLE_DIFF = """\
--- a/foo.py
+++ b/foo.py
@@ -1,4 +1,4 @@
 def foo():
-    return 1
+    return 2
     pass
"""


def test_diff_block_renders_filename() -> None:
    block = DiffBlock(SAMPLE_DIFF, filename="foo.py")
    out = block.render()
    assert "foo.py" in out


def test_diff_block_no_color_plain_text() -> None:
    block = DiffBlock(SAMPLE_DIFF, no_color=True)
    out = block.render()
    assert "[bold green]" not in out
    assert "+    return 2" in out


def test_diff_block_color_plus_green() -> None:
    block = DiffBlock(SAMPLE_DIFF, no_color=False)
    out = block.render()
    assert "bold green" in out


def test_diff_block_color_minus_red() -> None:
    block = DiffBlock(SAMPLE_DIFF, no_color=False)
    out = block.render()
    assert "bold red" in out


def test_diff_block_hunk_detection() -> None:
    block = DiffBlock(SAMPLE_DIFF)
    lines = SAMPLE_DIFF.splitlines()
    hunks = block._compute_hunks(lines)
    assert len(hunks) == 1
    assert lines[hunks[0]].startswith("@@")


# ── Toaster ───────────────────────────────────────────────────────────────────


def test_toast_format_color() -> None:
    out = _Toast._format("saved!", "success", no_color=False)
    assert "saved!" in out


def test_toast_format_no_color() -> None:
    out = _Toast._format("error!", "error", no_color=True)
    assert "[E]" in out
    assert "error!" in out


def test_toaster_constructs() -> None:
    t = Toaster(no_color=False)
    assert t._no_color is False


@pytest.mark.parametrize("severity", ["info", "success", "warning", "error"])
def test_toast_all_severities(severity: str) -> None:
    out = _Toast._format("msg", severity, no_color=True)  # type: ignore[arg-type]
    assert "msg" in out
