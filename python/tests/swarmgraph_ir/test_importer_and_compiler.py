"""Native importer + compiler pipeline (Commits 2 & 3)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime_cockpit.protocol.schemas import (
    NodeType,
    WorkflowEdge,
    WorkflowInfo,
    WorkflowNode,
)
from agent_runtime_cockpit.swarmgraph_ir import (
    IRNodeKind,
    SideEffectKind,
    compile_from_json,
    compile_workflow,
)

FIX = Path(__file__).parent / "fixtures"


def _wf() -> WorkflowInfo:
    return WorkflowInfo(
        id="wf",
        name="flow",
        runtime="langgraph",
        nodes=[
            WorkflowNode(id="__start__", label="START", type=NodeType.START),
            WorkflowNode(
                id="mcp",
                label="slack mcp",
                type=NodeType.TOOL,
                metadata={"is_mcp": True, "mcp_server_id": "slack", "mcp_tool_name": "send"},
            ),
            WorkflowNode(
                id="pay",
                label="Pay tool",
                type=NodeType.TOOL,
                metadata={"requires_paid_call": True},
            ),
            WorkflowNode(id="hitl", label="Human approval", type=NodeType.ROUTER),
            WorkflowNode(id="__end__", label="END", type=NodeType.END),
        ],
        edges=[
            WorkflowEdge(id="e1", from_node="__start__", to_node="mcp"),
            WorkflowEdge(id="e2", from_node="mcp", to_node="pay"),
            WorkflowEdge(id="e3", from_node="pay", to_node="hitl"),
            WorkflowEdge(id="e4", from_node="hitl", to_node="__end__"),
        ],
        entry_points=["__start__"],
    )


def test_node_kind_classification() -> None:
    res = compile_workflow(_wf(), use_sdk_risk=False)
    kinds = {n.id: n.kind for n in res.graph.nodes}
    assert kinds["mcp"] is IRNodeKind.MCP_TOOL
    assert kinds["pay"] is IRNodeKind.TOOL
    assert kinds["hitl"] is IRNodeKind.HUMAN_GATE
    assert kinds["__start__"] is IRNodeKind.START


def test_mcp_ref_built() -> None:
    res = compile_workflow(_wf(), use_sdk_risk=False)
    mcp = next(n for n in res.graph.nodes if n.id == "mcp")
    assert mcp.mcp_tool is not None
    assert mcp.mcp_tool.server_id == "slack"
    assert mcp.mcp_tool.tool_name == "send"


def test_paid_call_side_effect_inferred() -> None:
    res = compile_workflow(_wf(), use_sdk_risk=False)
    pay = next(n for n in res.graph.nodes if n.id == "pay")
    kinds = {se.kind for se in pay.side_effects}
    assert SideEffectKind.PAID_CALL in kinds
    assert pay.budget is not None and pay.budget.requires_paid_call


def test_compile_is_deterministic() -> None:
    a = compile_workflow(_wf(), use_sdk_risk=False)
    b = compile_workflow(_wf(), use_sdk_risk=False)
    assert a.graph.graph_hash == b.graph.graph_hash


def test_compile_from_workflow_json() -> None:
    text = (FIX / "native_minimal.workflow.json").read_text()
    res = compile_from_json(text, use_sdk_risk=False)
    assert res.ok
    assert res.graph.runtime == "native"


def test_compile_from_ir_json_passthrough() -> None:
    text = (FIX / "native_minimal.ir.json").read_text()
    res = compile_from_json(text, use_sdk_risk=False)
    assert res.ok
    assert res.graph.ir_version == 1


def test_compile_fails_closed_on_dangling_edge() -> None:
    bad = {
        "id": "bad",
        "name": "bad",
        "runtime": "native",
        "nodes": [{"id": "a", "type": "agent", "label": "a"}],
        "edges": [{"id": "e", "from_node": "a", "to_node": "ghost"}],
        "entry_points": ["a"],
    }
    res = compile_from_json(json.dumps(bad), use_sdk_risk=False)
    assert res.ok is False
    assert any("missing to_node" in e for e in res.validation.errors)
