"""
Tests for OpenAI Agents SDK adapter.

These tests verify:
1. Dual gating enforcement (ARC_OPENAI_RUN_BACKEND + ARC_OPENAI_ALLOW_COSTS)
2. SDK availability checks
3. Event capture via RunHooks
4. Conformance with adapter interface
"""
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from agent_runtime_cockpit.adapters.openai_agents import OpenAIAgentsAdapter
from agent_runtime_cockpit.protocol.schemas import RunStatus


@pytest.fixture
def adapter():
    return OpenAIAgentsAdapter()


@pytest.fixture
def workspace(tmp_path):
    """Create a minimal OpenAI Agents workspace."""
    workspace = tmp_path / "test_workspace"
    workspace.mkdir()
    
    # Create a minimal agents file
    agents_file = workspace / "agents.py"
    agents_file.write_text("""
from agents import Agent

agent = Agent(
    name="TestAgent",
    instructions="You are helpful.",
)
""")
    
    # Create pyproject.toml with agents dependency
    pyproject = workspace / "pyproject.toml"
    pyproject.write_text("""
[project]
name = "test-agents"
dependencies = ["openai-agents"]
""")
    
    return workspace


def test_adapter_id(adapter):
    assert adapter.adapter_id == "openai-agents"


def test_adapter_name(adapter):
    assert adapter.adapter_name == "OpenAI Agents"


def test_capabilities_without_sdk(adapter, monkeypatch):
    """Test capabilities when SDK is not installed."""
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None if name == "agents" else MagicMock())
    
    caps = adapter.capabilities()
    assert caps.can_inspect is True
    assert caps.can_run is False
    assert caps.can_export_workflow is True


def test_capabilities_with_sdk(adapter, monkeypatch):
    """Test capabilities when SDK is installed."""
    monkeypatch.setattr("importlib.util.find_spec", lambda name: MagicMock() if name == "agents" else None)
    
    caps = adapter.capabilities()
    assert caps.can_inspect is True
    assert caps.can_run is True
    assert caps.can_export_workflow is True


def test_detect_with_agents_file(adapter, workspace):
    """Test detection with agents.py file."""
    detected, score, evidence = adapter.detect(workspace)
    
    assert detected is True
    assert score > 0.3
    assert any("agents.py" in e or "import agents" in e for e in evidence)


def test_detect_without_agents(adapter, tmp_path):
    """Test detection in empty workspace."""
    detected, score, evidence = adapter.detect(tmp_path)
    
    assert detected is False
    assert score <= 0.3


def test_capability_report_missing_sdk(adapter, workspace, monkeypatch):
    """Test capability report when SDK is not installed."""
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None if name == "agents" else MagicMock())
    
    report = adapter.capability_report(workspace)
    
    assert report.runtime_id == "openai-agents"
    assert report.can_run is False
    assert report.availability == "missing_dependency"
    assert "not installed" in report.reason.lower()
    assert report.requires_paid_calls is True


def test_capability_report_missing_backend_env(adapter, workspace, monkeypatch):
    """Test capability report when ARC_OPENAI_RUN_BACKEND is not set."""
    monkeypatch.setattr("importlib.util.find_spec", lambda name: MagicMock() if name == "agents" else None)
    monkeypatch.delenv("ARC_OPENAI_RUN_BACKEND", raising=False)
    monkeypatch.delenv("ARC_OPENAI_ALLOW_COSTS", raising=False)
    
    report = adapter.capability_report(workspace)
    
    assert report.can_run is False
    assert report.availability == "paid_calls_blocked"
    assert "ARC_OPENAI_RUN_BACKEND" in report.reason


def test_capability_report_missing_allow_costs(adapter, workspace, monkeypatch):
    """Test capability report when ARC_OPENAI_ALLOW_COSTS is not set."""
    monkeypatch.setattr("importlib.util.find_spec", lambda name: MagicMock() if name == "agents" else None)
    monkeypatch.setenv("ARC_OPENAI_RUN_BACKEND", "openai")
    monkeypatch.delenv("ARC_OPENAI_ALLOW_COSTS", raising=False)
    
    report = adapter.capability_report(workspace)
    
    assert report.can_run is False
    assert report.availability == "paid_calls_blocked"
    assert "ARC_OPENAI_ALLOW_COSTS" in report.reason


def test_capability_report_fully_gated(adapter, workspace, monkeypatch):
    """Test capability report when both gates are enabled."""
    monkeypatch.setattr("importlib.util.find_spec", lambda name: MagicMock() if name == "agents" else None)
    monkeypatch.setenv("ARC_OPENAI_RUN_BACKEND", "openai")
    monkeypatch.setenv("ARC_OPENAI_ALLOW_COSTS", "true")
    
    report = adapter.capability_report(workspace)
    
    assert report.can_run is True
    assert report.availability == "runnable"
    assert report.requires_paid_calls is True


@pytest.mark.asyncio
async def test_run_workflow_missing_backend_gate(adapter, monkeypatch):
    """Test that run_workflow fails without ARC_OPENAI_RUN_BACKEND."""
    monkeypatch.delenv("ARC_OPENAI_RUN_BACKEND", raising=False)
    monkeypatch.setenv("ARC_OPENAI_ALLOW_COSTS", "true")
    
    with pytest.raises(RuntimeError, match="dual gating"):
        await adapter.run_workflow("test-workflow", {})


@pytest.mark.asyncio
async def test_run_workflow_missing_allow_costs_gate(adapter, monkeypatch):
    """Test that run_workflow fails without ARC_OPENAI_ALLOW_COSTS."""
    monkeypatch.setenv("ARC_OPENAI_RUN_BACKEND", "openai")
    monkeypatch.delenv("ARC_OPENAI_ALLOW_COSTS", raising=False)
    
    with pytest.raises(RuntimeError, match="dual gating"):
        await adapter.run_workflow("test-workflow", {})


