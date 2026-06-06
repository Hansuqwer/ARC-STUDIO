"""Tests for ArcRuntimeSDKAdapter (R79/Phase 111 Slice 110.1 + 110.2).

Contract parity with RuntimeAdapter + registry discovery. Truth: simulator/mock
only, can_run=False (no run path yet), no false positives.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.adapters.arc_runtime_sdk import ArcRuntimeSDKAdapter
from agent_runtime_cockpit.adapters.base import CapabilityReport, RuntimeAdapter
from agent_runtime_cockpit.adapters.registry import default_registry
from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities


def _sdk_workspace(tmp_path: Path, **manifest_extra) -> Path:
    manifest = {
        "schema_version": "1.0.0",
        "app_id": "demo-app",
        "sdk_version": "0.1.0",
        "capabilities": [],
    }
    manifest.update(manifest_extra)
    (tmp_path / "arc-sdk.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path


# ── Contract parity ───────────────────────────────────────────────────────────


def test_is_runtime_adapter_subclass():
    assert issubclass(ArcRuntimeSDKAdapter, RuntimeAdapter)


def test_adapter_identity():
    a = ArcRuntimeSDKAdapter()
    assert a.adapter_id == "arc-runtime-sdk"
    assert a.adapter_name == "ARC Runtime SDK"


def test_capabilities_returns_runtime_capabilities():
    caps = ArcRuntimeSDKAdapter().capabilities()
    assert isinstance(caps, RuntimeCapabilities)
    # Honest fake-mode report: no run path yet, no paid/network/secret/shell.
    assert caps.can_run is False
    assert caps.requires_paid_calls is False
    assert caps.requires_network is False
    assert caps.requires_secrets is False
    # Simulator artifacts can be inspected/streamed/replayed.
    assert caps.can_inspect is True
    assert caps.can_stream_events is True
    assert caps.can_replay is True


# ── detect() ──────────────────────────────────────────────────────────────────


def test_detect_with_sdk_manifest(tmp_path):
    ws = _sdk_workspace(tmp_path)
    detected, confidence, evidence = ArcRuntimeSDKAdapter().detect(ws)
    assert detected is True
    assert confidence >= 0.50
    assert any("arc-sdk.json" in e for e in evidence)


def test_detect_returns_tuple_shape(tmp_path):
    result = ArcRuntimeSDKAdapter().detect(_sdk_workspace(tmp_path))
    assert isinstance(result, tuple) and len(result) == 3
    detected, confidence, evidence = result
    assert isinstance(detected, bool)
    assert isinstance(confidence, float)
    assert isinstance(evidence, list)


def test_detect_empty_workspace_not_detected(tmp_path):
    detected, confidence, evidence = ArcRuntimeSDKAdapter().detect(tmp_path)
    assert detected is False
    assert confidence < 0.50
    assert evidence == []


def test_detect_confidence_increases_with_artifacts(tmp_path):
    ws = _sdk_workspace(tmp_path)
    (ws / "arc-runtime-pack.json").write_text("{}", encoding="utf-8")
    (ws / "capsules").mkdir()
    (ws / "fixtures").mkdir()
    detected, confidence, evidence = ArcRuntimeSDKAdapter().detect(ws)
    assert detected is True
    assert confidence >= 0.90  # 0.50 + 0.25 + 0.10 + 0.10
    assert "arc-runtime-pack.json" in evidence
    assert "capsules/" in evidence
    assert "fixtures/" in evidence


def test_detect_unknown_schema_version_low_confidence(tmp_path):
    ws = _sdk_workspace(tmp_path, schema_version="9.9.9")
    detected, confidence, _ = ArcRuntimeSDKAdapter().detect(ws)
    # Unknown schema scores 0.50*0.3 = 0.15 → below threshold.
    assert detected is False
    assert confidence < 0.50


# ── capability_report() ─────────────────────────────────────────────────────


def test_capability_report_fake_offline(tmp_path):
    report = ArcRuntimeSDKAdapter().capability_report(_sdk_workspace(tmp_path))
    assert isinstance(report, CapabilityReport)
    assert report.detected is True
    assert report.can_run is False
    assert report.availability == "detected_not_runnable"
    assert report.test_level == "fake_offline"
    assert report.fake_offline_supported is True
    assert report.local_real_available is False
    assert report.provider_backed is False
    assert report.version == "0.1.0"


def test_capability_report_not_detected(tmp_path):
    report = ArcRuntimeSDKAdapter().capability_report(tmp_path)
    assert report.detected is False
    assert report.can_run is False
    assert report.availability == "not_detected"
    # Missing arc-runtime CLI surfaces a non-auto-run doctor action.
    assert any(a.id == "install-arc-runtime" for a in report.doctor_actions)


def test_capability_report_parse_error(tmp_path):
    (tmp_path / "arc-sdk.json").write_text("{not valid json", encoding="utf-8")
    report = ArcRuntimeSDKAdapter().capability_report(tmp_path)
    # Parse error still scores ~0.05 → not detected by threshold.
    assert report.detected is False


def test_capability_report_paid_capability_flagged(tmp_path):
    ws = _sdk_workspace(tmp_path, capabilities=[{"id": "c1", "category": "paid_model"}])
    report = ArcRuntimeSDKAdapter().capability_report(ws)
    assert report.requires_paid_calls is True


def test_capability_report_notes_gate_approvals(tmp_path):
    ws = _sdk_workspace(tmp_path, gate_policy={"approved": [{"capability_id": "c1"}]})
    report = ArcRuntimeSDKAdapter().capability_report(ws)
    # Honesty: gate approvals are noted but NOT honored as can_run yet.
    assert report.can_run is False
    assert "approval" in (report.reason or "").lower()


# ── Registry discovery ──────────────────────────────────────────────────────


def test_registered_in_default_registry():
    adapter = default_registry().get("arc-runtime-sdk")
    assert adapter is not None
    assert isinstance(adapter, ArcRuntimeSDKAdapter)


def test_detect_all_lists_sdk_when_present(tmp_path):
    _sdk_workspace(tmp_path)
    runtimes = default_registry().detect_all(tmp_path)
    sdk = [r for r in runtimes if r.adapter == "arc-runtime-sdk"]
    assert len(sdk) == 1
    assert isinstance(sdk[0].capabilities, RuntimeCapabilities)
    assert sdk[0].capabilities.can_run is False
    assert sdk[0].evidence


def test_detect_all_omits_sdk_when_absent(tmp_path):
    runtimes = default_registry().detect_all(tmp_path)
    assert not any(r.adapter == "arc-runtime-sdk" for r in runtimes)


# ── Honesty: no run path (no false positive) ─────────────────────────────────


@pytest.mark.asyncio
async def test_run_workflow_not_implemented():
    """The P0 adapter has no run path; run_workflow must raise (not fake a run)."""
    with pytest.raises(NotImplementedError):
        await ArcRuntimeSDKAdapter().run_workflow("wf-1", {})
