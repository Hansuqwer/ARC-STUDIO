"""Pydantic AI export functionality.

Phase 29 PR 29.2: Export Pydantic AI Agent definitions to WorkflowInfo.

Strategy:
- AST-based static analysis (no code execution)
- Detect Agent instantiations
- Extract tools, model bindings, structured-output schemas
- Map to ARC WorkflowInfo structure
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from ...protocol.schemas import (
    WorkflowInfo,
    WorkflowNode,
    WorkflowEdge,
    NodeType,
    SourceLocation,
)

log = logging.getLogger(__name__)


class PydanticAIAgentVisitor(ast.NodeVisitor):
    """AST visitor to detect Pydantic AI Agent definitions."""

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.agents: list[dict[str, Any]] = []
        self.agent_counter = 0

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statements to detect Agent definitions."""
        # Look for assignments like: agent = Agent(model, ...)
        if isinstance(node.value, ast.Call):
            if self._is_agent_call(node.value):
                agent_name = self._get_target_name(node.targets[0]) if node.targets else None
                if agent_name:
                    agent_info = self._extract_agent_info(node.value, agent_name, node.lineno)
                    if agent_info:
                        self.agents.append(agent_info)

        self.generic_visit(node)

    def _get_target_name(self, target: ast.expr) -> str | None:
        """Extract variable name from assignment target."""
        if isinstance(target, ast.Name):
            return target.id
        return None

    def _is_agent_call(self, node: ast.Call) -> bool:
        """Check if a call is to Agent constructor."""
        if isinstance(node.func, ast.Name):
            return node.func.id == "Agent"
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr == "Agent"
        return False

    def _extract_agent_info(
        self, node: ast.Call, agent_name: str, lineno: int
    ) -> dict[str, Any] | None:
        """Extract agent information from Agent() call."""
        # Extract model (first positional arg or 'model' keyword)
        model = None
        if node.args:
            model = self._get_arg_repr(node.args[0])

        # Extract keyword arguments
        tools = []
        system_prompt = None
        result_type = None

        for keyword in node.keywords:
            if keyword.arg == "tools":
                tools = self._extract_tools(keyword.value)
            elif keyword.arg == "system_prompt":
                system_prompt = self._get_arg_repr(keyword.value)
            elif keyword.arg == "result_type":
                result_type = self._get_arg_repr(keyword.value)
            elif keyword.arg == "model" and not model:
                model = self._get_arg_repr(keyword.value)

        return {
            "name": agent_name,
            "model": model,
            "tools": tools,
            "system_prompt": system_prompt,
            "result_type": result_type,
            "lineno": lineno,
        }

    def _extract_tools(self, node: ast.expr) -> list[str]:
        """Extract tool names from tools list."""
        tools = []
        if isinstance(node, ast.List):
            for elt in node.elts:
                tool_name = self._get_arg_repr(elt)
                if tool_name:
                    tools.append(tool_name)
        return tools

    def _get_arg_repr(self, node: ast.expr) -> str | None:
        """Get string representation of an argument."""
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"{node.func.id}(...)"
            elif isinstance(node.func, ast.Attribute):
                return f"{self._get_attribute_name(node.func)}(...)"
        return None

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get full attribute name (e.g., 'module.Class')."""
        parts = []
        current = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))


def export_pydantic_ai_agents(workspace: Path) -> list[WorkflowInfo]:
    """Export Pydantic AI agents from workspace to WorkflowInfo.

    Phase 29 PR 29.2: Static analysis only, no code execution.

    Args:
        workspace: Path to workspace directory

    Returns:
        List of WorkflowInfo objects, one per detected agent
    """
    workflows = []

    # Scan Python files for Agent definitions
    for py_file in workspace.rglob("*.py"):
        if ".venv" in py_file.parts or "venv" in py_file.parts:
            continue
        if "node_modules" in py_file.parts:
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(py_file))

            visitor = PydanticAIAgentVisitor(py_file)
            visitor.visit(tree)

            # Convert each agent to WorkflowInfo
            for agent_info in visitor.agents:
                workflow = _agent_to_workflow(agent_info, py_file, workspace)
                workflows.append(workflow)

        except SyntaxError as e:
            log.debug("Failed to parse %s: %s", py_file, e)
        except Exception as e:
            log.debug("Failed to process %s: %s", py_file, e)

    return workflows


def _agent_to_workflow(
    agent_info: dict[str, Any], source_file: Path, workspace: Path
) -> WorkflowInfo:
    """Convert agent info to WorkflowInfo structure."""
    agent_name = agent_info["name"]
    rel_path = source_file.relative_to(workspace)

    # Create nodes for agent components
    nodes = []
    edges = []
    node_id_counter = 0

    # Agent node (central)
    agent_node = WorkflowNode(
        id=f"agent_{node_id_counter}",
        type=NodeType.AGENT,
        label=agent_name,
        metadata={
            "model": agent_info.get("model"),
            "system_prompt": agent_info.get("system_prompt"),
            "result_type": agent_info.get("result_type"),
        },
        source_location=SourceLocation(
            file=str(rel_path),
            line=agent_info["lineno"],
        ),
    )
    nodes.append(agent_node)
    node_id_counter += 1

    # Tool nodes
    for tool_name in agent_info.get("tools", []):
        tool_node = WorkflowNode(
            id=f"tool_{node_id_counter}",
            type=NodeType.TOOL,
            label=tool_name,
            metadata={"tool_name": tool_name},
        )
        nodes.append(tool_node)

        # Edge from agent to tool
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=agent_node.id,
                to_node=tool_node.id,
                label="uses",
            )
        )
        node_id_counter += 1

    return WorkflowInfo(
        id=f"pydantic_ai_{agent_name}",
        name=agent_name,
        description=f"Pydantic AI agent: {agent_name}",
        runtime="pydantic_ai",
        nodes=nodes,
        edges=edges,
        metadata={
            "source_file": str(rel_path),
            "model": agent_info.get("model"),
            "tool_count": len(agent_info.get("tools", [])),
        },
    )
