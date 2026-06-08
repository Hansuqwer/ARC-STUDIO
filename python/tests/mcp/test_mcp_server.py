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
    assert parsed["ok"] is True
    assert isinstance(parsed["data"], list)
    assert len(parsed["data"]) >= 3


def test_arc_doctor_includes_mcp_check(tmp_path: Path):
    """arc_doctor must include MCP support check."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")
    result = json.loads(tool())["data"]
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
    result = json.loads(tool())["data"]
    checks_by_name = {c["check"]: c for c in result}
    assert "trust" in checks_by_name
    assert checks_by_name["trust"]["level"] == "trusted"


def test_arc_doctor_includes_python_and_cli(tmp_path: Path):
    """arc_doctor must include python and cli checks."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")
    result = json.loads(tool())["data"]
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
    assert result["ok"] is False
    assert "not found" in result["error"]["message"]


def test_arc_trace_search_requires_index(tmp_path: Path):
    """arc_trace_search must indicate when SQLite index is missing."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_trace_search")
    result = json.loads(tool())
    assert result["ok"] is False
    assert "SQLite index not found" in result["error"]["message"]


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
    assert result["ok"] is True
    assert isinstance(result["data"], list)


def test_tool_rechecks_trust_after_server_creation(tmp_path: Path, monkeypatch):
    """Tool calls must fail closed if trust is revoked after server creation."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server
    import agent_runtime_cockpit.mcp.server as mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")

    def deny(_workspace):
        from agent_runtime_cockpit.security.trust import WorkspaceUntrusted

        raise WorkspaceUntrusted("revoked")

    monkeypatch.setattr(mcp_server, "ensure_trusted", deny)
    result = json.loads(tool())
    assert result["ok"] is False
    assert result["error"]["details"]["code"] == "WORKSPACE_UNTRUSTED"


def test_arc_trace_read_rejects_traversal_run_id(tmp_path: Path):
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_trace_read")
    result = json.loads(tool(run_id="../secret"))
    assert result["ok"] is False
    assert result["error"]["details"]["code"] == "INVALID_MCP_ARGUMENT"


def test_arc_audit_verify_rejects_traversal_run_id(tmp_path: Path):
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_audit_verify")
    result = json.loads(tool(run_id="../secret"))
    assert result["ok"] is False
    assert result["error"]["details"]["code"] == "INVALID_MCP_ARGUMENT"


def test_arc_trace_read_paginates_and_redacts(tmp_path: Path):
    from agent_runtime_cockpit.mcp.server import create_mcp_server
    from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    trust_workspace(tmp_path, note="test")
    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    store.save(
        RunRecord(
            id="run-safe",
            workflow_id="wf",
            runtime="fake",
            status=RunStatus.COMPLETED,
            started_at="2026-01-01T00:00:00Z",
            events=[
                RunEvent(
                    type="A",
                    timestamp="2026-01-01T00:00:00Z",
                    run_id="run-safe",
                    sequence=1,
                    data={"message": "ok"},
                ),
                RunEvent(
                    type="B",
                    timestamp="2026-01-01T00:00:01Z",
                    run_id="run-safe",
                    sequence=2,
                    data={"api_key": "sk-" + "a" * 40},
                ),
            ],
        )
    )
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_trace_read")
    result = json.loads(tool(run_id="run-safe", limit=1, offset=1))
    assert result["ok"] is True
    assert result["data"]["event_count"] == 2
    assert len(result["data"]["events"]) == 1
    assert result["data"]["events"][0]["data"]["api_key"] == "[REDACTED]"


def test_arc_trace_read_rejects_invalid_limit(tmp_path: Path):
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_trace_read")
    result = json.loads(tool(run_id="run-safe", limit=0))
    assert result["ok"] is False
    assert "limit must be" in result["error"]["message"]


def test_arc_task_create_rejects_excessive_retries(tmp_path: Path):
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_task_create")
    result = json.loads(tool(operation="noop", max_retries=99))
    assert result["ok"] is False
    assert "max_retries" in result["error"]["message"]


def test_allowed_tool_call_emits_mcp_audit_event(tmp_path: Path):
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")
    result = json.loads(tool())
    assert result["ok"] is True

    event = _last_mcp_audit_event(tmp_path)
    assert event["type"] == "mcp_tool_call"
    assert event["tool"] == "arc_doctor"
    assert event["decision"] == "allowed"
    assert event["transport"] == "stdio"
    assert event["workspace"] == str(tmp_path)
    assert "started_at" in event
    assert "ended_at" in event
    assert isinstance(event["duration_ms"], float | int)


