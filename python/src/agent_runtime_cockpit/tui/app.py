"""ARC Studio Textual App — main entry point for the TUI."""

from __future__ import annotations

import os

from textual.app import App
from textual.screen import Screen

from .data import DataStore
from .screen import ArcScreen
from .theme import ThemeManager


class ArcApp(App):
    """ARC Studio — Agent Runtime Cockpit TUI."""

    CSS_PATH = "tcss/base.tcss"

    BINDINGS = [("ctrl+q", "quit", "Quit")]

    def __init__(
        self,
        data: DataStore | None = None,
        theme: ThemeManager | None = None,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self._data = data or DataStore()
        self._theme = theme or ThemeManager()

    def get_default_screen(self) -> Screen:
        # Return ArcScreen as the first screen on the stack. App.compose() must
        # yield widgets (not a Screen); yielding a Screen leaves the default
        # empty screen active → blank window.
        return ArcScreen(self._data, self._theme)

    @property
    def data(self) -> DataStore:
        return self._data

    @property
    def theme_manager(self) -> ThemeManager:
        return self._theme


def run_tui(resume_id: str | None = None) -> None:
    """Launch the ARC Studio TUI.

    Called from cli/_app.py when bare `arc` is invoked in a TTY.
    Respects ARC_NO_TUI, ARC_CLASSIC, and NO_COLOR environment variables.

    Args:
        resume_id: Optional session ID to resume from.
    """
    if os.environ.get("ARC_NO_TUI"):
        return

    if os.environ.get("ARC_CLASSIC"):
        from agent_runtime_cockpit.cli_repl.chat_repl import run_chat_repl

        run_chat_repl()
        return

    data = DataStore()

    if resume_id:
        try:
            from agent_runtime_cockpit.cli_repl.session import ChatSession

            session = ChatSession.load(resume_id)
            if session:
                data.session_id = session.id
                for msg in session.history:
                    data.add_entry(msg["role"], msg.get("content", ""))
        except Exception:
            pass  # start fresh if resume fails

    theme = ThemeManager()
    ArcApp(data=data, theme=theme).run()
