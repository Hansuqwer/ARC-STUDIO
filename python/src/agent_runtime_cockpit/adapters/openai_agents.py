from __future__ import annotations

import importlib.util
from pathlib import Path

from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import WorkflowInfo
from ._static import dependency_evidence, import_evidence, static_workflow
from .base import RuntimeAdapter


class OpenAIAgentsAdapter(RuntimeAdapter):
    @property
    def adapter_id(self) -> str:
        return "openai-agents"

    @property
    def adapter_name(self) -> str:
        return "OpenAI Agents"

    def capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(can_inspect=True, can_run=False, can_export_workflow=True)

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        dep_score, evidence = dependency_evidence(workspace, ("openai-agents", "openai_agents"))
        import_score, import_hits = import_evidence(workspace, ("from agents", "import agents"))
        evidence.extend(import_hits)
        if importlib.util.find_spec("agents") is not None:
            evidence.append("agents package importable")
            dep_score = max(dep_score, 0.4)
        score = min(dep_score + import_score, 1.0)
        return score > 0.3, score, evidence

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        detected, _, evidence = self.detect(workspace)
        if not detected:
            return []
        return static_workflow(self.adapter_id, self.adapter_name, workspace, evidence)
