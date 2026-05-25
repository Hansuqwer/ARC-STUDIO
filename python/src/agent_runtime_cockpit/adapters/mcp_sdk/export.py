"""MCP Python SDK static workflow export.

T2 export maps MCP Python SDK server constructs to ARC WorkflowInfo without
importing or executing workspace code.

Detected and exported constructs:
- FastMCP server instances             -- server node
- @mcp.tool() decorated functions      -- tool nodes with TOOL type
- @mcp.resource(uri) decorated funcs   -- resource nodes with RESOURCE type
- @mcp.prompt() decorated functions    -- prompt nodes with PROMPT type
- Low-level Server instances           -- server node (low-level variant)

Each file with a FastMCP/Server definition becomes one WorkflowInfo, with
nodes for the server, tools, resources, and prompts found in that file.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path
from typing import Any

from ...protocol.schemas import NodeType, SourceLocation, WorkflowEdge, WorkflowInfo, WorkflowNode

log = logging.getLogger(__name__)

# Import markers that identify an MCP Python SDK file
MCP_IMPORT_MARKERS = (
    "from mcp.server.fastmcp",
    "from mcp.server import",
    "from mcp import",
    "import mcp",
    "from mcp.client",
    "from mcp.server.lowlevel",
)

# Names considered FastMCP server constructors
FASTMCP_CONSTRUCTOR = "FastMCP"

# Names considered low-level server constructors (from mcp.server or mcp.server.lowlevel)
LOW_LEVEL_CONSTRUCTORS = frozenset({"Server"})


class MCPSDKVisitor(ast.NodeVisitor):
    """Collect MCP Python SDK constructs from a source file via static AST analysis."""

    def __init__(self, source_file: Path) -> None:
        self.source_file = source_file
        self.servers: list[dict[str, Any]] = []
        self.tools: list[dict[str, Any]] = []
        self.resources: list[dict[str, Any]] = []
        self.prompts: list[dict[str, Any]] = []
        # Track variable names that hold FastMCP/Server instances
        # so we can match decorator calls like @mcp.tool()
        self._server_var_names: set[str] = set()

    def visit_Assign(self, node: ast.Assign) -> None:
        """Capture: mcp = FastMCP('name') or server = Server()."""
        if isinstance(node.value, ast.Call):
            call_name = _call_name(node.value)
            if call_name and _last_name(call_name) == FASTMCP_CONSTRUCTOR:
                var = _target_name(node.targets[0]) if node.targets else None
                name_arg = _constant_kw(node.value, "name") or _first_positional_str(node.value)
                self.servers.append(
                    {
                        "var_name": var,
                        "name": name_arg or (var or "unnamed"),
                        "kind": "fastmcp",
                        "lineno": node.lineno,
                    }
                )
                if var:
                    self._server_var_names.add(var)
            elif call_name and _last_name(call_name) in LOW_LEVEL_CONSTRUCTORS:
                var = _target_name(node.targets[0]) if node.targets else None
                name_arg = _first_positional_str(node.value)
                self.servers.append(
                    {
                        "var_name": var,
                        "name": name_arg or (var or "unnamed"),
                        "kind": "low_level",
                        "lineno": node.lineno,
                    }
                )
                if var:
                    self._server_var_names.add(var)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        """Capture annotated assignments: mcp: FastMCP = FastMCP('name')."""
        if isinstance(node.value, ast.Call):
            call_name = _call_name(node.value)
            if call_name and _last_name(call_name) == FASTMCP_CONSTRUCTOR:
                var = _target_name(node.target)
                name_arg = _constant_kw(node.value, "name") or _first_positional_str(node.value)
                self.servers.append(
                    {
                        "var_name": var,
                        "name": name_arg or (var or "unnamed"),
                        "kind": "fastmcp",
                        "lineno": node.lineno,
                    }
                )
                if var:
                    self._server_var_names.add(var)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_fn(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_fn(node)
        self.generic_visit(node)

    def _visit_fn(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        """Classify decorated functions into tools, resources, or prompts."""
        for dec in node.decorator_list:
            dec_str = _decorator_str(dec)
            if dec_str is None:
                continue

            # Detect @mcp.tool() / @server.tool() / @app.tool()
            if _is_mcp_decorator(dec_str, "tool", self._server_var_names):
                self.tools.append(
                    {
                        "name": node.name,
                        "lineno": node.lineno,
                        "decorator": dec_str,
                    }
                )
                return

            # Detect @mcp.resource("uri://...") / @server.resource(...)
            if _is_mcp_decorator(dec_str, "resource", self._server_var_names):
                uri = _decorator_first_arg_str(dec)
                self.resources.append(
                    {
                        "name": node.name,
                        "uri": uri,
                        "lineno": node.lineno,
                        "decorator": dec_str,
                    }
                )
                return

            # Detect @mcp.prompt() / @server.prompt()
            if _is_mcp_decorator(dec_str, "prompt", self._server_var_names):
                title = _decorator_kw_str(dec, "title")
                self.prompts.append(
                    {
                        "name": node.name,
                        "title": title or node.name,
                        "lineno": node.lineno,
                        "decorator": dec_str,
                    }
                )
                return


def export_mcp_sdk_workflows(workspace: Path) -> list[WorkflowInfo]:
    """Export MCP Python SDK servers from workspace to WorkflowInfo.

    Pure static AST analysis — no workspace code is imported or executed.
    Each Python file that defines at least one FastMCP/Server instance is
    exported as one WorkflowInfo containing all tools/resources/prompts
    found in that file.
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
        if not any(marker in content for marker in MCP_IMPORT_MARKERS):
            continue
        try:
            tree = ast.parse(content, filename=str(py_file))
        except SyntaxError as exc:
            log.debug("Failed to parse %s: %s", py_file, exc)
            continue
        except Exception as exc:  # noqa: BLE001
            log.debug("Unexpected parse error in %s: %s", py_file, exc)
            continue

        visitor = MCPSDKVisitor(py_file)
        visitor.visit(tree)

        # Emit one WorkflowInfo per server definition found in this file
        for server in visitor.servers:
            workflows.append(
                _server_to_workflow(
                    server,
                    visitor.tools,
                    visitor.resources,
                    visitor.prompts,
                    py_file,
                    workspace,
                )
            )

        # If no explicit server found but tools/resources/prompts exist,
        # emit one WorkflowInfo as an implicit server (common in module-level patterns)
        if not visitor.servers and (visitor.tools or visitor.resources or visitor.prompts):
            workflows.append(
                _server_to_workflow(
                    {
                        "var_name": None,
                        "name": py_file.stem,
                        "kind": "implicit",
                        "lineno": 1,
                    },
                    visitor.tools,
                    visitor.resources,
                    visitor.prompts,
                    py_file,
                    workspace,
                )
            )

    return workflows


