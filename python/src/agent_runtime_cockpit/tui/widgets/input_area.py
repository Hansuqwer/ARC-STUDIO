"""Input area widget — multi-line input with history."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, TextArea

from ..data import DataStore
from ..theme import ThemeManager


class InputArea(Container):
    """Bottom input area with a TextArea and send hint."""

    def __init__(self, data: DataStore, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self.theme = theme
        self._current_input: str = ""
        self._paste_buffer: str = ""

    def compose(self) -> ComposeResult:
        self._input = TextArea(
            "",
            id="prompt-input",
            language=None,
            show_line_numbers=False,
            max_checkpoints=20,
        )
        self._input.styles.height = 3
        self._input.styles.min_height = 3
        self._input.styles.max_height = 15
        self._hint = Label(
            "Shift+Enter: newline  ·  Enter: send  ·  /: commands  ·  @: files",
            id="send-hint",
        )
        self._hint.styles.height = 1
        yield self._input
        yield self._hint

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        self._current_input = self._input.text
        line_count = self._input.document.line_count
        new_height = min(max(line_count + 1, 3), 15)
        if self._input.styles.height != new_height:
            self._input.styles.height = new_height

    def on_key(self, event: events.Key) -> None:
        text = self._input.text.strip()

        if event.key == "enter" and not event.control and not event.shift:
            event.stop()
            event.prevent_default()
            if text:
                self.submit()
            return

        if event.key == "tab":
            event.stop()
            event.prevent_default()
            if self._paste_buffer:
                # expand paste chip
                self._input.load_text(self._paste_buffer)
                self._paste_buffer = ""
            elif text.startswith("/"):
                self.post_message(self.CompletionRequested(text))
            return

        if event.key == "ctrl+r":
            event.stop()
            event.prevent_default()
            self.post_message(self.HistorySearchRequested())
            return

        if event.key == "up" and not event.control:
            prev = self.data.history_up(self._current_input)
            if prev is not None:
                event.stop()
                event.prevent_default()
                self._input.load_text(prev)
            return

        if event.key == "down" and not event.control:
            nxt = self.data.history_down()
            if nxt is not None:
                event.stop()
                event.prevent_default()
                self._input.load_text(nxt)
            return

        if event.key == "ctrl+c":
            event.stop()
            event.prevent_default()
            self.post_message(self.InterruptRequested())
            return

    def on_paste(self, event: events.Paste) -> None:
        lines = event.text.splitlines()
        if len(lines) > 3 or len(event.text) > 150:
            self._paste_buffer = event.text
            self._input.insert(f"[Pasted {len(lines)} lines — Tab to expand]")
            event.prevent_default()

    def submit(self) -> None:
        text = self._input.text.strip()
        if not text:
            return
        self.data.add_to_history(text)
        self.post_message(self.Submitted(text))
        self._input.load_text("")
        self._input.styles.height = 3
        self._paste_buffer = ""

    def focus_input(self) -> None:
        self._input.focus()

    def set_text(self, text: str) -> None:
        self._input.load_text(text)
        self._input.focus()

    # ── Messages ────────────────────────────────────────────────────────

    class Submitted(events.Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    class InterruptRequested(events.Message):
        pass

    class HistorySearchRequested(events.Message):
        pass

    class CompletionRequested(events.Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text
