"""Google ADK adapter for ARC Studio.

Adapter Phase 34: T1 detection and T2 static export only.

T3 execution is intentionally not implemented because:
- Google ADK 0.x has active API/breaking-change churn before 1.0.
- Agent execution requires live Gemini/Google AI provider calls and
  Runner session/artifact infrastructure inappropriate for a local CLI.

Detected constructs: LlmAgent, SequentialAgent, ParallelAgent, LoopAgent,
FunctionTool, @tool-decorated functions.
"""

from __future__ import annotations

from pathlib import Path

from ...protocol.capabilities import RuntimeCapabilities
from ...protocol.schemas import WorkflowInfo
from ..base import CapabilityReport, DoctorAction, RuntimeAdapter
from .capabilities import get_google_adk_capabilities
from .detect import GoogleADKDetectionResult, detect_google_adk
from .export import GoogleADKVisitor, export_google_adk_workflows

__all__ = [
    "GoogleADKAdapter",
    "GoogleADKDetectionResult",
    "GoogleADKVisitor",
    "detect_google_adk",
    "export_google_adk_workflows",
]


class GoogleADKAdapter(RuntimeAdapter):
    """Google ADK adapter with static detection/export only."""

    @property
    def adapter_id(self) -> str:
        return "google_adk"

    @property
    def adapter_name(self) -> str:
        return "Google ADK"

    def capabilities(self) -> RuntimeCapabilities:
        return get_google_adk_capabilities()

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        result = detect_google_adk(workspace)
        return result.detected, result.confidence, result.evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        return export_google_adk_workflows(workspace)

    def capability_report(self, workspace: Path) -> CapabilityReport:
        result = detect_google_adk(workspace)
        if not result.detected:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=False,
                can_run=False,
                availability="not_detected",
                reason="Google ADK not detected in workspace",
                detected_artifacts=[],
                doctor_actions=[
                    DoctorAction(
                        id="install-google-adk",
                        label="Install Google ADK",
                        description="Install google-adk in this Python environment",
                        command="pip install google-adk",
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
                "Google ADK detected. T1 (detection) and T2 (static export) are available. "
                "T3 execution is intentionally not implemented: google-adk 0.x has active "
                "API churn and agent execution requires live Gemini/Google AI provider calls."
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
