"""ARC Time Travel — run replay & diff debugger (R101).

Record every state change per step (context, tool calls, model outputs, sandbox
decisions); replay forward/backward, branch from any step, and compare execution paths.

Builds on existing flight_recorder and run_diff infrastructure.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


class TimeTravelError(Exception):
    """Raised when time-travel operations fail (session not found, replay error, etc.)."""


TIME_TRAVEL_SCHEMA_VERSION = 1
MAX_SNAPSHOTS = 1000


class StepType(str, Enum):
    TOOL_CALL = "tool_call"
    MODEL_OUTPUT = "model_output"
    SANDBOX_DECISION = "sandbox_decision"
    CONTEXT_CHANGE = "context_change"
    HITL_GATE = "hitl_gate"
    CONSENSUS = "consensus"
    BRANCH_POINT = "branch_point"


@dataclass
class StateSnapshot:
    step_id: str
    step_type: StepType
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    context: dict[str, Any] = field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    model_outputs: list[dict[str, Any]] = field(default_factory=list)
    sandbox_decisions: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "step_type": self.step_type.value,
            "timestamp": self.timestamp,
            "context": self.context,
            "tool_calls": self.tool_calls,
            "model_outputs": self.model_outputs,
            "sandbox_decisions": self.sandbox_decisions,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StateSnapshot:
        return cls(
            step_id=data["step_id"],
            step_type=StepType(data["step_type"]),
            timestamp=data.get("timestamp", ""),
            context=data.get("context", {}),
            tool_calls=data.get("tool_calls", []),
            model_outputs=data.get("model_outputs", []),
            sandbox_decisions=data.get("sandbox_decisions", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Branch:
    branch_id: str
    parent_step_id: str
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    steps: list[StateSnapshot] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "branch_id": self.branch_id,
            "parent_step_id": self.parent_step_id,
            "created_at": self.created_at,
            "steps": [s.to_dict() for s in self.steps],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Branch:
        return cls(
            branch_id=data["branch_id"],
            parent_step_id=data["parent_step_id"],
            created_at=data.get("created_at", ""),
            steps=[StateSnapshot.from_dict(s) for s in data.get("steps", [])],
            metadata=data.get("metadata", {}),
        )


@dataclass
class TimeTravelSession:
    session_id: str
    run_id: str
    schema_version: int = TIME_TRAVEL_SCHEMA_VERSION
    steps: list[StateSnapshot] = field(default_factory=list)
    branches: list[Branch] = field(default_factory=list)
    current_step_index: int = -1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_step(self, step: StateSnapshot) -> int:
        self.steps.append(step)
        if len(self.steps) > MAX_SNAPSHOTS:
            dropped = len(self.steps) - MAX_SNAPSHOTS
            self.steps = self.steps[-MAX_SNAPSHOTS:]
            self.metadata["cap_warning"] = (
                f"snapshots capped at {MAX_SNAPSHOTS}; dropped {dropped} oldest"
            )
        self.current_step_index = len(self.steps) - 1
        return self.current_step_index

    def get_current_step(self) -> Optional[StateSnapshot]:
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def step_forward(self) -> Optional[StateSnapshot]:
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            return self.steps[self.current_step_index]
        return None

    def step_backward(self) -> Optional[StateSnapshot]:
        if self.current_step_index > 0:
            self.current_step_index -= 1
            return self.steps[self.current_step_index]
        return None

    def jump_to_step(self, index: int) -> Optional[StateSnapshot]:
        if 0 <= index < len(self.steps):
            self.current_step_index = index
            return self.steps[self.current_step_index]
        return None

    def branch_from_step(self, step_index: int, branch_id: str) -> Optional[Branch]:
        if 0 <= step_index < len(self.steps):
            parent_step = self.steps[step_index]
            branch = Branch(
                branch_id=branch_id,
                parent_step_id=parent_step.step_id,
                steps=self.steps[: step_index + 1].copy(),
            )
            self.branches.append(branch)
            return branch
        return None

    def get_branch(self, branch_id: str) -> Optional[Branch]:
        for branch in self.branches:
            if branch.branch_id == branch_id:
                return branch
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "run_id": self.run_id,
            "schema_version": self.schema_version,
            "steps": [s.to_dict() for s in self.steps],
            "branches": [b.to_dict() for b in self.branches],
            "current_step_index": self.current_step_index,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimeTravelSession:
        return cls(
            session_id=data["session_id"],
            run_id=data["run_id"],
            schema_version=data.get("schema_version", TIME_TRAVEL_SCHEMA_VERSION),
            steps=[StateSnapshot.from_dict(s) for s in data.get("steps", [])],
            branches=[Branch.from_dict(b) for b in data.get("branches", [])],
            current_step_index=data.get("current_step_index", -1),
            created_at=data.get("created_at", ""),
            metadata=data.get("metadata", {}),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            f.write("\n")

    @classmethod
    def load(cls, path: Path) -> TimeTravelSession:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


def create_session(session_id: str, run_id: str) -> TimeTravelSession:
    """Create a new time travel session."""
    return TimeTravelSession(session_id=session_id, run_id=run_id)


def load_session(path: Path) -> TimeTravelSession:
    """Load a time travel session from a file."""
    return TimeTravelSession.load(path)


def save_session(session: TimeTravelSession, path: Path) -> None:
    """Save a time travel session to a file."""
    session.save(path)


def compare_paths(session1: TimeTravelSession, session2: TimeTravelSession) -> dict[str, Any]:
    """Compare two execution paths and return a diff report."""
    steps1 = session1.steps
    steps2 = session2.steps

    min_len = min(len(steps1), len(steps2))
    diverged_at = None
    differences = []

    for i in range(min_len):
        s1 = steps1[i]
        s2 = steps2[i]
        if s1.step_type != s2.step_type:
            diverged_at = i
            differences.append(
                {
                    "step_index": i,
                    "type": "step_type_mismatch",
                    "left": s1.step_type.value,
                    "right": s2.step_type.value,
                }
            )
            break
        if s1.context != s2.context:
            differences.append(
                {
                    "step_index": i,
                    "type": "context_diff",
                    "left": s1.context,
                    "right": s2.context,
                }
            )
        if s1.tool_calls != s2.tool_calls:
            differences.append(
                {
                    "step_index": i,
                    "type": "tool_calls_diff",
                    "left_count": len(s1.tool_calls),
                    "right_count": len(s2.tool_calls),
                }
            )

    if len(steps1) != len(steps2):
        differences.append(
            {
                "type": "length_mismatch",
                "left_steps": len(steps1),
                "right_steps": len(steps2),
            }
        )

    return {
        "session1_id": session1.session_id,
        "session2_id": session2.session_id,
        "session1_steps": len(steps1),
        "session2_steps": len(steps2),
        "diverged_at": diverged_at,
        "differences": differences,
        "difference_count": len(differences),
        "paths_identical": len(differences) == 0,
    }


__all__ = [
    "TimeTravelError",
    "TIME_TRAVEL_SCHEMA_VERSION",
    "MAX_SNAPSHOTS",
    "StepType",
    "StateSnapshot",
    "Branch",
    "TimeTravelSession",
    "create_session",
    "load_session",
    "save_session",
    "compare_paths",
]
