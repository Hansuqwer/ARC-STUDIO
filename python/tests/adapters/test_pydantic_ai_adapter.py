"""Tests for PydanticAIAdapter — fully offline."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from agent_runtime_cockpit.adapters.pydantic_ai_adapter import PydanticAIAdapter
from agent_runtime_cockpit.gating import GatingError


@pytest.fixture()
def adapter():
    return PydanticAIAdapter()


def test_adapter_id(adapter):
    assert adapter.adapter_id == "pydantic-ai"


def test_capabilities_can_run_false_by_default(adapter):
    env = {}
    with patch.dict(os.environ, env, clear=False):
        os.environ.pop("ARC_PYDANTIC_AI_EXPORT", None)
        os.environ.pop("ARC_PYDANTIC_AI_ALLOW_COSTS", None)
        caps = adapter.capabilities()
    assert not caps.can_run
    assert caps.can_inspect
    assert caps.can_export_workflow


def test_capabilities_can_run_when_gated(adapter):
    env = {"ARC_PYDANTIC_AI_EXPORT": "mymod:agent", "ARC_PYDANTIC_AI_ALLOW_COSTS": "true"}
    with patch(
        "agent_runtime_cockpit.adapters.pydantic_ai_adapter._pydantic_ai_installed",
        return_value=(True, "1.106.0"),
    ):
        with patch.dict(os.environ, env):
            caps = adapter.capabilities()
    assert caps.can_run


def test_detect_delegates_to_package(adapter, tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.pydantic_ai_adapter.detect_pydantic_ai"
    ) as mock_detect:
        from agent_runtime_cockpit.adapters.pydantic_ai import PydanticAIDetectionResult

        mock_detect.return_value = PydanticAIDetectionResult(
            detected=True,
            confidence=0.9,
            evidence=["pydantic_ai installed"],
            version="1.106.0",
            model_providers=[],
        )
        detected, conf, evidence = adapter.detect(tmp_path)
    assert detected
    assert conf == 0.9


def test_export_workflow_delegates_to_package(adapter, tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.pydantic_ai_adapter.export_pydantic_ai_agents",
        return_value=[],
    ) as mock_export:
        result = adapter.export_workflow(tmp_path)
    mock_export.assert_called_once_with(tmp_path)
    assert result == []


@pytest.mark.asyncio
async def test_run_workflow_raises_without_gate(adapter, tmp_path):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ARC_PYDANTIC_AI_ALLOW_COSTS", None)
        with pytest.raises(GatingError):
            await adapter.run_workflow("wf", {"prompt": "hi"}, tmp_path)


@pytest.mark.asyncio
async def test_run_workflow_raises_without_export(adapter, tmp_path):
    with patch.dict(os.environ, {"ARC_PYDANTIC_AI_ALLOW_COSTS": "true"}):
        os.environ.pop("ARC_PYDANTIC_AI_EXPORT", None)
        with pytest.raises(GatingError):
            await adapter.run_workflow("wf", {"prompt": "hi"}, tmp_path)


@pytest.mark.asyncio
async def test_run_workflow_calls_run_sync(adapter, tmp_path):
    mock_result = MagicMock()
    mock_result.output = "the answer"
    mock_agent = MagicMock()
    mock_agent.name = "my_agent"
    mock_agent.run_sync = MagicMock(return_value=mock_result)

    env = {"ARC_PYDANTIC_AI_ALLOW_COSTS": "true", "ARC_PYDANTIC_AI_EXPORT": "mymod:agent"}
    with patch.dict(os.environ, env):
        with patch(
            "agent_runtime_cockpit.adapters.pydantic_ai_adapter.importlib.import_module",
            return_value=MagicMock(agent=mock_agent),
        ):
            record = await adapter.run_workflow("wf", {"prompt": "test"}, tmp_path)

    mock_agent.run_sync.assert_called_once_with("test")
    assert record.status.value == "completed"
    assert record.metadata["outputs"]["result"] == "the answer"
    assert any(e.type == "AGENT_RUN_START" for e in record.events)
    assert any(e.type == "AGENT_RUN_END" for e in record.events)


@pytest.mark.asyncio
async def test_run_workflow_records_error(adapter, tmp_path):
    mock_agent = MagicMock()
    mock_agent.run_sync = MagicMock(side_effect=RuntimeError("api error"))

    env = {"ARC_PYDANTIC_AI_ALLOW_COSTS": "true", "ARC_PYDANTIC_AI_EXPORT": "mymod:agent"}
    with patch.dict(os.environ, env):
        with patch(
            "agent_runtime_cockpit.adapters.pydantic_ai_adapter.importlib.import_module",
            return_value=MagicMock(agent=mock_agent),
        ):
            record = await adapter.run_workflow("wf", {"prompt": "fail"}, tmp_path)

    assert record.status.value == "failed"
    assert any(e.type == "AGENT_RUN_ERROR" for e in record.events)
