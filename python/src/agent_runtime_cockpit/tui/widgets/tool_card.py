"""Tool card widget — displays tool call status and output."""

from __future__ import annotations

from textual.widgets import Static

from ..data import TranscriptEntry
from ..theme import ThemeManager

_STATUS_ICONS = {"running": "●", "success": "✓", "error": "✗", "cancelled": "⊘"}


class ToolCard(Static):
    """Collapsible tool call card with status header."""

    def __init__(self, entry: TranscriptEntry, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.entry = entry
        self.theme = theme
        self._collapsed = False

    def toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        self.refresh()

    def render(self) -> str:
        status = self.entry.metadata.get("status", "running")
        tool_name = self.entry.metadata.get("tool_name", "Tool")
        duration = self.entry.metadata.get("duration", "")
        icon = _STATUS_ICONS.get(status, "●")
        header = f"┌ {tool_name} {icon} {duration} ─┐"
        if self._collapsed:
            return header
        body_lines = [f"│ {l}" for l in self.entry.content.split("\n")[:20]]
        if self.entry.content.count("\n") > 20:
            body_lines.append(f"│ … ({self.entry.content.count(chr(10)) - 20} more lines)")
        footer = "└" + "─" * max(len(header) - 2, 48) + "┘"
        return "\n".join([header] + body_lines + [footer])
