"""Letta (MemGPT) adapter for ARC Studio.

Letta is a server-backed stateful-agent framework. Unlike other adapters,
run_workflow sends a message to an existing agent on a running Letta server
rather than loading code from the workspace.

API verified against letta-client v1.12.1 (context7 /letta-ai/letta-python):
  from letta_client import Letta
  client = Letta(api_key=..., base_url=...)  # cloud or local
  response = client.agents.messages.create(
      agent_id=agent_id,
      messages=[{"role": "user", "content": prompt}],
  )
  for msg in response.messages:
      if msg.message_type == "assistant_message":
          print(msg.content)

Gating:
  ARC_LETTA_AGENT_ID=agent-xxx   # required — target agent on the server
  ARC_LETTA_ALLOW_COSTS=true     # dual-gate
  LETTA_API_KEY or LETTA_BASE_URL  # at least one must be set
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
from . import letta_mapping  # noqa: F401 — registers AG-UI mapper on import

log = logging.getLogger(__name__)

try:
    from letta_client import Letta as _LettaClient  # noqa: F401 — patchable in tests
except ImportError:
    _LettaClient = None  # type: ignore[assignment,misc]

_AGENT_ID_ENV = "ARC_LETTA_AGENT_ID"
_ALLOW_ENV = "ARC_LETTA_ALLOW_COSTS"


def _letta_installed() -> bool:
    return importlib.util.find_spec("letta_client") is not None


def _server_configured() -> bool:
    return bool(os.environ.get("LETTA_API_KEY") or os.environ.get("LETTA_BASE_URL"))


class LettaAdapter(RuntimeAdapter):
    """Adapter for Letta (MemGPT) stateful-agent projects."""

    @property
    def adapter_id(self) -> str:
        return "letta"

    @property
    def adapter_name(self) -> str:
        return "Letta (MemGPT)"

    def sdk_version(self) -> str:
        from .base import _sdk_version_for

        return _sdk_version_for("letta")

    def capabilities(self) -> RuntimeCapabilities:
        agent_id = os.environ.get(_AGENT_ID_ENV)
        allow_costs = os.environ.get(_ALLOW_ENV, "").strip().lower() == "true"
        can_run = _letta_installed() and bool(agent_id) and allow_costs and _server_configured()
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
        if _letta_installed():
            evidence.append("letta_client installed")
        if os.environ.get("LETTA_API_KEY"):
            evidence.append("LETTA_API_KEY set")
        if os.environ.get("LETTA_BASE_URL"):
            evidence.append("LETTA_BASE_URL set")

        _, import_ev = import_evidence(workspace, ("from letta", "import letta_client"))
        _, dep_ev = dependency_evidence(workspace, ("letta-client", "letta_client"))
        evidence += import_ev + dep_ev

        # .af agent files
        af_files = list(workspace.glob("**/*.af"))
        evidence += [str(f.relative_to(workspace)) for f in af_files[:3]]

        if not evidence:
            return False, 0.0, []

        confidence = 0.0
        if _letta_installed():
            confidence += 0.4
        if _server_configured():
            confidence += 0.4
        if import_ev or dep_ev or af_files:
            confidence += 0.2
        confidence = min(confidence, 1.0)

        return True, confidence, evidence

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        actions: list[DoctorAction] = []
        if not _letta_installed():
            actions.append(
                DoctorAction(
                    id="install_letta",
                    label="Install letta-client",
                    description="pip install letta-client",
                    severity="warning",
                )
            )
        if not _server_configured():
            actions.append(
                DoctorAction(
                    id="set_server",
                    label="Configure Letta server",
                    description="Set LETTA_API_KEY (cloud) or LETTA_BASE_URL (local server)",
                    severity="warning",
                )
            )
        if not os.environ.get(_AGENT_ID_ENV):
            actions.append(
                DoctorAction(
                    id="set_agent_id",
                    label="Set agent ID",
                    description=f"Set {_AGENT_ID_ENV}=agent-<id> (get from Letta UI or API)",
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
        from ..protocol.schemas import WorkflowInfo, WorkflowNode, NodeType

        detected, _, evidence = self.detect(workspace)
        if not detected:
            return []
        agent_id = os.environ.get(_AGENT_ID_ENV, "")
        return [
            WorkflowInfo(
                id=f"letta::{agent_id or workspace.name}",
                name=agent_id or "letta-agent",
                runtime=self.adapter_id,
                nodes=[WorkflowNode(id="agent", label="Letta Agent", type=NodeType.AGENT)],
                edges=[],
                metadata={"evidence": evidence, "agent_id": agent_id},
            )
        ]

    async def run_workflow(
        self,
        workflow_id: str,
        inputs: dict[str, Any],
        workspace: Path | None = None,
    ) -> RunRecord:
        require_dual_gate("LETTA")

        agent_id = os.environ.get(_AGENT_ID_ENV)
        if not agent_id:
            raise GatingError(
                f"{_AGENT_ID_ENV} is not set. Set it to the Letta agent ID (e.g. agent-d9be0846)."
            )
        if not _server_configured():
            raise GatingError("Set LETTA_API_KEY or LETTA_BASE_URL to connect to a Letta server.")

        if _LettaClient is None:
            raise GatingError("letta-client is not installed: pip install letta-client")
        Letta = _LettaClient
        run_id = str(uuid.uuid4())
        started = datetime.now(timezone.utc)
        events: list[RunEvent] = []
        seq = 0

        prompt = inputs.get("prompt") or inputs.get("input") or str(inputs)
        events.append(
            make_event(run_id, seq, "LETTA_RUN_START", {"agent_id": agent_id, "prompt": prompt})
        )
        seq += 1

        client_kwargs: dict[str, Any] = {}
        if api_key := os.environ.get("LETTA_API_KEY"):
            client_kwargs["api_key"] = api_key
        if base_url := os.environ.get("LETTA_BASE_URL"):
            client_kwargs["base_url"] = base_url

        try:
            client = Letta(**client_kwargs)
            response = client.agents.messages.create(
                agent_id=agent_id,
                messages=[{"role": "user", "content": prompt}],
            )
            # Extract assistant message text
            output_parts = [
                msg.content
                for msg in response.messages
                if getattr(msg, "message_type", None) == "assistant_message"
                and getattr(msg, "content", None)
            ]
            output = "\n".join(output_parts) if output_parts else str(response.messages)
            events.append(make_event(run_id, seq, "LETTA_RUN_END", {"output": output}))
            status = RunStatus.COMPLETED
        except Exception as exc:
            output = f"error: {exc}"
            events.append(make_event(run_id, seq, "LETTA_RUN_ERROR", {"error": str(exc)}))
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
            metadata={"inputs": inputs, "outputs": {"result": output}, "agent_id": agent_id},
        )
