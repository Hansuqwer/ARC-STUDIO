"""DSPy export functionality.

Phase 30: Export DSPy programs/modules to WorkflowInfo.

Strategy:
- AST-based static analysis (no code execution)
- Detect Signature subclasses and extract input/output fields
- Detect Module subclasses and their composition
- Detect module instantiations (Predict, ChainOfThought, ReAct, etc.)
- Map to ARC WorkflowInfo structure
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


DSPY_MODULE_TYPES = frozenset(
    {
        "Predict",
        "ChainOfThought",
        "ReAct",
        "ProgramOfThought",
        "MultiChainComparison",
        "Parallel",
        "BestOfN",
        "Refine",
        "CodeAct",
    }
)


class DSPySignatureVisitor(ast.NodeVisitor):
    """AST visitor to detect DSPy Signature definitions."""

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.signatures: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to find Signature subclasses."""
        if self._is_signature_class(node):
            sig_info = self._extract_signature_info(node)
            self.signatures.append(sig_info)

        self.generic_visit(node)

    def _is_signature_class(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from dspy.Signature."""
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                if base.attr == "Signature":
                    return True
                if self._get_attribute_name(base).endswith(".Signature"):
                    return True
            elif isinstance(base, ast.Name):
                if base.id == "Signature":
                    return True
        return False

    def _extract_signature_info(self, node: ast.ClassDef) -> dict[str, Any]:
        """Extract signature fields from a Signature class."""
        input_fields = []
        output_fields = []
        docstring = ast.get_docstring(node) or ""

        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                field_name = item.target.id
                field_type = self._get_annotation_repr(item.annotation)
                is_input, is_output = self._classify_field(item)

                if is_input:
                    input_fields.append({"name": field_name, "type": field_type})
                elif is_output:
                    output_fields.append({"name": field_name, "type": field_type})

        return {
            "name": node.name,
            "docstring": docstring,
            "input_fields": input_fields,
            "output_fields": output_fields,
            "lineno": node.lineno,
        }

    def _classify_field(self, node: ast.AnnAssign) -> tuple[bool, bool]:
        """Classify a field as input, output, or both based on its value."""
        is_input = False
        is_output = False

        if node.value is not None:
            if isinstance(node.value, ast.Call):
                func_name = self._get_call_name(node.value)
                if func_name and "InputField" in func_name:
                    is_input = True
                elif func_name and "OutputField" in func_name:
                    is_output = True
        else:
            is_output = True

        return is_input, is_output

    def _get_call_name(self, node: ast.Call) -> str | None:
        """Get the function name from a Call node."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return self._get_attribute_name(node.func)
        return None

    def _get_annotation_repr(self, node: ast.expr | None) -> str:
        """Get string representation of a type annotation."""
        if node is None:
            return "Any"
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        elif isinstance(node, ast.Subscript):
            value = self._get_annotation_repr(node.value)
            slice_repr = self._get_annotation_repr(node.slice)
            return f"{value}[{slice_repr}]"
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        return "Any"

    def _get_attribute_name(self, node: ast.Attribute) -> str:
        """Get full attribute name."""
        parts = []
        current: ast.expr = node
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts))


