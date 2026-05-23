"""Tests for task models and state machine."""

from datetime import datetime, timedelta, timezone

import pytest

from agent_runtime_cockpit.tasks.models import Task, TaskStatus, TaskType


def test_task_creation_defaults():
    """Test task creation with default values."""
    task = Task(type=TaskType.RUN, operation="test_operation")

    assert task.id is not None
    assert len(task.id) > 0
    assert task.type == TaskType.RUN
    assert task.operation == "test_operation"
    assert task.params == {}
    assert task.status == TaskStatus.PENDING
    assert task.result is None
    assert task.error is None
    assert task.created_at is not None
    assert task.started_at is None
    assert task.ended_at is None
    assert task.expires_at is not None
    assert task.retry_count == 0
    assert task.max_retries == 3
    assert task.next_retry_at is None


def test_task_creation_with_params():
    """Test task creation with custom parameters."""
    params = {"workflow_id": "test_workflow", "runtime": "swarmgraph"}
    task = Task(
        type=TaskType.RUN,
        operation="execute_workflow",
        params=params,
        max_retries=5,
    )

    assert task.params == params
    assert task.max_retries == 5


def test_task_types():
    """Test all task types."""
    run_task = Task(type=TaskType.RUN, operation="run")
    trace_task = Task(type=TaskType.TRACE, operation="trace")
    audit_task = Task(type=TaskType.AUDIT, operation="audit")

    assert run_task.type == TaskType.RUN
    assert trace_task.type == TaskType.TRACE
    assert audit_task.type == TaskType.AUDIT


def test_valid_state_transitions():
    """Test valid state transitions."""
    task = Task(type=TaskType.RUN, operation="test")

    # PENDING -> RUNNING
    assert task.can_transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.RUNNING)
    assert task.status == TaskStatus.RUNNING
    assert task.started_at is not None

    # RUNNING -> COMPLETED
    assert task.can_transition_to(TaskStatus.COMPLETED)
    task.transition_to(TaskStatus.COMPLETED)
    assert task.status == TaskStatus.COMPLETED
    assert task.ended_at is not None


def test_failed_to_running_transition():
    """Test retry transition from FAILED to RUNNING."""
    task = Task(type=TaskType.RUN, operation="test")
    task.transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.FAILED)

    assert task.status == TaskStatus.FAILED
    assert task.ended_at is not None

    # FAILED -> RUNNING (retry)
    assert task.can_transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.RUNNING)
    assert task.status == TaskStatus.RUNNING


def test_invalid_state_transitions():
    """Test invalid state transitions."""
    task = Task(type=TaskType.RUN, operation="test")

    # PENDING -> COMPLETED (invalid, must go through RUNNING)
    assert not task.can_transition_to(TaskStatus.COMPLETED)
    with pytest.raises(ValueError, match="Invalid transition"):
        task.transition_to(TaskStatus.COMPLETED)

    # Complete the task
    task.transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.COMPLETED)

    # COMPLETED -> RUNNING (invalid, terminal state)
    assert not task.can_transition_to(TaskStatus.RUNNING)
    with pytest.raises(ValueError, match="Invalid transition"):
        task.transition_to(TaskStatus.RUNNING)


def test_cancel_from_pending():
    """Test cancellation from PENDING state."""
    task = Task(type=TaskType.RUN, operation="test")

    assert task.can_transition_to(TaskStatus.CANCELLED)
    task.transition_to(TaskStatus.CANCELLED)
    assert task.status == TaskStatus.CANCELLED
    assert task.ended_at is not None


def test_cancel_from_running():
    """Test cancellation from RUNNING state."""
    task = Task(type=TaskType.RUN, operation="test")
    task.transition_to(TaskStatus.RUNNING)

    assert task.can_transition_to(TaskStatus.CANCELLED)
    task.transition_to(TaskStatus.CANCELLED)
    assert task.status == TaskStatus.CANCELLED
    assert task.ended_at is not None


def test_cancel_from_failed():
    """Test cancellation from FAILED state."""
    task = Task(type=TaskType.RUN, operation="test")
    task.transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.FAILED)

    assert task.can_transition_to(TaskStatus.CANCELLED)
    task.transition_to(TaskStatus.CANCELLED)
    assert task.status == TaskStatus.CANCELLED


