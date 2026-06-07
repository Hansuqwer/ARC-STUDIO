"""ContextMeter — header-inline context usage indicator.

Implements UX_AUDIT R-002. Reads from DataStore.total_tokens. The full
overlay (mockup 05) ships as a separate view in Phase P1.
"""

from __future__ import annotations

from textual.widgets import Static

from ..data import DataStore
from ..theme import ThemeManager

# Soft baseline used only until an active model's real limit is wired via
# DataStore.context_limit. 200k reflects current mainstream model context
# windows (Claude/GPT-class) far better than the old 64k guess.
_DEFAULT_CONTEXT_LIMIT = 200_000


class ContextMeter(Static):
    """One-line `ctx N% · used/total tok` chip."""

    DEFAULT_CSS = """
    ContextMeter {
        width: auto;
        height: 1;
        padding: 0 1;
        content-align: right middle;
    }
    """

    def __init__(self, data: DataStore, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self.theme = theme

    def render(self) -> str:
        used = int(getattr(self.data, "total_tokens", 0) or 0)
        limit = int(getattr(self.data, "context_limit", 0) or _DEFAULT_CONTEXT_LIMIT)
        if limit <= 0:
            return f"tok {used}"
        pct = min(100, int(used * 100 / max(1, limit)))
        no_color = bool(getattr(self.theme.current, "no_color", False))
        bucket = "calm" if pct < 60 else "notice" if pct < 80 else "warn" if pct < 95 else "danger"
        if no_color:
            return f"ctx {pct}% [{bucket}] {used:>5}/{limit}"
        style_map = {
            "calm": "dim",
            "notice": "cyan",
            "warn": "yellow",
            "danger": "bold red",
        }
        style = style_map[bucket]
        return f"[{style}]ctx {pct}% \u00b7 {used}/{limit} tok[/]"


__all__ = ["ContextMeter"]
