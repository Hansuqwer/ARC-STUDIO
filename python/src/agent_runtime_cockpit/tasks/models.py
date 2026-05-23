"""Task models and state machine for async execution."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Task execution status."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """Type of task operation."""

    RUN = "run"
    TRACE = "trace"
    AUDIT = "audit"


class Task(BaseModel):
    """Task model for async execution with retry support."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: TaskType
    operation: str
    params: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
    expires_at: str = Field(
        default_factory=lambda: (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    )
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: Optional[str] = None

    def can_transition_to(self, new_status: TaskStatus) -> bool:
        """Check if transition to new status is valid."""
        valid_transitions = {
            TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.RUNNING: {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            },
            TaskStatus.FAILED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
            TaskStatus.COMPLETED: set(),  # Terminal state
            TaskStatus.CANCELLED: set(),  # Terminal state
        }
        return new_status in valid_transitions.get(self.status, set())

    def transition_to(self, new_status: TaskStatus) -> None:
        """Transition to new status with validation."""
        if not self.can_transition_to(new_status):
            raise ValueError(f"Invalid transition from {self.status} to {new_status}")
        self.status = new_status

        # Update timestamps
        now = datetime.now(timezone.utc).isoformat()
        if new_status == TaskStatus.RUNNING and not self.started_at:
            self.started_at = now
        elif new_status in {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.CANCELLED,
        }:
            self.ended_at = now

    def should_retry(self) -> bool:
        """Check if task should be retried."""
        return self.status == TaskStatus.FAILED and self.retry_count < self.max_retries

    def calculate_next_retry(self) -> str:
        """Calculate next retry time with exponential backoff."""
        # Exponential backoff: 2^retry_count seconds
        delay_seconds = 2**self.retry_count
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=delay_seconds)
        return next_retry.isoformat()

    def is_expired(self) -> bool:
        """Check if task has expired."""
        expires = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) > expires

    def to_dict(self) -> dict[str, Any]:
        """Convert task to dictionary."""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """Create task from dictionary."""
        return cls.model_validate(data)
