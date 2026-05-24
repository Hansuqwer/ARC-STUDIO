"""LM Arena Runtime Adapter.

Wraps the Arena service as a standard ARC runtime adapter so that LM Arena
chat requests can be made through the existing `startRun` flow (CLI or daemon).

When the user selects `lmarena` as the runtime, this adapter translates
standard run inputs into an ArenaRequest and returns the result as a RunRecord.

Modes are inferred from the workflow_id:
  - arena-battle       → ArenaMode.BATTLE
  - arena-direct       → ArenaMode.DIRECT (default)
  - arena-code         → ArenaMode.CODE
  - arena-agent-preview → ArenaMode.AGENT_ARENA_PREVIEW
"""

from __future__ import annotations

import os
import uuid
from pathlib import Path
from typing import Any

from ..arena.models import ArenaMode, ArenaRequest, PrivacyLevel
from ..arena.service import arena_request, store_arena_run
from ..gating import GatingError
from ..protocol.capabilities import RuntimeCapabilities
from ..protocol.schemas import RunRecord, RunStatus
from ..security.profiles import enforce_profile, resolve_profile
from ..storage.jsonl import JsonlTraceStore
from .base import CapabilityReport, RuntimeAdapter

ARENA_MODES: dict[str, ArenaMode] = {
    "arena-battle": ArenaMode.BATTLE,
    "arena-direct": ArenaMode.DIRECT,
    "arena-code": ArenaMode.CODE,
    "arena-agent-preview": ArenaMode.AGENT_ARENA_PREVIEW,
}

DEFAULT_ARENA_MODE = ArenaMode.DIRECT
DEFAULT_ARENA_MODEL = "gpt-4o-mini-2024-07-18"


class LmarenaAdapter(RuntimeAdapter):
    """Adapter that routes run requests through the LM Arena service."""

    @property
    def adapter_id(self) -> str:
        return "lmarena"

    @property
    def adapter_name(self) -> str:
        return "LM Arena"

    def capabilities(self) -> RuntimeCapabilities:
        live = os.environ.get("ARC_ALLOW_LIVE_ARENA", "").lower() in {"true", "1"}
        return RuntimeCapabilities(
            can_inspect=False,
            can_run=True,
            can_trace=True,
            can_replay=False,
            can_export_schema=False,
            can_export_workflow=False,
            can_stream_events=False,
            can_audit=False,
            can_checkpoint=False,
            can_resume=False,
            can_fork=False,
            can_diff=False,
            can_eval=False,
            requires_paid_calls=live,
            requires_network=live,
            requires_shell=False,
            requires_secrets=live,
        )

    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        """Always detected — the Arena stub backend is always available."""
        mode = (
            "live mode"
            if os.environ.get("ARC_ALLOW_LIVE_ARENA", "").lower() in {"true", "1"}
            else "stub mode"
        )
        return True, 0.5, [f"Arena runtime available ({mode})"]

    def capability_report(self, workspace: Path) -> CapabilityReport:
        live = os.environ.get("ARC_ALLOW_LIVE_ARENA", "").lower() in {"true", "1"}
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=True,
            can_run=True,
            availability="runnable",
            reason=None,
            detected_artifacts=["Arena runtime is always available"],
            required_env=["ARC_LMARENA_RUN_BACKEND", "ARC_LMARENA_ALLOW_COSTS"] if live else [],
            requires_paid_calls=live,
            version=None,
            doctor_actions=[],
        )

    async def run_workflow(
        self, workflow_id: str, inputs: dict[str, Any] | None = None
    ) -> RunRecord:
        """Execute an Arena request and return the run record.

        Inputs accepted:
          - prompt (str): the user prompt/question
          - arena_mode (str, optional): one of battle/direct/code/agent-arena-preview
            (inferred from workflow_id if not set)
          - arena_model (str, optional): model ID string
          - allow_paid_calls (bool, default False)
        """
        inputs = inputs or {}
        workspace_raw = inputs.get("workspace", "")
        workspace = Path(workspace_raw) if workspace_raw else Path.cwd()
        prompt = str(inputs.get("prompt", "")).strip()
        allow_paid_calls = bool(inputs.get("allow_paid_calls", False))
        profile_id = str(inputs.get("profile_id", "local-safe"))
        profile = resolve_profile(profile_id)
        if allow_paid_calls and not profile.allow_paid_calls:
            raise GatingError(f"Profile '{profile_id}' does not allow paid calls.")
        enforce_profile(profile, self.adapter_id)

        # Determine mode from workflow_id or explicit input
        raw_mode = str(inputs.get("arena_mode", "")).strip().lower()
        if raw_mode:
            try:
                mode = ArenaMode(raw_mode)
            except ValueError:
                mode = DEFAULT_ARENA_MODE
        else:
            mode = ARENA_MODES.get(workflow_id, DEFAULT_ARENA_MODE)

        model = str(inputs.get("arena_model", inputs.get("model", DEFAULT_ARENA_MODEL))).strip()
        if not model:
            model = DEFAULT_ARENA_MODEL

        # Build ArenaRequest
        req = ArenaRequest(
            mode=mode,
            prompt=prompt,
            workspace=str(workspace),
            model=model,
            privacy=PrivacyLevel.PRIVATE,
            allow_paid_calls=allow_paid_calls,
            profile_id=profile_id,
        )

        # Process through arena service
        response = arena_request(workspace, req)
        if not response.run_id:
            response.run_id = f"arena-{uuid.uuid4().hex[:12]}"

        # Store the run
        store = JsonlTraceStore(workspace / ".arc" / "traces")
        run = store_arena_run(store, response, req)

        # Mirror RunRecord fields for CLI output
        return RunRecord(
            id=run.id,
            workflow_id=workflow_id,
            runtime="lmarena",
            status=RunStatus.COMPLETED,
            started_at=run.started_at,
            ended_at=run.ended_at,
            events=run.events,
            metadata={
                **run.metadata,
                "adapter": self.adapter_id,
                "arena_mode": mode.value,
                "arena_model": model,
            },
        )
