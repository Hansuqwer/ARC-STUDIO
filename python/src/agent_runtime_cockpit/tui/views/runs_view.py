"""Runs view — sortable DataTable of stored runs."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Label

from .side_panel import SidePanel


class RunsView(SidePanel):
    """List stored runs from JsonlTraceStore."""

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    def __init__(self, workspace: Path, **kwargs) -> None:
        super().__init__(workspace=workspace, **kwargs)

    def compose(self) -> ComposeResult:
        yield DataTable(id="runs-table")

    def on_mount(self) -> None:
        table = self.query_one("#runs-table", DataTable)
        table.add_columns("Run ID", "Status", "Runtime", "Events", "Date")
        try:
            from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

            store = JsonlTraceStore(self.workspace / ".arc" / "traces")
            run_ids = store.list_runs()[:100]
            if not run_ids:
                self.mount(Label("No runs stored. Run 'arc run <workflow>' to create one."))
                return
            for rid in run_ids:
                rec = store.load(rid)
                if rec:
                    table.add_row(
                        rid[:16],
                        rec.status.value,
                        rec.runtime or "",
                        str(len(rec.events)),
                        (rec.started_at or "")[:19],
                    )
        except Exception as e:
            self.mount(Label(f"Error loading runs: {e}"))
