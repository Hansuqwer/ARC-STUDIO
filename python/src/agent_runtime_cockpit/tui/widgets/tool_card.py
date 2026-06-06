"""Tool card widget — displays tool call status and output.

Implements UX_AUDIT R-005:
- Expand/collapse via Enter or x key (no fixed 20-line truncation)
- Risk badge in header when metadata.risk is set
- Copy hint shown in expanded state
- NO_COLOR aware
"""

from __future__ import annotations

from textual import events
from textual.message import Message
from textual.widgets import Static

from ..data import TranscriptEntry
from ..theme import ThemeManager

_STATUS_ICONS = {"running": "●", "success": "✓", "error": "✗", "cancelled": "⊘"}
_STATUS_ICONS_ASCII = {"running": "[*]", "success": "[OK]", "error": "[ERR]", "cancelled": "[X]"}
_RISK_STYLE = {"low": "green", "medium": "yellow", "high": "red", "critical": "bold red"}
_PREVIEW_LINES = 5


class ToolCard(Static):
    """Collapsible tool call card with status header.

    Keys (when focused): Enter or x = expand/collapse; r = rerun.
    NO_COLOR aware; trims only in collapsed state.
    """

    class RerunRequested(Message):
        def __init__(self, entry: TranscriptEntry) -> None:
            super().__init__()
            self.entry = entry

    DEFAULT_CSS = """
    ToolCard {
        height: auto;
        margin-bottom: 1;
    }
    """

    def __init__(self, entry: TranscriptEntry, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.entry = entry
        self.theme = theme
        self._collapsed = True  # start collapsed; Enter expands

    def toggle_collapse(self) -> None:
        self._collapsed = not self._collapsed
        self.refresh()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("enter", "x"):
            event.stop()
            self.toggle_collapse()
        elif event.key == "r":
            event.stop()
            self.post_message(self.RerunRequested(self.entry))

    def render(self) -> str:
        no_color = bool(getattr(self.theme.current, "no_color", False))
        status = self.entry.metadata.get("status", "running")
        tool_name = self.entry.metadata.get("tool_name", "Tool")
        duration = self.entry.metadata.get("duration", "")
        risk = self.entry.metadata.get("risk", "")

        icon = (_STATUS_ICONS_ASCII if no_color else _STATUS_ICONS).get(status, "●")
        risk_badge = ""
        if risk:
            if no_color:
                risk_badge = f" [{risk.upper()}]"
            else:
                style = _RISK_STYLE.get(risk, "")
                risk_badge = f" [{style}]{risk}[/]"

        hint = " [dim]↵ expand · r rerun[/]" if self._collapsed and not no_color else ""
        header = f"┌ {tool_name} {icon}{risk_badge} {duration}{hint} ─┐"

        if self._collapsed:
            preview = self.entry.content.split("\n")[:_PREVIEW_LINES]
            body = [f"│ {l}" for l in preview]
            total = self.entry.content.count("\n") + 1
            if total > _PREVIEW_LINES:
                body.append(f"│ … ({total - _PREVIEW_LINES} more lines — press x to expand)")
        else:
            body = [f"│ {l}" for l in self.entry.content.split("\n")]
            if not no_color:
                body.append("│ [dim]x = collapse · Ctrl+C to copy[/]")

        footer = "└" + "─" * max(len(tool_name) + 12, 48) + "┘"
        return "\n".join([header] + body + [footer])
