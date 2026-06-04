"""ActivityTray — Ctrl+X slide-in panel showing live security decisions.

Implements UX_AUDIT R-008. Shows:
  - MCP_CALL_DECISION events (McpDecisionBanner rows)
  - CAPABILITY_CARD_DECISION events (CapabilityCardBanner rows)
  - Recent shell escape decisions

Toggled via Ctrl+X (action_toggle_activity on ArcScreen).
Renders last N_MAX entries; oldest drops off top.
NO_COLOR aware.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Literal

from textual.app import ComposeResult
from textual.containers import Container, VerticalScroll
from textual.widgets import Label

from .mcp_banner import McpDecisionBanner
from .capability_banner import CapabilityCardBanner

N_MAX = 20
EventKind = Literal["mcp_call", "capability_card", "shell"]


@dataclass
class _ActivityEntry:
    kind: EventKind
    payload: dict


class ActivityTray(Container):
    """Side panel listing the last N_MAX security gate decisions."""

    DEFAULT_CSS = """
    ActivityTray {
        dock: right;
        width: 40;
        height: 100%;
        background: $surface;
        border-left: tall $accent;
        display: none;
        padding: 0;
    }
    ActivityTray.visible {
        display: block;
    }
    #tray-title {
        height: 1;
        background: $accent;
        color: $text;
        padding: 0 1;
        text-style: bold;
    }
    #tray-scroll {
        height: 1fr;
    }
    """

    def __init__(self, no_color: bool = False, **kwargs) -> None:
        super().__init__(id="activity-tray", **kwargs)
        self.no_color = no_color
        self._entries: deque[_ActivityEntry] = deque(maxlen=N_MAX)

    def compose(self) -> ComposeResult:
        yield Label("⚡ Activity  [Ctrl+X to close]", id="tray-title")
        with VerticalScroll(id="tray-scroll"):
            yield Label("(no activity yet)", id="tray-empty")

    # ── Public API ────────────────────────────────────────────────────────

    def toggle(self) -> None:
        self.toggle_class("visible")

    def push_mcp_decision(self, payload: dict) -> None:
        entry = _ActivityEntry(kind="mcp_call", payload=payload)
        self._entries.append(entry)
        self._refresh_rows()

    def push_capability_decision(self, payload: dict) -> None:
        entry = _ActivityEntry(kind="capability_card", payload=payload)
        self._entries.append(entry)
        self._refresh_rows()

    def push_shell_decision(self, payload: dict) -> None:
        entry = _ActivityEntry(kind="shell", payload=payload)
        self._entries.append(entry)
        self._refresh_rows()

    # ── Internal ──────────────────────────────────────────────────────────

    def _refresh_rows(self) -> None:
        try:
            scroll = self.query_one("#tray-scroll", VerticalScroll)
        except Exception:
            # Widget not yet mounted (e.g. in unit tests) — skip DOM update.
            return
        scroll.remove_children()
        if not self._entries:
            scroll.mount(Label("(no activity yet)", id="tray-empty"))
            return
        for entry in reversed(self._entries):
            if entry.kind == "mcp_call":
                p = entry.payload
                scroll.mount(
                    McpDecisionBanner(
                        server_id=p.get("server_id", "?"),
                        tool_name=p.get("tool_name", "?"),
                        decision=p.get("decision", "allow"),
                        risk_score=p.get("risk_score", "low"),
                        reason=p.get("reason", ""),
                        no_color=self.no_color,
                    )
                )
            elif entry.kind == "capability_card":
                p = entry.payload
                scroll.mount(
                    CapabilityCardBanner(
                        decision=p.get("decision", "allow"),
                        reason=p.get("reason", ""),
                        card_id=p.get("card_id"),
                        no_color=self.no_color,
                    )
                )
            else:
                p = entry.payload
                decision = p.get("decision", "allow")
                cmd = p.get("command", "")[:30]
                label = f"{'[OK]' if decision == 'allow' else '[DENY]'} shell: {cmd}" if self.no_color else f"{'✓' if decision == 'allow' else '✗'} shell: {cmd}"
                scroll.mount(Label(label))


__all__ = ["ActivityTray"]
