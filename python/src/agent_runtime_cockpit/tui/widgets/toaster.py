"""Toaster — transient notification toasts in the bottom-right corner.

Implements UX_AUDIT R-014. Shows 1-line notifications that auto-dismiss
after a configurable timeout. Severity: info/success/warning/error.
NO_COLOR aware.
"""

from __future__ import annotations

import asyncio
from typing import Literal

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label

Severity = Literal["info", "success", "warning", "error"]

_SEVERITY_STYLE: dict[Severity, str] = {
    "info": "bold cyan",
    "success": "bold green",
    "warning": "bold yellow",
    "error": "bold red",
}
_SEVERITY_GLYPH: dict[Severity, str] = {
    "info": "ℹ",
    "success": "✓",
    "warning": "⚠",
    "error": "✗",
}
_SEVERITY_ASCII: dict[Severity, str] = {
    "info": "[I]",
    "success": "[OK]",
    "warning": "[!]",
    "error": "[E]",
}


class _Toast(Label):
    """Single toast notification row."""

    DEFAULT_CSS = """
    _Toast {
        height: 1;
        width: auto;
        padding: 0 1;
        margin-bottom: 0;
    }
    """

    def __init__(self, message: str, severity: Severity, no_color: bool = False, **kwargs) -> None:
        text = self._format(message, severity, no_color)
        super().__init__(text, **kwargs)

    @staticmethod
    def _format(message: str, severity: Severity, no_color: bool) -> str:
        if no_color:
            return f"{_SEVERITY_ASCII[severity]} {message}"
        style = _SEVERITY_STYLE[severity]
        glyph = _SEVERITY_GLYPH[severity]
        return f"[{style}]{glyph}[/] {message}"


class Toaster(Container):
    """Bottom-right notification area.

    Usage:
        toaster = self.query_one("#toaster", Toaster)
        toaster.show("File saved", severity="success")
    """

    DEFAULT_CSS = """
    Toaster {
        dock: bottom;
        align: right bottom;
        width: auto;
        height: auto;
        padding: 0;
        background: transparent;
        layer: overlay;
    }
    """

    def __init__(self, no_color: bool = False, **kwargs) -> None:
        super().__init__(id="toaster", **kwargs)
        self._no_color = no_color

    def compose(self) -> ComposeResult:
        return iter([])  # starts empty

    def show(self, message: str, severity: Severity = "info", timeout: float = 3.0) -> None:
        """Display a toast that auto-dismisses after *timeout* seconds."""
        toast = _Toast(message, severity=severity, no_color=self._no_color)
        self.mount(toast)
        self.call_after_refresh(self._schedule_dismiss, toast, timeout)

    def _schedule_dismiss(self, toast: _Toast, timeout: float) -> None:
        async def _dismiss() -> None:
            await asyncio.sleep(timeout)
            if toast.is_attached:
                toast.remove()

        self.call_later(_dismiss)


__all__ = ["Toaster", "Severity"]
