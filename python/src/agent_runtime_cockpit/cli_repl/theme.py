"""Theme for the ARC Studio interactive shell.

Stable labels, colors, and an ASCII/Unicode box fallback. Kept tiny and
dependency-light so rendering stays deterministic and testable.
"""

from __future__ import annotations

import os
import sys

from rich import box

# CommandResult.state -> (display label, rich style)
STATE_STYLES: dict[str, tuple[str, str]] = {
    "present": ("ok", "green"),
    "ok": ("ok", "green"),
    "absent": ("empty", "yellow"),
    "empty": ("empty", "yellow"),
    "blocked": ("blocked", "red"),
    "denied": ("denied", "red"),
    "degraded": ("degraded", "yellow"),
    "error": ("error", "red"),
    "failed": ("error", "red"),
}

# message block kind -> (title, border style)
BLOCK_STYLES: dict[str, tuple[str, str]] = {
    "user": ("User", "cyan"),
    "assistant": ("Assistant", "green"),
    "tool": ("Tool", "magenta"),
    "system": ("System", "blue"),
    "warning": ("Warning", "yellow"),
    "error": ("Error", "red"),
}

# Slash commands surfaced as the idle command palette.
PALETTE = ["/help", "/status", "/model", "/session", "/tools", "/sandbox", "/clear", "/exit"]


def ascii_only() -> bool:
    """True when the terminal cannot be trusted with Unicode box characters."""
    if os.environ.get("ARC_ASCII") == "1":
        return True
    encoding = (getattr(sys.stdout, "encoding", "") or "").lower()
    return "utf" not in encoding


def panel_box(use_ascii: bool | None = None) -> box.Box:
    """Return the box style for panels (ASCII fallback or simple Unicode)."""
    if use_ascii is None:
        use_ascii = ascii_only()
    return box.ASCII if use_ascii else box.SQUARE


def state_style(state: str) -> tuple[str, str]:
    """Return (label, style) for a CommandResult state."""
    return STATE_STYLES.get(state, (state, "white"))
