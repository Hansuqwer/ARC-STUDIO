from __future__ import annotations

import importlib
import importlib.util
import os
from pathlib import Path

from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import WorkflowInfo
from ._static import dependency_evidence, import_evidence, static_workflow
from .base import CapabilityReport, DoctorAction, RuntimeAdapter

EXPORT_ENV = "ARC_LLAMAINDEX_EXPORT"


class LlamaIndexAdapter(RuntimeAdapter):
    @property
    def adapter_id(self) -> str:
        return "llamaindex"

    @property
    def adapter_name(self) -> str:
        return "LlamaIndex"

    def capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(can_inspect=True, can_run=False, can_export_workflow=True)

    def capability_report(self, workspace: Path) -> CapabilityReport:
        detected, _, evidence = self.detect(workspace)
        importable, version = self._llamaindex_importable()
        if not importable:
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="missing_dependency",
                reason="Install llama-index in this Python environment.",
                detected_artifacts=evidence,
                required_env=[EXPORT_ENV],
                requires_paid_calls=True,
                doctor_actions=[
                    DoctorAction(
                        id="install-llamaindex",
                        label="Install LlamaIndex",
                        description="Install llama-index in this Python environment",
                        command="pip install llama-index",
                        safe_to_auto_run=False,
                    ),
                ],
            )
        if not os.environ.get(EXPORT_ENV):
            return CapabilityReport(
                runtime_id=self.adapter_id,
                detected=detected,
                can_run=False,
                availability="missing_export_target",
                reason=f"Set {EXPORT_ENV}=module:attribute to a LlamaIndex workflow entry point.",
                detected_artifacts=evidence,
                required_env=[EXPORT_ENV],
                version=version,
                requires_paid_calls=True,
                doctor_actions=self._doctor_actions(workspace),
            )
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=detected,
            can_run=False,
            availability="detected_not_runnable",
            reason="LlamaIndex export target is configured, but this adapter does not expose a runnable path yet.",
            detected_artifacts=evidence,
            required_env=[EXPORT_ENV],
            version=version,
            requires_paid_calls=True,
            doctor_actions=self._doctor_actions(workspace),
        )

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        return [
            DoctorAction(
                id="set-llamaindex-export",
                label="Set ARC_LLAMAINDEX_EXPORT",
                description=f"Set {EXPORT_ENV}=module:attribute to your LlamaIndex entry point",
                command=f"export {EXPORT_ENV}=my_index:workflow",
                safe_to_auto_run=False,
            ),
        ]

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        dep_score, evidence = dependency_evidence(workspace, ("llama-index", "llama_index"))
        import_score, import_hits = import_evidence(
            workspace, ("from llama_index", "import llama_index")
        )
        evidence.extend(import_hits)
        if importlib.util.find_spec("llama_index") is not None:
            evidence.append("llama_index package importable")
            dep_score = max(dep_score, 0.4)
        score = min(dep_score + import_score, 1.0)
        return score > 0.3, score, evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        detected, _, evidence = self.detect(workspace)
        if not detected:
            return []
        return static_workflow(self.adapter_id, self.adapter_name, workspace, evidence)

    def _llamaindex_importable(self) -> tuple[bool, str | None]:
        if importlib.util.find_spec("llama_index") is None:
            return False, None
        try:
            module = importlib.import_module("llama_index")
        except Exception:
            return False, None
        return True, getattr(module, "__version__", None)
