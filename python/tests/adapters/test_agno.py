"""Tests for AgnoAdapter — fully offline."""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime_cockpit.adapters.agno import AgnoAdapter
from agent_runtime_cockpit.gating import GatingError


@pytest.fixture()
def adapter():
    return AgnoAdapter()


def test_adapter_id(adapter):
    assert adapter.adapter_id == "agno"


def test_capabilities_false_by_default(adapter):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ARC_AGNO_EXPORT", None)
        os.environ.pop("ARC_AGNO_ALLOW_COSTS", None)
        caps = adapter.capabilities()
    assert not caps.can_run
    assert caps.can_inspect


def test_capabilities_can_run_when_gated(adapter):
    env = {"ARC_AGNO_EXPORT": "mymod:agent", "ARC_AGNO_ALLOW_COSTS": "true"}
    with patch("agent_runtime_cockpit.adapters.agno._installed", return_value=True):
        with patch.dict(os.environ, env):
            assert adapter.capabilities().can_run


def test_detect_no_evidence(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.agno._installed", return_value=False):
        detected, conf, _ = adapter.detect(tmp_path)
    assert not detected


def test_detect_installed(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.agno._installed", return_value=True):
        detected, conf, evidence = adapter.detect(tmp_path)
    assert detected
    assert any("agno installed" in e for e in evidence)


def test_export_empty_when_not_detected(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.agno._installed", return_value=False):
        assert adapter.export_workflow(tmp_path) == []


def test_export_returns_node(adapter, tmp_path):
    with patch("agent_runtime_cockpit.adapters.agno._installed", return_value=True):
        with patch.dict(os.environ, {"ARC_AGNO_EXPORT": "mod:agent"}):
            workflows = adapter.export_workflow(tmp_path)
    assert len(workflows) == 1
    assert workflows[0].nodes[0].id == "agent"


@pytest.mark.asyncio
async def test_run_raises_without_gate(adapter, tmp_path):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ARC_AGNO_ALLOW_COSTS", None)
        with pytest.raises(GatingError):
            await adapter.run_workflow("wf", {"prompt": "hi"}, tmp_path)


@pytest.mark.asyncio
async def test_run_raises_without_export(adapter, tmp_path):
    with patch.dict(os.environ, {"ARC_AGNO_ALLOW_COSTS": "true"}):
        os.environ.pop("ARC_AGNO_EXPORT", None)
        with pytest.raises(GatingError, match="ARC_AGNO_EXPORT"):
            await adapter.run_workflow("wf", {"prompt": "hi"}, tmp_path)


@pytest.mark.asyncio
async def test_run_calls_arun_and_returns_record(adapter, tmp_path):
    mock_result = MagicMock()
    mock_result.content = "Agno says hello"
    mock_agent = MagicMock()
    mock_agent.arun = AsyncMock(return_value=mock_result)

    env = {"ARC_AGNO_ALLOW_COSTS": "true", "ARC_AGNO_EXPORT": "mymod:agent"}
    with patch.dict(os.environ, env):
        with patch(
            "agent_runtime_cockpit.adapters.agno.importlib.import_module",
            return_value=MagicMock(agent=mock_agent),
        ):
            record = await adapter.run_workflow("wf", {"prompt": "hi"}, tmp_path)

    assert record.status.value == "completed"
    assert record.metadata["outputs"]["result"] == "Agno says hello"
    assert any(e.type == "AGNO_RUN_START" for e in record.events)
    assert any(e.type == "AGNO_RUN_END" for e in record.events)


@pytest.mark.asyncio
async def test_run_records_error(adapter, tmp_path):
    mock_agent = MagicMock()
    mock_agent.arun = AsyncMock(side_effect=RuntimeError("model error"))

    env = {"ARC_AGNO_ALLOW_COSTS": "true", "ARC_AGNO_EXPORT": "mymod:agent"}
    with patch.dict(os.environ, env):
        with patch(
            "agent_runtime_cockpit.adapters.agno.importlib.import_module",
            return_value=MagicMock(agent=mock_agent),
        ):
            record = await adapter.run_workflow("wf", {"prompt": "fail"}, tmp_path)

    assert record.status.value == "failed"
    assert any(e.type == "AGNO_RUN_ERROR" for e in record.events)
