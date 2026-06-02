"""Runtimes view — DataTable of detected runtimes and capabilities."""

from __future__ import annotations

from pathlib import Path

from textual.app import ComposeResult
from textual.widgets import DataTable, Label

from .side_panel import SidePanel


class RuntimesView(SidePanel):
    """Show detected runtimes from RuntimeRouter."""

    def __init__(self, workspace: Path, **kwargs) -> None:
        super().__init__(workspace=workspace, **kwargs)

    def compose(self) -> ComposeResult:
        yield DataTable(id="runtimes-table")

    def on_mount(self) -> None:
        table = self.query_one("#runtimes-table", DataTable)
        table.add_columns("Runtime", "Detected", "Can Run", "Paid")
        try:
            from agent_runtime_cockpit.orchestration.runtime_router import RuntimeRouter

            router = RuntimeRouter(self.workspace)
            runtimes = router.list_runtimes(self.workspace)
            if not runtimes:
                self.mount(Label("No runtimes detected."))
                return
            for rt in runtimes:
                table.add_row(
                    rt.get("id", ""),
                    "yes" if rt.get("detected") else "no",
                    "yes" if rt.get("can_run") else "no",
                    "yes" if rt.get("paid") else "no",
                )
        except Exception as e:
            self.mount(Label(f"Error loading runtimes: {e}"))
