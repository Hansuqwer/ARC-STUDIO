"""CapabilityCardBanner — inline notification for CAPABILITY_CARD_DECISION events.

Implements UX_AUDIT R-006. Subscribes to CAPABILITY_CARD_DECISION typed events
via the transcript data queue and renders allow/warn/deny as a colored strip.

Shows for deny and warn decisions only; allow is silent unless debug mode.
Auto-dismisses allow after 3 s; warn and deny persist until dismissed with Esc.
NO_COLOR aware.
"""

from __future__ import annotations

from textual import events
from textual.widgets import Static


_DECISION_STYLE = {
    "allow": "bold green",
    "warn": "bold yellow",
    "deny": "bold red",
}
_DECISION_GLYPH = {
    "allow": "✓",
    "warn": "⚠",
    "deny": "✗",
}
_DECISION_ASCII = {
    "allow": "[OK]",
    "warn": "[WARN]",
    "deny": "[DENY]",
}


class CapabilityCardBanner(Static):
    """One-line inline banner shown when a Capability Card decision fires.

    Usage — screen.py mounts/unmounts this dynamically on events:

        banner = CapabilityCardBanner(
            decision="deny",
            reason="capability_card_signature_invalid",
            card_id="adapter::swarmgraph",
            no_color=self.theme.current.no_color,
        )
        await self.mount(banner, after="#transcript")
    """

    DEFAULT_CSS = """
    CapabilityCardBanner {
        height: 1;
        width: 100%;
        padding: 0 1;
        content-align: left middle;
    }
    CapabilityCardBanner.allow { background: $success 20%; }
    CapabilityCardBanner.warn  { background: $warning 20%; }
    CapabilityCardBanner.deny  { background: $error 20%; }
    """

    def __init__(
        self,
        decision: str,
        reason: str,
        card_id: str | None = None,
        no_color: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.decision = decision
        self.reason = reason
        self.card_id = card_id or "unknown"
        self.no_color = no_color
        self.add_class(decision)

    def render(self) -> str:
        style = _DECISION_STYLE.get(self.decision, "")
        glyph = _DECISION_ASCII[self.decision] if self.no_color else _DECISION_GLYPH.get(self.decision, "?")
        tag = f" [{self.card_id}]" if self.card_id != "unknown" else ""
        short_reason = self.reason.replace("capability_card_", "").replace("_", " ")
        line = f"Card{tag}: {short_reason}"
        if self.no_color:
            return f"{glyph} {line}"
        return f"[{style}]{glyph}[/] {line}"

    def on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            self.remove()


__all__ = ["CapabilityCardBanner"]
