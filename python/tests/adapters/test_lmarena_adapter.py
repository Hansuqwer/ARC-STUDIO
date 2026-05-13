"""Tests for the LM Arena runtime adapter."""
from pathlib import Path

from agent_runtime_cockpit.adapters.lmarena import LmarenaAdapter
from agent_runtime_cockpit.adapters.registry import default_registry


def test_adapter_id_and_name():
    adapter = LmarenaAdapter()
    assert adapter.adapter_id == "lmarena"
    assert adapter.adapter_name == "LM Arena"


def test_detect_always_true():
    adapter = LmarenaAdapter()
    detected, confidence, evidence = adapter.detect(Path("/tmp"))
    assert detected is True
    assert confidence > 0
    assert len(evidence) > 0


def test_capabilities():
    adapter = LmarenaAdapter()
    caps = adapter.capabilities()
    assert caps.can_run is True
    assert caps.can_trace is True
    assert caps.can_inspect is False
    assert caps.can_export_workflow is False
    assert caps.requires_paid_calls is False
    assert caps.requires_network is False


def test_capability_report():
    adapter = LmarenaAdapter()
    report = adapter.capability_report(Path("/tmp"))
    assert report.runtime_id == "lmarena"
    assert report.detected is True
    assert report.can_run is True
    assert report.availability == "runnable"
    assert report.requires_paid_calls is False


def test_live_capability_report(monkeypatch):
    monkeypatch.setenv("ARC_ALLOW_LIVE_ARENA", "true")
    adapter = LmarenaAdapter()
    caps = adapter.capabilities()
    report = adapter.capability_report(Path("/tmp"))
    assert caps.requires_paid_calls is True
    assert caps.requires_network is True
    assert caps.requires_secrets is True
    assert report.requires_paid_calls is True
    assert "ARC_LMARENA_ALLOW_COSTS" in report.required_env


async def test_run_workflow_direct(tmp_path):
    """Default mode (direct) should produce a single candidate."""
    adapter = LmarenaAdapter()
    run = await adapter.run_workflow("arena-direct", {
        "workspace": str(tmp_path),
        "prompt": "Hello from test",
    })
    assert run.id.startswith("arena-")
    assert run.runtime == "lmarena"
    assert run.status.value == "completed"
    assert run.metadata.get("arena_mode") == "direct"


async def test_run_workflow_battle(tmp_path):
    """Battle mode should produce multiple candidates."""
    adapter = LmarenaAdapter()
    run = await adapter.run_workflow("arena-battle", {
        "workspace": str(tmp_path),
        "prompt": "Compare models",
        "arena_model": "gpt-4o-mini-2024-07-18",
    })
    assert run.id.startswith("arena-")
    assert run.runtime == "lmarena"
    assert run.status.value == "completed"
    assert run.metadata.get("arena_mode") == "battle"


async def test_run_workflow_code(tmp_path):
    """Code mode should include patch/diff."""
    adapter = LmarenaAdapter()
    run = await adapter.run_workflow("arena-code", {
        "workspace": str(tmp_path),
        "prompt": "Write a Python function",
        "arena_mode": "code",
    })
    assert run.runtime == "lmarena"
    assert run.metadata.get("arena_mode") == "code"


async def test_run_workflow_agent_preview(tmp_path):
    """Agent arena preview mode should include plan."""
    adapter = LmarenaAdapter()
    run = await adapter.run_workflow("arena-agent-preview", {
        "workspace": str(tmp_path),
        "prompt": "Build a web app",
        "arena_mode": "agent-arena-preview",
    })
    assert run.runtime == "lmarena"
    assert run.metadata.get("arena_mode") == "agent-arena-preview"


async def test_run_workflow_rejects_paid_calls_with_safe_profile(tmp_path):
    adapter = LmarenaAdapter()
    try:
        await adapter.run_workflow("arena-direct", {
            "workspace": str(tmp_path),
            "prompt": "Hello",
            "allow_paid_calls": True,
            "profile_id": "local-safe",
        })
    except Exception as exc:
        assert "does not allow paid calls" in str(exc)
    else:
        raise AssertionError("Expected paid-call profile rejection")


def test_registered_in_default_registry():
    """LmarenaAdapter should be auto-registered."""
    registry = default_registry()
    adapter = registry.get("lmarena")
    assert adapter is not None
    assert adapter.adapter_id == "lmarena"


def test_registry_detect(tmp_path):
    """Registry detect_all should include lmarena."""
    registry = default_registry()
    results = registry.detect_all(tmp_path)
    lmarena_results = [r for r in results if r.adapter == "lmarena"]
    assert len(lmarena_results) >= 1