def _server_to_workflow(
    server: dict[str, Any],
    tools: list[dict[str, Any]],
    resources: list[dict[str, Any]],
    prompts: list[dict[str, Any]],
    source_file: Path,
    workspace: Path,
) -> WorkflowInfo:
    rel_path = source_file.relative_to(workspace)
    nodes: list[WorkflowNode] = []
    edges: list[WorkflowEdge] = []

    server_node = WorkflowNode(
        id="server_0",
        type=NodeType.AGENT,
        label=server["name"],
        metadata={
            "kind": server["kind"],
            "var_name": server.get("var_name"),
        },
        source_location=SourceLocation(file=str(rel_path), line=server["lineno"]),
    )
    nodes.append(server_node)

    for idx, tool in enumerate(tools, start=1):
        tool_node = WorkflowNode(
            id=f"tool_{idx}",
            type=NodeType.TOOL,
            label=tool["name"],
            metadata={"decorator": tool.get("decorator")},
            source_location=SourceLocation(file=str(rel_path), line=tool["lineno"]),
        )
        nodes.append(tool_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=server_node.id,
                to_node=tool_node.id,
                label="exposes_tool",
            )
        )

    for idx, resource in enumerate(resources, start=1):
        resource_node = WorkflowNode(
            id=f"resource_{idx}",
            type=NodeType.TOOL,  # NodeType.RESOURCE not in current schema; use TOOL
            label=resource["name"],
            metadata={
                "uri": resource.get("uri"),
                "decorator": resource.get("decorator"),
                "node_kind": "resource",
            },
            source_location=SourceLocation(file=str(rel_path), line=resource["lineno"]),
        )
        nodes.append(resource_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=server_node.id,
                to_node=resource_node.id,
                label="exposes_resource",
            )
        )

    for idx, prompt in enumerate(prompts, start=1):
        prompt_node = WorkflowNode(
            id=f"prompt_{idx}",
            type=NodeType.TOOL,  # NodeType.PROMPT not in current schema; use TOOL
            label=prompt["name"],
            metadata={
                "title": prompt.get("title"),
                "decorator": prompt.get("decorator"),
                "node_kind": "prompt",
            },
            source_location=SourceLocation(file=str(rel_path), line=prompt["lineno"]),
        )
        nodes.append(prompt_node)
        edges.append(
            WorkflowEdge(
                id=f"edge_{len(edges)}",
                from_node=server_node.id,
                to_node=prompt_node.id,
                label="exposes_prompt",
            )
        )

    return WorkflowInfo(
        id=f"mcp_sdk_{server['name']}_{source_file.stem}",
        name=server["name"],
        description=(
            f"MCP server '{server['name']}' with {len(tools)} tool(s), "
            f"{len(resources)} resource(s), {len(prompts)} prompt(s)"
        ),
        runtime="mcp_sdk",
        nodes=nodes,
        edges=edges,
        entry_points=[server_node.id],
        metadata={
            "source_file": str(rel_path),
            "kind": server["kind"],
            "tool_count": len(tools),
            "resource_count": len(resources),
            "prompt_count": len(prompts),
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


def _first_positional_str(node: ast.Call) -> str | None:
    """Return the first positional argument as a string if it's a constant."""
    if node.args and isinstance(node.args[0], ast.Constant):
        return str(node.args[0].value)
    return None


def _decorator_str(dec: ast.expr) -> str | None:
    """Return a compact string representation of a decorator for pattern matching."""
    if isinstance(dec, ast.Name):
        return dec.id
    if isinstance(dec, ast.Attribute):
        return f"{_expr_name(dec.value)}.{dec.attr}"
    if isinstance(dec, ast.Call):
        inner = _decorator_str(dec.func)
        return inner
    return None


def _decorator_first_arg_str(dec: ast.expr) -> str | None:
    """Return first positional argument of a decorator call if string constant."""
    if isinstance(dec, ast.Call) and dec.args:
        if isinstance(dec.args[0], ast.Constant):
            return str(dec.args[0].value)
    return None


def _decorator_kw_str(dec: ast.expr, kw: str) -> str | None:
    """Return keyword argument value from decorator call."""
    if isinstance(dec, ast.Call):
        return _constant_kw(dec, kw)
    return None


def _is_mcp_decorator(dec_str: str, method: str, server_var_names: set[str]) -> bool:
    """Return True if dec_str represents a call like <server_var>.<method>."""
    # Direct match: mcp.tool, server.tool, app.tool, etc.
    if dec_str.endswith(f".{method}"):
        prefix = dec_str[: -(len(method) + 1)]
        # Any name that is a known server variable, or any short variable name
        # that could plausibly be an MCP server instance
        if server_var_names and prefix in server_var_names:
            return True
        # Heuristic: if no server vars found yet (module-level scan), accept
        # any single-identifier prefix that isn't an obvious non-server name
        if not server_var_names:
            return _looks_like_mcp_var(prefix)
        # Even with known vars, accept common MCP variable names
        return _looks_like_mcp_var(prefix)
    return False


def _looks_like_mcp_var(name: str) -> bool:
    """Heuristic: does this variable name look like an MCP server instance?"""
    # Common naming conventions for MCP servers
    common = {"mcp", "server", "app", "fastmcp", "srv", "s"}
    return name.lower() in common or name.lower().startswith("mcp")


def _skip_path(path: Path) -> bool:
    ignored = {".venv", "venv", "node_modules", "__pycache__", ".git"}
    return any(part in ignored for part in path.parts)
