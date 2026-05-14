"""AG2 runtime adapter — detection and runner wrapper."""

from __future__ import annotations

from pathlib import Path

from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import WorkflowInfo
from ._static import static_workflow
from .ag2.detect import is_ag2_workspace
from .base import CapabilityReport, DoctorAction, RuntimeAdapter


class AG2Adapter(RuntimeAdapter):
    """Adapter for AG2 (AutoGen) agent teams.

    Current state:
      - Detection: scans workspace for autogen dependency and GroupChatManager usage.
      - Runner: AG2Runner exists but requires a workspace export target.
      - Execution: not runnable by default; can_run depends on export target presence.
    """

    @property
    def adapter_id(self) -> str:
        return "ag2"

    @property
    def adapter_name(self) -> str:
        return "AG2"

    def capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(
            can_inspect=True,
            can_run=False,
            can_export_workflow=True,
        )

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        detected = is_ag2_workspace(workspace)
        evidence: list[str] = []
        if detected:
            evidence.append("autogen dependency or GroupChatManager usage detected")
        return detected, 0.7 if detected else 0.0, evidence

    def capability_report(self, workspace: Path) -> CapabilityReport:
        detected, confidence, evidence = self.detect(workspace)
        actions: list[DoctorAction] = []
        if not detected:
            actions.append(
                DoctorAction(
                    id="install_ag2",
                    label="Install AG2 (autogen)",
                    description="Run: pip install autogen-agentchat",
                )
            )
        else:
            actions.append(
                DoctorAction(
                    id="configure_ag2_export",
                    label="Set export target",
                    description="Set ARC_AG2_EXPORT=module:TeamClass to enable execution",
                )
            )
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=detected,
            can_run=False,
            availability="missing_export_target" if detected else "missing_dependency",
            reason="AG2 runner exists but no export target configured" if detected else "AG2 (autogen) not installed",
            detected_artifacts=evidence,
            required_env=["ARC_AG2_EXPORT"],
            requires_paid_calls=False,
            doctor_actions=actions,
        )

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        detected, _, evidence = self.detect(workspace)
        if not detected:
            return []
        return static_workflow(self.adapter_id, self.adapter_name, workspace, evidence)
