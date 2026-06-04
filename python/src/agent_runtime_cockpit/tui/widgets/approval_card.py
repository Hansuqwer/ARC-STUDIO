"""ApprovalCard — universal approval modal for all gate types.

Implements UX_AUDIT R-007. Replaces the HITL-only ApprovalBar with a
richer card that handles:
  - HITL (human-in-the-loop)
  - CAPABILITY_CARD_DECISION (deny/warn)
  - MCP_CALL_DECISION (block/warn)
  - Paid-call gate
  - Trust denial

Keys: y=allow  n=deny  a=always-allow  Esc=deny
NO_COLOR aware: renders ASCII box instead of rich borders.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from textual import events
from textual.app import ComposeResult
from textual.containers import Container
from textual.screen import ModalScreen
from textual.widgets import Label

GateKind = Literal["hitl", "capability", "mcp", "paid", "trust", "shell"]

_KIND_LABEL: dict[GateKind, str] = {
    "hitl": "HITL approval required",
    "capability": "Capability Card decision",
    "mcp": "MCP outbound call risk",
    "paid": "Paid call gate",
    "trust": "Workspace trust required",
    "shell": "Shell command approval",
}
_KIND_STYLE: dict[GateKind, str] = {
    "hitl": "bold yellow",
    "capability": "bold cyan",
    "mcp": "bold red",
    "paid": "bold magenta",
    "trust": "bold red",
    "shell": "bold yellow",
}


@dataclass
class ApprovalRequest:
    kind: GateKind
    prompt_id: str
    detail: str = ""
    remediation: str = ""
    risk_level: str = ""
    on_decision: Callable[[str], None] | None = None


class ApprovalCard(ModalScreen[str]):
    """Universal approval modal. Dismisses with 'allow'/'deny'/'always'."""

    DEFAULT_CSS = """
    ApprovalCard {
        align: center middle;
    }
    #card-container {
        background: $surface;
        border: tall $accent;
        padding: 1 2;
        width: 60;
        max-width: 80;
        height: auto;
    }
    #card-title {
        text-style: bold;
        margin-bottom: 1;
    }
    #card-detail {
        margin-bottom: 1;
    }
    #card-remediation {
        color: $text-muted;
        margin-bottom: 1;
    }
    #card-risk {
        color: $warning;
        margin-bottom: 1;
    }
    #card-keys {
        text-style: dim;
        margin-top: 1;
    }
    """

    def __init__(self, request: ApprovalRequest, no_color: bool = False, **kwargs) -> None:
        super().__init__(**kwargs)
        self.request = request
        self.no_color = no_color

    def compose(self) -> ComposeResult:
        r = self.request
        label_text = _KIND_LABEL.get(r.kind, "Approval required")
        style = _KIND_STYLE.get(r.kind, "bold")

        if self.no_color:
            title = f"[{label_text.upper()}] {r.prompt_id}"
        else:
            title = f"[{style}]{label_text}[/] — {r.prompt_id}"

        with Container(id="card-container"):
            yield Label(title, id="card-title")
            if r.detail:
                yield Label(r.detail, id="card-detail")
            if r.risk_level:
                risk_label = (
                    f"Risk: {r.risk_level.upper()}"
                    if self.no_color
                    else f"[bold red]Risk: {r.risk_level.upper()}[/]"
                )
                yield Label(risk_label, id="card-risk")
            if r.remediation:
                yield Label(f"→ {r.remediation}", id="card-remediation")
            yield Label(
                "[y] Allow  [n] Deny  [a] Always allow  [Esc] Deny",
                id="card-keys",
            )

    def on_key(self, event: events.Key) -> None:
        decision: str | None = None
        if event.key == "y":
            decision = "allow"
        elif event.key in ("n", "escape"):
            decision = "deny"
        elif event.key == "a":
            decision = "always"
        if decision is not None:
            event.stop()
            if self.request.on_decision:
                self.request.on_decision(decision)
            self.dismiss(decision)


__all__ = ["ApprovalCard", "ApprovalRequest", "GateKind"]
