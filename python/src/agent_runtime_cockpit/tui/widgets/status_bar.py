"""Status bar widget — 1-line footer."""

from __future__ import annotations

from pathlib import Path

from textual.widgets import Static

from ..data import DataStore
from ..theme import ThemeManager


class StatusBar(Static):
    """Persistent bottom status bar."""

    def __init__(self, data: DataStore, theme: ThemeManager, **kwargs) -> None:
        super().__init__(**kwargs)
        self.data = data
        self.theme = theme

    def render(self) -> str:
        width = self.size.width if self.size else 80
        ws = str(self.data.workspace)
        home = str(Path.home())
        if ws.startswith(home):
            ws = "~" + ws[len(home) :]
        if len(ws) > 30:
            ws = "…" + ws[-29:]
        cost = f"${self.data.total_cost_usd:.4f}" if self.data.total_cost_usd > 0 else "$0"
        session_short = self.data.session_id[:8] if self.data.session_id else "--------"
        daemon_dot = "●" if self.data.daemon_online else "○"
        stream_indicator = " ● streaming" if self.data.is_streaming else ""
        paid_indicator = " $paid" if getattr(self.data, "allow_paid", False) else ""
        model_str = ""
        if getattr(self.data, "current_provider", None) or getattr(
            self.data, "current_model", None
        ):
            p = getattr(self.data, "current_provider", "") or ""
            m = (getattr(self.data, "current_model", "") or "").split("/")[-1][:20]
            model_str = f" │ {p}/{m}" if p else f" │ {m}"
        line = (
            f" {self.data.mode} │ {self.data.runtime_mode}{paid_indicator}{model_str} │ {ws} │ "
            f"{session_short} │ {cost} │"
            f" {daemon_dot}{stream_indicator} │"
            f" Esc:cancel  /:commands  Ctrl+P:palette"
        )
        if len(line) > width:
            line = line[: width - 1] + "…"
        return line
