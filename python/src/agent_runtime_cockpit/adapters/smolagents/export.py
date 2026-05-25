"""Smolagents export functionality.

Static AST export only. No workspace code is imported or executed.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from ...protocol.schemas import NodeType, SourceLocation, WorkflowEdge, WorkflowInfo, WorkflowNode

log = logging.getLogger(__name__)

AGENT_TYPES = frozenset({"CodeAgent", "ToolCallingAgent", "ManagedAgent"})
MODEL_TYPES = frozenset(
    {
        "InferenceClientModel",
        "LiteLLMModel",
        "OpenAIModel",
        "TransformersModel",
        "AzureOpenAIModel",
        "AmazonBedrockModel",
        "OllamaModel",
    }
)


class SmolagentsVisitor(ast.NodeVisitor):
    """AST visitor to detect Smolagents agents, tools, and models."""

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.agents: list[dict[str, Any]] = []
        self.tools: list[dict[str, Any]] = []
        self.models: dict[str, dict[str, Any]] = {}

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if self._has_tool_decorator(node):
            self.tools.append(
                {
                    "name": node.name,
                    "inputs": [arg.arg for arg in node.args.args],
                    "lineno": node.lineno,
                }
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self._is_tool_subclass(node):
            self.tools.append({"name": node.name, "inputs": [], "lineno": node.lineno})
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        if not isinstance(node.value, ast.Call):
            self.generic_visit(node)
            return

        target_name = self._target_name(node.targets[0]) if node.targets else None
        call_name = self._call_name(node.value)
        if target_name and call_name in MODEL_TYPES:
            self.models[target_name] = {
                "name": target_name,
                "model_type": call_name,
                "lineno": node.lineno,
            }
        if target_name and call_name in AGENT_TYPES:
            self.agents.append(self._agent_info(target_name, call_name, node.value, node.lineno))
        self.generic_visit(node)

    def _agent_info(
        self, var_name: str, agent_type: str, node: ast.Call, lineno: int
    ) -> dict[str, Any]:
        tools: list[str] = []
        model: str | None = None
        for keyword in node.keywords:
            if keyword.arg == "tools":
                tools = self._extract_list_names(keyword.value)
            elif keyword.arg == "model":
                model = self._expr_repr(keyword.value)
        return {
            "name": var_name,
            "agent_type": agent_type,
            "tools": tools,
            "model": model,
            "code_execution": agent_type == "CodeAgent",
            "lineno": lineno,
        }

    def _has_tool_decorator(self, node: ast.FunctionDef) -> bool:
        return any(
            (isinstance(dec, ast.Name) and dec.id == "tool")
            or (isinstance(dec, ast.Attribute) and dec.attr == "tool")
            for dec in node.decorator_list
        )

    def _is_tool_subclass(self, node: ast.ClassDef) -> bool:
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "Tool":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "Tool":
                return True
        return False

    def _extract_list_names(self, node: ast.expr) -> list[str]:
        if isinstance(node, ast.List):
            return [name for item in node.elts if (name := self._expr_repr(item))]
        return []

    def _target_name(self, target: ast.expr) -> str | None:
        return target.id if isinstance(target, ast.Name) else None

    def _call_name(self, node: ast.Call) -> str | None:
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None

    def _expr_repr(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Constant):
            return str(node.value)
        if isinstance(node, ast.Call):
            return f"{self._call_name(node) or 'call'}(...)"
        if isinstance(node, ast.Attribute):
            return node.attr
        return None


def export_smolagents_workflows(workspace: Path) -> list[WorkflowInfo]:
    """Export Smolagents agents from workspace to WorkflowInfo."""
    workflows: list[WorkflowInfo] = []
    for py_file in workspace.rglob("*.py"):
        if ".venv" in py_file.parts or "venv" in py_file.parts:
            continue
        if "node_modules" in py_file.parts:
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            if "smolagents" not in content:
                continue
            tree = ast.parse(content, filename=str(py_file))
            visitor = SmolagentsVisitor(py_file)
            visitor.visit(tree)
            for agent in visitor.agents:
                workflows.append(_agent_to_workflow(agent, visitor.tools, py_file, workspace))
        except SyntaxError as e:
            log.debug("Failed to parse %s: %s", py_file, e)
        except Exception as e:
            log.debug("Failed to process %s: %s", py_file, e)
    return workflows


def _agent_to_workflow(
    agent: dict[str, Any], tools: list[dict[str, Any]], source_file: Path, workspace: Path
) -> WorkflowInfo:
    rel_path = source_file.relative_to(workspace)
    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []
    agent_node = WorkflowNode(
        id="agent_0",
        type=NodeType.AGENT,
        label=agent["name"],
        metadata={
            "agent_type": agent["agent_type"],
            "model": agent.get("model"),
            "code_execution": agent.get("code_execution", False),
        },
        source_location=SourceLocation(file=str(rel_path), line=agent["lineno"]),
    )
    nodes.append(agent_node)
    known_tools = {tool["name"]: tool for tool in tools}
    for index, tool_name in enumerate(agent.get("tools", []), start=1):
        clean_name = tool_name.replace("(...)", "")
        tool_meta = known_tools.get(clean_name, {})
        tool_node = WorkflowNode(
            id=f"tool_{index}",
            type=NodeType.TOOL,
            label=clean_name,
            metadata={"inputs": tool_meta.get("inputs", [])},
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
        id=f"smolagents_{agent['name']}",
        name=agent["name"],
        description=f"Smolagents {agent['agent_type']}: {agent['name']}",
        runtime="smolagents",
        nodes=nodes,
        edges=edges,
        entry_points=[agent_node.id],
        metadata={
            "source_file": str(rel_path),
            "kind": "agent",
            "agent_type": agent["agent_type"],
            "tool_count": len(agent.get("tools", [])),
            "code_execution": agent.get("code_execution", False),
        },
    )