@pytest.mark.asyncio
async def test_run_workflow_missing_sdk(adapter, monkeypatch):
    """Test that run_workflow fails when SDK is not installed."""
    monkeypatch.setenv("ARC_OPENAI_RUN_BACKEND", "openai")
    monkeypatch.setenv("ARC_OPENAI_ALLOW_COSTS", "true")
    monkeypatch.setattr("importlib.util.find_spec", lambda name: None if name == "agents" else MagicMock())
    
    run = await adapter.run_workflow("test-workflow", {})
    
    assert run.status == RunStatus.FAILED
    assert run.runtime == "openai-agents"
    assert any("not installed" in e.data.get("error", "").lower() for e in run.events)


@pytest.mark.asyncio
async def test_run_workflow_with_fake_sdk(adapter, monkeypatch):
    """Test run_workflow with mocked SDK (no live calls)."""
    monkeypatch.setenv("ARC_OPENAI_RUN_BACKEND", "openai")
    monkeypatch.setenv("ARC_OPENAI_ALLOW_COSTS", "true")
    
    # Mock SDK availability
    monkeypatch.setattr("importlib.util.find_spec", lambda name: MagicMock() if name == "agents" else None)
    
    # Mock SDK classes
    mock_agent = MagicMock()
    mock_agent.name = "TestAgent"
    mock_agent.instructions = "Test instructions"
    
    mock_result = MagicMock()
    mock_result.final_output = "Test output"
    
    mock_runner = MagicMock()
    mock_runner.run = AsyncMock(return_value=mock_result)
    
    mock_hooks_class = MagicMock()
    
    # Patch imports
    with patch.dict("sys.modules", {
        "agents": MagicMock(
            Agent=MagicMock(return_value=mock_agent),
            Runner=mock_runner,
            RunHooks=mock_hooks_class,
        )
    }):
        run = await adapter.run_workflow("test-workflow", {"prompt": "Hello"})
    
    assert run.status == RunStatus.COMPLETED
    assert run.runtime == "openai-agents"
    assert run.workflow_id == "test-workflow"
    assert len(run.events) >= 2  # At least RUN_STARTED and RUN_COMPLETED
    assert run.events[0].type == "RUN_STARTED"
    assert run.events[-1].type == "RUN_COMPLETED"
    assert run.metadata["backend"] == "openai"
    assert run.metadata["cost_allowed"] is True


@pytest.mark.asyncio
async def test_run_workflow_captures_events(adapter, monkeypatch):
    """Test that RunHooks properly capture agent lifecycle events."""
    monkeypatch.setenv("ARC_OPENAI_RUN_BACKEND", "openai")
    monkeypatch.setenv("ARC_OPENAI_ALLOW_COSTS", "true")
    monkeypatch.setattr("importlib.util.find_spec", lambda name: MagicMock() if name == "agents" else None)
    
    mock_agent = MagicMock()
    mock_agent.name = "TestAgent"
    mock_agent.instructions = "Test"
    
    mock_result = MagicMock()
    mock_result.final_output = "Done"
    
    # Track that Runner.run was called with hooks parameter
    run_called_with_hooks = []
    
    async def mock_run(agent, prompt, hooks=None):
        if hooks is not None:
            run_called_with_hooks.append(True)
        return mock_result
    
    # Create a proper base class for RunHooks
    class FakeRunHooksBase:
        pass
    
    with patch.dict("sys.modules", {
        "agents": MagicMock(
            Agent=MagicMock(return_value=mock_agent),
            Runner=MagicMock(run=mock_run),
            RunHooks=FakeRunHooksBase,  # Base class for hooks
        )
    }):
        run = await adapter.run_workflow("test-workflow", {})
    
    assert run.status == RunStatus.COMPLETED
    assert len(run_called_with_hooks) == 1  # Runner.run was called with hooks


def test_export_workflow(adapter, workspace):
    """Test workflow export."""
    workflows = adapter.export_workflow(workspace)
    
    assert len(workflows) > 0
    assert workflows[0].runtime == "openai-agents"


def test_export_workflow_not_detected(adapter, tmp_path):
    """Test workflow export when not detected."""
    workflows = adapter.export_workflow(tmp_path)
    
    assert len(workflows) == 0


def test_no_live_provider_regression(adapter, monkeypatch):
    """
    Regression test: Ensure no live provider calls without dual gating.
    
    This test verifies the security invariant that the adapter will never
    make live OpenAI API calls unless both gates are explicitly enabled.
    """
    # Scenario 1: No env vars set
    monkeypatch.delenv("ARC_OPENAI_RUN_BACKEND", raising=False)
    monkeypatch.delenv("ARC_OPENAI_ALLOW_COSTS", raising=False)
    
    with pytest.raises(RuntimeError, match="dual gating"):
        import asyncio
        asyncio.run(adapter.run_workflow("test", {}))
    
    # Scenario 2: Only backend set
    monkeypatch.setenv("ARC_OPENAI_RUN_BACKEND", "openai")
    monkeypatch.delenv("ARC_OPENAI_ALLOW_COSTS", raising=False)
    
    with pytest.raises(RuntimeError, match="dual gating"):
        asyncio.run(adapter.run_workflow("test", {}))
    
    # Scenario 3: Only allow_costs set
    monkeypatch.delenv("ARC_OPENAI_RUN_BACKEND", raising=False)
    monkeypatch.setenv("ARC_OPENAI_ALLOW_COSTS", "true")
    
    with pytest.raises(RuntimeError, match="dual gating"):
        asyncio.run(adapter.run_workflow("test", {}))
