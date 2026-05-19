from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class AgentRole(str, Enum):
    queen = "queen"
    worker = "worker"
    judge = "judge"
    router = "router"


class AgentStatus(str, Enum):
    idle = "idle"
    running = "running"
    completed = "completed"
    failed = "failed"
    timed_out = "timed_out"


class TaskStatus(str, Enum):
    pending = "pending"
    assigned = "assigned"
    in_progress = "in_progress"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TaskPriority(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class SwarmFailureCause(str, Enum):
    worker_timeout = "worker_timeout"
    consensus_failed = "consensus_failed"
    hitl_rejected = "hitl_rejected"
    budget_exhausted = "budget_exhausted"
    internal_error = "internal_error"
    cancelled = "cancelled"


class SwarmStatus(str, Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class AgentSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=lambda: f"agent-{uuid.uuid4().hex[:8]}")
    name: str = Field(..., min_length=1, max_length=128)
    role: AgentRole = Field(default=AgentRole.worker)
    description: str = Field(default="", max_length=1024)
    model: str = Field(default="fake-stub")
    system_prompt: str = Field(default="", max_length=8192)
    max_tasks: int = Field(default=5, ge=1, le=100)
    timeout_seconds: float = Field(default=30.0, ge=1, le=600)


class AgentState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    agent_id: str
    status: AgentStatus = Field(default=AgentStatus.idle)
    current_task_id: str | None = Field(default=None)
    completed_tasks: list[str] = Field(default_factory=list)
    error: str | None = Field(default=None)
    started_at: datetime | None = Field(default=None)
    completed_at: datetime | None = Field(default=None)


class AgentVote(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    agent_id: str
    task_id: str
    round: int = Field(default=0, ge=0)
    approved: bool
    confidence: float = Field(default=1.0, ge=0, le=1)
    reasoning: str = Field(default="", max_length=4096)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ApprovalDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    approved: bool
    reason: str = Field(default="", max_length=2048)
    token_id: str | None = Field(default=None)
    decided_by: str = Field(default="auto")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class WorkerResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    worker_id: str
    task_id: str
    output: str = Field(default="", max_length=65536)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    error: str | None = Field(default=None)
    duration_seconds: float = Field(default=0.0, ge=0)
    cost_usd: float = Field(default=0.0, ge=0)
    token_count: int = Field(default=0, ge=0)
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = Field(default=None)


class QueenDirective(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    task_id: str
    prompt: str = Field(..., max_length=32768)
    assigned_worker_ids: list[str] = Field(default_factory=list)
    expected_output_count: int = Field(default=1, ge=1)
    context: dict[str, Any] = Field(default_factory=dict)
    priority: TaskPriority = Field(default=TaskPriority.medium)


class SwarmTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(default_factory=lambda: f"task-{uuid.uuid4().hex[:12]}")
    prompt: str = Field(..., max_length=32768)
    status: TaskStatus = Field(default=TaskStatus.pending)
    assigned_agent_id: str | None = Field(default=None)
    directive: QueenDirective | None = Field(default=None)
    result: WorkerResult | None = Field(default=None)
    votes: list[AgentVote] = Field(default_factory=list)
    approval: ApprovalDecision | None = Field(default=None)
    priority: TaskPriority = Field(default=TaskPriority.medium)
    parent_task_id: str | None = Field(default=None)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime | None = Field(default=None)
