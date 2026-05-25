"""Haystack adapter for ARC Studio.

Phase 31: Detection, export, and gated runner scaffold for Haystack pipelines.

T1 (Detection): AST-based detection of Pipeline, @component, add_component(),
   connect(), and YAML pipeline definitions.
T2 (Export): AST-based export of Pipeline DAGs to WorkflowInfo.
T3 (Runner): Gated scaffold only. Requires ARC_HAYSTACK_RUNNER_ENABLED=1.
   No live provider calls without explicit gate.
"""

from __future__ import annotations

from pathlib import Path

from ...protocol.capabilities import RuntimeCapabilities
from ...protocol.schemas import WorkflowInfo
from ..base import CapabilityReport, DoctorAction, RuntimeAdapter
from .capabilities import get_haystack_capabilities
from .detect import detect_haystack
from .export import export_haystack_workflows

__all__ = [
    "HaystackAdapter",
    "detect_haystack",
    "HaystackDetectionResult",
    "export_haystack_workflows",
    "HaystackEventHandler",
    "run_haystack_pipeline",
    "is_runner_enabled",
]

from .detect import HaystackDetectionResult
from .runner import HaystackEventHandler, is_runner_enabled, run_haystack_pipeline


class HaystackAdapter(RuntimeAdapter):
    """Haystack adapter for ARC Studio.

    Detects, exports, and (when gated) executes Haystack pipelines.
    Pipeline DAG maps cleanly to ARC run plans.
    """

    @property
    def adapter_id(self) -> str:
        return "haystack"

    @property
    def adapter_name(self) -> str:
        return "Haystack"

    def capabilities(self) -> RuntimeCapabilities:
        return get_haystack_capabilities()

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        """Detect Haystack usage in workspace.

        Returns:
            (detected, confidence_0_to_1, evidence_list)

        """
        result = detect_haystack(workspace)
        return result.detected, result.confidence, result.evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        """Export Haystack workflows from workspace.

        AST-based export of Pipeline DAGs and Component definitions.
        No code execution (static analysis only).

        Returns:
            List of WorkflowInfo for detected Haystack pipelines

        """
        return export_haystack_workflows(workspace)

    def capability_report(self, workspace: Path) -> CapabilityReport:
        """Return detailed capability report for Haystack adapter."""
        result = detect_haystack(workspace)

        if not result.detected:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=False,
                can_run=False,
                availability="not_detected",
                reason="Haystack not detected in workspace",
                detected_artifacts=[],
                doctor_actions=[
                    DoctorAction(
                        id="install-haystack",
                        label="Install Haystack",
                        description="Install haystack-ai in this Python environment",
                        command="pip install haystack-ai",
                        safe_to_auto_run=False,
                    ),
                ],
            )

        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=True,
            can_run=False,
            availability="detected_not_runnable",
            reason=(
                "Haystack detected. T1 (detection) and T2 (export) available. "
                "T3 (runner) is gated scaffold only; set ARC_HAYSTACK_RUNNER_ENABLED=1 to enable. "
                "Pipeline DAG maps cleanly to ARC run plans."
            ),
            detected_artifacts=result.evidence,
            version=result.version,
            doctor_actions=[],
            test_level="unknown",
            fake_offline_supported=False,
            local_real_gated=True,
            local_real_available=False,
            provider_backed=False,
        )
