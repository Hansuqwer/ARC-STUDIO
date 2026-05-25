"""Haystack export functionality.

Phase 31: Export Haystack pipelines to WorkflowInfo.

Strategy:
- AST-based static analysis (no code execution)
- Detect @component decorated classes
- Detect Pipeline() instantiations and add_component()/connect() calls
- Map Pipeline DAG to ARC WorkflowInfo structure
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from ...protocol.schemas import (
    NodeType,
    SourceLocation,
    WorkflowEdge,
    WorkflowInfo,
    WorkflowNode,
)

log = logging.getLogger(__name__)


HAYSTACK_COMPONENT_CATEGORIES = {
    "retriever": NodeType.AGENT,
    "generator": NodeType.AGENT,
    "embedder": NodeType.AGENT,
    "ranker": NodeType.AGENT,
    "reader": NodeType.AGENT,
    "converter": NodeType.AGENT,
    "splitter": NodeType.AGENT,
    "writer": NodeType.END,
    "router": NodeType.ROUTER,
    "branch": NodeType.ROUTER,
    "joiner": NodeType.AGENT,
}


class HaystackComponentVisitor(ast.NodeVisitor):
    """AST visitor to detect @component decorated classes."""

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.components: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        if self._has_component_decorator(node):
            comp_info = self._extract_component_info(node)
            self.components.append(comp_info)

        self.generic_visit(node)

    def _has_component_decorator(self, node: ast.ClassDef) -> bool:
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Name) and decorator.id == "component":
                return True
            if isinstance(decorator, ast.Attribute) and decorator.attr == "component":
                return True
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "component":
                    return True
                if isinstance(decorator.func, ast.Attribute) and decorator.func.attr == "component":
                    return True
        return False

    def _extract_component_info(self, node: ast.ClassDef) -> dict[str, Any]:
        output_types = []
        has_run_method = False
        run_inputs = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == "run":
                    has_run_method = True
                    for arg in item.args.args:
                        if arg.arg != "self":
                            run_inputs.append(arg.arg)

                for decorator in item.decorator_list:
                    if self._is_output_types_decorator(decorator):
                        output_types.extend(self._extract_output_types(decorator))

        return {
            "name": node.name,
            "output_types": output_types,
            "run_inputs": run_inputs,
            "has_run_method": has_run_method,
            "lineno": node.lineno,
        }

    def _is_output_types_decorator(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                return node.func.attr == "output_types"
        return False

    def _extract_output_types(self, node: ast.Call) -> list[str]:
        types = []
        for keyword in node.keywords:
            if keyword.arg:
                types.append(keyword.arg)
        return types


class HaystackPipelineVisitor(ast.NodeVisitor):
    """AST visitor to detect Pipeline construction and wiring."""

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.pipelines: list[dict[str, Any]] = []
        self._current_pipeline: dict[str, Any] | None = None
        self._pipeline_vars: set[str] = set()

    def visit_Assign(self, node: ast.Assign) -> None:
        if isinstance(node.value, ast.Call):
            if self._is_pipeline_call(node.value):
                name = self._get_target_name(node.targets[0])
                if name:
                    self._pipeline_vars.add(name)
                    self._current_pipeline = {
                        "var_name": name,
                        "components": [],
                        "connections": [],
                        "lineno": node.lineno,
                    }
                    self.pipelines.append(self._current_pipeline)

        self.generic_visit(node)

    def visit_Expr(self, node: ast.Expr) -> None:
        if isinstance(node.value, ast.Call):
            self._check_pipeline_method(node.value)

        self.generic_visit(node)

    def _is_pipeline_call(self, node: ast.Call) -> bool:
        if isinstance(node.func, ast.Name):
            return node.func.id == "Pipeline"
        if isinstance(node.func, ast.Attribute):
            return node.func.attr == "Pipeline"
        return False

    def _check_pipeline_method(self, node: ast.Call) -> None:
        if not isinstance(node.func, ast.Attribute):
            return

        if isinstance(node.func.value, ast.Name):
            if node.func.value.id not in self._pipeline_vars:
                return
        else:
            return

        method_name = node.func.attr

        if method_name == "add_component":
            comp_info = self._extract_add_component(node)
            if comp_info and self._current_pipeline:
                self._current_pipeline["components"].append(comp_info)

        elif method_name == "connect":
            conn_info = self._extract_connect(node)
            if conn_info and self._current_pipeline:
                self._current_pipeline["connections"].append(conn_info)

    def _extract_add_component(self, node: ast.Call) -> dict[str, Any] | None:
        name = None
        component_type = None

        if node.args and len(node.args) >= 2:
            name = self._get_arg_repr(node.args[0])
            component_type = self._get_component_type(node.args[1])
        elif node.args and len(node.args) == 1:
            name = self._get_arg_repr(node.args[0])

        for keyword in node.keywords:
            if keyword.arg == "name":
                name = self._get_arg_repr(keyword.value)
            elif keyword.arg == "instance":
                component_type = self._get_component_type(keyword.value)

        if name:
            return {
                "name": name.strip("'\""),
                "component_type": component_type or "unknown",
            }
        return None

    def _extract_connect(self, node: ast.Call) -> dict[str, Any] | None:
        if len(node.args) >= 2:
            source = self._get_arg_repr(node.args[0])
            target = self._get_arg_repr(node.args[1])
            if source and target:
                return {
                    "source": source.strip("'\""),
                    "target": target.strip("'\""),
                }
        return None

    def _get_component_type(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            if isinstance(node.func, ast.Attribute):
                return node.func.attr
        if isinstance(node, ast.Name):
            return node.id
        return None

    def _get_target_name(self, target: ast.expr) -> str | None:
        if isinstance(target, ast.Name):
            return target.id
        return None

    def _get_arg_repr(self, node: ast.expr) -> str | None:
        if isinstance(node, ast.Constant):
            return str(node.value)
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            parts = []
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"{node.func.id}(...)"
            if isinstance(node.func, ast.Attribute):
                return f"{node.func.attr}(...)"
        return None


def export_haystack_workflows(workspace: Path) -> list[WorkflowInfo]:
    """Export Haystack pipelines from workspace to WorkflowInfo.

    Phase 31: Static analysis only, no code execution.

    Args:
        workspace: Path to workspace directory

    Returns:
        List of WorkflowInfo objects, one per detected pipeline

    """
    workflows = []

    for py_file in workspace.rglob("*.py"):
        if ".venv" in py_file.parts or "venv" in py_file.parts:
            continue
        if "node_modules" in py_file.parts:
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")

            if "haystack" not in content:
                continue

            tree = ast.parse(content, filename=str(py_file))

            comp_visitor = HaystackComponentVisitor(py_file)
            comp_visitor.visit(tree)

            pipe_visitor = HaystackPipelineVisitor(py_file)
            pipe_visitor.visit(tree)

            for comp in comp_visitor.components:
                workflow = _component_to_workflow(comp, py_file, workspace)
                workflows.append(workflow)

            for pipe in pipe_visitor.pipelines:
                workflow = _pipeline_to_workflow(pipe, comp_visitor.components, py_file, workspace)
                workflows.append(workflow)

        except SyntaxError as e:
            log.debug("Failed to parse %s: %s", py_file, e)
        except Exception as e:
            log.debug("Failed to process %s: %s", py_file, e)

    return workflows


def _component_to_workflow(
    comp_info: dict[str, Any], source_file: Path, workspace: Path
) -> WorkflowInfo:
    """Convert a @component class to WorkflowInfo."""
    comp_name = comp_info["name"]
    rel_path = source_file.relative_to(workspace)

    nodes = []
    edges = []
    node_id = 0

    comp_node = WorkflowNode(
        id=f"comp_{node_id}",
        type=NodeType.AGENT,
        label=comp_name,
        metadata={
            "output_types": comp_info.get("output_types", []),
            "run_inputs": comp_info.get("run_inputs", []),
        },
        source_location=SourceLocation(
            file=str(rel_path),
            line=comp_info["lineno"],
        ),
    )
    nodes.append(comp_node)
    node_id += 1

    for input_name in comp_info.get("run_inputs", []):
        input_node = WorkflowNode(
            id=f"input_{node_id}",
            type=NodeType.START,
            label=input_name,
            metadata={"kind": "run_input"},
        )
        nodes.append(input_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=input_node.id,
                to_node=comp_node.id,
                label="input",
            )
        )
        node_id += 1

    for output_name in comp_info.get("output_types", []):
        output_node = WorkflowNode(
            id=f"output_{node_id}",
            type=NodeType.END,
            label=output_name,
            metadata={"kind": "output_type"},
        )
        nodes.append(output_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=comp_node.id,
                to_node=output_node.id,
                label="output",
            )
        )
        node_id += 1

    return WorkflowInfo(
        id=f"haystack_comp_{comp_name}",
        name=comp_name,
        description=f"Haystack Component: {comp_name}",
        runtime="haystack",
        nodes=nodes,
        edges=edges,
        entry_points=[comp_node.id],
        metadata={
            "source_file": str(rel_path),
            "kind": "component",
            "has_run_method": comp_info.get("has_run_method", False),
        },
    )


def _pipeline_to_workflow(
    pipe_info: dict[str, Any],
    components: list[dict[str, Any]],
    source_file: Path,
    workspace: Path,
) -> WorkflowInfo:
    """Convert a Pipeline construction to WorkflowInfo."""
    pipe_name = pipe_info["var_name"]
    rel_path = source_file.relative_to(workspace)

    nodes = []
    edges = []
    node_id = 0
    name_to_node_id: dict[str, str] = {}

    for comp in pipe_info.get("components", []):
        comp_name = comp["name"]
        comp_type = comp.get("component_type", "unknown")
        node_type = _classify_component_type(comp_type)

        node = WorkflowNode(
            id=f"node_{node_id}",
            type=node_type,
            label=comp_name,
            metadata={
                "component_type": comp_type,
            },
            source_location=SourceLocation(
                file=str(rel_path),
                line=pipe_info["lineno"],
            ),
        )
        nodes.append(node)
        name_to_node_id[comp_name] = node.id
        node_id += 1

    for conn in pipe_info.get("connections", []):
        source_path = conn["source"]
        target_path = conn["target"]

        source_comp = source_path.split(".")[0] if "." in source_path else source_path
        target_comp = target_path.split(".")[0] if "." in target_path else target_path

        source_id = name_to_node_id.get(source_comp)
        target_id = name_to_node_id.get(target_comp)

        if source_id and target_id:
            source_socket = source_path.split(".")[-1] if "." in source_path else ""
            target_socket = target_path.split(".")[-1] if "." in target_path else ""
            label = f"{source_socket} → {target_socket}" if source_socket else "connect"

            edges.append(
                WorkflowEdge(
                    id=f"edge_{len(edges)}",
                    from_node=source_id,
                    to_node=target_id,
                    label=label,
                )
            )

    entry_points = [nodes[0].id] if nodes else []

    return WorkflowInfo(
        id=f"haystack_pipe_{pipe_name}",
        name=pipe_name,
        description=f"Haystack Pipeline: {pipe_name}",
        runtime="haystack",
        nodes=nodes,
        edges=edges,
        entry_points=entry_points,
        metadata={
            "source_file": str(rel_path),
            "kind": "pipeline",
            "component_count": len(pipe_info.get("components", [])),
            "connection_count": len(pipe_info.get("connections", [])),
        },
    )


def _classify_component_type(component_type: str) -> NodeType:
    """Classify a Haystack component type into an ARC NodeType."""
    type_lower = component_type.lower()

    for keyword, node_type in HAYSTACK_COMPONENT_CATEGORIES.items():
        if keyword in type_lower:
            return node_type

    return NodeType.AGENT
