"""McpDecisionBanner — one-line MCP call risk decision inside the ActivityTray.

Subscribes to MCP_CALL_DECISION events. Renders allow/warn/deny for each
outbound MCP tool call with server_id, tool_name, and risk level.
NO_COLOR aware.
"""

from __future__ import annotations

from textual.widgets import Static

_DECISION_GLYPH = {"allow": "✓", "warn": "⚠", "deny": "✗"}
_DECISION_ASCII = {"allow": "[OK]", "warn": "[WARN]", "deny": "[DENY]"}
_DECISION_STYLE = {"allow": "bold green", "warn": "bold yellow", "deny": "bold red"}
_RISK_STYLE = {"low": "green", "medium": "yellow", "high": "red", "critical": "bold red"}


class McpDecisionBanner(Static):
    """Single-line MCP call risk decision row inside ActivityTray."""

    DEFAULT_CSS = """
    McpDecisionBanner {
        height: 1;
        width: 100%;
        padding: 0 1;
    }
    """

    def __init__(
        self,
        server_id: str,
        tool_name: str,
        decision: str,
        risk_score: str,
        reason: str = "",
        no_color: bool = False,
        **kwargs,
    ) -> None:
        super().__init__(**kwargs)
        self.server_id = server_id
        self.tool_name = tool_name
        self.decision = decision
        self.risk_score = risk_score
        self.reason = reason
        self.no_color = no_color

    def render(self) -> str:
        glyph = _DECISION_ASCII[self.decision] if self.no_color else _DECISION_GLYPH.get(self.decision, "?")
        d_style = _DECISION_STYLE.get(self.decision, "")
        r_style = _RISK_STYLE.get(self.risk_score, "")
        tool = f"{self.server_id}/{self.tool_name}"
        if self.no_color:
            return f"{glyph} {tool} risk={self.risk_score.upper()}"
        return (
            f"[{d_style}]{glyph}[/] {tool} "
            f"[{r_style}]risk={self.risk_score}[/]"
        )


__all__ = ["McpDecisionBanner"]
