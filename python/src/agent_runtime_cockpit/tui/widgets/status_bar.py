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
        # P0-4: token usage meter
        no_color = bool(getattr(self.theme.current, "no_color", False))
        tok = self.data.total_tokens
        lim = self.data.context_limit
        if lim > 0:
            pct = int(tok / lim * 100)
            if no_color:
                tier = "[low]" if pct < 60 else "[warn]" if pct < 85 else "[hot]"
                tok_str = f"{tier} tok {tok}/{lim} ({pct}%)"
            else:
                color = "green" if pct < 60 else "yellow" if pct < 85 else "red"
                tok_str = f"[{color}]tok {tok}/{lim} ({pct}%)[/]"
        else:
            tok_str = f"tok {tok}"
        model_str = ""
        if getattr(self.data, "current_provider", None) or getattr(
            self.data, "current_model", None
        ):
            p = getattr(self.data, "current_provider", "") or ""
            m = (getattr(self.data, "current_model", "") or "").split("/")[-1][:20]
            model_str = f" │ {p}/{m}" if p else f" │ {m}"
        # QuotaWarning flash
        warning_str = ""
        warnings = getattr(self.data, "quota_warnings", [])
        if warnings:
            latest = warnings[-1]
            pct = latest.usage_pct
            if no_color:
                warning_str = " [WARN]" if pct < 1.0 else " [CRITICAL]"
            else:
                warning_str = " [yellow]⚠[/]" if pct < 1.0 else " [bold red]🛑[/]"
        line = (
            f" {self.data.mode} │ {self.data.runtime_mode}{paid_indicator}{model_str} │ {ws} │ "
            f"{session_short} │ {cost} │ {tok_str}{warning_str} │"
            f" {daemon_dot}{stream_indicator} │"
            f" Esc:cancel  /:commands  Ctrl+P:palette"
        )
        if len(line) > width:
            line = line[: width - 1] + "…"
        return line
