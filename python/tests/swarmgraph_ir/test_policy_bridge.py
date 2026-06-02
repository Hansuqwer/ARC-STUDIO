"""WorkflowInfo bridge to the existing policy linter (Commit 3).

The linter is used UNCHANGED; the IR only produces a faithful WorkflowInfo.
"""

from __future__ import annotations

from pathlib import Path

from agent_runtime_cockpit.protocol.schemas import (
    NodeType,
    WorkflowEdge,
    WorkflowInfo,
    WorkflowNode,
)
from agent_runtime_cockpit.security.policy_linter import lint_workflow
from agent_runtime_cockpit.swarmgraph_ir import compile_workflow, to_workflow_info


def _risky_wf() -> WorkflowInfo:
    return WorkflowInfo(
        id="wf-risky",
        name="exfiltrate secrets and delete production database rm -rf",
        runtime="langgraph",
        nodes=[
            WorkflowNode(id="__start__", label="START", type=NodeType.START),
            WorkflowNode(
                id="mcp",
                label="slack mcp tool",
                type=NodeType.TOOL,
                metadata={"is_mcp": True, "mcp_server_id": "slack", "mcp_tool_name": "send"},
            ),
            WorkflowNode(
                id="writer",
                label="Writer",
                type=NodeType.TOOL,
                metadata={"requires_paid_call": True, "write_path": "/etc/passwd"},
            ),
            WorkflowNode(
                id="priv",
                label="Privileged op",
                type=NodeType.TOOL,
                metadata={"privileged": True},
            ),
            WorkflowNode(id="__end__", label="END", type=NodeType.END),
        ],
        edges=[
            WorkflowEdge(id="e1", from_node="__start__", to_node="mcp"),
            WorkflowEdge(id="e2", from_node="mcp", to_node="writer"),
            WorkflowEdge(id="e3", from_node="writer", to_node="priv"),
            WorkflowEdge(id="e4", from_node="priv", to_node="__end__"),
        ],
        entry_points=["__start__"],
    )


def test_bridge_round_trips_linter_metadata_keys() -> None:
    res = compile_workflow(_risky_wf(), workspace="/home/user/proj")
    wf = res.workflow_info
    md = {n.id: n.metadata for n in wf.nodes}
    assert md["mcp"].get("is_mcp") is True
    assert md["writer"].get("requires_paid_call") is True
    assert md["writer"].get("write_path")
    assert md["priv"].get("privileged") is True


def test_linter_fires_expected_rules_through_bridge() -> None:
    res = compile_workflow(_risky_wf(), workspace="/home/user/proj")
    report = lint_workflow(res.workflow_info, workspace_root=Path("/home/user/proj"))
    fired = {i.rule for i in report.issues}
    # write_path outside workspace + privileged-without-trust are errors → blocks run.
    assert "write_outside_workspace" in fired
    assert "privileged_node" in fired
    assert "paid_call_unguarded" in fired
    assert "untrusted_mcp_tool" in fired
    assert report.can_run is False


def test_to_workflow_info_labels_hitl_for_linter() -> None:
    from agent_runtime_cockpit.swarmgraph_ir import (
        IRAdapterProvenance,
        IRGraph,
        IRNode,
        IRNodeKind,
    )

    g = IRGraph(
        id="g",
        runtime="native",
        provenance=IRAdapterProvenance(adapter_id="native", runtime="native"),
        nodes=[IRNode(id="gate", label="signoff", kind=IRNodeKind.HUMAN_GATE)],
    )
    wf = to_workflow_info(g)
    assert "hitl" in wf.nodes[0].label.lower()
