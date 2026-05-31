from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .config import SwarmGraphConfig
from .models import AgentSpec, AgentState, AgentStatus, SwarmStatus, SwarmTask, TaskStatus


class SwarmCheckpoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=lambda: f"ckpt-{uuid.uuid4().hex[:12]}")
    round: int = Field(default=0, ge=0)
    config: SwarmGraphConfig
    agents: dict[str, AgentState] = Field(default_factory=dict)
    tasks: dict[str, SwarmTask] = Field(default_factory=dict)
    status: SwarmStatus = Field(default=SwarmStatus.pending)
    accumulated_cost_usd: float = Field(default=0.0, ge=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    # Serialized event history accumulated up to and including this checkpoint.
    # Each entry is the dict produced by SwarmGraphEvent.to_dict().
    events: list[dict[str, Any]] = Field(default_factory=list)


class SwarmState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"swarm-{uuid.uuid4().hex[:12]}")
    config: SwarmGraphConfig
    agents: dict[str, AgentState] = Field(default_factory=dict)
    tasks: dict[str, SwarmTask] = Field(default_factory=dict)
    spec_map: dict[str, AgentSpec] = Field(default_factory=dict)
    status: SwarmStatus = Field(default=SwarmStatus.pending)
    current_round: int = Field(default=0, ge=0)
    accumulated_cost_usd: float = Field(default=0.0, ge=0)
    error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    checkpoint_history: list[SwarmCheckpoint] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    # In-memory mirror of all events emitted during this run (or seeded from a
    # checkpoint on resume). Each entry is the dict produced by
    # SwarmGraphEvent.to_dict(). The runner keeps the typed list; state keeps
    # the serializable copy for checkpoint persistence.
    events: list[dict[str, Any]] = Field(default_factory=list)

    def save_checkpoint(self) -> SwarmCheckpoint:
        ckpt = SwarmCheckpoint(
            round=self.current_round,
            config=self.config,
            agents=copy.deepcopy(self.agents),
            tasks=copy.deepcopy(self.tasks),
            status=self.status,
            accumulated_cost_usd=self.accumulated_cost_usd,
            events=list(self.events),
        )
        self.checkpoint_history.append(ckpt)
        return ckpt

    def restore_checkpoint(self, ckpt_id: str) -> bool:
        for ckpt in self.checkpoint_history:
            if ckpt.id == ckpt_id:
                self.restore_checkpoint_object(ckpt)
                return True
        return False

    def restore_checkpoint_object(self, ckpt: SwarmCheckpoint) -> None:
        self.current_round = ckpt.round
        self.config = ckpt.config
        self.agents = copy.deepcopy(ckpt.agents)
        self.tasks = copy.deepcopy(ckpt.tasks)
        self.status = ckpt.status
        self.accumulated_cost_usd = ckpt.accumulated_cost_usd
        self.events = list(ckpt.events)
        self.updated_at = datetime.now(timezone.utc)

    @classmethod
    def from_checkpoint(cls, checkpoint: SwarmCheckpoint) -> SwarmState:
        """Rehydrate a SwarmState from a durable checkpoint.

        The resumed state continues from the checkpoint's round, tasks, agents,
        config, and accumulated cost rather than starting fresh. The checkpoint
        itself is preserved as the first entry of the resumed history so the
        lineage is auditable.

        Idempotency: tasks that already reached a terminal state
        (``completed`` / ``failed`` / ``cancelled``) are preserved as-is and are
        never re-dispatched on resume. Tasks left mid-flight (``assigned`` /
        ``in_progress``) when the checkpoint was taken are reset to ``pending``
        so resume re-runs exactly those, and only those.
        """
        tasks = copy.deepcopy(checkpoint.tasks)
        requeued: list[str] = []
        for task in tasks.values():
            if task.status in (TaskStatus.assigned, TaskStatus.in_progress):
                task.status = TaskStatus.pending
                requeued.append(task.id)

        state = cls(
            config=checkpoint.config,
            agents=copy.deepcopy(checkpoint.agents),
            tasks=tasks,
            status=checkpoint.status,
            current_round=checkpoint.round,
            accumulated_cost_usd=checkpoint.accumulated_cost_usd,
            events=list(checkpoint.events),
        )
        state.checkpoint_history.append(checkpoint)
        state.metadata["resumed_from"] = checkpoint.id
        state.metadata["resumed_from_round"] = checkpoint.round
        state.metadata["resumed_requeued_tasks"] = requeued
        return state

    def fork(self, new_config: SwarmGraphConfig | None = None) -> SwarmState:
        return SwarmState(
            config=new_config or self.config,
            agents=copy.deepcopy(self.agents),
            tasks=copy.deepcopy(self.tasks),
            spec_map=copy.deepcopy(self.spec_map),
            status=SwarmStatus.pending,
            accumulated_cost_usd=0.0,
        )

    def get_pending_tasks(self) -> list[SwarmTask]:
        return [t for t in self.tasks.values() if t.status == TaskStatus.pending]

    def get_idle_agents(self) -> list[tuple[str, AgentState]]:
        return [(aid, a) for aid, a in self.agents.items() if a.status == AgentStatus.idle]

    def all_tasks_completed(self) -> bool:
        if not self.tasks:
            return False
        return all(
            t.status in (TaskStatus.completed, TaskStatus.failed, TaskStatus.cancelled)
            for t in self.tasks.values()
        )

    def failed_tasks(self) -> list[SwarmTask]:
        return [t for t in self.tasks.values() if t.status == TaskStatus.failed]
