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
        # Assigned before super().__init__ because Textual's App init reads
        # get_css_variables(), which needs the theme present.
        self._data = data or DataStore()
        self._theme = theme or ThemeManager()
        super().__init__(**kwargs)

    def get_default_screen(self) -> Screen:
        # Return ArcScreen as the first screen on the stack. App.compose() must
        # yield widgets (not a Screen); yielding a Screen leaves the default
        # empty screen active → blank window.
        return ArcScreen(self._data, self._theme)

    def get_css_variables(self) -> dict[str, str]:
        """Inject the active theme's tokens so base.tcss ($background, …) re-skins.

        Merged on top of Textual's built-ins; calling ``reskin()`` after a theme
        change re-reads these.
        """
        variables = super().get_css_variables()
        theme = getattr(self, "_theme", None)
        if theme is None:
            return variables
        t = theme.current
        variables.update(
            {
                "background": t.background,
                "foreground": t.foreground,
                "surface": t.surface,
                "input-bg": t.input_bg,
                "border": t.border,
                "border-focus": t.border_focus,
                "muted": t.muted,
                "accent": t.accent,
                "success": t.success,
                "error": t.error,
                "warning": t.warning,
                "info": t.info,
            }
        )
        return variables

    def reskin(self) -> None:
        """Re-apply CSS variables after a theme change (best-effort)."""
        try:
            self.refresh_css(animate=False)
        except Exception:
            pass

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
