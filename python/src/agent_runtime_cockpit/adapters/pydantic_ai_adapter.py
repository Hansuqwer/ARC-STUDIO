"""Pydantic AI RuntimeAdapter for ARC Studio.

Wires the existing pydantic_ai detection/export/runner package into the
RuntimeAdapter contract.

Run API (verified pydantic_ai v1.106):
  result = agent.run_sync(prompt)   → RunResult
  str(result.output)                → text output

Gating:
  ARC_PYDANTIC_AI_EXPORT=module:attr   # export target
  ARC_PYDANTIC_AI_ALLOW_COSTS=true     # dual-gate for paid calls

Use TestModel for offline testing:
  from pydantic_ai.models.test import TestModel
  agent = Agent(model=TestModel())
"""

from __future__ import annotations

import importlib
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
from .base import DoctorAction, RuntimeAdapter
from .pydantic_ai import PydanticAIDetectionResult, detect_pydantic_ai, export_pydantic_ai_agents
from .pydantic_ai.runner import PydanticAIEventHandler
from . import pydantic_ai_mapping  # noqa: F401 — registers AG-UI mapper on import

log = logging.getLogger(__name__)

_EXPORT_ENV = "ARC_PYDANTIC_AI_EXPORT"
_ALLOW_ENV = "ARC_PYDANTIC_AI_ALLOW_COSTS"


def _pydantic_ai_installed() -> tuple[bool, str | None]:
    spec = importlib.util.find_spec("pydantic_ai")
    if spec is None:
        return False, None
    try:
        import pydantic_ai as _p

        return True, getattr(_p, "__version__", None)
    except Exception:
        return True, None


class PydanticAIAdapter(RuntimeAdapter):
    """Adapter for Pydantic AI agent projects."""

    @property
    def adapter_id(self) -> str:
        return "pydantic-ai"

    @property
    def adapter_name(self) -> str:
        return "Pydantic AI"

    def sdk_version(self) -> str:
        from .base import _sdk_version_for

        return _sdk_version_for("pydantic-ai")

    def capabilities(self) -> RuntimeCapabilities:
        installed, _ = _pydantic_ai_installed()
        export_set = bool(os.environ.get(_EXPORT_ENV))
        allow_costs = os.environ.get(_ALLOW_ENV, "").strip().lower() == "true"
        return RuntimeCapabilities(
            can_inspect=True,
            can_run=installed and export_set and allow_costs,
            can_export_workflow=True,
            can_export_schema=False,
            can_trace=False,
            can_stream_events=False,
        )

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        result: PydanticAIDetectionResult = detect_pydantic_ai(workspace)
        return result.detected, result.confidence, result.evidence

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        installed, _ = _pydantic_ai_installed()
        actions: list[DoctorAction] = []
        if not installed:
            actions.append(
                DoctorAction(
                    id="install_pydantic_ai",
                    label="Install pydantic-ai",
                    description="pip install pydantic-ai",
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
        return export_pydantic_ai_agents(workspace)

    async def run_workflow(
        self,
        workflow_id: str,
        inputs: dict[str, Any],
        workspace: Path | None = None,
    ) -> RunRecord:
        require_dual_gate("PYDANTIC_AI")

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

        def _emit(rid: str, event_type: str, data: dict) -> None:
            nonlocal seq
            events.append(make_event(rid, seq, event_type, data))
            seq += 1

        try:
            with workspace_import_path(ws):
                mod = importlib.import_module(module_name)
            agent = getattr(mod, attr_name)
        except Exception as exc:
            raise GatingError(f"Failed to load {_EXPORT_ENV}={target!r}: {exc}") from exc

        handler = PydanticAIEventHandler(run_id, _emit)
        agent_name = getattr(agent, "name", attr_name)
        prompt = inputs.get("prompt") or inputs.get("input") or str(inputs)

        handler.on_run_start(agent_name, {"prompt": prompt})
        try:
            result = agent.run_sync(prompt)
            output = str(getattr(result, "output", result))
            handler.on_run_end(agent_name, output)
            status = RunStatus.COMPLETED
        except Exception as exc:
            output = f"error: {exc}"
            handler.on_run_error(agent_name, exc)
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
