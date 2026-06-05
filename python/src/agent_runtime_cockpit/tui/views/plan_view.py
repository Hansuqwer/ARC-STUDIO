"""PlanView — read-only predicted-plan panel for Plan mode (UX_AUDIT R-012).

Renders a deterministic SimulationReport (from simulation/simulator.py) as a
read-only plan: predicted side effects, tool calls, gates, and cost. No
execution, no network, no writes — Plan mode is strictly read-then-decide.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from textual.app import ComposeResult
from textual.widgets import Label, Static

from .side_panel import SidePanel


def _format_report(report: Any) -> str:
    """Render a SimulationReport into a plain-text plan. Never raises."""
    lines: list[str] = []
    try:
        summary = getattr(report, "summary", None)
        lines.append(f"Plan for graph: {getattr(report, 'graph_id', '?')}")
        lines.append("─" * 60)

        side_effects = getattr(report, "side_effects", []) or []
        tool_calls = getattr(report, "tool_calls", []) or []
        gates = getattr(report, "gates", []) or []
        warnings = getattr(report, "warnings", []) or []

        lines.append(f"Predicted side effects: {len(side_effects)}")
        for se in side_effects[:10]:
            kind = getattr(se, "kind", getattr(se, "code", "effect"))
            target = getattr(se, "target", getattr(se, "message", ""))
            lines.append(f"  • {kind}: {str(target)[:60]}")

        lines.append(f"Predicted tool calls: {len(tool_calls)}")
        for tc in tool_calls[:10]:
            name = getattr(tc, "tool_name", getattr(tc, "name", "tool"))
            lines.append(f"  • {name}")

        if gates:
            lines.append(f"Gates: {len(gates)}")
            for g in gates[:10]:
                gname = getattr(g, "name", getattr(g, "kind", "gate"))
                lines.append(f"  • {gname}")

        cost = getattr(report, "cost", None)
        if cost is not None:
            est = getattr(cost, "estimated_usd", getattr(cost, "total_usd", None))
            if est is not None:
                lines.append(f"Estimated cost: ${float(est):.4f}")

        if warnings:
            lines.append(f"⚠ Warnings: {len(warnings)}")
            for w in warnings[:5]:
                lines.append(f"  ⚠ {getattr(w, 'message', '')[:60]}")

        if summary is not None:
            lines.append("─" * 60)
            lines.append(f"Summary: {summary}")
    except Exception as exc:  # noqa: BLE001
        lines.append(f"[plan] could not render report: {exc}")
    return "\n".join(lines)


class PlanView(SidePanel):
    """Read-only Plan-mode panel. Shows a predicted plan from a SimulationReport."""

    def __init__(self, report: Any = None, workspace: Path | None = None, **kwargs) -> None:
        super().__init__(workspace=workspace, **kwargs)
        self._report = report

    def compose(self) -> ComposeResult:
        yield Label("◆ Plan mode · read-only (no execution)", id="plan-header")
        if self._report is None:
            yield Static(
                "No simulation available.\n"
                "Compile an IR graph and run `arc simulate` to populate a plan.",
                id="plan-body",
            )
        else:
            yield Static(_format_report(self._report), id="plan-body")
