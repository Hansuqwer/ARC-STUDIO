"""Input area widget — multi-line input with history."""

from __future__ import annotations

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, TextArea

from ..data import DataStore
from ..theme import ThemeManager


class PromptTextArea(TextArea):
    """TextArea subclass that owns Enter/Tab/Up/Down/Ctrl+R key handling.

    TextArea.check_consume_key / _on_key eats keys before they bubble to the
    parent Container. We intercept the keys that InputArea needs and post
    typed messages instead so they are handled reliably regardless of focus.
    """

    def _on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            # Submit — prevent the default newline insertion.
            event.prevent_default()
            event.stop()
            self.post_message(InputArea.SubmitRequested())
            return

        # shift+enter / ctrl+j → newline (fall through to TextArea default).
        if event.key in ("shift+enter", "ctrl+j"):
            return

        if event.key == "tab":
            event.prevent_default()
            event.stop()
            self.post_message(InputArea.TabRequested(self.text))
            return

        if event.key == "ctrl+r":
            event.prevent_default()
            event.stop()
            self.post_message(InputArea.HistorySearchRequested())
            return

        if event.key == "up":
            # Only hijack Up when caret is on the first line.
            if self.cursor_location[0] == 0:
                event.prevent_default()
                event.stop()
                self.post_message(InputArea.HistoryPrev())
                return

        if event.key == "down":
            # Only hijack Down when caret is on the last line.
            if self.cursor_location[0] == self.document.line_count - 1:
                event.prevent_default()
                event.stop()
                self.post_message(InputArea.HistoryNext())
                return

        if event.key == "ctrl+c":
            event.prevent_default()
            event.stop()
            self.post_message(InputArea.InterruptRequested())
            return


class InputArea(Container):
    """Bottom input area with a TextArea and send hint."""

    def __init__(self, data: DataStore, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self.theme = theme
        self._current_input: str = ""
        self._paste_buffer: str = ""

    def compose(self) -> ComposeResult:
        self._input = PromptTextArea(
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
            "Shift+Enter: newline  ·  Enter: send  ·  /: commands",
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

    # ── Message handlers (posted by PromptTextArea) ──────────────────────

    def on_input_area_submit_requested(self, event: "InputArea.SubmitRequested") -> None:
        self.submit()

    def on_input_area_tab_requested(self, event: "InputArea.TabRequested") -> None:
        if self._paste_buffer:
            self._input.load_text(self._paste_buffer)
            self._paste_buffer = ""
        elif event.text.strip().startswith("/"):
            self.post_message(self.CompletionRequested(event.text.strip()))

    def on_input_area_history_prev(self, event: "InputArea.HistoryPrev") -> None:
        prev = self.data.history_up(self._current_input)
        if prev is not None:
            self._input.load_text(prev)

    def on_input_area_history_next(self, event: "InputArea.HistoryNext") -> None:
        nxt = self.data.history_down()
        if nxt is not None:
            self._input.load_text(nxt)

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

    class SubmitRequested(events.Message):
        """Posted by PromptTextArea when Enter is pressed."""

    class TabRequested(events.Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text

    class HistoryPrev(events.Message):
        """Posted by PromptTextArea when Up is pressed on the first line."""

    class HistoryNext(events.Message):
        """Posted by PromptTextArea when Down is pressed on the last line."""

    class InterruptRequested(events.Message):
        pass

    class HistorySearchRequested(events.Message):
        pass

    class CompletionRequested(events.Message):
        def __init__(self, text: str) -> None:
            super().__init__()
            self.text = text