class DSPyModuleVisitor(ast.NodeVisitor):
    """AST visitor to detect DSPy Module definitions and instantiations."""

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.modules: list[dict[str, Any]] = []
        self.instantiations: list[dict[str, Any]] = []

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Visit class definitions to find Module subclasses."""
        if self._is_module_class(node):
            module_info = self._extract_module_info(node)
            self.modules.append(module_info)

        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignments to detect module instantiations."""
        if isinstance(node.value, ast.Call):
            inst = self._check_instantiation(node.value)
            if inst:
                name = self._get_target_name(node.targets[0])
                if name:
                    inst["var_name"] = name
                    inst["lineno"] = node.lineno
                    self.instantiations.append(inst)

        self.generic_visit(node)

    def _is_module_class(self, node: ast.ClassDef) -> bool:
        """Check if class inherits from dspy.Module."""
        for base in node.bases:
            if isinstance(base, ast.Attribute):
                if base.attr == "Module":
                    return True
            elif isinstance(base, ast.Name):
                if base.id == "Module":
                    return True
        return False

    def _extract_module_info(self, node: ast.ClassDef) -> dict[str, Any]:
        """Extract module composition from a Module class."""
        sub_modules = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                for stmt in ast.walk(item):
                    if isinstance(stmt, ast.Assign):
                        if isinstance(stmt.value, ast.Call):
                            inst = self._check_instantiation(stmt.value)
                            if inst:
                                name = self._get_target_name(stmt.targets[0])
                                if name:
                                    inst["var_name"] = name
                                    sub_modules.append(inst)

        return {
            "name": node.name,
            "sub_modules": sub_modules,
            "lineno": node.lineno,
        }

    def _check_instantiation(self, node: ast.Call) -> dict[str, Any] | None:
        """Check if a call is a DSPy module instantiation."""
        module_type = None

        if isinstance(node.func, ast.Attribute):
            if node.func.attr in DSPY_MODULE_TYPES:
                module_type = node.func.attr
        elif isinstance(node.func, ast.Name):
            if node.func.id in DSPY_MODULE_TYPES:
                module_type = node.func.id

        if module_type is None:
            return None

        signature_arg = None
        tools = []

        if node.args:
            signature_arg = self._get_arg_repr(node.args[0])

        for keyword in node.keywords:
            if keyword.arg == "tools":
                tools = self._extract_tools(keyword.value)

        return {
            "module_type": module_type,
            "signature": signature_arg,
            "tools": tools,
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

    def _get_target_name(self, target: ast.expr) -> str | None:
        """Extract variable name from assignment target."""
        if isinstance(target, ast.Name):
            return target.id
        elif isinstance(target, ast.Attribute):
            return target.attr
        return None

    def _get_arg_repr(self, node: ast.expr) -> str | None:
        """Get string representation of an argument."""
        if isinstance(node, ast.Constant):
            return str(node.value)
        elif isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            parts = []
            current: ast.expr = node
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return f"{node.func.id}(...)"
            elif isinstance(node.func, ast.Attribute):
                return f"{node.func.attr}(...)"
        return None


def export_dspy_workflows(workspace: Path) -> list[WorkflowInfo]:
    """Export DSPy programs from workspace to WorkflowInfo.

    Phase 30: Static analysis only, no code execution.

    Args:
        workspace: Path to workspace directory

    Returns:
        List of WorkflowInfo objects, one per detected DSPy program/module

    """
    workflows = []

    for py_file in workspace.rglob("*.py"):
        if ".venv" in py_file.parts or "venv" in py_file.parts:
            continue
        if "node_modules" in py_file.parts:
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")

            if "dspy" not in content and "dspy_ai" not in content:
                continue

            tree = ast.parse(content, filename=str(py_file))

            sig_visitor = DSPySignatureVisitor(py_file)
            sig_visitor.visit(tree)

            mod_visitor = DSPyModuleVisitor(py_file)
            mod_visitor.visit(tree)

            for sig in sig_visitor.signatures:
                workflow = _signature_to_workflow(sig, py_file, workspace)
                workflows.append(workflow)

            for mod in mod_visitor.modules:
                workflow = _module_to_workflow(mod, sig_visitor.signatures, py_file, workspace)
                workflows.append(workflow)

            if not mod_visitor.modules and mod_visitor.instantiations:
                workflow = _instantiations_to_workflow(
                    mod_visitor.instantiations, py_file, workspace
                )
                workflows.append(workflow)

        except SyntaxError as e:
            log.debug("Failed to parse %s: %s", py_file, e)
        except Exception as e:
            log.debug("Failed to process %s: %s", py_file, e)

    return workflows


def _signature_to_workflow(
    sig_info: dict[str, Any], source_file: Path, workspace: Path
) -> WorkflowInfo:
    """Convert a Signature definition to WorkflowInfo."""
    sig_name = sig_info["name"]
    rel_path = source_file.relative_to(workspace)

    nodes = []
    edges = []
    node_id = 0

    sig_node = WorkflowNode(
        id=f"sig_{node_id}",
        type=NodeType.AGENT,
        label=sig_name,
        metadata={
            "docstring": sig_info.get("docstring", ""),
            "input_fields": sig_info.get("input_fields", []),
            "output_fields": sig_info.get("output_fields", []),
        },
        source_location=SourceLocation(
            file=str(rel_path),
            line=sig_info["lineno"],
        ),
    )
    nodes.append(sig_node)
    node_id += 1

    for field in sig_info.get("input_fields", []):
        input_node = WorkflowNode(
            id=f"input_{node_id}",
            type=NodeType.START,
            label=field["name"],
            metadata={"type": field.get("type", "Any")},
        )
        nodes.append(input_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=input_node.id,
                to_node=sig_node.id,
                label="input",
            )
        )
        node_id += 1

    for field in sig_info.get("output_fields", []):
        output_node = WorkflowNode(
            id=f"output_{node_id}",
            type=NodeType.END,
            label=field["name"],
            metadata={"type": field.get("type", "Any")},
        )
        nodes.append(output_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=sig_node.id,
                to_node=output_node.id,
                label="output",
            )
        )
        node_id += 1

    return WorkflowInfo(
        id=f"dspy_sig_{sig_name}",
        name=sig_name,
        description=f"DSPy Signature: {sig_name}",
        runtime="dspy",
        nodes=nodes,
        edges=edges,
        entry_points=[sig_node.id],
        metadata={
            "source_file": str(rel_path),
            "kind": "signature",
            "input_count": len(sig_info.get("input_fields", [])),
            "output_count": len(sig_info.get("output_fields", [])),
        },
    )


