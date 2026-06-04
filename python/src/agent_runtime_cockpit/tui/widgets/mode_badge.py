"""ModeBadge — visible Plan/Build/Auto/Review chip in the header.

Implements UX_AUDIT R-003. Cycles via Shift+Tab handled by ArcScreen.
"""

from __future__ import annotations

from typing import Literal

from textual.widgets import Static

from ..data import DataStore
from ..theme import ThemeManager

Mode = Literal["plan", "build", "auto", "review"]
_CYCLE: tuple[Mode, ...] = ("plan", "build", "auto", "review")

_GLYPHS: dict[Mode, str] = {
    "plan": "\u25b2",  # ▲
    "build": "\u25a0",  # ■
    "auto": "\u25b6",  # ▶
    "review": "\u25c6",  # ◆
}
_ASCII_LABELS: dict[Mode, str] = {
    "plan": "(plan)",
    "build": "(build)",
    "auto": "(auto)",
    "review": "(review)",
}
_STYLES: dict[Mode, str] = {
    "plan": "bold yellow",
    "build": "bold cyan",
    "auto": "bold red",
    "review": "bold magenta",
}


class ModeBadge(Static):
    """Small colored chip showing the current agent mode."""

    DEFAULT_CSS = """
    ModeBadge {
        width: auto;
        height: 1;
        padding: 0 1;
        content-align: center middle;
    }
    """

    def __init__(self, data: DataStore, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self.theme = theme

    def render(self) -> str:
        mode = self._current_mode()
        no_color = bool(getattr(self.theme.current, "no_color", False))
        if no_color:
            return _ASCII_LABELS[mode]
        return f"[{_STYLES[mode]}]{_GLYPHS[mode]} {mode}[/]"

    def _current_mode(self) -> Mode:
        raw = getattr(self.data, "mode", "build")
        if raw in _CYCLE:
            return raw  # type: ignore[return-value]
        return "build"

    def cycle(self) -> Mode:
        """Advance to the next mode and return it."""
        current = self._current_mode()
        idx = _CYCLE.index(current)
        nxt = _CYCLE[(idx + 1) % len(_CYCLE)]
        self.data.mode = nxt
        self.refresh()
        return nxt

    def set_mode(self, mode: Mode) -> None:
        """Jump directly to a named mode."""
        if mode in _CYCLE:
            self.data.mode = mode
            self.refresh()


__all__ = ["ModeBadge", "Mode"]
