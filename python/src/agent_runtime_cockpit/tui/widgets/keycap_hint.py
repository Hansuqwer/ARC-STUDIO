"""KeycapHint — inline keycap chip for affordance hints (R-015).

Renders a key name as a 1px-bordered chip: [y] [Esc] [Ctrl+P].
NO_COLOR: plain [key] bracket form without markup.
Color: dim white border, regular fg text.
"""

from __future__ import annotations

from textual.widgets import Static


class KeycapHint(Static):
    """Renders a single key name as an inline bordered chip.

    Usage in Rich markup context (e.g. inside a Static.render string):
        call `KeycapHint.markup("Ctrl+P")` → "[dim][[/dim]Ctrl+P[dim]][/dim]"

    As a standalone widget:
        yield KeycapHint("Ctrl+P")
    """

    DEFAULT_CSS = """
    KeycapHint {
        width: auto;
        height: 1;
        padding: 0 0;
    }
    """

    def __init__(self, key: str, no_color: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._key = key
        self._no_color = no_color

    def render(self) -> str:
        return self.markup(self._key, no_color=self._no_color)

    @staticmethod
    def markup(key: str, *, no_color: bool = False) -> str:
        """Return Rich markup for an inline keycap chip."""
        if no_color:
            return f"[{key}]"
        return f"[dim][[/dim][bold]{key}[/bold][dim]][/dim]"


__all__ = ["KeycapHint"]
