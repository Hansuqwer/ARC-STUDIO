"""Semantic Kernel adapter for ARC Studio.

Adapter Phase 33: T1 detection and T2 static export only. Runtime execution is
not implemented because Semantic Kernel flows can trigger provider calls and the
Python SDK has active API churn.
"""

from __future__ import annotations

from pathlib import Path

from ...protocol.capabilities import RuntimeCapabilities
from ...protocol.schemas import WorkflowInfo
from ..base import CapabilityReport, DoctorAction, RuntimeAdapter
from .capabilities import get_semantic_kernel_capabilities
from .detect import SemanticKernelDetectionResult, detect_semantic_kernel
from .export import SemanticKernelVisitor, export_semantic_kernel_workflows

__all__ = [
    "SemanticKernelAdapter",
    "SemanticKernelDetectionResult",
    "SemanticKernelVisitor",
    "detect_semantic_kernel",
    "export_semantic_kernel_workflows",
]


class SemanticKernelAdapter(RuntimeAdapter):
    """Semantic Kernel adapter with static detection/export only."""

    @property
    def adapter_id(self) -> str:
        return "semantic_kernel"

    @property
    def adapter_name(self) -> str:
        return "Semantic Kernel"

    def capabilities(self) -> RuntimeCapabilities:
        return get_semantic_kernel_capabilities()

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        result = detect_semantic_kernel(workspace)
        return result.detected, result.confidence, result.evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        return export_semantic_kernel_workflows(workspace)

    def capability_report(self, workspace: Path) -> CapabilityReport:
        result = detect_semantic_kernel(workspace)
        if not result.detected:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=False,
                can_run=False,
                availability="not_detected",
                reason="Semantic Kernel not detected in workspace",
                detected_artifacts=[],
                doctor_actions=[
                    DoctorAction(
                        id="install-semantic-kernel",
                        label="Install Semantic Kernel",
                        description="Install semantic-kernel in this Python environment",
                        command="pip install semantic-kernel",
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
                "Semantic Kernel detected. T1 (detection) and T2 (export) are available. "
                "T3 execution is intentionally not implemented due SDK churn and provider-call risk."
            ),
            detected_artifacts=result.evidence,
            version=result.version,
            doctor_actions=[],
            test_level="unknown",
            fake_offline_supported=False,
            local_real_gated=False,
            local_real_available=False,
            provider_backed=False,
        )
