"""Banner widget — 3-line startup header with logo, version, workspace, daemon."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import Static

from agent_runtime_cockpit import __version__

from ..data import DataStore
from ..theme import ThemeManager


class Banner(Static):
    """Top-of-screen banner. Collapses to 1 line at < 24 rows."""

    def __init__(self, data: DataStore, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self.theme = theme
        self._compact = False

    def on_resize(self, event) -> None:
        self._compact = event.size.height < 24
        self.refresh()

    def render(self) -> str:
        if self._compact:
            return self._render_compact()
        return self._render_full()

    def _render_full(self) -> str:
        ws = str(self.data.workspace)
        home = str(Path.home())
        if ws.startswith(home):
            ws = "~" + ws[len(home) :]
        daemon_dot = "●" if self.data.daemon_online else "○"
        daemon_text = f"daemon {daemon_dot} {'online' if self.data.daemon_online else 'offline'}"
        lines = [
            f"  █████╗ ██████╗  ██████╗     ARC Studio v{__version__}",
            f" ██╔══██╗██╔══██╗██╔════╝     {ws}",
            f" ███████║██████╔╝██║          {daemon_text}  ·  /help for commands",
        ]
        return "\n".join(lines)

    def _render_compact(self) -> str:
        ws = str(self.data.workspace)
        home = str(Path.home())
        if ws.startswith(home):
            ws = "~" + ws[len(home) :]
        return f" ARC Studio v{__version__} | {ws} | /help"
