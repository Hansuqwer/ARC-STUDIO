"""Tests for MCPSDKAdapter interface."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.adapters.mcp_sdk import MCPSDKAdapter
from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities


def test_adapter_identity():
    adapter = MCPSDKAdapter()
    assert adapter.adapter_id == "mcp_sdk"
    assert adapter.adapter_name == "MCP Python SDK"


def test_capabilities_are_honest():
    caps = MCPSDKAdapter().capabilities()
    assert isinstance(caps, RuntimeCapabilities)
    # T1 + T2 only
    assert caps.can_inspect is True
    assert caps.can_export_workflow is True
    # T3 not implemented
    assert caps.can_run is False
    assert caps.can_stream_events is False
    assert caps.can_trace is False
    assert caps.can_replay is False
    assert caps.can_audit is False


def test_detect_not_detected_empty(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(False, None),
    ):
        detected, confidence, evidence = MCPSDKAdapter().detect(tmp_path)
    assert detected is False
    assert confidence == 0.0
    assert evidence == []


def test_detect_found_in_workspace(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\nmcp = FastMCP('Test')\n"
    )
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(False, None),
    ):
        detected, confidence, evidence = MCPSDKAdapter().detect(tmp_path)
    assert detected is True
    assert confidence > 0.0
    assert evidence


def test_export_workflow(tmp_path):
    (tmp_path / "server.py").write_text(
        "from mcp.server.fastmcp import FastMCP\nmcp = FastMCP('Test')\n"
    )
    workflows = MCPSDKAdapter().export_workflow(tmp_path)
    assert len(workflows) == 1
    assert workflows[0].runtime == "mcp_sdk"


def test_capability_report_not_detected(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(False, None),
    ):
        report = MCPSDKAdapter().capability_report(tmp_path)
    assert report.detected is False
    assert report.availability == "not_detected"
    assert len(report.doctor_actions) == 1
    assert report.doctor_actions[0].id == "install-mcp"
    assert "mcp" in report.doctor_actions[0].command.lower()


def test_capability_report_detected_mentions_t3_not_implemented(tmp_path):
    (tmp_path / "server.py").write_text("from mcp.server.fastmcp import FastMCP\n")
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(False, None),
    ):
        report = MCPSDKAdapter().capability_report(tmp_path)
    assert report.detected is True
    assert report.can_run is False
    assert report.availability == "detected_not_runnable"
    assert "T3" in (report.reason or "")
    assert "not implemented" in (report.reason or "").lower()
    assert report.local_real_gated is False
    assert report.provider_backed is False


def test_capability_report_detected_has_version(tmp_path):
    (tmp_path / "server.py").write_text("from mcp.server.fastmcp import FastMCP\n")
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(True, "1.8.0"),
    ):
        report = MCPSDKAdapter().capability_report(tmp_path)
    assert report.version == "1.8.0"


def test_capability_report_detected_no_doctor_actions(tmp_path):
    (tmp_path / "server.py").write_text("from mcp.server.fastmcp import FastMCP\n")
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(False, None),
    ):
        report = MCPSDKAdapter().capability_report(tmp_path)
    assert report.detected is True
    # No doctor actions when detected (can't auto-install mcp into user project)
    assert report.doctor_actions == []


def test_run_workflow_not_implemented():
    with pytest.raises(NotImplementedError):
        asyncio.run(MCPSDKAdapter().run_workflow("wf"))


def test_adapter_registered_in_default_registry():
    from agent_runtime_cockpit.adapters.registry import default_registry

    registry = default_registry()
    adapter = registry.get("mcp_sdk")
    assert adapter is not None
    assert isinstance(adapter, MCPSDKAdapter)


def test_adapter_in_all_adapters():
    from agent_runtime_cockpit.adapters.registry import default_registry

    registry = default_registry()
    ids = [a.adapter_id for a in registry.all()]
    assert "mcp_sdk" in ids


def test_trust_posture_mentioned_in_reason(tmp_path):
    """Trust is the key reason T3 is deferred; ensure it's communicated."""
    (tmp_path / "server.py").write_text("from mcp.server.fastmcp import FastMCP\n")
    with patch(
        "agent_runtime_cockpit.adapters.mcp_sdk.detect.detect_mcp_sdk_import",
        return_value=(False, None),
    ):
        report = MCPSDKAdapter().capability_report(tmp_path)
    reason = (report.reason or "").lower()
    assert "trust" in reason or "transport" in reason or "privileged" in reason
