"""Simulation report diff - compare two SimulationReport objects."""

from __future__ import annotations

from .models import DiffSubject, DiffSubjectKind, RunDiffReport, SimulationDiff


def diff_simulation_reports(left, right):
    from .models import DiffSummary

    left_sum = left.summary
    right_sum = right.summary
    hitl_delta = right_sum.hitl_gate_count - left_sum.hitl_gate_count
    paid_delta = right_sum.paid_call_count - left_sum.paid_call_count
    sim_diff = SimulationDiff(
        summary_changed=(
            left_sum.total_nodes != right_sum.total_nodes
            or left_sum.reachable_nodes != right_sum.reachable_nodes
        ),
        reachable_nodes_left=left_sum.reachable_nodes,
        reachable_nodes_right=right_sum.reachable_nodes,
        hitl_gates_left=left_sum.hitl_gate_count,
        hitl_gates_right=right_sum.hitl_gate_count,
        hitl_gate_delta=hitl_delta,
        paid_calls_left=left_sum.paid_call_count,
        paid_calls_right=right_sum.paid_call_count,
        paid_call_delta=paid_delta,
        mcp_tools_left=left_sum.mcp_tool_count,
        mcp_tools_right=right_sum.mcp_tool_count,
        gate_count_left=left_sum.gate_count,
        gate_count_right=right_sum.gate_count,
        policy_regression=not right.policy.can_run and left.policy.can_run,
        can_run_left=left.policy.can_run,
        can_run_right=right.policy.can_run,
        warnings_added=[w for w in right.warnings if w not in left.warnings],
        warnings_removed=[w for w in left.warnings if w not in right.warnings],
    )
    summary = DiffSummary()
    if hitl_delta < 0:
        summary.hitl_gate_delta = hitl_delta
    summary.paid_call_delta = paid_delta
    summary.policy_issues_added = right.policy.warning_count + right.policy.error_count
    summary.policy_issues_removed = left.policy.warning_count + left.policy.error_count
    summary.compute_total()
    report = RunDiffReport(
        left=DiffSubject(
            kind=DiffSubjectKind.SIMULATION_REPORT,
            id=left.graph_id,
            metadata={
                "graph_hash": left.graph_hash,
                "reachable_nodes": left_sum.reachable_nodes,
                "can_run": left.policy.can_run,
            },
        ),
        right=DiffSubject(
            kind=DiffSubjectKind.SIMULATION_REPORT,
            id=right.graph_id,
            metadata={
                "graph_hash": right.graph_hash,
                "reachable_nodes": right_sum.reachable_nodes,
                "can_run": right.policy.can_run,
            },
        ),
        mode="simulation_vs_simulation",
        summary=summary,
        simulation_diff=sim_diff,
        warnings=["SIMULATION POLICY REGRESSION: can_run changed from True to False"]
        if sim_diff.policy_regression
        else [],
    )
    return report.with_hash()
