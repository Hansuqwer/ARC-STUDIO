"""Tests: R-SEC1 — TOOL_RISK_LEVELS + arc_run_start subprocess isolation (Phase 283)."""

from __future__ import annotations

from pathlib import Path

from agent_runtime_cockpit.mcp.server import TOOL_RISK_LEVELS
from agent_runtime_cockpit.security.trust import trust_workspace


# ── TOOL_RISK_LEVELS ────────────────────────────────────────────────────────


def test_tool_risk_levels_contains_all_13_tools():
    assert len(TOOL_RISK_LEVELS) == 13


def test_arc_run_start_is_high_risk():
    assert TOOL_RISK_LEVELS["arc_run_start"] == "HIGH"


def test_arc_task_cancel_is_medium_risk():
    assert TOOL_RISK_LEVELS["arc_task_cancel"] == "MEDIUM"


def test_low_risk_tools_are_low():
    low_tools = [
        "arc_doctor",
        "arc_runtime_capabilities",
        "arc_run_status",
        "arc_trace_search",
        "arc_trace_read",
        "arc_audit_verify",
        "arc_hitl_list",
        "arc_task_status",
        "arc_task_result",
        "arc_swarmgraph_plan",
        "arc_swarmgraph_assess_risk",
    ]
    for tool in low_tools:
        assert TOOL_RISK_LEVELS[tool] == "LOW", f"{tool} should be LOW"


def test_only_valid_risk_levels():
    valid = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    for tool, level in TOOL_RISK_LEVELS.items():
        assert level in valid, f"{tool} has invalid level {level}"


def test_arc_run_start_tool_registered(tmp_path: Path):
    """arc_run_start must be registered as an MCP tool."""
    trust_workspace(tmp_path)
    from agent_runtime_cockpit.mcp.server import create_mcp_server

    server = create_mcp_server(workspace=tmp_path)
    tool_names = [t.name for t in server._tool_manager.list_tools()]
    assert "arc_run_start" in tool_names


def test_subprocess_env_does_not_include_api_key(tmp_path: Path):
    """SubprocessIsolationProvider must strip API keys from the environment."""
    import os

    from agent_runtime_cockpit.isolation.subprocess import SubprocessIsolationProvider
    from agent_runtime_cockpit.security.validation import SAFE_ENV_KEYS

    provider = SubprocessIsolationProvider(
        safe_env_keys=frozenset(SAFE_ENV_KEYS),
        workspace_root=tmp_path,
        max_output_bytes=1024,
    )
    env_with_key = dict(os.environ)
    env_with_key["OPENAI_API_KEY"] = "sk-secret"
    filtered = provider.filter_env(env_with_key)
    assert "OPENAI_API_KEY" not in filtered


def test_arc_run_start_risk_higher_than_read_tools():
    """arc_run_start must be riskier than all read-only tools."""
    order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    run_start_level = order[TOOL_RISK_LEVELS["arc_run_start"]]
    for tool, level in TOOL_RISK_LEVELS.items():
        if tool != "arc_run_start" and level == "LOW":
            assert run_start_level > order[level], f"{tool} LOW should be below arc_run_start HIGH"
