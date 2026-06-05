"""Runs view — searchable, sortable DataTable of stored runs (R-017)."""

from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.widgets import DataTable, Input, Label

from .side_panel import SidePanel

# Each row: (run_id, status, runtime, events, date)
_Row = tuple[str, str, str, str, str]

_SORT_KEYS = ("date", "status", "runtime")


class RunsView(SidePanel):
    """List stored runs from JsonlTraceStore with live filter + sort toggle."""

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("s", "cycle_sort", "Sort"),
    ]

    def __init__(self, workspace: Path, **kwargs) -> None:
        super().__init__(workspace=workspace, **kwargs)
        self._rows: list[_Row] = []
        self._sort_idx = 0  # index into _SORT_KEYS; default "date" (descending)

    def compose(self) -> ComposeResult:
        yield Label("Runs  (type to filter · s to sort · Esc to close)", id="runs-header")
        yield Input(placeholder="Filter by id / status / runtime…", id="runs-filter")
        yield DataTable(id="runs-table")

    def on_mount(self) -> None:
        table = self.query_one("#runs-table", DataTable)
        table.add_columns("Run ID", "Status", "Runtime", "Events", "Date")
        self._rows = self._load_rows()
        if not self._rows:
            self.mount(Label("No runs stored. Run 'arc run <workflow>' to create one."))
            return
        self._populate(self._rows)
        self.query_one("#runs-filter", Input).focus()

    def _load_rows(self) -> list[_Row]:
        try:
            from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

            store = JsonlTraceStore(self.workspace / ".arc" / "traces")
            rows: list[_Row] = []
            for rid in store.list_runs()[:100]:
                rec = store.load(rid)
                if rec:
                    rows.append(
                        (
                            rid[:16],
                            rec.status.value,
                            rec.runtime or "",
                            str(len(rec.events)),
                            (rec.started_at or "")[:19],
                        )
                    )
            return rows
        except Exception as e:  # pragma: no cover - defensive
            self.mount(Label(f"Error loading runs: {e}"))
            return []

    def _sorted(self, rows: list[_Row]) -> list[_Row]:
        key = _SORT_KEYS[self._sort_idx]
        if key == "date":
            return sorted(rows, key=lambda r: r[4], reverse=True)
        if key == "status":
            return sorted(rows, key=lambda r: r[1])
        return sorted(rows, key=lambda r: r[2])  # runtime

    def _filtered(self, query: str) -> list[_Row]:
        q = query.strip().lower()
        if not q:
            return list(self._rows)
        return [
            r for r in self._rows if q in r[0].lower() or q in r[1].lower() or q in r[2].lower()
        ]

    def _populate(self, rows: list[_Row]) -> None:
        table = self.query_one("#runs-table", DataTable)
        table.clear()
        for row in self._sorted(rows):
            table.add_row(*row)

    @on(Input.Changed, "#runs-filter")
    def _on_filter(self, event: Input.Changed) -> None:
        self._populate(self._filtered(event.value))

    def action_cycle_sort(self) -> None:
        self._sort_idx = (self._sort_idx + 1) % len(_SORT_KEYS)
        query = self.query_one("#runs-filter", Input).value
        self._populate(self._filtered(query))
        self.query_one("#runs-header", Label).update(
            f"Runs  (sort: {_SORT_KEYS[self._sort_idx]} · type to filter · s to sort · Esc)"
        )
