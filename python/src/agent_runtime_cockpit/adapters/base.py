"""ARC Runtime Adapter Base Class.

All runtime adapters (SwarmGraph, LangGraph, CrewAI, etc.) must implement this interface.
The interface is intentionally minimal and stable — adapters may raise NotImplementedError
for features they don't support, and must report capabilities honestly.
"""

from __future__ import annotations

import abc
from pathlib import Path
from typing import Any, AsyncIterator, Literal

from pydantic import BaseModel, Field

from ..protocol.schemas import (
    RunEvent,
    RunRecord,
    RuntimeCapabilities,
    SchemaInfo,
    WorkflowInfo,
    WorkspaceInfo,
)

RuntimeAvailability = Literal[
    "runnable",
    "detected_not_runnable",
    "missing_dependency",
    "missing_export_target",
    "paid_calls_blocked",
    "not_detected",
]

CapabilityTestLevel = Literal["unknown", "fake_offline", "gated_local_real", "provider_backed"]


class DoctorAction(BaseModel):
    """A suggested action to make this runtime runnable."""

    id: str
    label: str
    description: str
    command: str = ""
    safe_to_auto_run: bool = False


class CapabilityReport(BaseModel):
    runtime_id: str
    detected: bool
    can_run: bool
    availability: RuntimeAvailability
    reason: str | None = None
    detected_artifacts: list[str] = Field(default_factory=list)
    required_env: list[str] = Field(default_factory=list)
    version: str | None = None
    requires_paid_calls: bool = False
    doctor_actions: list[DoctorAction] = Field(default_factory=list)

    # Evidence classification. Defaults preserve old reports while new runtimes can
    # distinguish offline scaffolds, gated local-real paths, and provider-backed runs.
    test_level: CapabilityTestLevel = "unknown"
    fake_offline_supported: bool = False
    local_real_gated: bool = False
    local_real_available: bool = False
    provider_backed: bool = False

    # Cockpit primitive flags (mirrors RuntimeCapabilities)
    can_emit_contract: bool = False
    can_emit_receipt: bool = False
    can_emit_autopsy: bool = False
    can_emit_evidence: bool = False
    has_stable_ids: bool = False


class RuntimeAdapter(abc.ABC):
    """Abstract base for all ARC runtime adapters.

    Implementation rules:
    - capabilities() must never lie (no false positives).
    - detect() must check for actual project files, not just claim success.
    - Unsupported operations must raise NotImplementedError, not return fake data.
    - All methods that read files must handle missing/corrupt files gracefully.
    """

    @property
    @abc.abstractmethod
    def adapter_id(self) -> str:
        """Unique adapter identifier, e.g. 'swarmgraph', 'langgraph'."""
        ...

    @property
    @abc.abstractmethod
    def adapter_name(self) -> str:
        """Human-readable adapter name."""
        ...

    @abc.abstractmethod
    def capabilities(self) -> RuntimeCapabilities:
        """Return HONEST capabilities for this adapter."""
        ...

    def capability_report(self, workspace: Path) -> CapabilityReport:
        """Return runnable status with a reason for UI/router decisions."""
        detected, _, evidence = self.detect(workspace)
        caps = self.capabilities()
        can_run = caps.can_run
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=detected,
            can_run=can_run,
            availability="runnable"
            if can_run
            else ("detected_not_runnable" if detected else "not_detected"),
            reason=None if can_run else "Runtime is detected but does not expose a runnable path.",
            detected_artifacts=evidence,
            doctor_actions=self._doctor_actions(workspace),
            can_emit_contract=caps.can_emit_contract,
            can_emit_receipt=caps.can_emit_receipt,
            can_emit_autopsy=caps.can_emit_autopsy,
            can_emit_evidence=caps.can_emit_evidence,
            has_stable_ids=caps.has_stable_ids,
        )

    def _doctor_actions(self, workspace: Path) -> list[DoctorAction]:
        """Subclasses may override to return runtime-specific fix actions."""
        return []

    def sdk_version(self) -> str:
        """Return the SDK version string for this adapter's underlying library.

        Default returns 'unknown'. Override in subclasses to return the actual
        installed package version via importlib.metadata.version or __version__.
        """
        return "unknown"

    @abc.abstractmethod
    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        """Detect whether this adapter's runtime is present in the workspace.

        Returns:
            (detected, confidence_0_to_1, evidence_list)

        Rules:
        - confidence must be derived from real evidence, not hardcoded.
        - evidence must list actual file names or config keys found.
        - Never return (True, ...) if no evidence was found.

        """
        ...

    def inspect_workspace(self, workspace: Path) -> WorkspaceInfo:
        """Inspect the workspace and return runtime info."""
        raise NotImplementedError(f"{self.adapter_id} does not implement inspect_workspace")

    def export_workflow(self, workspace: Path) -> list[WorkflowInfo]:
        """Export workflow topology from the workspace."""
        raise NotImplementedError(f"{self.adapter_id} does not implement export_workflow")

    def export_schemas(self, workspace: Path) -> list[SchemaInfo]:
        """Export JSON schemas from the workspace."""
        raise NotImplementedError(f"{self.adapter_id} does not implement export_schemas")

    async def run_workflow(
        self, workflow_id: str, inputs: dict[str, Any] | None = None
    ) -> RunRecord:
        """Execute a workflow and return a run record."""
        raise NotImplementedError(f"{self.adapter_id} does not implement run_workflow")

    async def stream_events(self, run_id: str) -> AsyncIterator[RunEvent]:
        """Stream run events (AG-UI compatible)."""
        raise NotImplementedError(f"{self.adapter_id} does not implement stream_events")
        yield  # make it a generator

    def get_run(self, run_id: str) -> RunRecord:
        """Get a completed or in-progress run record."""
        raise NotImplementedError(f"{self.adapter_id} does not implement get_run")

    def list_runs(self, workspace: Path) -> list[RunRecord]:
        """List all runs for a workspace."""
        raise NotImplementedError(f"{self.adapter_id} does not implement list_runs")

    # ── Capability Card enforcement helper (D-01 wiring) ──────────────────
    def enforce_capability_card(
        self,
        *,
        workflow_id: str,
        workspace: Path,
    ) -> dict:
        """Look up and enforce the adapter-level Capability Card.

        Returns a dict suitable for emitting as a CAPABILITY_CARD_DECISION
        event payload. Never raises on the default (warn) mode. Adapters MUST
        call this once at the top of run_workflow() to satisfy the wiring
        contract from EXECUTION_PROMPT.md Item 1.
        """
        import os
        from ..capabilities.enforcement import enforce_card, resolve_mode
        from ..capabilities.registry import CardRegistry

        env = {"ARC_CAPABILITIES_ENFORCE": os.environ.get("ARC_CAPABILITIES_ENFORCE", "")}
        mode = resolve_mode(env=env)

        try:
            registry = CardRegistry(workspace=workspace)
            card_id = f"adapter::{self.adapter_id}"
            card = registry.load(card_id)
        except Exception:
            card = None

        result = enforce_card(card=card, signed=None, mode=mode)
        return {
            "action": "run_workflow",
            "workflow_id": workflow_id,
            "adapter_id": self.adapter_id,
            "decision": result.decision,
            "reason": result.reason,
            "card_id": result.card_id,
            "card_hash": result.card_hash,
            "mode": mode,
            "correlation_id": result.correlation_id,
            "details": result.details,
        }


def _sdk_version_for(package_name: str) -> str:
    """Return installed version of *package_name*, or 'unknown' if not installed."""
    try:
        from importlib.metadata import version

        return version(package_name)
    except Exception:
        return "unknown"
