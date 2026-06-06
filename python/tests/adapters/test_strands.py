"""Tests for StrandsAdapter — fully offline (no real SDK or API calls)."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

from agent_runtime_cockpit.adapters.strands import StrandsAdapter
from agent_runtime_cockpit.gating import GatingError


@pytest.fixture()
def adapter():
    return StrandsAdapter()


@pytest.fixture()
def tmp_workspace(tmp_path):
    return tmp_path


# --- identity ---


def test_adapter_id(adapter):
    assert adapter.adapter_id == "strands"


def test_adapter_name(adapter):
    assert "Strands" in adapter.adapter_name


# --- detect: strands not installed ---


def test_detect_not_installed_returns_false(adapter, tmp_workspace):
    with patch(
        "agent_runtime_cockpit.adapters.strands.importlib.util.find_spec", return_value=None
    ):
        detected, confidence, evidence = adapter.detect(tmp_workspace)
    assert not detected
    assert confidence == 0.0
    assert evidence == []


def test_detect_installed_no_workspace_files(adapter, tmp_workspace):
    with patch(
        "agent_runtime_cockpit.adapters.strands._strands_installed", return_value=(True, "1.42.0")
    ):
        detected, confidence, evidence = adapter.detect(tmp_workspace)
    assert detected
    assert confidence == 0.5
    assert any("1.42.0" in e for e in evidence)


def test_detect_workspace_import_evidence(adapter, tmp_workspace):
    (tmp_workspace / "agent.py").write_text("from strands import Agent\nagent = Agent()\n")
    with patch(
        "agent_runtime_cockpit.adapters.strands._strands_installed", return_value=(True, "1.42.0")
    ):
        detected, confidence, evidence = adapter.detect(tmp_workspace)
    assert detected
    assert confidence > 0.5
    assert any("agent.py" in e for e in evidence)


def test_detect_requirements_evidence(adapter, tmp_workspace):
    (tmp_workspace / "requirements.txt").write_text("strands-agents>=1.40\n")
    with patch(
        "agent_runtime_cockpit.adapters.strands._strands_installed", return_value=(False, None)
    ):
        detected, confidence, evidence = adapter.detect(tmp_workspace)
    assert detected
    assert any("requirements.txt" in e for e in evidence)


# --- capabilities ---


def test_capabilities_can_run_false_by_default(adapter):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ARC_STRANDS_EXPORT", None)
        os.environ.pop("ARC_STRANDS_ALLOW_COSTS", None)
        caps = adapter.capabilities()
    assert not caps.can_run
    assert caps.can_inspect  # always True — detection is always available
    assert caps.can_export_workflow


def test_capabilities_can_run_true_when_gated(adapter):
    env = {"ARC_STRANDS_EXPORT": "my_mod:my_agent", "ARC_STRANDS_ALLOW_COSTS": "true"}
    with patch(
        "agent_runtime_cockpit.adapters.strands._strands_installed", return_value=(True, "1.42.0")
    ):
        with patch.dict(os.environ, env):
            caps = adapter.capabilities()
    assert caps.can_run
    assert caps.can_inspect
    assert caps.can_export_workflow


# --- export_workflow ---


def test_export_workflow_not_detected_returns_empty(adapter, tmp_workspace):
    with patch(
        "agent_runtime_cockpit.adapters.strands._strands_installed", return_value=(False, None)
    ):
        result = adapter.export_workflow(tmp_workspace)
    assert result == []


def test_export_workflow_returns_single_node(adapter, tmp_workspace):
    (tmp_workspace / "agent.py").write_text("from strands import Agent\n")
    with patch(
        "agent_runtime_cockpit.adapters.strands._strands_installed", return_value=(True, "1.42.0")
    ):
        with patch.dict(os.environ, {"ARC_STRANDS_EXPORT": "agent:my_agent"}):
            workflows = adapter.export_workflow(tmp_workspace)
    assert len(workflows) == 1
    wf = workflows[0]
    assert len(wf.nodes) == 1
    assert wf.nodes[0].id == "agent"
    assert "strands" in wf.id


# --- run_workflow: gating ---


@pytest.mark.asyncio
async def test_run_workflow_raises_without_gate(adapter, tmp_workspace):
    with patch.dict(os.environ, {}, clear=False):
        os.environ.pop("ARC_STRANDS_ALLOW_COSTS", None)
        os.environ.pop("ARC_STRANDS_EXPORT", None)
        with pytest.raises(GatingError):
            await adapter.run_workflow("strands::ws", {"prompt": "hi"}, tmp_workspace)


@pytest.mark.asyncio
async def test_run_workflow_raises_without_export(adapter, tmp_workspace):
    with patch.dict(os.environ, {"ARC_STRANDS_ALLOW_COSTS": "true"}):
        os.environ.pop("ARC_STRANDS_EXPORT", None)
        with pytest.raises(GatingError):
            await adapter.run_workflow("strands::ws", {"prompt": "hi"}, tmp_workspace)


@pytest.mark.asyncio
async def test_run_workflow_executes_and_returns_record(adapter, tmp_workspace):
    mock_result = MagicMock()
    mock_result.__str__ = lambda self: "42"
    mock_agent = MagicMock(return_value=mock_result)

    env = {"ARC_STRANDS_ALLOW_COSTS": "true", "ARC_STRANDS_EXPORT": "mymod:agent"}
    with patch.dict(os.environ, env):
        with patch(
            "agent_runtime_cockpit.adapters.strands.importlib.import_module",
            return_value=MagicMock(agent=mock_agent),
        ):
            record = await adapter.run_workflow("strands::ws", {"prompt": "test"}, tmp_workspace)

    assert record.status.value == "completed"
    assert record.metadata["outputs"]["result"] == "42"
    assert any(e.type == "STRANDS_RUN_START" for e in record.events)
    assert any(e.type == "STRANDS_RUN_END" for e in record.events)


@pytest.mark.asyncio
async def test_run_workflow_records_error_on_exception(adapter, tmp_workspace):
    mock_agent = MagicMock(side_effect=RuntimeError("model error"))
    env = {"ARC_STRANDS_ALLOW_COSTS": "true", "ARC_STRANDS_EXPORT": "mymod:agent"}
    with patch.dict(os.environ, env):
        with patch(
            "agent_runtime_cockpit.adapters.strands.importlib.import_module",
            return_value=MagicMock(agent=mock_agent),
        ):
            record = await adapter.run_workflow("strands::ws", {"prompt": "fail"}, tmp_workspace)

    assert record.status.value == "failed"
    assert any(e.type == "STRANDS_RUN_ERROR" for e in record.events)
