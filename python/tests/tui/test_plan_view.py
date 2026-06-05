"""Tests for PlanView (R-012) — read-only plan rendering."""

from __future__ import annotations

from types import SimpleNamespace

from agent_runtime_cockpit.tui.views.plan_view import PlanView, _format_report


def test_empty_report_renders_placeholder():
    view = PlanView(report=None)
    # compose() yields a placeholder Static when no report
    widgets = list(view.compose())
    assert len(widgets) == 2  # header + body
    bodies = [w for w in widgets if getattr(w, "id", "") == "plan-body"]
    assert bodies


def test_format_report_lists_side_effects_and_tools():
    report = SimpleNamespace(
        graph_id="g-123",
        summary="2 nodes",
        side_effects=[SimpleNamespace(kind="write", target="/tmp/x")],
        tool_calls=[SimpleNamespace(tool_name="bash")],
        gates=[],
        warnings=[],
        cost=SimpleNamespace(estimated_usd=0.0042),
    )
    out = _format_report(report)
    assert "g-123" in out
    assert "Predicted side effects: 1" in out
    assert "write" in out
    assert "bash" in out
    assert "$0.0042" in out


def test_format_report_shows_warnings():
    report = SimpleNamespace(
        graph_id="g-x",
        summary="",
        side_effects=[],
        tool_calls=[],
        gates=[],
        warnings=[SimpleNamespace(message="unreachable node n3")],
        cost=None,
    )
    out = _format_report(report)
    assert "Warnings: 1" in out
    assert "unreachable node n3" in out


def test_format_report_never_raises_on_garbage():
    out = _format_report(object())  # no attributes
    assert isinstance(out, str)
    assert "Plan for graph" in out or "could not render" in out


def test_plan_view_is_read_only_modal():
    """PlanView extends SidePanel (ModalScreen) — Escape closes, no exec."""
    from agent_runtime_cockpit.tui.views.side_panel import SidePanel

    assert issubclass(PlanView, SidePanel)
