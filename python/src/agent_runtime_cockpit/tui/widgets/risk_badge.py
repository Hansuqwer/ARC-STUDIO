"""RiskBadge — inline risk level chip (R-016).

Renders ●low / ●medium / ●high / ●critical with semantic colors.
NO_COLOR fallback: [L] / [M] / [H] / [C].
"""

from __future__ import annotations

from typing import Literal

from textual.widgets import Static

RiskLevel = Literal["low", "medium", "high", "critical"]

_COLOR: dict[RiskLevel, str] = {
    "low": "green",
    "medium": "yellow",
    "high": "red",
    "critical": "bold red",
}
_ASCII: dict[RiskLevel, str] = {
    "low": "[L]",
    "medium": "[M]",
    "high": "[H]",
    "critical": "[C]",
}


class RiskBadge(Static):
    """Displays a colored risk level chip.

    Usage as a standalone widget:
        yield RiskBadge("high")

    Usage as inline markup:
        RiskBadge.markup("high")  → "[red]●high[/]"
    """

    DEFAULT_CSS = """
    RiskBadge {
        width: auto;
        height: 1;
    }
    """

    def __init__(self, level: RiskLevel, no_color: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self._level = level
        self._no_color = no_color

    def render(self) -> str:
        return self.markup(self._level, no_color=self._no_color)

    @staticmethod
    def markup(level: str, *, no_color: bool = False) -> str:
        """Return Rich markup for an inline risk badge."""
        level = level.lower()
        if no_color:
            return _ASCII.get(level, f"[{level}]")  # type: ignore[arg-type]
        color = _COLOR.get(level, "white")  # type: ignore[arg-type]
        return f"[{color}]●{level}[/]"


__all__ = ["RiskBadge", "RiskLevel"]
