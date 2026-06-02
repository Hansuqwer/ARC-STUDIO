"""Help screen overlay."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import ModalScreen
from textual.widgets import Label, VerticalScroll

_HELP_TEXT = """ARC Studio — Help
═══════════════════════════════════════════════════════════
KEYBOARD SHORTCUTS
──────────────────
  Enter              Submit message
  Shift+Enter        Insert newline
  Ctrl+C (once)      Interrupt agent
  Ctrl+C (twice)     Exit ARC Studio
  Ctrl+D             Exit (from empty input)
  Ctrl+P / Ctrl+K    Command palette
  Ctrl+R             History search
  Ctrl+L             Scroll to bottom
  Ctrl+O             Expand/collapse tool card
  Ctrl+T             Export transcript
  Esc                Cancel / interrupt
  Up / Down          Input history
  Tab                Autocomplete
  F1 / ?             This help

SLASH COMMANDS
──────────────
  /help              Show this help
  /clear             Clear transcript
  /exit, /quit       Exit ARC Studio
  /sessions          List & switch sessions
  /theme             Toggle dark/light theme
  /version           Show version
  /status            Show workspace status
  /doctor            Run diagnostics
  /runs              List stored runs
  /runtimes          List detected runtimes
  /hitl              HITL pending prompts
  /profiles          List run profiles

SHELL ESCAPE
────────────
  !<command>         Run shell command directly"""


class HelpScreen(ModalScreen):
    """Scrollable help overlay."""

    BINDINGS = [Binding("escape", "dismiss", "Close"), Binding("f1", "dismiss", "Close")]

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label(_HELP_TEXT)
