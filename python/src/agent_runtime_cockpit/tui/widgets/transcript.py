"""Transcript widget — scrollable message history."""

from __future__ import annotations

from textual.containers import VerticalScroll
from textual.widgets import Static

from ..data import DataStore, TranscriptEntry
from ..theme import ThemeManager


class Transcript(VerticalScroll):
    """Scrollable container for all transcript entries."""

    def __init__(self, data: DataStore, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self.theme = theme
        self._rendered_count = 0
        self._auto_scroll = True

    def on_mount(self) -> None:
        self.set_interval(0.1, self._check_new_entries)

    def _check_new_entries(self) -> None:
        if len(self.data.entries) > self._rendered_count:
            for entry in self.data.entries[self._rendered_count :]:
                self._render_entry(entry)
            self._rendered_count = len(self.data.entries)
            if self._auto_scroll:
                self.scroll_end(animate=False)

    def _render_entry(self, entry: TranscriptEntry) -> None:
        if entry.metadata.get("type") == "diff":
            from .diff_block import DiffBlock

            self.mount(DiffBlock(entry.content, entry.metadata.get("filename", "diff")))
        elif entry.role == "tool":
            from .tool_card import ToolCard

            self.mount(ToolCard(entry, self.theme))
        elif entry.role == "assistant":
            # UX R-004: assistant body gets markdown + syntax via MarkdownBlock.
            # We still emit a small role header above it so timestamps stay visible.
            from .markdown_block import MarkdownBlock

            self.mount(MessageHeader(entry, self.theme))
            no_color = bool(getattr(self.theme.current, "no_color", False))
            self.mount(MarkdownBlock(entry.content, no_color=no_color))
        else:
            msg = MessageWidget(entry, self.theme, self.data)
            self.mount(msg)

    def scroll_to_bottom(self) -> None:
        self._auto_scroll = True
        self.scroll_end(animate=False)

    def on_click(self, event) -> None:
        self._auto_scroll = False

    def key_end(self) -> None:
        self.scroll_to_bottom()


class MessageHeader(Static):
    """One-line role + timestamp header. Used above MarkdownBlock for assistant.

    Kept tiny so it never competes with the body for vertical space.
    """

    def __init__(self, entry: TranscriptEntry, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.entry = entry
        self.theme = theme

    def render(self) -> str:
        no_color = bool(getattr(self.theme.current, "no_color", False))
        label = {"user": "you", "assistant": "arc", "system": "sys"}.get(
            self.entry.role, self.entry.role
        )
        if no_color:
            return f"> {label}  {self.entry.display_time}"
        color = {
            "user": "magenta",
            "assistant": "cyan",
            "system": "dim",
        }.get(self.entry.role, "white")
        return f"[bold {color}]\u25b8 {label}[/]  [dim]{self.entry.display_time}[/]"


class MessageWidget(Static):
    """A single message in the transcript."""

    def __init__(
        self, entry: TranscriptEntry, theme: ThemeManager, data: DataStore, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.entry = entry
        self.theme = theme
        self.data = data

    def render(self) -> str:
        entry = self.entry
        if entry.role == "user":
            lines = [f"▸ You  {entry.display_time}"]
            lines += [f"  {l}" for l in entry.content.split("\n")]
            return "\n".join(lines)
        elif entry.role == "assistant":
            lines = [f"▸ ARC  {entry.display_time}"]
            lines += [f"  {l}" for l in entry.content.split("\n")]
            return "\n".join(lines)
        elif entry.role == "system":
            lines = [f"▸ SYS  {entry.display_time}"]
            lines += [f"  {l}" for l in entry.content.split("\n")]
            return "\n".join(lines)
        else:
            return f"[{entry.role}] {entry.content}"
