"""Semantic Kernel static workflow export.

T2 export maps common Semantic Kernel constructs to ARC WorkflowInfo without
importing or executing workspace code.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from ...protocol.schemas import NodeType, SourceLocation, WorkflowEdge, WorkflowInfo, WorkflowNode

log = logging.getLogger(__name__)

AGENT_TYPES = frozenset(
    {
        "ChatCompletionAgent",
        "SequentialOrchestration",
        "ConcurrentOrchestration",
        "HandoffOrchestration",
        "GroupChatOrchestration",
    }
)


class SemanticKernelVisitor(ast.NodeVisitor):
    """Collect Semantic Kernel static constructs."""

    def __init__(self, source_file: Path) -> None:
        self.source_file = source_file
        self.kernel_vars: list[dict[str, Any]] = []
        self.plugins: list[dict[str, Any]] = []
        self.functions: list[dict[str, Any]] = []
        self.agents: list[dict[str, Any]] = []
        self.invocations: list[dict[str, Any]] = []

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call):
            call_name = _call_name(node.value)
            target = _target_name(node.targets[0]) if node.targets else None
            if target and call_name and call_name.endswith("Kernel"):
                self.kernel_vars.append({"name": target, "lineno": node.lineno})
            if target and call_name and _last_name(call_name) in AGENT_TYPES:
                self.agents.append(
                    {
                        "name": _constant_kw(node.value, "name") or target,
                        "var_name": target,
                        "agent_type": _last_name(call_name),
                        "instructions": _constant_kw(node.value, "instructions"),
                        "lineno": node.lineno,
                    }
                )
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        if isinstance(node.value, ast.Call):
            call_name = _call_name(node.value)
            target = _target_name(node.target)
            if target and call_name and _last_name(call_name) in AGENT_TYPES:
                self.agents.append(
                    {
                        "name": _constant_kw(node.value, "name") or target,
                        "var_name": target,
                        "agent_type": _last_name(call_name),
                        "instructions": _constant_kw(node.value, "instructions"),
                        "lineno": node.lineno,
                    }
                )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        plugin_functions: list[dict[str, Any]] = []
        for item in node.body:
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and _has_kernel_function(
                item
            ):
                function = _function_info(item, plugin_name=node.name)
                plugin_functions.append(function)
                self.functions.append(function)
        if plugin_functions:
            self.plugins.append(
                {"name": node.name, "functions": plugin_functions, "lineno": node.lineno}
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        if _has_kernel_function(node):
            self.functions.append(_function_info(node, plugin_name=None))
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if _has_kernel_function(node):
            self.functions.append(_function_info(node, plugin_name=None))
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name = _call_name(node)
        if call_name:
            method = _last_name(call_name)
            if method == "add_plugin":
                self.plugins.append(
                    {
                        "name": _constant_kw(node, "plugin_name")
                        or _first_arg_name(node)
                        or "plugin",
                        "functions": [],
                        "lineno": node.lineno,
                    }
                )
            elif method in {"invoke", "invoke_prompt"}:
                self.invocations.append(
                    {
                        "method": method,
                        "function_name": _constant_kw(node, "function_name"),
                        "plugin_name": _constant_kw(node, "plugin_name"),
                        "lineno": node.lineno,
                    }
                )
        self.generic_visit(node)


def export_semantic_kernel_workflows(workspace: Path) -> list[WorkflowInfo]:
    """Export Semantic Kernel workflows from Python files."""
    workflows: list[WorkflowInfo] = []
    for py_file in workspace.rglob("*.py"):
        if _skip_path(py_file):
            continue
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            log.debug("Failed to read %s: %s", py_file, exc)
            continue
        if "semantic_kernel" not in content and "kernel_function" not in content:
            continue
        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError as exc:
            log.debug("Failed to parse %s: %s", py_file, exc)
            continue
        visitor = SemanticKernelVisitor(py_file)
        visitor.visit(tree)
        if (
            visitor.kernel_vars
            or visitor.plugins
            or visitor.functions
            or visitor.agents
            or visitor.invocations
        ):
            workflows.append(_visitor_to_workflow(visitor, py_file, workspace))
    return workflows


def _visitor_to_workflow(
    visitor: SemanticKernelVisitor, source_file: Path, workspace: Path
) -> WorkflowInfo:
    rel_path = source_file.relative_to(workspace)
    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []
    previous_id: str | None = None

    def add_node(
        kind: str, label: str, node_type: NodeType, lineno: int, metadata: dict[str, Any]
    ) -> str:
        node_id = f"{kind}_{len(nodes)}"
        nodes.append(
            WorkflowNode(
                id=node_id,
                label=label,
                type=node_type,
                source_location=SourceLocation(file=str(rel_path), line=lineno),
                metadata=metadata,
            )
        )
        return node_id

    for kernel in visitor.kernel_vars:
        previous_id = add_node(
            "kernel", kernel["name"], NodeType.START, kernel["lineno"], {"kind": "Kernel"}
        )

    for plugin in _dedupe_by_name(visitor.plugins):
        plugin_id = add_node(
            "plugin",
            plugin["name"],
            NodeType.TOOL,
            plugin["lineno"],
            {"kind": "plugin", "function_count": len(plugin.get("functions", []))},
        )
        if previous_id:
            edges.append(_edge(previous_id, plugin_id, "adds_plugin", len(edges)))
        for function in plugin.get("functions", []):
            fn_id = add_node(
                "function",
                function["name"],
                NodeType.TOOL,
                function["lineno"],
                {
                    "kind": "kernel_function",
                    "plugin": plugin["name"],
                    "description": function.get("description"),
                },
            )
            edges.append(_edge(plugin_id, fn_id, "exposes", len(edges)))
        previous_id = plugin_id

    plugin_function_names = {
        fn["name"] for plugin in visitor.plugins for fn in plugin.get("functions", [])
    }
    for function in visitor.functions:
        if function["name"] in plugin_function_names and function.get("plugin_name"):
            continue
        fn_id = add_node(
            "function",
            function["name"],
            NodeType.TOOL,
            function["lineno"],
            {"kind": "kernel_function", "description": function.get("description")},
        )
        if previous_id:
            edges.append(_edge(previous_id, fn_id, "exposes", len(edges)))
        previous_id = fn_id

    for agent in visitor.agents:
        agent_id = add_node(
            "agent",
            agent["name"],
            NodeType.AGENT,
            agent["lineno"],
            {"kind": agent["agent_type"], "instructions": agent.get("instructions")},
        )
        if previous_id:
            edges.append(_edge(previous_id, agent_id, "uses", len(edges)))
        previous_id = agent_id

    for invocation in visitor.invocations:
        label = invocation.get("function_name") or invocation["method"]
        invoke_id = add_node("invoke", label, NodeType.END, invocation["lineno"], invocation)
        if previous_id:
            edges.append(_edge(previous_id, invoke_id, "invokes", len(edges)))
        previous_id = invoke_id

    if not nodes:
        nodes.append(
            WorkflowNode(id="semantic_kernel_0", label=source_file.stem, type=NodeType.UNKNOWN)
        )

    return WorkflowInfo(
        id=f"semantic_kernel_{source_file.stem}",
        name=f"{source_file.stem} (Semantic Kernel)",
        runtime="semantic_kernel",
        source_file=str(rel_path),
        nodes=nodes,
        edges=edges,
        entry_points=[nodes[0].id],
        metadata={
            "source_file": str(rel_path),
            "kind": "semantic_kernel_static_export",
            "kernel_count": len(visitor.kernel_vars),
            "plugin_count": len(visitor.plugins),
            "function_count": len(visitor.functions),
            "agent_count": len(visitor.agents),
            "invocation_count": len(visitor.invocations),
        },
    )


def _function_info(
    node: ast.FunctionDef | ast.AsyncFunctionDef, plugin_name: str | None
) -> dict[str, Any]:
    return {
        "name": _kernel_function_name(node) or node.name,
        "python_name": node.name,
        "plugin_name": plugin_name,
        "description": _kernel_function_description(node) or ast.get_docstring(node),
        "lineno": node.lineno,
    }


def _has_kernel_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return any(
        _decorator_name(decorator).endswith("kernel_function") for decorator in node.decorator_list
    )


def _kernel_function_name(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and _decorator_name(decorator).endswith(
            "kernel_function"
        ):
            return _constant_kw(decorator, "name")
    return None


def _kernel_function_description(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str | None:
    for decorator in node.decorator_list:
        if isinstance(decorator, ast.Call) and _decorator_name(decorator).endswith(
            "kernel_function"
        ):
            return _constant_kw(decorator, "description")
    return None


def _decorator_name(node: ast.expr) -> str:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _attribute_name(node)
    return ""


def _call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return _attribute_name(node.func)
    return None


def _attribute_name(node: ast.Attribute) -> str:
    parts: list[str] = []
    current: ast.expr = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    return ".".join(reversed(parts))


def _target_name(target: ast.expr) -> str | None:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return None


def _constant_kw(node: ast.Call, name: str) -> str | None:
    for keyword in node.keywords:
        if keyword.arg == name and isinstance(keyword.value, ast.Constant):
            return str(keyword.value.value)
    return None


def _first_arg_name(node: ast.Call) -> str | None:
    if not node.args:
        return None
    arg = node.args[0]
    if isinstance(arg, ast.Call):
        return _call_name(arg)
    if isinstance(arg, ast.Name):
        return arg.id
    return None


def _last_name(name: str) -> str:
    return name.rsplit(".", maxsplit=1)[-1]


def _edge(from_node: str, to_node: str, label: str, index: int) -> WorkflowEdge:
    return WorkflowEdge(id=f"edge_{index}", from_node=from_node, to_node=to_node, label=label)


def _dedupe_by_name(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, int]] = set()
    for item in items:
        key = (str(item.get("name", "")), int(item.get("lineno", 0)))
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def _skip_path(path: Path) -> bool:
    ignored = {".venv", "venv", "node_modules", "__pycache__"}
    return any(part in ignored for part in path.parts)