def test_denied_tool_call_emits_mcp_audit_event(tmp_path: Path):
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_trace_read")
    result = json.loads(tool(run_id="../secret"))
    assert result["ok"] is False

    event = _last_mcp_audit_event(tmp_path)
    assert event["tool"] == "arc_trace_read"
    assert event["decision"] == "denied"
    assert event["error_code"] == "INVALID_MCP_ARGUMENT"
    assert event["args"]["run_id"] == "../secret"


def test_mcp_audit_redacts_args_and_hashes_them(tmp_path: Path):
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    secret = "sk-" + "b" * 40
    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_task_create")
    result = json.loads(tool(operation="noop", params=json.dumps({"api_key": secret})))
    assert result["ok"] is True

    event = _last_mcp_audit_event(tmp_path)
    serialized = json.dumps(event)
    assert secret not in serialized
    assert "[REDACTED]" in serialized
    assert len(event["args_hash"]) == 64


def test_mcp_audit_records_truncation(tmp_path: Path, monkeypatch):
    from agent_runtime_cockpit.mcp.server import create_mcp_server
    import agent_runtime_cockpit.mcp.server as mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")

    def capped(_data, *, workspace, max_bytes=mcp_server._MAX_MCP_OUTPUT_BYTES):
        return json.dumps({"ok": True, "data": {"truncated": True}}), True

    monkeypatch.setattr(mcp_server, "_redacted_json_envelope", capped)
    result = json.loads(tool())
    assert result["ok"] is True

    event = _last_mcp_audit_event(tmp_path)
    assert event["decision"] == "allowed"
    assert event["truncated"] is True


def test_mcp_audit_write_failure_does_not_break_tool_response(tmp_path: Path):
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    (tmp_path / ".arc").mkdir()
    (tmp_path / ".arc" / "audit").write_text("not a directory", encoding="utf-8")
    server = create_mcp_server(workspace=tmp_path)
    tool = _get_tool_fn(server, "arc_doctor")

    result = json.loads(tool())
    assert result["ok"] is True


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


def _last_mcp_audit_event(workspace: Path) -> dict:
    path = workspace / ".arc" / "audit" / "mcp.events.jsonl"
    lines = [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    return json.loads(lines[-1])


def test_arc_swarmgraph_plan_tool(tmp_path: Path):
    """arc_swarmgraph_plan is registered + returns a deterministic DAG plan (risk-gated)."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    assert "arc_swarmgraph_plan" in _get_tool_names(server)
    tool = _get_tool_fn(server, "arc_swarmgraph_plan")
    parsed = json.loads(tool(task="build a REST API and write tests"))
    assert parsed["ok"] is True
    assert parsed["data"]["planner"] == "deterministic"
    assert parsed["data"]["provider_backed"] is False
    assert isinstance(parsed["data"]["nodes"], list)


def test_arc_swarmgraph_assess_risk_tool(tmp_path: Path):
    """arc_swarmgraph_assess_risk is registered + returns a deterministic risk assessment."""
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)
    assert "arc_swarmgraph_assess_risk" in _get_tool_names(server)
    tool = _get_tool_fn(server, "arc_swarmgraph_assess_risk")
    parsed = json.loads(tool(task="delete the production database"))
    assert parsed["ok"] is True
    assert "risk_level" in parsed["data"]
    assert parsed["data"]["provider_backed"] is False


def test_swarmgraph_mcp_cli_parity(tmp_path: Path):
    """Parity (gate 3): MCP tools and the CLI both delegate to the SAME deterministic core
    (decomposition.plan_dag / adaptive_consensus.assess_risk); both surfaces respond
    deterministically with no provider calls."""
    import inspect

    from agent_runtime_cockpit.cli import swarmgraph as cli_swarmgraph
    from agent_runtime_cockpit.mcp import server as mcp_server
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    trust_workspace(tmp_path, note="test")
    server = create_mcp_server(workspace=tmp_path)

    # both MCP tools respond deterministically (provider-free)
    mcp_plan = json.loads(
        _get_tool_fn(server, "arc_swarmgraph_plan")(task="build a REST API and write tests")
    )["data"]
    assert mcp_plan["planner"] == "deterministic" and mcp_plan["topological_order"]
    assert mcp_plan["provider_backed"] is False
    mcp_risk = json.loads(
        _get_tool_fn(server, "arc_swarmgraph_assess_risk")(
            task="delete prod db", target_runtime="production"
        )
    )["data"]
    assert mcp_risk["risk_level"] and mcp_risk["provider_backed"] is False

    # source parity: MCP server and CLI import the SAME deterministic core modules
    server_src = inspect.getsource(mcp_server)
    cli_src = inspect.getsource(cli_swarmgraph)
    for core in (
        "swarmgraph.decomposition import plan_dag",
        "swarmgraph.adaptive_consensus import assess_risk",
    ):
        assert core in server_src, f"MCP server missing shared core: {core}"
        assert core in cli_src, f"CLI missing shared core: {core}"
