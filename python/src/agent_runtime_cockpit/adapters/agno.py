"""Agno (ex-Phidata) adapter for ARC Studio.

API verified against agno (context7 /agno-agi/docs):
  from agno.agent import Agent
  run: RunOutput = agent.run("prompt")   # sync → RunOutput.content
  run = await agent.arun("prompt")       # async → RunOutput.content

Gating:
  ARC_AGNO_EXPORT=module:attr   # export target
  ARC_AGNO_ALLOW_COSTS=true     # dual-gate
"""

from __future__ import annotations

import importlib
import importlib.util
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..gating import GatingError, require_dual_gate
from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import RunEvent, RunRecord, RunStatus
from ._shared import make_event, workspace_import_path
from ._static import dependency_evidence, import_evidence
from .base import DoctorAction, RuntimeAdapter
from . import agno_mapping  # noqa: F401 — registers AG-UI mapper on import

log = logging.getLogger(__name__)

_EXPORT_ENV = "ARC_AGNO_EXPORT"
_ALLOW_ENV = "ARC_AGNO_ALLOW_COSTS"


def _installed() -> bool:
    return importlib.util.find_spec("agno") is not None


class AgnoAdapter(RuntimeAdapter):
    """Adapter for Agno (ex-Phidata) multi-agent projects."""

    @property
    def adapter_id(self) -> str:
        return "agno"

    @property
    def adapter_name(self) -> str:
        return "Agno"

    def capabilities(self) -> RuntimeCapabilities:
        export_set = bool(os.environ.get(_EXPORT_ENV))
        allow_costs = os.environ.get(_ALLOW_ENV, "").strip().lower() == "true"
        return RuntimeCapabilities(
            can_inspect=True,
            can_run=_installed() and export_set and allow_costs,
            can_export_workflow=True,
            can_export_schema=False,
            can_trace=False,
            can_stream_events=False,
        )

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        evidence: list[str] = []
        if _installed():
            evidence.append("agno installed")
        _, import_ev = import_evidence(workspace, ("from agno", "import agno"))
        _, dep_ev = dependency_evidence(workspace, ("agno",))
        evidence += import_ev + dep_ev
        if not evidence:
            return False, 0.0, []
        confidence = min(
            (0.5 if _installed() else 0.0) + (0.4 if import_ev or dep_ev else 0.0), 1.0
        )
        return True, confidence, evidence

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        actions: list[DoctorAction] = []
        if not _installed():
            actions.append(
                DoctorAction(
                    id="install_agno",
                    label="Install agno",
                    description="pip install agno",
                    severity="warning",
                )
            )
        if not os.environ.get(_EXPORT_ENV):
            actions.append(
                DoctorAction(
                    id="set_export",
                    label="Set export target",
                    description=f"Set {_EXPORT_ENV}=my_module:my_agent",
                    severity="info",
                )
            )
        if not os.environ.get(_ALLOW_ENV):
            actions.append(
                DoctorAction(
                    id="enable_costs",
                    label="Enable paid calls",
                    description=f"Set {_ALLOW_ENV}=true (dual-gate)",
                    severity="info",
                )
            )
        return actions

    def export_workflow(self, workspace: Path):
        from ..protocol.schemas import NodeType, WorkflowInfo, WorkflowNode

        detected, _, evidence = self.detect(workspace)
        if not detected:
            return []
        target = os.environ.get(_EXPORT_ENV, "")
        return [
            WorkflowInfo(
                id=f"agno::{workspace.name}",
                name=target.split(":")[-1] if ":" in target else "agno-agent",
                runtime=self.adapter_id,
                nodes=[WorkflowNode(id="agent", label="Agno Agent", type=NodeType.AGENT)],
                edges=[],
                metadata={"evidence": evidence, "export_target": target},
            )
        ]

    async def run_workflow(
        self,
        workflow_id: str,
        inputs: dict[str, Any],
        workspace: Path | None = None,
    ) -> RunRecord:
        require_dual_gate("AGNO")
        target = os.environ.get(_EXPORT_ENV)
        if not target or ":" not in target:
            raise GatingError(f"{_EXPORT_ENV} not set. Use {_EXPORT_ENV}=my_module:my_agent")

        ws = workspace or Path.cwd()
        module_name, attr_name = target.split(":", 1)
        try:
            with workspace_import_path(ws):
                mod = importlib.import_module(module_name)
            agent = getattr(mod, attr_name)
        except Exception as exc:
            raise GatingError(f"Failed to load {_EXPORT_ENV}={target!r}: {exc}") from exc

        run_id = str(uuid.uuid4())
        started = datetime.now(timezone.utc)
        events: list[RunEvent] = []
        seq = 0
        prompt = inputs.get("prompt") or inputs.get("input") or str(inputs)

        events.append(make_event(run_id, seq, "AGNO_RUN_START", {"prompt": prompt}))
        seq += 1
        try:
            result = await agent.arun(prompt)
            output = str(getattr(result, "content", result))
            events.append(make_event(run_id, seq, "AGNO_RUN_END", {"output": output}))
            status = RunStatus.COMPLETED
        except Exception as exc:
            output = f"error: {exc}"
            events.append(make_event(run_id, seq, "AGNO_RUN_ERROR", {"error": str(exc)}))
            status = RunStatus.FAILED

        ended = datetime.now(timezone.utc)
        return RunRecord(
            id=run_id,
            workflow_id=workflow_id,
            runtime=self.adapter_id,
            status=status,
            started_at=started.isoformat(),
            ended_at=ended.isoformat(),
            events=events,
            metadata={"inputs": inputs, "outputs": {"result": output}},
        )
