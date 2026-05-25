"""DSPy adapter for ARC Studio.

Phase 30: Detection, export, and gated runner scaffold for DSPy programs.

T1 (Detection): AST-based detection of dspy.Signature, dspy.Module,
   dspy.Predict, dspy.ChainOfThought, dspy.ReAct, and optimizers.
T2 (Export): AST-based export of DSPy programs to WorkflowInfo.
T3 (Runner): Gated scaffold only. Requires ARC_DSPY_RUNNER_ENABLED=1.
   No live provider calls without explicit gate.
"""

from __future__ import annotations

from pathlib import Path

from ...protocol.capabilities import RuntimeCapabilities
from ...protocol.schemas import WorkflowInfo
from ..base import CapabilityReport, DoctorAction, RuntimeAdapter
from .capabilities import get_dspy_capabilities
from .detect import detect_dspy
from .export import export_dspy_workflows

__all__ = [
    "DSPyAdapter",
    "detect_dspy",
    "DSPyDetectionResult",
    "export_dspy_workflows",
    "DSPyEventHandler",
    "run_dspy_program",
    "is_runner_enabled",
]

from .detect import DSPyDetectionResult
from .runner import DSPyEventHandler, is_runner_enabled, run_dspy_program


class DSPyAdapter(RuntimeAdapter):
    """DSPy adapter for ARC Studio.

    Detects, exports, and (when gated) executes DSPy programs.
    """

    @property
    def adapter_id(self) -> str:
        return "dspy"

    @property
    def adapter_name(self) -> str:
        return "DSPy"

    def capabilities(self) -> RuntimeCapabilities:
        return get_dspy_capabilities()

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        """Detect DSPy usage in workspace.

        Returns:
            (detected, confidence_0_to_1, evidence_list)

        """
        result = detect_dspy(workspace)
        return result.detected, result.confidence, result.evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        """Export DSPy workflows from workspace.

        AST-based export of Signature definitions and Module compositions.
        No code execution (static analysis only).

        Returns:
            List of WorkflowInfo for detected DSPy programs

        """
        return export_dspy_workflows(workspace)

    def capability_report(self, workspace: Path) -> CapabilityReport:
        """Return detailed capability report for DSPy adapter."""
        result = detect_dspy(workspace)

        if not result.detected:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=False,
                can_run=False,
                availability="not_detected",
                reason="DSPy not detected in workspace",
                detected_artifacts=[],
                doctor_actions=[
                    DoctorAction(
                        id="install-dspy",
                        label="Install DSPy",
                        description="Install dspy in this Python environment",
                        command="pip install dspy",
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
                "DSPy detected. T1 (detection) and T2 (export) available. "
                "T3 (runner) is gated scaffold only; set ARC_DSPY_RUNNER_ENABLED=1 to enable."
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
