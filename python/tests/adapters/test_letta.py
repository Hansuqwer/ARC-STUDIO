"""Tests for LettaAdapter — fully offline (mocked Letta client)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from agent_runtime_cockpit.adapters.letta import LettaAdapter
from agent_runtime_cockpit.gating import GatingError


@pytest.fixture()
def adapter():
    return LettaAdapter()


def test_adapter_id(adapter):
    assert adapter.adapter_id == "letta"


def test_adapter_name(adapter):
    assert "Letta" in adapter.adapter_name


def test_capabilities_can_run_false_by_default(adapter):
    with patch.dict(os.environ, {}, clear=False):
        for k in ("ARC_LETTA_AGENT_ID", "ARC_LETTA_ALLOW_COSTS", "LETTA_API_KEY", "LETTA_BASE_URL"):
            os.environ.pop(k, None)
        caps = adapter.capabilities()
    assert not caps.can_run
    assert caps.can_inspect
    assert caps.can_export_workflow


def test_capabilities_can_run_when_gated(adapter):
    env = {
        "ARC_LETTA_AGENT_ID": "agent-123",
        "ARC_LETTA_ALLOW_COSTS": "true",
        "LETTA_API_KEY": "test-key",
    }
    with patch("agent_runtime_cockpit.adapters.letta._letta_installed", return_value=True):
        with patch.dict(os.environ, env):
            caps = adapter.capabilities()
    assert caps.can_run


def test_detect_no_evidence(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.letta._letta_installed", return_value=False):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LETTA_API_KEY", None)
            os.environ.pop("LETTA_BASE_URL", None)
            detected, conf, evidence = adapter.detect(tmp_path)
    assert not detected
    assert conf == 0.0


def test_detect_with_sdk_and_key(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.letta._letta_installed", return_value=True):
        with patch.dict(os.environ, {"LETTA_API_KEY": "sk-test"}):
            detected, conf, evidence = adapter.detect(tmp_path)
    assert detected
    assert conf >= 0.8
    assert any("letta_client installed" in e for e in evidence)
    assert any("LETTA_API_KEY" in e for e in evidence)


def test_detect_af_file(adapter, tmp_path):
    (tmp_path / "my_agent.af").write_text("{}")
    with patch("agent_runtime_cockpit.adapters.letta._letta_installed", return_value=False):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LETTA_API_KEY", None)
            os.environ.pop("LETTA_BASE_URL", None)
            detected, _, evidence = adapter.detect(tmp_path)
    assert detected
    assert any(".af" in e for e in evidence)


def test_export_workflow_no_detection(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.letta._letta_installed", return_value=False):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LETTA_API_KEY", None)
            os.environ.pop("LETTA_BASE_URL", None)
            result = adapter.export_workflow(tmp_path)
    assert result == []


def test_export_workflow_returns_node(adapter, tmp_path):
    env = {"LETTA_API_KEY": "k", "ARC_LETTA_AGENT_ID": "agent-abc"}
    with patch("agent_runtime_cockpit.adapters.letta._letta_installed", return_value=True):
        with patch.dict(os.environ, env):
            workflows = adapter.export_workflow(tmp_path)
    assert len(workflows) == 1
    assert workflows[0].nodes[0].id == "agent"
    assert "agent-abc" in workflows[0].id


@pytest.mark.asyncio
async def test_run_workflow_raises_without_gate(adapter, tmp_path):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ARC_LETTA_ALLOW_COSTS", None)
        os.environ.pop("ARC_LETTA_AGENT_ID", None)
        with pytest.raises(GatingError):
            await adapter.run_workflow("letta::wf", {"prompt": "hi"}, tmp_path)


@pytest.mark.asyncio
async def test_run_workflow_raises_without_agent_id(adapter, tmp_path):
    with patch.dict(os.environ, {"ARC_LETTA_ALLOW_COSTS": "true"}):
        os.environ.pop("ARC_LETTA_AGENT_ID", None)
        with pytest.raises(GatingError, match="ARC_LETTA_AGENT_ID"):
            await adapter.run_workflow("letta::wf", {"prompt": "hi"}, tmp_path)


@pytest.mark.asyncio
async def test_run_workflow_executes_and_returns_record(adapter, tmp_path):
    mock_msg = MagicMock()
    mock_msg.message_type = "assistant_message"
    mock_msg.content = "Hello from Letta"
    mock_response = MagicMock()
    mock_response.messages = [mock_msg]

    mock_client = MagicMock()
    mock_client.agents.messages.create.return_value = mock_response

    env = {
        "ARC_LETTA_ALLOW_COSTS": "true",
        "ARC_LETTA_AGENT_ID": "agent-abc",
        "LETTA_API_KEY": "test-key",
    }
    with patch.dict(os.environ, env):
        with patch("agent_runtime_cockpit.adapters.letta._LettaClient", return_value=mock_client):
            record = await adapter.run_workflow("letta::wf", {"prompt": "hi"}, tmp_path)

    assert record.status.value == "completed"
    assert record.metadata["outputs"]["result"] == "Hello from Letta"
    assert any(e.type == "LETTA_RUN_START" for e in record.events)
    assert any(e.type == "LETTA_RUN_END" for e in record.events)
