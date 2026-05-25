"""Google ADK static workflow export.

T2 export maps Google ADK agent constructs to ARC WorkflowInfo without
importing or executing workspace code.

Detected constructs:
- LlmAgent / Agent  — core LLM-driven agent
- SequentialAgent   — runs sub-agents in order
- ParallelAgent     — runs sub-agents concurrently
- LoopAgent         — runs sub-agents in a loop
- FunctionTool      — function-based tool
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from ...protocol.schemas import NodeType, SourceLocation, WorkflowEdge, WorkflowInfo, WorkflowNode

log = logging.getLogger(__name__)

# Agent types exposed by google.adk.agents
AGENT_TYPES = frozenset(
    {
        "LlmAgent",
        "Agent",  # common alias used in samples
        "SequentialAgent",
        "ParallelAgent",
        "LoopAgent",
    }
)

WORKFLOW_AGENT_TYPES = frozenset({"SequentialAgent", "ParallelAgent", "LoopAgent"})

# Import markers that indicate a google.adk usage file
ADK_IMPORT_MARKERS = (
    "import google.adk",
    "from google.adk",
)


class GoogleADKVisitor(ast.NodeVisitor):
    """Collect Google ADK static constructs from a source file."""

    def __init__(self, source_file: Path) -> None:
        self.source_file = source_file
        self.agents: list[dict[str, Any]] = []
        self.tools: list[dict[str, Any]] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call):
            call_name = _call_name(node.value)
            target = _target_name(node.targets[0]) if node.targets else None
            if target and call_name and _last_name(call_name) in AGENT_TYPES:
                self.agents.append(self._agent_info(target, call_name, node.value, node.lineno))
            if target and call_name and _last_name(call_name) == "FunctionTool":
                self.tools.append({"name": target, "lineno": node.lineno})
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.value, ast.Call):
            call_name = _call_name(node.value)
            target = _target_name(node.target)
            if target and call_name and _last_name(call_name) in AGENT_TYPES:
                self.agents.append(self._agent_info(target, call_name, node.value, node.lineno))
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # @tool decorator from google.adk.tools
        if _has_tool_decorator(node):
            self.tools.append({"name": node.name, "lineno": node.lineno})
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if _has_tool_decorator(node):
            self.tools.append({"name": node.name, "lineno": node.lineno})
        self.generic_visit(node)

    def _agent_info(
        self,
        var_name: str,
        call_name: str,
        node: ast.Call,
        lineno: int,
    ) -> dict[str, Any]:
        agent_type = _last_name(call_name)
        name = _constant_kw(node, "name") or var_name
        model = _constant_kw(node, "model")
        instruction = _constant_kw(node, "instruction")
        description = _constant_kw(node, "description")
        # sub_agents keyword (SequentialAgent/ParallelAgent/LoopAgent)
        sub_agents = _list_names(node, "sub_agents")
        tools = _list_names(node, "tools")
        return {
            "name": name,
            "var_name": var_name,
            "agent_type": agent_type,
            "model": model,
            "instruction": instruction,
            "description": description,
            "sub_agents": sub_agents,
            "tools": tools,
            "lineno": lineno,
        }


def export_google_adk_workflows(workspace: Path) -> list[WorkflowInfo]:
    """Export Google ADK agents from workspace to WorkflowInfo.

    Pure static AST analysis — no workspace code is imported or executed.
    """
    workflows: list[WorkflowInfo] = []
    for py_file in workspace.rglob("*.py"):
        if _skip_path(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            log.debug("Failed to read %s: %s", py_file, exc)
            continue
        if not any(marker in content for marker in ADK_IMPORT_MARKERS):
            continue
        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError as exc:
            log.debug("Failed to parse %s: %s", py_file, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            log.debug("Unexpected parse error in %s: %s", py_file, exc)
            continue
        visitor = GoogleADKVisitor(py_file)
        visitor.visit(tree)
        for agent in visitor.agents:
            workflows.append(_agent_to_workflow(agent, visitor.tools, py_file, workspace))
    return workflows


def _agent_to_workflow(
    agent: dict[str, Any],
    tools: list[dict[str, Any]],
    source_file: Path,
    workspace: Path,
) -> WorkflowInfo:
    rel_path = source_file.relative_to(workspace)
    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []

    agent_type = agent["agent_type"]
    is_workflow_agent = agent_type in WORKFLOW_AGENT_TYPES

    agent_node = WorkflowNode(
        id="agent_0",
        type=NodeType.AGENT,
        label=agent["name"],
        metadata={
            "agent_type": agent_type,
            "model": agent.get("model"),
            "instruction": agent.get("instruction"),
            "description": agent.get("description"),
            "is_workflow_agent": is_workflow_agent,
        },
        source_location=SourceLocation(file=str(rel_path), line=agent["lineno"]),
    )
    nodes.append(agent_node)

    # Sub-agents (SequentialAgent/ParallelAgent/LoopAgent)
    for idx, sub_name in enumerate(agent.get("sub_agents", []), start=1):
        sub_node = WorkflowNode(
            id=f"sub_agent_{idx}",
            type=NodeType.AGENT,
            label=sub_name,
            metadata={"role": "sub_agent"},
        )
        nodes.append(sub_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=agent_node.id,
                to_node=sub_node.id,
                label="orchestrates",
            )
        )

    # Tools referenced in agent definition
    known_tools = {t["name"]: t for t in tools}
    for idx, tool_name in enumerate(agent.get("tools", []), start=1):
        clean = tool_name.replace("(...)", "")
        tool_meta = known_tools.get(clean, {})
        tool_node = WorkflowNode(
            id=f"tool_{idx}",
            type=NodeType.TOOL,
            label=clean,
            metadata={"lineno": tool_meta.get("lineno")},
        )
        nodes.append(tool_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=agent_node.id,
                to_node=tool_node.id,
                label="uses",
            )
        )

    return WorkflowInfo(
        id=f"google_adk_{agent['name']}",
        name=agent["name"],
        description=(agent.get("description") or f"Google ADK {agent_type}: {agent['name']}"),
        runtime="google_adk",
        nodes=nodes,
        edges=edges,
        entry_points=[agent_node.id],
        metadata={
            "source_file": str(rel_path),
            "kind": "agent",
            "agent_type": agent_type,
            "sub_agent_count": len(agent.get("sub_agents", [])),
            "tool_count": len(agent.get("tools", [])),
            "model": agent.get("model"),
        },
    )


# ── AST helpers ──────────────────────────────────────────────────────────────


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return f"{_expr_name(node.func.value)}.{node.func.attr}"
    return None


def _last_name(qualified: str | None) -> str:
    if not qualified:
        return ""
    return qualified.rsplit(".", 1)[-1]


def _target_name(target: ast.expr) -> str | None:
    return target.id if isinstance(target, ast.Name) else None


def _expr_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return f"{_expr_name(node.value)}.{node.attr}"
    return "?"


def _constant_kw(node: ast.Call, kw: str) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == kw and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value)
    return None


def _list_names(node: ast.Call, kw: str) -> list[str]:
    for keyword in node.keywords:
        if keyword.arg == kw and isinstance(keyword.value, ast.List):
            names: list[str] = []
            for elt in keyword.value.elts:
                name = _target_name(elt) or (elt.value if isinstance(elt, ast.Constant) else None)
                if name:
                    names.append(str(name))
            return names
    return []


def _has_tool_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for dec in node.decorator_list:
        if isinstance(dec, ast.Name) and dec.id == "tool":
            return True
        if isinstance(dec, ast.Attribute) and dec.attr == "tool":
            return True
    return False


def _skip_path(path: Path) -> bool:
    ignored = {".venv", "venv", "node_modules", "__pycache__", ".git"}
    return any(part in ignored for part in path.parts)
