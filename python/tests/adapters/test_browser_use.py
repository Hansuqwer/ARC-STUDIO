"""Tests for BrowserUseAdapter — fully offline (mocked Agent)."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime_cockpit.adapters.browser_use import BrowserUseAdapter
from agent_runtime_cockpit.gating import GatingError


@pytest.fixture()
def adapter():
    return BrowserUseAdapter()


def test_adapter_id(adapter):
    assert adapter.adapter_id == "browser-use"


def test_capabilities_false_by_default(adapter):
    with patch.dict(os.environ, {}, clear=False):
        for k in ("ARC_BROWSER_USE_ALLOW_COSTS", "ARC_BROWSER_USE_ALLOW_BROWSER"):
            os.environ.pop(k, None)
        caps = adapter.capabilities()
    assert not caps.can_run
    assert caps.can_inspect
    assert caps.can_export_workflow


def test_capabilities_can_run_when_gated(adapter):
    env = {"ARC_BROWSER_USE_ALLOW_COSTS": "true", "ARC_BROWSER_USE_ALLOW_BROWSER": "true"}
    with patch("agent_runtime_cockpit.adapters.browser_use._installed", return_value=True):
        with patch.dict(os.environ, env):
            assert adapter.capabilities().can_run


def test_detect_no_evidence(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.browser_use._installed", return_value=False):
        detected, conf, evidence = adapter.detect(tmp_path)
    assert not detected
    assert conf == 0.0


def test_detect_installed(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.browser_use._installed", return_value=True):
        detected, conf, evidence = adapter.detect(tmp_path)
    assert detected
    assert conf == 0.5
    assert any("browser_use installed" in e for e in evidence)


def test_detect_workspace_import(adapter, tmp_path):
    (tmp_path / "agent.py").write_text("from browser_use import Agent\n")
    with patch("agent_runtime_cockpit.adapters.browser_use._installed", return_value=True):
        detected, conf, evidence = adapter.detect(tmp_path)
    assert detected
    assert conf > 0.5
    assert any("agent.py" in e for e in evidence)


def test_export_workflow_empty_when_not_detected(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.browser_use._installed", return_value=False):
        assert adapter.export_workflow(tmp_path) == []


def test_export_workflow_returns_node(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.browser_use._installed", return_value=True):
        workflows = adapter.export_workflow(tmp_path)
    assert len(workflows) == 1
    assert workflows[0].nodes[0].id == "agent"
    assert "browser-use" in workflows[0].id


@pytest.mark.asyncio
async def test_run_raises_without_cost_gate(adapter, tmp_path):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ARC_BROWSER_USE_ALLOW_COSTS", None)
        with pytest.raises(GatingError):
            await adapter.run_workflow("wf", {"task": "hi"}, tmp_path)


@pytest.mark.asyncio
async def test_run_raises_without_browser_gate(adapter, tmp_path):
    with patch.dict(os.environ, {"ARC_BROWSER_USE_ALLOW_COSTS": "true"}):
        os.environ.pop("ARC_BROWSER_USE_ALLOW_BROWSER", None)
        with pytest.raises(GatingError, match="ARC_BROWSER_USE_ALLOW_BROWSER"):
            await adapter.run_workflow("wf", {"task": "hi"}, tmp_path)


@pytest.mark.asyncio
async def test_run_executes_and_returns_record(adapter, tmp_path):
    mock_history = MagicMock()
    mock_history.final_result.return_value = "Search result"
    mock_history.is_done.return_value = True
    mock_history.has_errors.return_value = False
    mock_history.number_of_steps.return_value = 3
    mock_history.urls.return_value = ["https://example.com"]

    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(return_value=mock_history)

    env = {"ARC_BROWSER_USE_ALLOW_COSTS": "true", "ARC_BROWSER_USE_ALLOW_BROWSER": "true"}
    with patch.dict(os.environ, env):
        with patch(
            "agent_runtime_cockpit.adapters.browser_use._BrowserAgent", return_value=mock_agent
        ):
            record = await adapter.run_workflow("wf", {"task": "find news"}, tmp_path)

    assert record.status.value == "completed"
    assert record.metadata["outputs"]["result"] == "Search result"
    assert any(e.type == "BROWSER_USE_RUN_START" for e in record.events)
    assert any(e.type == "BROWSER_USE_RUN_END" for e in record.events)


@pytest.mark.asyncio
async def test_run_records_error(adapter, tmp_path):
    mock_agent = MagicMock()
    mock_agent.run = AsyncMock(side_effect=RuntimeError("browser crash"))

    env = {"ARC_BROWSER_USE_ALLOW_COSTS": "true", "ARC_BROWSER_USE_ALLOW_BROWSER": "true"}
    with patch.dict(os.environ, env):
        with patch(
            "agent_runtime_cockpit.adapters.browser_use._BrowserAgent", return_value=mock_agent
        ):
            record = await adapter.run_workflow("wf", {"task": "fail"}, tmp_path)

    assert record.status.value == "failed"
    assert any(e.type == "BROWSER_USE_RUN_ERROR" for e in record.events)