def test_should_retry_logic():
    """Test retry logic."""
    task = Task(type=TaskType.RUN, operation="test", max_retries=3)

    # Not failed yet, should not retry
    assert not task.should_retry()

    # Fail the task
    task.transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.FAILED)

    # Should retry (0 < 3)
    assert task.should_retry()

    # Increment retry count
    task.retry_count = 1
    assert task.should_retry()

    task.retry_count = 2
    assert task.should_retry()

    # Max retries reached
    task.retry_count = 3
    assert not task.should_retry()


def test_calculate_next_retry():
    """Test exponential backoff calculation."""
    task = Task(type=TaskType.RUN, operation="test")

    # First retry: 2^0 = 1 second
    task.retry_count = 0
    next_retry = task.calculate_next_retry()
    next_retry_dt = datetime.fromisoformat(next_retry)
    now = datetime.now(timezone.utc)
    diff = (next_retry_dt - now).total_seconds()
    assert 0.5 <= diff <= 2.0  # Allow some tolerance

    # Second retry: 2^1 = 2 seconds
    task.retry_count = 1
    next_retry = task.calculate_next_retry()
    next_retry_dt = datetime.fromisoformat(next_retry)
    now = datetime.now(timezone.utc)
    diff = (next_retry_dt - now).total_seconds()
    assert 1.5 <= diff <= 3.0

    # Third retry: 2^2 = 4 seconds
    task.retry_count = 2
    next_retry = task.calculate_next_retry()
    next_retry_dt = datetime.fromisoformat(next_retry)
    now = datetime.now(timezone.utc)
    diff = (next_retry_dt - now).total_seconds()
    assert 3.5 <= diff <= 5.0


def test_is_expired():
    """Test expiry checking."""
    task = Task(type=TaskType.RUN, operation="test")

    # Not expired (default 24 hours)
    assert not task.is_expired()

    # Set expiry to past
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    task.expires_at = past.isoformat()
    assert task.is_expired()

    # Set expiry to future
    future = datetime.now(timezone.utc) + timedelta(hours=1)
    task.expires_at = future.isoformat()
    assert not task.is_expired()


def test_task_serialization():
    """Test task serialization to/from dict."""
    original = Task(
        type=TaskType.RUN,
        operation="test_operation",
        params={"key": "value"},
        max_retries=5,
    )
    original.transition_to(TaskStatus.RUNNING)
    original.result = {"output": "success"}

    # Serialize
    data = original.to_dict()
    assert isinstance(data, dict)
    assert data["id"] == original.id
    assert data["type"] == TaskType.RUN.value
    assert data["operation"] == "test_operation"
    assert data["params"] == {"key": "value"}
    assert data["status"] == TaskStatus.RUNNING.value
    assert data["result"] == {"output": "success"}
    assert data["max_retries"] == 5

    # Deserialize
    restored = Task.from_dict(data)
    assert restored.id == original.id
    assert restored.type == original.type
    assert restored.operation == original.operation
    assert restored.params == original.params
    assert restored.status == original.status
    assert restored.result == original.result
    assert restored.max_retries == original.max_retries


def test_task_with_error():
    """Test task with error information."""
    task = Task(type=TaskType.RUN, operation="test")
    task.transition_to(TaskStatus.RUNNING)
    task.error = "Connection timeout"
    task.transition_to(TaskStatus.FAILED)

    assert task.status == TaskStatus.FAILED
    assert task.error == "Connection timeout"
    assert task.ended_at is not None


def test_task_with_result():
    """Test task with result data."""
    task = Task(type=TaskType.RUN, operation="test")
    task.transition_to(TaskStatus.RUNNING)
    task.result = {
        "run_id": "run_123",
        "status": "completed",
        "audit_chain_ref": "audit_456",
        "cost_breakdown": {"total": 0.05},
    }
    task.transition_to(TaskStatus.COMPLETED)

    assert task.status == TaskStatus.COMPLETED
    assert task.result is not None
    assert task.result["run_id"] == "run_123"
    assert task.result["cost_breakdown"]["total"] == 0.05
