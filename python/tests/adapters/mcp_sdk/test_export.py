"""Tests for MCP Python SDK static workflow export."""

from __future__ import annotations

import ast

from agent_runtime_cockpit.adapters.mcp_sdk.export import (
    MCPSDKVisitor,
    export_mcp_sdk_workflows,
)
from agent_runtime_cockpit.protocol.schemas import NodeType


# ── MCPSDKVisitor ────────────────────────────────────────────────────────────


def test_visitor_fastmcp_server(tmp_path):
    src = "from mcp.server.fastmcp import FastMCP\nmcp = FastMCP('Demo')\n"
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert len(visitor.servers) == 1
    assert visitor.servers[0]["name"] == "Demo"
    assert visitor.servers[0]["kind"] == "fastmcp"


def test_visitor_fastmcp_no_name_uses_var(tmp_path):
    src = "from mcp.server.fastmcp import FastMCP\nmy_server = FastMCP()\n"
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert len(visitor.servers) == 1
    assert visitor.servers[0]["name"] == "my_server"
    assert visitor.servers[0]["var_name"] == "my_server"


def test_visitor_tool_decorator(tmp_path):
    src = (
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.tool()\n"
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert len(visitor.tools) == 1
    assert visitor.tools[0]["name"] == "add"


def test_visitor_multiple_tools(tmp_path):
    src = (
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.tool()\ndef add(a: int, b: int) -> int: ...\n\n"
        "@mcp.tool()\ndef subtract(a: int, b: int) -> int: ...\n\n"
        "@mcp.tool()\ndef multiply(a: int, b: int) -> int: ...\n"
    )
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert len(visitor.tools) == 3
    names = [t["name"] for t in visitor.tools]
    assert "add" in names
    assert "subtract" in names
    assert "multiply" in names


def test_visitor_resource_decorator(tmp_path):
    src = (
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.resource('config://settings')\n"
        "def get_settings() -> str:\n"
        "    return '{}'\n"
    )
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert len(visitor.resources) == 1
    assert visitor.resources[0]["name"] == "get_settings"
    assert visitor.resources[0]["uri"] == "config://settings"


def test_visitor_resource_template_uri(tmp_path):
    src = (
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.resource('file://docs/{name}')\n"
        "def read_doc(name: str) -> str:\n"
        "    return 'content'\n"
    )
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert visitor.resources[0]["uri"] == "file://docs/{name}"


def test_visitor_prompt_decorator(tmp_path):
    src = (
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.prompt(title='Code Review')\n"
        "def review_code(code: str) -> str:\n"
        "    return f'Review: {code}'\n"
    )
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert len(visitor.prompts) == 1
    assert visitor.prompts[0]["name"] == "review_code"
    assert visitor.prompts[0]["title"] == "Code Review"


def test_visitor_prompt_no_title_uses_fn_name(tmp_path):
    src = (
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.prompt()\n"
        "def greet(name: str) -> str:\n"
        "    return f'Hello {name}'\n"
    )
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert visitor.prompts[0]["title"] == "greet"


def test_visitor_async_tool(tmp_path):
    src = (
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.tool()\n"
        "async def fetch_data(url: str) -> str:\n"
        "    return 'data'\n"
    )
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert len(visitor.tools) == 1
    assert visitor.tools[0]["name"] == "fetch_data"


def test_visitor_annotated_assign_fastmcp(tmp_path):
    src = "from mcp.server.fastmcp import FastMCP\nmcp: FastMCP = FastMCP('Typed')\n"
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "server.py")
    visitor.visit(tree)
    assert len(visitor.servers) == 1
    assert visitor.servers[0]["name"] == "Typed"


def test_visitor_empty_file(tmp_path):
    src = "# just a comment\n"
    tree = ast.parse(src)
    visitor = MCPSDKVisitor(tmp_path / "empty.py")
    visitor.visit(tree)
    assert visitor.servers == []
    assert visitor.tools == []
    assert visitor.resources == []
    assert visitor.prompts == []


# ── export_mcp_sdk_workflows ─────────────────────────────────────────────────


def test_export_empty_workspace(tmp_path):
    workflows = export_mcp_sdk_workflows(tmp_path)
    assert workflows == []


