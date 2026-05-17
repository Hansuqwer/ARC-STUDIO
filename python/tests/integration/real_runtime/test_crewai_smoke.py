"""Opt-in real-runtime CrewAI smoke tests for release readiness.

These tests are intentionally skipped in the default offline gate. Enable with
``ARC_REAL_RUNTIME_SMOKE=1`` and set ``ARC_CREWAI_EXPORT=module:attr`` when
validating a release candidate or nightly CI.

No provider calls are made — only import and availability checks.
"""
from __future__ import annotations

import os
import importlib.util

import pytest

from agent_runtime_cockpit.adoption.crewai_runner import CrewAIAdoptionRunner
from agent_runtime_cockpit.adoption.langgraph_runner import _setup_swarmgraph_paths
from agent_runtime_cockpit.adoption.protocol import AdoptionStatus


pytestmark = pytest.mark.real_runtime


def _requires_real_runtime_smoke() -> None:
    if os.environ.get("ARC_REAL_RUNTIME_SMOKE") != "1":
        pytest.skip("set ARC_REAL_RUNTIME_SMOKE=1 to run real-runtime smoke tests")


def _requires_crewai_runtime() -> None:
    _requires_real_runtime_smoke()
    if importlib.util.find_spec("crewai") is None:
        pytest.skip("crewai package is not installed; skipping optional real-runtime CrewAI smoke")


def _requires_crewai_export() -> str:
    _requires_crewai_runtime()
    export_env = "ARC_CREWAI_EXPORT"
    value = os.environ.get(export_env)
    if value is None:
        pytest.skip(f"set {export_env}=module:attr to run optional real-runtime CrewAI smoke")
    if ":" not in value:
        pytest.fail(f"{export_env} must use module:attr format (e.g. my_crew:crew)")
    return value


def test_crewai_package_importable() -> None:
    """Verify CrewAI can be imported when available."""
    _requires_crewai_runtime()


def test_crewai_export_env_is_set() -> None:
    """Verify ARC_CREWAI_EXPORT is set for real-runtime smoke."""
    _requires_crewai_export()


def test_crewai_adoption_runner_availability_reports_real_status(tmp_path) -> None:
    """Verify CrewAI adoption runner detects real availability."""
    _requires_crewai_runtime()

    _setup_swarmgraph_paths()

    capability = CrewAIAdoptionRunner().check_availability(tmp_path)

    assert capability.status is AdoptionStatus.RUNNABLE, (
        f"Expected RUNNABLE, got {capability.status}: {capability.reason}"
    )
    assert "CrewAI" in capability.reason
    assert "SwarmGraph" in capability.reason


def test_crewai_standalone_adapter_detects_export(tmp_path) -> None:
    """Verify standalone CrewAI adapter can detect export target."""
    _requires_crewai_export()

    from agent_runtime_cockpit.adapters.crewai import CrewAIAdapter

    adapter = CrewAIAdapter()
    report = adapter.capability_report(tmp_path)

    assert report.can_run is True, (
        f"CrewAI adapter should be runnable with export set: {report.reason}"
    )
    assert "ARC_CREWAI_EXPORT" in report.required_env
    assert report.requires_paid_calls is True
