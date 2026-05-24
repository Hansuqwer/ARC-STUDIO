"""LangChain export functionality.

Phase 26 T2: Export Runnable/LCEL compositions to WorkflowInfo.

Strategy:
- AST-based static analysis (no code execution)
- Detect LCEL pipe operator (|) chains
- Detect RunnableSequence instantiations
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


class LangChainChainVisitor(ast.NodeVisitor):
    """AST visitor to detect LangChain Runnable compositions."""

    def __init__(self, source_file: Path):
        self.source_file = source_file
        self.chains: list[dict[str, Any]] = []
        self.current_chain: dict[str, Any] | None = None
        self.chain_counter = 0

    def visit_Assign(self, node: ast.Assign) -> None:
        """Visit assignment statements to detect chain definitions."""
        # Look for assignments like: chain = prompt | llm | parser
        if isinstance(node.value, ast.BinOp) and isinstance(node.value.op, ast.BitOr):
            # This is a pipe operator chain
            chain_name = self._get_target_name(node.targets[0]) if node.targets else None
            if chain_name:
                chain_info = self._extract_pipe_chain(node.value, chain_name, node.lineno)
                if chain_info:
                    self.chains.append(chain_info)

        # Look for RunnableSequence instantiations
        elif isinstance(node.value, ast.Call):
            if self._is_runnable_sequence_call(node.value):
                chain_name = self._get_target_name(node.targets[0]) if node.targets else None
                if chain_name:
                    chain_info = self._extract_sequence_chain(node.value, chain_name, node.lineno)
                    if chain_info:
                        self.chains.append(chain_info)

        self.generic_visit(node)

    def _get_target_name(self, target: ast.expr) -> str | None:
        """Extract variable name from assignment target."""
        if isinstance(target, ast.Name):
            return target.id
        return None

    def _is_runnable_sequence_call(self, node: ast.Call) -> bool:
        """Check if a call is to RunnableSequence."""
        if isinstance(node.func, ast.Name):
            return node.func.id == "RunnableSequence"
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr == "RunnableSequence"
        return False

    def _extract_pipe_chain(
        self, node: ast.BinOp, chain_name: str, lineno: int
    ) -> dict[str, Any] | None:
        """Extract chain information from pipe operator expression."""
        components = self._flatten_pipe_chain(node)
        if not components:
            return None

        return {
            "name": chain_name,
            "type": "pipe_chain",
            "components": components,
            "lineno": lineno,
        }

    def _flatten_pipe_chain(self, node: ast.expr) -> list[str]:
        """Flatten nested pipe operators into a list of component names."""
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            # Recursively flatten left and right sides
            left = self._flatten_pipe_chain(node.left)
            right = self._flatten_pipe_chain(node.right)
            return left + right
        else:
            # Leaf node - extract component name
            name = self._get_component_name(node)
            return [name] if name else []

    def _get_component_name(self, node: ast.expr) -> str | None:
        """Extract component name from AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return node.func.attr
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _extract_sequence_chain(
        self, node: ast.Call, chain_name: str, lineno: int
    ) -> dict[str, Any] | None:
        """Extract chain information from RunnableSequence call."""
        components = []
        for arg in node.args:
            name = self._get_component_name(arg)
            if name:
                components.append(name)

        if not components:
            return None

        return {
            "name": chain_name,
            "type": "sequence_chain",
            "components": components,
            "lineno": lineno,
        }


def scan_workspace_for_chains(workspace: Path) -> list[dict[str, Any]]:
    """Scan workspace for LangChain Runnable compositions.

    Returns list of detected chains with their components.
    """
    all_chains = []

    # Scan Python files
    for py_file in workspace.rglob("*.py"):
        if ".venv" in py_file.parts or "venv" in py_file.parts:
            continue
        if "node_modules" in py_file.parts:
            continue

        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content, filename=str(py_file))

            visitor = LangChainChainVisitor(py_file)
            visitor.visit(tree)

            for chain in visitor.chains:
                chain["source_file"] = str(py_file.relative_to(workspace))
                all_chains.append(chain)

        except SyntaxError as e:
            log.debug("Syntax error parsing %s: %s", py_file, e)
        except Exception as e:
            log.debug("Failed to parse %s: %s", py_file, e)

    return all_chains


def chain_to_workflow_info(
    chain: dict[str, Any], workspace: Path, runtime: str = "langchain"
) -> WorkflowInfo:
    """Convert detected chain to WorkflowInfo structure.

    Args:
        chain: Chain information from AST scan
        workspace: Workspace path
        runtime: Runtime identifier

    Returns:
        WorkflowInfo representing the chain

    """
    chain_name = chain["name"]
    components = chain["components"]
    source_file = chain.get("source_file")
    lineno = chain.get("lineno", 1)

    # Create nodes for each component
    nodes = []
    for i, component in enumerate(components):
        node = WorkflowNode(
            id=f"{chain_name}_{component}_{i}",
            label=component,
            type=NodeType.UNKNOWN,  # Could be AGENT, TOOL, etc. but we don't know from AST
            source_location=SourceLocation(file=source_file or "", line=lineno)
            if source_file
            else None,
            metadata={"component_index": i, "component_name": component},
        )
        nodes.append(node)

    # Create edges connecting components in sequence
    edges = []
    for i in range(len(components) - 1):
        edge = WorkflowEdge(
            id=f"{chain_name}_edge_{i}",
            from_node=nodes[i].id,
            to_node=nodes[i + 1].id,
            label=None,
            conditional=False,
            metadata={"chain_type": chain["type"]},
        )
        edges.append(edge)

    # Entry point is the first component
    entry_points = [nodes[0].id] if nodes else []

    return WorkflowInfo(
        id=f"langchain_{chain_name}",
        name=chain_name,
        runtime=runtime,
        source_file=source_file,
        nodes=nodes,
        edges=edges,
        entry_points=entry_points,
        metadata={
            "chain_type": chain["type"],
            "component_count": len(components),
            "detection_method": "ast_scan",
        },
    )


def export_langchain_workflows(workspace: Path) -> list[WorkflowInfo]:
    """Export LangChain workflows from workspace.

    Phase 26 T2: AST-based export only (no code execution).

    Args:
        workspace: Workspace path to scan

    Returns:
        List of WorkflowInfo for detected chains

    """
    chains = scan_workspace_for_chains(workspace)

    workflows = []
    for chain in chains:
        try:
            workflow = chain_to_workflow_info(chain, workspace)
            workflows.append(workflow)
        except Exception as e:
            log.warning("Failed to convert chain %s to workflow: %s", chain.get("name"), e)

    return workflows
