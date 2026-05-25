"""Tests for GoogleADKAdapter interface."""

from __future__ import annotations

import asyncio
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.adapters.google_adk import GoogleADKAdapter
from agent_runtime_cockpit.protocol.capabilities import RuntimeCapabilities


def test_adapter_identity():
    adapter = GoogleADKAdapter()
    assert adapter.adapter_id == "google_adk"
    assert adapter.adapter_name == "Google ADK"


def test_capabilities_are_honest():
    caps = GoogleADKAdapter().capabilities()
    assert isinstance(caps, RuntimeCapabilities)
    # T1 + T2 only
    assert caps.can_inspect is True
    assert caps.can_export_workflow is True
    # T3 not implemented
    assert caps.can_run is False
    assert caps.can_stream_events is False
    assert caps.can_trace is False
    # Honest resource requirements
    assert caps.requires_network is True
    assert caps.requires_secrets is True


def test_detect_not_detected_empty(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(False, None),
    ):
        detected, confidence, evidence = GoogleADKAdapter().detect(tmp_path)
    assert detected is False
    assert confidence == 0.0
    assert evidence == []


def test_detect_found_in_workspace(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from google.adk.agents import LlmAgent\nroot = LlmAgent(name='R')\n"
    )
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(False, None),
    ):
        detected, confidence, evidence = GoogleADKAdapter().detect(tmp_path)
    assert detected is True
    assert confidence > 0.0
    assert evidence


def test_export_workflow(tmp_path):
    (tmp_path / "agent.py").write_text(
        "from google.adk.agents import LlmAgent\nroot = LlmAgent(name='Root')\n"
    )
    workflows = GoogleADKAdapter().export_workflow(tmp_path)
    assert len(workflows) == 1
    assert workflows[0].runtime == "google_adk"


def test_capability_report_not_detected(tmp_path):
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(False, None),
    ):
        report = GoogleADKAdapter().capability_report(tmp_path)
    assert report.detected is False
    assert report.availability == "not_detected"
    assert report.doctor_actions[0].id == "install-google-adk"
    assert "pip install google-adk" in report.doctor_actions[0].command


def test_capability_report_detected_mentions_t3_not_implemented(tmp_path):
    (tmp_path / "agent.py").write_text("from google.adk.agents import LlmAgent\n")
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(False, None),
    ):
        report = GoogleADKAdapter().capability_report(tmp_path)
    assert report.detected is True
    assert report.can_run is False
    assert report.availability == "detected_not_runnable"
    assert "T3" in (report.reason or "")
    assert "not implemented" in (report.reason or "").lower()
    assert report.local_real_gated is False
    assert report.provider_backed is False


def test_capability_report_detected_has_version(tmp_path):
    (tmp_path / "agent.py").write_text("from google.adk.agents import LlmAgent\n")
    with patch(
        "agent_runtime_cockpit.adapters.google_adk.detect.detect_google_adk_import",
        return_value=(True, "0.4.1"),
    ):
        report = GoogleADKAdapter().capability_report(tmp_path)
    assert report.version == "0.4.1"


def test_run_workflow_not_implemented():
    with pytest.raises(NotImplementedError):
        asyncio.run(GoogleADKAdapter().run_workflow("wf"))


def test_adapter_registered_in_default_registry():
    from agent_runtime_cockpit.adapters.registry import default_registry

    registry = default_registry()
    adapter = registry.get("google_adk")
    assert adapter is not None
    assert isinstance(adapter, GoogleADKAdapter)
