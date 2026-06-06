"""Browser Use adapter for ARC Studio.

Browser Use (97K stars) enables AI agents to control web browsers.

API verified against browser-use (context7 /browser-use/browser-use):
  from browser_use import Agent
  agent = Agent(task=task, llm=llm)
  history = await agent.run(max_steps=100)  # AgentHistoryList
  history.final_result()   # final extracted content
  history.is_done()        # bool
  history.has_errors()     # bool
  history.urls()           # visited URLs

NOTE: Browser Use requires a running browser (Playwright/Chrome). This adapter
is detect-only by default; execution is triple-gated because it:
  - launches a real browser process
  - makes real LLM API calls
  - browses the open web

Gating:
  ARC_BROWSER_USE_ALLOW_COSTS=true   # dual-gate
  ARC_BROWSER_USE_ALLOW_BROWSER=true # explicit browser-launch gate
  Prompt/task from run_workflow inputs["prompt"] or inputs["task"]
"""

from __future__ import annotations

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
from ._shared import make_event
from ._static import dependency_evidence, import_evidence
from .base import DoctorAction, RuntimeAdapter
from . import browser_use_mapping  # noqa: F401 — registers AG-UI mapper on import

log = logging.getLogger(__name__)

_ALLOW_COSTS_ENV = "ARC_BROWSER_USE_ALLOW_COSTS"
_ALLOW_BROWSER_ENV = "ARC_BROWSER_USE_ALLOW_BROWSER"

try:
    from browser_use import Agent as _BrowserAgent  # noqa: F401 — patchable
except ImportError:
    _BrowserAgent = None  # type: ignore[assignment,misc]


def _installed() -> bool:
    return importlib.util.find_spec("browser_use") is not None


class BrowserUseAdapter(RuntimeAdapter):
    """Adapter for Browser Use browser-automation agent projects."""

    @property
    def adapter_id(self) -> str:
        return "browser-use"

    @property
    def adapter_name(self) -> str:
        return "Browser Use"

    def sdk_version(self) -> str:
        from .base import _sdk_version_for

        return _sdk_version_for("browser-use")

    def capabilities(self) -> RuntimeCapabilities:
        allow_costs = os.environ.get(_ALLOW_COSTS_ENV, "").strip().lower() == "true"
        allow_browser = os.environ.get(_ALLOW_BROWSER_ENV, "").strip().lower() == "true"
        can_run = _installed() and allow_costs and allow_browser
        return RuntimeCapabilities(
            can_inspect=True,
            can_run=can_run,
            can_export_workflow=True,
            can_export_schema=False,
            can_trace=False,
            can_stream_events=False,
        )

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        evidence: list[str] = []
        if _installed():
            evidence.append("browser_use installed")

        _, import_ev = import_evidence(workspace, ("from browser_use", "import browser_use"))
        _, dep_ev = dependency_evidence(workspace, ("browser-use", "browser_use"))
        evidence += import_ev + dep_ev

        if not evidence:
            return False, 0.0, []

        confidence = 0.5 if _installed() else 0.0
        if import_ev or dep_ev:
            confidence = min(confidence + 0.4, 1.0)
        return True, confidence, evidence

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        actions: list[DoctorAction] = []
        if not _installed():
            actions.append(
                DoctorAction(
                    id="install_browser_use",
                    label="Install browser-use",
                    description="pip install browser-use && playwright install chromium",
                    severity="warning",
                )
            )
        if not os.environ.get(_ALLOW_COSTS_ENV):
            actions.append(
                DoctorAction(
                    id="enable_costs",
                    label="Enable paid calls",
                    description=f"Set {_ALLOW_COSTS_ENV}=true (dual-gate)",
                    severity="info",
                )
            )
        if not os.environ.get(_ALLOW_BROWSER_ENV):
            actions.append(
                DoctorAction(
                    id="enable_browser",
                    label="Allow browser launch",
                    description=f"Set {_ALLOW_BROWSER_ENV}=true (explicit browser-launch gate)",
                    severity="info",
                )
            )
        return actions

    def export_workflow(self, workspace: Path):
        from ..protocol.schemas import NodeType, WorkflowInfo, WorkflowNode

        detected, _, evidence = self.detect(workspace)
        if not detected:
            return []
        return [
            WorkflowInfo(
                id=f"browser-use::{workspace.name}",
                name="browser-use-agent",
                runtime=self.adapter_id,
                nodes=[WorkflowNode(id="agent", label="Browser Agent", type=NodeType.AGENT)],
                edges=[],
                metadata={"evidence": evidence},
            )
        ]

    async def run_workflow(
        self,
        workflow_id: str,
        inputs: dict[str, Any],
        workspace: Path | None = None,
    ) -> RunRecord:
        require_dual_gate("BROWSER_USE")

        if os.environ.get(_ALLOW_BROWSER_ENV, "").strip().lower() != "true":
            raise GatingError(
                f"Browser Use requires {_ALLOW_BROWSER_ENV}=true "
                "(explicit gate: this adapter launches a real browser process)"
            )
        if _BrowserAgent is None:
            raise GatingError("browser-use is not installed: pip install browser-use")

        task = inputs.get("task") or inputs.get("prompt") or inputs.get("input") or str(inputs)
        run_id = str(uuid.uuid4())
        started = datetime.now(timezone.utc)
        events: list[RunEvent] = []
        seq = 0

        events.append(make_event(run_id, seq, "BROWSER_USE_RUN_START", {"task": task}))
        seq += 1

        try:
            agent = _BrowserAgent(task=task)
            history = await agent.run(max_steps=50)
            output = history.final_result() or ""
            if not output and history.extracted_content():
                output = "\n".join(c for c in history.extracted_content() if c)
            status = RunStatus.COMPLETED if history.is_done() else RunStatus.FAILED
            events.append(
                make_event(
                    run_id,
                    seq,
                    "BROWSER_USE_RUN_END",
                    {
                        "output": str(output),
                        "steps": history.number_of_steps(),
                        "urls": history.urls()[:5],
                        "has_errors": history.has_errors(),
                    },
                )
            )
        except Exception as exc:
            output = f"error: {exc}"
            events.append(make_event(run_id, seq, "BROWSER_USE_RUN_ERROR", {"error": str(exc)}))
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
            metadata={"inputs": inputs, "outputs": {"result": str(output)}},
        )