def test_export_simple_fastmcp_server(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.tool()\n"
        "def add(a: int, b: int) -> int:\n"
        "    return a + b\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    assert len(workflows) == 1
    wf = workflows[0]
    assert wf.runtime == "mcp_sdk"
    assert wf.name == "Demo"
    assert wf.metadata["tool_count"] == 1
    assert wf.metadata["resource_count"] == 0
    assert wf.metadata["prompt_count"] == 0


def test_export_workflow_nodes_and_edges(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.tool()\ndef t1() -> str: ...\n\n"
        "@mcp.resource('x://y')\ndef r1() -> str: ...\n\n"
        "@mcp.prompt()\ndef p1() -> str: ...\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    assert len(workflows) == 1
    wf = workflows[0]
    # server + 1 tool + 1 resource + 1 prompt
    assert len(wf.nodes) == 4
    assert len(wf.edges) == 3

    server_nodes = [n for n in wf.nodes if n.id == "server_0"]
    tool_nodes = [n for n in wf.nodes if n.id.startswith("tool_")]
    resource_nodes = [n for n in wf.nodes if n.id.startswith("resource_")]
    prompt_nodes = [n for n in wf.nodes if n.id.startswith("prompt_")]

    assert len(server_nodes) == 1
    assert len(tool_nodes) == 1
    assert len(resource_nodes) == 1
    assert len(prompt_nodes) == 1

    assert server_nodes[0].type == NodeType.AGENT
    assert tool_nodes[0].type == NodeType.TOOL
    assert resource_nodes[0].type == NodeType.RESOURCE
    assert resource_nodes[0].metadata.get("node_kind") == "resource"
    assert prompt_nodes[0].type == NodeType.PROMPT
    assert prompt_nodes[0].metadata.get("node_kind") == "prompt"


def test_export_ignores_non_mcp_decorator_when_server_var_known(tmp_path):
    """Avoid matching app.tool() when app is not the known MCP server instance."""
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n"
        "app = object()\n\n"
        "@app.tool()\n"
        "def flask_like_tool() -> str: ...\n\n"
        "@mcp.tool()\n"
        "def real_tool() -> str: ...\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    assert len(workflows) == 1
    tool_nodes = [n for n in workflows[0].nodes if n.id.startswith("tool_")]
    assert [n.label for n in tool_nodes] == ["real_tool"]


def test_export_edge_labels(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.tool()\ndef t() -> str: ...\n\n"
        "@mcp.resource('x://y')\ndef r() -> str: ...\n\n"
        "@mcp.prompt()\ndef p() -> str: ...\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    wf = workflows[0]
    labels = {e.label for e in wf.edges}
    assert "exposes_tool" in labels
    assert "exposes_resource" in labels
    assert "exposes_prompt" in labels


def test_export_entry_points(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\nmcp = FastMCP('Demo')\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    assert workflows[0].entry_points == ["server_0"]


def test_export_workflow_id_includes_runtime(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\nmcp = FastMCP('MyServer')\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    assert workflows[0].runtime == "mcp_sdk"
    assert "mcp_sdk" in workflows[0].id


def test_export_source_file_in_metadata(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\nmcp = FastMCP('Demo')\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    assert "server.py" in workflows[0].metadata["source_file"]


def test_export_skips_non_mcp_file(tmp_path):
    (tmp_path / "other.py").write_text("x = 1\n")
    workflows = export_mcp_sdk_workflows(tmp_path)
    assert workflows == []


def test_export_handles_syntax_error(tmp_path):
    (tmp_path / "broken.py").write_text(
        "from mcp.server.fastmcp import FastMCP\ndef (\n"  # invalid syntax
    )
    # Should not raise; silently skip
    workflows = export_mcp_sdk_workflows(tmp_path)
    assert workflows == []


def test_export_implicit_server_from_tools_only(tmp_path):
    """If file has @mcp.tool() but no explicit FastMCP(...), still emit workflow."""
    (tmp_path / "tools.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "# server defined elsewhere\n\n"
        "@mcp.tool()\n"
        "def my_tool() -> str: ...\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    # Should emit implicit server workflow
    assert len(workflows) == 1
    assert workflows[0].metadata["tool_count"] == 1


def test_export_multiple_files(tmp_path):
    (tmp_path / "server_a.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('ServerA')\n"
        "@mcp.tool()\ndef t_a() -> str: ...\n"
    )
    (tmp_path / "server_b.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "app = FastMCP('ServerB')\n"
        "@app.tool()\ndef t_b() -> str: ...\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    names = {wf.name for wf in workflows}
    assert "ServerA" in names
    assert "ServerB" in names


def test_export_uri_preserved_in_resource_node(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\n"
        "mcp = FastMCP('Demo')\n\n"
        "@mcp.resource('file://docs/{name}')\n"
        "def read_doc(name: str) -> str:\n"
        "    return 'content'\n"
    )
    workflows = export_mcp_sdk_workflows(tmp_path)
    wf = workflows[0]
    resource_nodes = [n for n in wf.nodes if n.metadata.get("node_kind") == "resource"]
    assert resource_nodes[0].metadata["uri"] == "file://docs/{name}"
