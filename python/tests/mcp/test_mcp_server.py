"""Tests for the MCP Local Control Plane (Phase 26 / R19).

Tests cover:
- Server creation with untrusted workspace (must fail)
- Server creation with trusted workspace (must succeed)
- Tool registration and basic JSON output
- Trust-gated enforcement
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.security.trust import trust_workspace


def test_create_mcp_server_untrusted_workspace(tmp_path: Path):
    """Server creation must raise MCPServerError for untrusted workspace."""
    from agent_runtime_cockpit.mcp.server import MCPServerError, create_mcp_server

    with pytest.raises(MCPServerError, match="untrusted"):
        create_mcp_server(workspace=tmp_path)


def test_create_mcp_server_trusted_workspace(tmp_path: Path):
    """Server creation must succeed for trusted workspace."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    # Trust the workspace first
    trust_workspace(tmp_path, note="test")

    server = create_mcp_server(workspace=tmp_path)
    assert server is not None
    assert server.name == "ARC Studio"


def test_arc_doctor_tool_registered(tmp_path: Path):
    """arc_doctor tool must be registered on the server."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    assert hasattr(server, "_tool_manager") or hasattr(server, "_tools")

    # Verify the tool exists by checking its name in the registered tools
    tool_names = _get_tool_names(server)
    assert "arc_doctor" in tool_names


def test_arc_run_status_tool_registered(tmp_path: Path):
    """arc_run_status tool must be registered."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool_names = _get_tool_names(server)
    assert "arc_run_status" in tool_names


def test_arc_trace_search_tool_registered(tmp_path: Path):
    """arc_trace_search tool must be registered."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool_names = _get_tool_names(server)
    assert "arc_trace_search" in tool_names


def test_arc_trace_read_tool_registered(tmp_path: Path):
    """arc_trace_read tool must be registered."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool_names = _get_tool_names(server)
    assert "arc_trace_read" in tool_names


def test_arc_audit_verify_tool_registered(tmp_path: Path):
    """arc_audit_verify tool must be registered."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool_names = _get_tool_names(server)
    assert "arc_audit_verify" in tool_names


def test_arc_hitl_list_tool_registered(tmp_path: Path):
    """arc_hitl_list tool must be registered."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool_names = _get_tool_names(server)
    assert "arc_hitl_list" in tool_names


def test_arc_runtime_capabilities_tool_registered(tmp_path: Path):
    """arc_runtime_capabilities tool must be registered."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool_names = _get_tool_names(server)
    assert "arc_runtime_capabilities" in tool_names


def test_arc_doctor_returns_json(tmp_path: Path):
    """arc_doctor tool must return valid JSON."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")
    result = tool()
    parsed = json.loads(result)
    assert isinstance(parsed, list)
    assert len(parsed) >= 3


def test_arc_doctor_includes_mcp_check(tmp_path: Path):
    """arc_doctor must include MCP support check."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")
    result = json.loads(tool())
    checks_by_name = {c["check"]: c for c in result}
    assert "mcp" in checks_by_name
    assert checks_by_name["mcp"]["ok"] is True
    assert checks_by_name["mcp"]["transport"] == "stdio"


def test_arc_doctor_includes_trust_check(tmp_path: Path):
    """arc_doctor must include trust status."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")
    result = json.loads(tool())
    checks_by_name = {c["check"]: c for c in result}
    assert "trust" in checks_by_name
    assert checks_by_name["trust"]["level"] == "trusted"


def test_arc_doctor_includes_python_and_cli(tmp_path: Path):
    """arc_doctor must include python and cli checks."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")
    result = json.loads(tool())
    checks_by_name = {c["check"]: c for c in result}
    assert "python" in checks_by_name
    assert "cli" in checks_by_name


def test_arc_run_status_returns_error_for_missing_run(tmp_path: Path):
    """arc_run_status must return error for non-existent run."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_run_status")
    result = json.loads(tool(run_id="nonexistent"))
    assert "error" in result
    assert "not found" in result["error"]


def test_arc_trace_search_requires_index(tmp_path: Path):
    """arc_trace_search must indicate when SQLite index is missing."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_trace_search")
    result = json.loads(tool())
    assert "error" in result


def test_arc_audit_verify_returns_error_for_missing_run(tmp_path: Path):
    """arc_audit_verify must handle missing run gracefully."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_audit_verify")
    result = json.loads(tool(run_id="nonexistent"))
    assert "ok" in result
    assert result["ok"] is False


def test_arc_hitl_list_returns_empty_for_no_prompts(tmp_path: Path):
    """arc_hitl_list must return empty list when no prompts exist."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_hitl_list")
    result = json.loads(tool())
    assert isinstance(result, list)


def test_resources_registered(tmp_path: Path):
    """MCP resources must be registered for runs, traces, and audit."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)

    # Check that all three resource patterns exist
    resource_patterns = _get_resource_patterns(server)
    assert any("arc://runs/" in str(r) for r in resource_patterns)
    assert any("arc://traces/" in str(r) for r in resource_patterns)
    assert any("arc://audit/" in str(r) for r in resource_patterns)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _get_tool_names(server) -> list[str]:
    """Get registered tool names from a FastMCP server."""
    tm = getattr(server, "_tool_manager", None)
    if tm is not None and hasattr(tm, "_tools"):
        return list(tm._tools.keys())
    return []


def _get_resource_patterns(server) -> list[str]:
    """Get registered resource URI patterns from a FastMCP server."""
    rm = getattr(server, "_resource_manager", None)
    if rm is not None and hasattr(rm, "_templates"):
        return list(rm._templates.keys())
    return []


def _get_tool_fn(server, name: str):
    """Get a tool callable by name from a FastMCP server."""
    tm = getattr(server, "_tool_manager", None)
    if tm is not None and hasattr(tm, "_tools"):
        tool = tm._tools.get(name)
        if tool is not None:
            return getattr(tool, "fn", None)
    raise ValueError(f"Tool '{name}' not found")