def _module_to_workflow(
    mod_info: dict[str, Any],
    signatures: list[dict[str, Any]],
    source_file: Path,
    workspace: Path,
) -> WorkflowInfo:
    """Convert a Module class to WorkflowInfo."""
    mod_name = mod_info["name"]
    rel_path = source_file.relative_to(workspace)

    nodes = []
    edges = []
    node_id = 0

    mod_node = WorkflowNode(
        id=f"mod_{node_id}",
        type=NodeType.AGENT,
        label=mod_name,
        metadata={"kind": "dspy.Module"},
        source_location=SourceLocation(
            file=str(rel_path),
            line=mod_info["lineno"],
        ),
    )
    nodes.append(mod_node)
    node_id += 1

    prev_node_id = mod_node.id
    for sub in mod_info.get("sub_modules", []):
        sub_node = WorkflowNode(
            id=f"step_{node_id}",
            type=_module_type_to_node_type(sub["module_type"]),
            label=f"{sub.get('var_name', sub['module_type'])}",
            metadata={
                "module_type": sub["module_type"],
                "signature": sub.get("signature"),
                "tools": sub.get("tools", []),
            },
        )
        nodes.append(sub_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=prev_node_id,
                to_node=sub_node.id,
                label="calls",
            )
        )

        for tool_name in sub.get("tools", []):
            tool_node = WorkflowNode(
                id=f"tool_{node_id}",
                type=NodeType.TOOL,
                label=tool_name,
                metadata={"tool_name": tool_name},
            )
            nodes.append(tool_node)
            edges.append(
                WorkflowEdge(
                    id=f"edge_{len(edges)}",
                    from_node=sub_node.id,
                    to_node=tool_node.id,
                    label="uses",
                )
            )
            node_id += 1

        prev_node_id = sub_node.id
        node_id += 1

    return WorkflowInfo(
        id=f"dspy_mod_{mod_name}",
        name=mod_name,
        description=f"DSPy Module: {mod_name}",
        runtime="dspy",
        nodes=nodes,
        edges=edges,
        entry_points=[mod_node.id],
        metadata={
            "source_file": str(rel_path),
            "kind": "module",
            "sub_module_count": len(mod_info.get("sub_modules", [])),
        },
    )


def _instantiations_to_workflow(
    instantiations: list[dict[str, Any]], source_file: Path, workspace: Path
) -> WorkflowInfo:
    """Convert standalone module instantiations to WorkflowInfo."""
    rel_path = source_file.relative_to(workspace)

    nodes = []
    edges = []
    node_id = 0

    prev_id = None
    for inst in instantiations:
        var_name = inst.get("var_name", inst["module_type"])
        node = WorkflowNode(
            id=f"inst_{node_id}",
            type=_module_type_to_node_type(inst["module_type"]),
            label=var_name,
            metadata={
                "module_type": inst["module_type"],
                "signature": inst.get("signature"),
                "tools": inst.get("tools", []),
            },
            source_location=SourceLocation(
                file=str(rel_path),
                line=inst["lineno"],
            ),
        )
        nodes.append(node)

        if prev_id is not None:
            edges.append(
                WorkflowEdge(
                    id=f"edge_{len(edges)}",
                    from_node=prev_id,
                    to_node=node.id,
                    label="sequence",
                )
            )

        for tool_name in inst.get("tools", []):
            tool_node = WorkflowNode(
                id=f"tool_{node_id}",
                type=NodeType.TOOL,
                label=tool_name,
                metadata={"tool_name": tool_name},
            )
            nodes.append(tool_node)
            edges.append(
                WorkflowEdge(
                    id=f"edge_{len(edges)}",
                    from_node=node.id,
                    to_node=tool_node.id,
                    label="uses",
                )
            )
            node_id += 1

        prev_id = node.id
        node_id += 1

    entry = nodes[0].id if nodes else "inst_0"
    return WorkflowInfo(
        id=f"dspy_inst_{source_file.stem}",
        name=f"{source_file.stem} (DSPy)",
        description=f"DSPy program: {source_file.stem}",
        runtime="dspy",
        nodes=nodes,
        edges=edges,
        entry_points=[entry],
        metadata={
            "source_file": str(rel_path),
            "kind": "instantiation",
            "module_count": len(instantiations),
        },
    )


def _module_type_to_node_type(module_type: str) -> NodeType:
    """Map DSPy module type to ARC NodeType."""
    mapping = {
        "Predict": NodeType.AGENT,
        "ChainOfThought": NodeType.AGENT,
        "ReAct": NodeType.AGENT,
        "ProgramOfThought": NodeType.AGENT,
        "MultiChainComparison": NodeType.AGENT,
        "Parallel": NodeType.AGENT,
        "BestOfN": NodeType.AGENT,
        "Refine": NodeType.AGENT,
        "CodeAct": NodeType.AGENT,
    }
    return mapping.get(module_type, NodeType.AGENT)
