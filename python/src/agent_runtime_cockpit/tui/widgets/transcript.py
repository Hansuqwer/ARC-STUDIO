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
        # CR-009: the last assistant entry is mutated in place by
        # DataStore.append_to_last during streaming (the entry count does not
        # change), so we track its MarkdownBlock to re-render it on growth.
        self._last_block = None
        self._last_block_index = -1
        self._last_block_text = ""

    def on_mount(self) -> None:
        self.set_interval(0.1, self._check_new_entries)

    def _check_new_entries(self) -> None:
        entries = self.data.entries
        if len(entries) > self._rendered_count:
            for index in range(self._rendered_count, len(entries)):
                self._render_entry(entries[index], index)
            self._rendered_count = len(entries)
            if self._auto_scroll:
                self.scroll_end(animate=False)
        # CR-009: reflect in-place streaming growth of the last assistant entry.
        self._refresh_streaming_block()

    def _refresh_streaming_block(self) -> None:
        block = self._last_block
        if block is None or self._last_block_index < 0:
            return
        entries = self.data.entries
        if self._last_block_index >= len(entries):
            return
        entry = entries[self._last_block_index]
        if entry.role == "assistant" and entry.content != self._last_block_text:
            self._last_block_text = entry.content
            block.update_body(entry.content)
            if self._auto_scroll:
                self.scroll_end(animate=False)

    def _render_entry(self, entry: TranscriptEntry, index: int = -1) -> None:
        if entry.metadata.get("type") == "diff":
            from .diff_block import DiffBlock

            self.mount(DiffBlock(entry.content, entry.metadata.get("filename", "diff")))
            self._last_block = None
        elif entry.role == "tool":
            from .tool_card import ToolCard

            self.mount(ToolCard(entry, self.theme))
            self._last_block = None
        elif entry.role == "assistant":
            # UX R-004: assistant body gets markdown + syntax via MarkdownBlock.
            # We still emit a small role header above it so timestamps stay visible.
            from .markdown_block import MarkdownBlock

            self.mount(MessageHeader(entry, self.theme))
            no_color = bool(getattr(self.theme.current, "no_color", False))
            block = MarkdownBlock(entry.content, no_color=no_color)
            self.mount(block)
            # Track this block so streaming deltas re-render it (CR-009).
            self._last_block = block
            self._last_block_index = index
            self._last_block_text = entry.content
        else:
            msg = MessageWidget(entry, self.theme, self.data)
            self.mount(msg)
            self._last_block = None

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
