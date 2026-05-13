"""
ARC Runtime Adapter Base Class

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
    WorkspaceInfo, WorkflowInfo, SchemaInfo, RunRecord, RunEvent, RuntimeCapabilities
)

RuntimeAvailability = Literal[
    "runnable",
    "detected_not_runnable",
    "missing_dependency",
    "missing_export_target",
    "paid_calls_blocked",
    "not_detected",
]


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


class RuntimeAdapter(abc.ABC):
    """
    Abstract base for all ARC runtime adapters.

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
        can_run = self.capabilities().can_run
        return CapabilityReport(
            runtime_id=self.adapter_id,
            detected=detected,
            can_run=can_run,
            availability="runnable" if can_run else ("detected_not_runnable" if detected else "not_detected"),
            reason=None if can_run else "Runtime is detected but does not expose a runnable path.",
            detected_artifacts=evidence,
        )

    @abc.abstractmethod
    def detect(self, workspace: Path) -> tuple[bool, float, list[str]]:
        """
        Detect whether this adapter's runtime is present in the workspace.

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

    async def run_workflow(self, workflow_id: str, inputs: dict[str, Any] | None = None) -> RunRecord:
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
