"""Replay capability schema for LangGraph and other adapters (Phase 28 / R21)."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class ReplayCapability(BaseModel):
    """Replay capability analysis for a run.

    Describes what can and cannot be replayed for a given run,
    with warnings about limitations and safety concerns.
    """

    run_id: str = Field(..., description="Run ID being analyzed")
    runtime: str = Field(..., description="Runtime adapter (e.g., 'langgraph')")

    # Core capability flags
    can_replay_trace: bool = Field(
        default=True,
        description="Whether the trace can be replayed (inspect-only)",
    )
    can_resume_checkpoint: bool = Field(
        default=False,
        description="Whether execution can resume from a checkpoint",
    )
    requires_thread_id: bool = Field(
        default=False,
        description="Whether resuming requires a thread ID",
    )
    side_effects_wrapped: bool = Field(
        default=False,
        description="Whether side effects are properly wrapped/declared idempotent",
    )

    # Determinism level
    determinism_level: str = Field(
        default="inspect_only",
        description="Level of replay determinism: 'exact', 'simulated', 'inspect_only', 'unsafe'",
    )

    # Checkpointer detection
    has_checkpointer: bool = Field(
        default=False,
        description="Whether a checkpointer was detected in the graph",
    )
    checkpointer_type: Optional[str] = Field(
        default=None,
        description="Type of checkpointer if detected (e.g., 'MemorySaver', 'SqliteSaver')",
    )

    # Thread ID detection
    thread_id_detected: bool = Field(
        default=False,
        description="Whether a thread ID was used in the run",
    )
    thread_id: Optional[str] = Field(
        default=None,
        description="Thread ID if detected",
    )

    # Warnings and limitations
    warnings: list[str] = Field(
        default_factory=list,
        description="Warnings about replay limitations and safety concerns",
    )

    # Human-readable report
    report: str = Field(
        default="",
        description="Human-readable report of replay capabilities",
    )

    def is_resumable(self) -> bool:
        """Check if the run is resumable (not just inspect-only)."""
        return self.can_resume_checkpoint and self.has_checkpointer

    def is_safe_to_replay(self) -> bool:
        """Check if replay is safe (no unhandled side effects)."""
        return self.side_effects_wrapped or self.determinism_level == "exact"

    def get_capability_summary(self) -> str:
        """Get a one-line summary of replay capabilities."""
        if self.is_resumable():
            if self.is_safe_to_replay():
                return "Resumable with safe replay"
            else:
                return "Resumable but may have side effects"
        elif self.can_replay_trace:
            return "Inspect-only (no checkpoint resume)"
        else:
            return "Cannot replay"

    def add_warning(self, warning: str) -> None:
        """Add a warning to the warnings list."""
        if warning not in self.warnings:
            self.warnings.append(warning)

    def generate_report(self) -> str:
        """Generate a human-readable report of replay capabilities."""
        lines = [
            f"Replay Capability Report for Run: {self.run_id}",
            f"Runtime: {self.runtime}",
            "",
            "Capabilities:",
            f"  - Trace Replay: {'✓' if self.can_replay_trace else '✗'} (inspect-only)",
            f"  - Checkpoint Resume: {'✓' if self.can_resume_checkpoint else '✗'}",
            f"  - Thread ID Required: {'✓' if self.requires_thread_id else '✗'}",
            f"  - Side Effects Wrapped: {'✓' if self.side_effects_wrapped else '✗'}",
            f"  - Determinism Level: {self.determinism_level}",
            "",
            "Detection:",
            f"  - Checkpointer: {'✓' if self.has_checkpointer else '✗'}",
        ]

        if self.checkpointer_type:
            lines.append(f"  - Checkpointer Type: {self.checkpointer_type}")

        if self.thread_id_detected:
            lines.append(f"  - Thread ID: {self.thread_id}")

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            for warning in self.warnings:
                lines.append(f"  ⚠ {warning}")

        lines.append("")
        lines.append(f"Summary: {self.get_capability_summary()}")

        return "\n".join(lines)
