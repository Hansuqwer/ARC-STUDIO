"""ARC Studio TUI — Textual-based interactive agentic cockpit.

Phase 4.1: Interactive shell skeleton with:
- ArcApp: Textual App subclass (main entry)
- ArcScreen: Primary chat screen (banner + transcript + status + input)
- DataStore: Reactive state container
- ThemeManager: Dark/light/no-color theme switching
- Widgets: Banner, StatusBar, InputArea, Transcript, MessageWidget

Usage:
    arc          → Launches TUI (when TTY + not ARC_NO_TUI)
    arc tui      → Explicit TUI launch
    ARC_CLASSIC=1 arc → Existing inline REPL fallback
"""

from .app import ArcApp, run_tui
from .data import DataStore
from .screen import ArcScreen
from .theme import ThemeManager

__all__ = ["ArcApp", "ArcScreen", "DataStore", "ThemeManager", "run_tui"]
