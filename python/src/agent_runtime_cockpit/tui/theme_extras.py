"""Theme extras — NO_COLOR glyph fallbacks and ARC_REDUCED_MOTION helper.

Implements UX_AUDIT P3 R-044 and R-045.

Usage:
    from agent_runtime_cockpit.tui.theme_extras import glyph, is_reduced_motion

    status_icon = glyph("●", alt="[*]", no_color=no_color)
    if not is_reduced_motion():
        self._start_spinner()
"""

from __future__ import annotations

import os

# Maps Unicode glyph → ASCII/text fallback used when NO_COLOR is set.
_FALLBACK: dict[str, str] = {
    "●": "[*]",
    "○": "[ ]",
    "✓": "[OK]",
    "✗": "[X]",
    "⊘": "[/]",
    "⚠": "[!]",
    "ℹ": "[i]",
    "▲": "(plan)",
    "■": "(build)",
    "▶": "(auto)",
    "◆": "(review)",
    "→": "->",
    "←": "<-",
    "…": "...",
    "·": ".",
    "┌": "+",
    "┐": "+",
    "└": "+",
    "┘": "+",
    "─": "-",
    "│": "|",
    "╭": "+",
    "╮": "+",
    "╰": "+",
    "╯": "+",
}


def glyph(unicode_char: str, *, alt: str | None = None, no_color: bool = False) -> str:
    """Return *unicode_char* unless NO_COLOR is active, in which case return the fallback.

    *alt* overrides the built-in fallback table.
    """
    if not no_color:
        return unicode_char
    if alt is not None:
        return alt
    return _FALLBACK.get(unicode_char, unicode_char)


def is_reduced_motion() -> bool:
    """Return True when ARC_REDUCED_MOTION=1 (or any truthy value) is set."""
    val = os.environ.get("ARC_REDUCED_MOTION", "0").strip().lower()
    return val in ("1", "true", "yes", "on")


def thinking_indicator(no_color: bool = False) -> str:
    """Return the 'Thinking…' indicator string, respecting NO_COLOR and ARC_REDUCED_MOTION."""
    if is_reduced_motion():
        return "Thinking..."
    if no_color:
        return "[*] Thinking..."
    return "● Thinking…"


__all__ = ["glyph", "is_reduced_motion", "thinking_indicator", "_FALLBACK"]
