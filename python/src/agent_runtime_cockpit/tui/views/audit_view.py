"""Audit view — list recent sandbox audit events."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import DataTable, Label

from .side_panel import SidePanel


class AuditView(SidePanel):
    """Show last 50 sandbox audit events."""

    def __init__(self, workspace: Path, **kwargs) -> None:
        super().__init__(workspace=workspace, **kwargs)

    def compose(self) -> ComposeResult:
        yield DataTable(id="audit-table")

    def on_mount(self) -> None:
        table = self.query_one("#audit-table", DataTable)
        table.add_columns("Time", "Command", "Decision", "Provider")
        try:
            import json

            audit_file = Path.home() / ".arc" / "audit" / "sandbox.events.jsonl"
            if not audit_file.exists():
                self.mount(Label("No audit events found. Run 'arc sandbox run' first."))
                return
            lines = audit_file.read_text().splitlines()[-50:]
            for line in lines:
                try:
                    ev = json.loads(line)
                    cmd = " ".join(ev.get("command", []))[:30]
                    table.add_row(
                        ev.get("started_at", "")[:19],
                        cmd,
                        "allow" if ev.get("allowed") else "deny",
                        ev.get("provider", ""),
                    )
                except Exception:
                    continue
        except Exception as e:
            self.mount(Label(f"Error loading audit: {e}"))
