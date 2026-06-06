"""Strands Agents (AWS) adapter for ARC Studio.

Detects and (optionally, gated) runs Strands Agents projects.
Source: https://strandsagents.com  /  https://pypi.org/project/strands-agents/

Run API (verified v1.42.0):
  agent = Agent(tools=[...], model=BedrockModel(...))
  result = agent("prompt")       # AgentResult
  str(result)                    # concatenated text content

Gating: default model is BedrockModel (AWS creds). Set:
  ARC_STRANDS_ALLOW_COSTS=true   # dual-gate (paid calls)
  ARC_STRANDS_EXPORT=module:attr  # export target
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
from ..protocol.schemas import (
    NodeType,
    RunEvent,
    RunRecord,
    RunStatus,
    WorkflowInfo,
    WorkflowNode,
)
from ._shared import make_event, workspace_import_path
from ._static import dependency_evidence, import_evidence
from .base import DoctorAction, RuntimeAdapter

log = logging.getLogger(__name__)

_EXPORT_ENV = "ARC_STRANDS_EXPORT"
_ALLOW_ENV = "ARC_STRANDS_ALLOW_COSTS"


def _strands_installed() -> tuple[bool, str | None]:
    """Return (installed, version_or_None)."""
    spec = importlib.util.find_spec("strands")
    if spec is None:
        return False, None
    try:
        import strands as _s

        return True, getattr(_s, "__version__", None)
    except Exception:
        return True, None


class StrandsAdapter(RuntimeAdapter):
    """Adapter for Strands Agents (AWS) projects."""

    @property
    def adapter_id(self) -> str:
        return "strands"

    @property
    def adapter_name(self) -> str:
        return "Strands Agents (AWS)"

    def capabilities(self) -> RuntimeCapabilities:
        installed, _ = _strands_installed()
        export_set = bool(os.environ.get(_EXPORT_ENV))
        allow_costs = os.environ.get(_ALLOW_ENV, "").strip().lower() == "true"
        can_run = installed and export_set and allow_costs
        return RuntimeCapabilities(
            can_inspect=True,  # detection is always available
            can_run=can_run,
            can_export_workflow=True,
            can_export_schema=False,
            can_trace=False,
            can_stream_events=False,
        )

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        installed, version = _strands_installed()
        evidence: list[str] = []
        if installed:
            evidence.append(f"strands installed (version: {version or 'unknown'})")

        _, import_ev = import_evidence(workspace, ("from strands", "import strands"))
        _, dep_ev = dependency_evidence(workspace, ("strands-agents", "strands_agents"))
        evidence += import_ev + dep_ev

        if not evidence:
            return False, 0.0, []

        confidence = 0.0
        if installed:
            confidence += 0.5
        if import_ev or dep_ev:
            confidence += 0.4
        confidence = min(confidence, 1.0)

        return True, confidence, evidence

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        actions: list[DoctorAction] = []
        installed, _ = _strands_installed()
        if not installed:
            actions.append(
                DoctorAction(
                    id="install_strands",
                    label="Install strands-agents",
                    description="pip install strands-agents",
                    severity="warning",
                )
            )
        if not os.environ.get(_EXPORT_ENV):
            actions.append(
                DoctorAction(
                    id="set_export",
                    label="Set export target",
                    description=f"Set {_EXPORT_ENV}=my_module:my_agent to enable execution",
                    severity="info",
                )
            )
        if not os.environ.get(_ALLOW_ENV):
            actions.append(
                DoctorAction(
                    id="enable_costs",
                    label="Enable paid calls",
                    description=f"Set {_ALLOW_ENV}=true to allow paid API calls (dual-gate)",
                    severity="info",
                )
            )
        return actions

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        detected, _, evidence = self.detect(workspace)
        if not detected:
            return []
        target = os.environ.get(_EXPORT_ENV, "")
        return [
            WorkflowInfo(
                id=f"strands::{workspace.name}",
                name=target.split(":")[-1] if ":" in target else "strands-agent",
                runtime=self.adapter_id,
                nodes=[
                    WorkflowNode(
                        id="agent",
                        label="Agent",
                        type=NodeType.AGENT,
                    )
                ],
                edges=[],
                source_file=None,
                metadata={"evidence": evidence, "export_target": target},
            )
        ]

    async def run_workflow(
        self,
        workflow_id: str,
        inputs: dict[str, Any],
        workspace: Path | None = None,
    ) -> RunRecord:
        require_dual_gate("STRANDS")

        target = os.environ.get(_EXPORT_ENV)
        if not target or ":" not in target:
            raise GatingError(
                f"{_EXPORT_ENV} is not set or invalid. Set {_EXPORT_ENV}=my_module:my_agent"
            )

        ws = workspace or Path.cwd()
        module_name, attr_name = target.split(":", 1)

        run_id = str(uuid.uuid4())
        started = datetime.now(timezone.utc)
        events: list[RunEvent] = []
        seq = 0

        try:
            with workspace_import_path(ws):
                mod = importlib.import_module(module_name)
            agent = getattr(mod, attr_name)
        except Exception as exc:
            raise GatingError(f"Failed to load {_EXPORT_ENV}={target!r}: {exc}") from exc

        prompt = inputs.get("prompt") or inputs.get("input") or str(inputs)
        events.append(make_event(run_id, seq, "STRANDS_RUN_START", {"prompt": prompt}))
        seq += 1

        try:
            result = agent(prompt)
            output = str(result)
            events.append(make_event(run_id, seq, "STRANDS_RUN_END", {"output": output}))
            status = RunStatus.COMPLETED
        except Exception as exc:
            output = f"error: {exc}"
            events.append(make_event(run_id, seq, "STRANDS_RUN_ERROR", {"error": str(exc)}))
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
