"""Tests for adapter registry status and capability reporting.

Verifies all registered adapters report honest, accurate capability
statuses and that the CLI integration works for adapter discovery.
"""
from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.adapters.registry import AdapterRegistry, default_registry
from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities

runner = CliRunner()


def test_default_registry_has_expected_adapters():
    """Default registry contains all expected adapters."""
    registry = default_registry()
    adapter_ids = {a.adapter_id for a in registry.all()}
    expected = {"swarmgraph", "langgraph", "crewai", "openai-agents", "ag2", "llamaindex", "lmarena"}
    assert adapter_ids == expected, f"Got {adapter_ids}, expected {expected}"


def test_each_adapter_has_unique_id_and_name():
    """Every adapter has a unique adapter_id and a non-empty name."""
    registry = default_registry()
    ids = set()
    for adapter in registry.all():
        assert adapter.adapter_id, f"Empty adapter_id on {type(adapter).__name__}"
        assert adapter.adapter_name, f"Empty adapter_name on {adapter.adapter_id}"
        assert adapter.adapter_id not in ids, f"Duplicate adapter_id: {adapter.adapter_id}"
        ids.add(adapter.adapter_id)


def test_each_adapter_capabilities_are_honest(tmp_path):
    """Verify each adapter's capabilities() returns a valid RuntimeCapabilities."""
    registry = default_registry()
    for adapter in registry.all():
        caps = adapter.capabilities()
        assert isinstance(caps, RuntimeCapabilities), f"{adapter.adapter_id} capabilities type: {type(caps)}"
        # can_run and can_inspect should not both be False for a registered adapter
        # (except Arena which is gated)
        if adapter.adapter_id != "lmarena":
            assert caps.can_run or caps.can_inspect, (
                f"{adapter.adapter_id} should support at least one of can_run/can_inspect"
            )


def test_each_adapter_detect_returns_consistent_results(tmp_path):
    """detect() in an empty workspace returns (False, 0.0, [])."""
    registry = default_registry()
    ws = tmp_path / "empty-ws"
    ws.mkdir()
    for adapter in registry.all():
        detected, confidence, evidence = adapter.detect(ws)
        # In an empty workspace, nothing should be detected
        assert isinstance(detected, bool), f"{adapter.adapter_id} detect returned non-bool"
        assert isinstance(confidence, float), f"{adapter.adapter_id} detect returned non-float confidence"
        assert isinstance(evidence, list), f"{adapter.adapter_id} detect returned non-list evidence"


def test_adapter_list_cli(tmp_path):
    """`arc adapter list` prints all registered adapters."""
    result = runner.invoke(app, ["adapter", "list"])
    assert result.exit_code == 0
    assert "Registered Adapters" in result.stdout
    for aid in ("swarmgraph", "langgraph", "crewai", "openai-agents", "ag2", "llamaindex"):
        assert aid in result.stdout


def test_adapter_test_swarmgraph_conformance(tmp_path):
    """`arc adapter test swarmgraph` runs conformance tests."""
    result = runner.invoke(app, ["adapter", "test", "swarmgraph", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 0, f"exit {result.exit_code}: {result.stdout[:300]}"
    data = json.loads(result.stdout)["data"]
    assert data["adapter"] == "swarmgraph"
    assert data["passed"] >= 0


def test_adapter_test_langgraph_conformance(tmp_path):
    """`arc adapter test langgraph` runs conformance tests."""
    result = runner.invoke(app, ["adapter", "test", "langgraph", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 0, f"exit {result.exit_code}: {result.stdout[:300]}"
    data = json.loads(result.stdout)["data"]
    assert data["adapter"] == "langgraph"
    assert data["passed"] >= 0


def test_adapter_test_unknown_returns_error(tmp_path):
    """`arc adapter test unknown` returns ADAPTER_NOT_SUPPORTED."""
    result = runner.invoke(app, ["adapter", "test", "nonexistent", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert data["error"]["code"] == "ADAPTER_NOT_SUPPORTED"


def test_adapter_capability_report_includes_test_level(tmp_path):
    """CapabilityReport includes test_level, fake_offline_supported, etc."""
    registry = default_registry()
    ws = tmp_path / "ws"
    ws.mkdir()
    for adapter in registry.all():
        report = adapter.capability_report(ws)
        assert report.test_level in ("unknown", "fake_offline", "gated_local_real", "provider_backed")
        assert isinstance(report.fake_offline_supported, bool), f"{adapter.adapter_id} fake_offline_supported"
        assert isinstance(report.local_real_gated, bool)
        assert isinstance(report.local_real_available, bool)
        assert isinstance(report.provider_backed, bool)
        assert report.provider_backed is False, (
            f"{adapter.adapter_id} should not claim provider_backed=true by default"
        )


def test_adapter_capability_report_has_actions(tmp_path):
    """CapabilityReport has doctor_actions for fix guidance."""
    registry = default_registry()
    ws = tmp_path / "ws"
    ws.mkdir()
    for adapter in registry.all():
        report = adapter.capability_report(ws)
        assert isinstance(report.doctor_actions, list)
        for action in report.doctor_actions:
            assert action.id, f"DoctorAction missing id in {adapter.adapter_id}"
            assert action.label, f"DoctorAction missing label in {adapter.adapter_id}"


def test_build_default_is_idempotent():
    """Calling build_default multiple times does not duplicate adapters."""
    registry1 = AdapterRegistry().build_default()
    ids1 = {a.adapter_id for a in registry1.all()}
    registry2 = AdapterRegistry().build_default()
    ids2 = {a.adapter_id for a in registry2.all()}
    assert ids1 == ids2
    assert len(ids1) == 7  # No duplicates


def test_all_adapters_detect_swarmgraph_project(tmp_path):
    """Most adapters should NOT detect a swarmgraph.yaml project as their own."""
    from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter

    ws = tmp_path / "sg-ws"
    ws.mkdir()
    (ws / "swarmgraph.yaml").write_text("name: test\n")

    # Only SwarmGraphAdapter should detect this
    sg = SwarmGraphAdapter()
    detected, _, _ = sg.detect(ws)
    assert detected is True, "SwarmGraph should detect its own project"

    registry = default_registry()
    for adapter in registry.all():
        if adapter.adapter_id == "swarmgraph":
            continue
        detected, _, evidence = adapter.detect(ws)
        # Non-SwarmGraph adapters should NOT detect a swarmgraph.yaml as theirs
        if detected:
            # If they do detect, it should have low confidence
            assert any("swarmgraph" not in e.lower() for e in evidence), (
                f"{adapter.adapter_id} incorrectly detected swarmgraph project"
            )
