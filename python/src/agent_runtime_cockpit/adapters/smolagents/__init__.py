"""Smolagents adapter for ARC Studio.

T1/T2 are static. T3 is gated due to code execution and provider/network risk.
"""

from __future__ import annotations

from pathlib import Path

from ...protocol.capabilities import RuntimeCapabilities
from ...protocol.schemas import WorkflowInfo
from ..base import CapabilityReport, DoctorAction, RuntimeAdapter
from .capabilities import get_smolagents_capabilities
from .detect import SmolagentsDetectionResult, detect_smolagents
from .export import export_smolagents_workflows
from .runner import (
    SmolagentsEventHandler,
    is_live_provider_enabled,
    is_runner_enabled,
    run_smolagents_agent,
)

__all__ = [
    "SmolagentsAdapter",
    "SmolagentsDetectionResult",
    "SmolagentsEventHandler",
    "detect_smolagents",
    "export_smolagents_workflows",
    "is_runner_enabled",
    "run_smolagents_agent",
]


class SmolagentsAdapter(RuntimeAdapter):
    """Smolagents adapter for ARC Studio."""

    @property
    def adapter_id(self) -> str:
        return "smolagents"

    @property
    def adapter_name(self) -> str:
        return "Smolagents"

    def capabilities(self) -> RuntimeCapabilities:
        return get_smolagents_capabilities()

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        result = detect_smolagents(workspace)
        return result.detected, result.confidence, result.evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        return export_smolagents_workflows(workspace)

    def capability_report(self, workspace: Path) -> CapabilityReport:
        result = detect_smolagents(workspace)
        if not result.detected:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=False,
                can_run=False,
                availability="not_detected",
                reason="Smolagents not detected in workspace",
                detected_artifacts=[],
                doctor_actions=[
                    DoctorAction(
                        id="install-smolagents",
                        label="Install Smolagents",
                        description="Install smolagents in this Python environment",
                        command="pip install 'smolagents[toolkit]'",
                        safe_to_auto_run=False,
                    )
                ],
            )
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=True,
            can_run=False,
            availability="detected_not_runnable",
            reason=(
                "Smolagents detected. T1/T2 static analysis available. T3 runner is "
                "gated by ARC_SMOLAGENTS_RUNNER_ENABLED=1 and "
                "ARC_ALLOW_LIVE_PROVIDER_TESTS=true. CodeAgent also requires explicit "
                "sandbox configuration and risk confirmation because it can execute generated code."
            ),
            detected_artifacts=result.evidence,
            version=result.version,
            doctor_actions=[],
            test_level="unknown",
            fake_offline_supported=False,
            local_real_gated=True,
            local_real_available=is_runner_enabled() and is_live_provider_enabled(),
            provider_backed=False,
        )
