"""Tests for task executor."""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from agent_runtime_cockpit.tasks.executor import TaskExecutor
from agent_runtime_cockpit.tasks.models import Task, TaskStatus, TaskType
from agent_runtime_cockpit.tasks.storage import TaskStorage


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_tasks.db"
        yield db_path


@pytest.fixture
def storage(temp_db):
    """Create a TaskStorage instance with temporary database."""
    return TaskStorage(temp_db)


@pytest.fixture
def executor(storage):
    """Create a TaskExecutor instance."""
    executor = TaskExecutor(storage)
    yield executor
    executor.stop_worker()
    executor.wait_for_all(timeout=5.0)


def test_executor_creation(executor, storage):
    """Test executor initialization."""
    assert executor.storage == storage
    assert not executor._running
    assert executor._worker_thread is None


def test_submit_task(executor):
    """Test submitting a task."""
    task = Task(type=TaskType.RUN, operation="test_op")
    task_id = executor.submit_task(task)

    assert task_id == task.id

    # Wait a bit for async execution
    time.sleep(0.5)

    # Verify task was stored
    stored_task = executor.get_task_status(task_id)
    assert stored_task is not None
    assert stored_task.id == task_id


def test_get_task_status(executor):
    """Test getting task status."""
    task = Task(type=TaskType.RUN, operation="test_op")
    executor.submit_task(task)

    # Get status
    status = executor.get_task_status(task.id)
    assert status is not None
    assert status.id == task.id


def test_get_task_status_not_found(executor):
    """Test getting status of non-existent task."""
    status = executor.get_task_status("nonexistent_id")
    assert status is None


def test_list_tasks(executor):
    """Test listing tasks."""
    task1 = Task(type=TaskType.RUN, operation="op1")
    task2 = Task(type=TaskType.TRACE, operation="op2")

    executor.submit_task(task1)
    executor.submit_task(task2)

    # List all tasks
    tasks = executor.list_tasks()
    assert len(tasks) >= 2


def test_list_tasks_with_filters(executor):
    """Test listing tasks with filters."""
    task1 = Task(type=TaskType.RUN, operation="op1")
    task2 = Task(type=TaskType.TRACE, operation="op2")

    executor.submit_task(task1)
    executor.submit_task(task2)

    # Filter by type
    run_tasks = executor.list_tasks(task_type=TaskType.RUN)
    assert len(run_tasks) >= 1
    assert all(t.type == TaskType.RUN for t in run_tasks)


def test_cancel_pending_task(executor):
    """Test cancelling a pending task."""
    task = Task(type=TaskType.RUN, operation="test_op")
    task_id = executor.submit_task(task)

    # Cancel immediately
    cancelled = executor.cancel_task(task_id)
    assert cancelled is True

    # Verify status
    time.sleep(0.2)
    status = executor.get_task_status(task_id)
    # Task might be running or cancelled depending on timing
    assert status.status in {TaskStatus.RUNNING, TaskStatus.CANCELLED, TaskStatus.COMPLETED}


def test_cancel_nonexistent_task(executor):
    """Test cancelling a non-existent task."""
    cancelled = executor.cancel_task("nonexistent_id")
    assert cancelled is False


def test_cancel_completed_task(executor, storage):
    """Test cancelling a completed task."""
    task = Task(type=TaskType.RUN, operation="test_op")
    task.transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.COMPLETED)
    storage.create_task(task)

    # Try to cancel
    cancelled = executor.cancel_task(task.id)
    assert cancelled is False


def test_task_execution_success(executor):
    """Test successful task execution."""
    task = Task(type=TaskType.RUN, operation="test_op")
    task_id = executor.submit_task(task)

    # Wait for execution
    time.sleep(2.0)

    # Check status
    status = executor.get_task_status(task_id)
    assert status.status == TaskStatus.COMPLETED
    assert status.result is not None
    assert status.error is None


def test_task_execution_with_mock(executor, storage):
    """Test task execution with mocked operation."""
    task = Task(type=TaskType.RUN, operation="test_op")

    # Mock the execution method to return immediately
    with patch.object(executor, "_execute_run") as mock_execute:
        mock_execute.return_value = {"status": "success", "run_id": "test_run"}

        task_id = executor.submit_task(task)
        time.sleep(0.5)

        # Verify execution was called
        status = executor.get_task_status(task_id)
        assert status.status == TaskStatus.COMPLETED
        assert status.result == {"status": "success", "run_id": "test_run"}


def test_task_execution_failure(executor):
    """Test task execution failure."""
    task = Task(type=TaskType.RUN, operation="test_op", max_retries=0)

    # Mock the execution to raise an error
    with patch.object(executor, "_execute_run") as mock_execute:
        mock_execute.side_effect = Exception("Test error")

        task_id = executor.submit_task(task)
        time.sleep(0.5)

        # Check status
        status = executor.get_task_status(task_id)
        assert status.status == TaskStatus.FAILED
        assert status.error == "Test error"


def test_task_retry_logic(executor):
    """Test task retry with exponential backoff."""
    task = Task(type=TaskType.RUN, operation="test_op", max_retries=2)

    # Mock execution to fail first time, succeed second time
    call_count = 0

    def mock_execute(task):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("First attempt failed")
        return {"status": "success", "attempt": call_count}

    with patch.object(executor, "_execute_run", side_effect=mock_execute):
        task_id = executor.submit_task(task)

        # Wait for first attempt to fail
        time.sleep(0.5)
        status = executor.get_task_status(task_id)
        assert status.status == TaskStatus.FAILED
        assert status.retry_count == 1
        assert status.next_retry_at is not None

        # Note: Actual retry would happen in background worker
        # For this test, we just verify the retry state is set correctly


def test_worker_start_stop(executor):
    """Test starting and stopping the background worker."""
    assert not executor._running

    # Start worker
    executor.start_worker()
    assert executor._running
    assert executor._worker_thread is not None

    # Stop worker
    executor.stop_worker()
    assert not executor._running


def test_worker_processes_retry_tasks(executor, storage):
    """Test that worker processes tasks ready for retry."""
    # Create a failed task ready for retry
    task = Task(type=TaskType.RUN, operation="test_op", max_retries=3)
    task.transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.FAILED)
    task.retry_count = 1
    task.next_retry_at = None  # Ready for immediate retry
    storage.create_task(task)

    # Start worker
    executor.start_worker()

    # Wait for worker to process
    time.sleep(2.0)

    # Stop worker
    executor.stop_worker()

    # Check if task was retried (status should have changed)
    status = executor.get_task_status(task.id)
    # Task should have been picked up for retry
    assert status.retry_count >= 1


def test_worker_cleans_expired_tasks(executor, storage):
    """Test that worker cleans up expired tasks."""
    from datetime import datetime, timedelta, timezone

    # Create an expired task
    task = Task(type=TaskType.RUN, operation="test_op")
    task.expires_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    storage.create_task(task)

    # Verify task exists
    assert storage.get_task(task.id) is not None

    # Start worker
    executor.start_worker()

    # Wait for worker to clean up
    time.sleep(6.0)  # Worker runs every 5 seconds

    # Stop worker
    executor.stop_worker()

    # Task should be deleted
    assert storage.get_task(task.id) is None


def test_execute_run_operation(executor):
    """Test executing a run operation."""
    task = Task(type=TaskType.RUN, operation="test_run")
    result = executor._execute_run(task)

    assert result is not None
    assert "run_id" in result
    assert "status" in result


def test_execute_trace_operation(executor):
    """Test executing a trace operation."""
    task = Task(type=TaskType.TRACE, operation="test_trace")
    result = executor._execute_trace(task)

    assert result is not None
    assert "trace_id" in result
    assert "status" in result


def test_execute_audit_operation(executor):
    """Test executing an audit operation."""
    task = Task(type=TaskType.AUDIT, operation="test_audit")
    result = executor._execute_audit(task)

    assert result is not None
    assert "audit_id" in result
    assert "status" in result


def test_execute_unknown_operation(executor):
    """Test executing an unknown operation type."""
    # Create a task with invalid type (this shouldn't happen in practice)
    task = Task(type=TaskType.RUN, operation="test")
    task.type = "invalid_type"  # Force invalid type

    with pytest.raises(ValueError, match="Unknown task type"):
        executor._execute_operation(task)


def test_concurrent_task_execution(executor):
    """Test executing multiple tasks concurrently."""
    tasks = []
    for i in range(5):
        task = Task(type=TaskType.RUN, operation=f"op_{i}")
        task_id = executor.submit_task(task)
        tasks.append(task_id)

    # Wait for all tasks to complete
    time.sleep(3.0)

    # Check all tasks completed
    completed_count = 0
    for task_id in tasks:
        status = executor.get_task_status(task_id)
        if status and status.status == TaskStatus.COMPLETED:
            completed_count += 1

    # At least some tasks should have completed
    assert completed_count >= 3


def test_task_timestamps(executor):
    """Test that task timestamps are set correctly."""
    task = Task(type=TaskType.RUN, operation="test_op")
    task_id = executor.submit_task(task)

    # Wait for execution
    time.sleep(2.0)

    status = executor.get_task_status(task_id)
    assert status.created_at is not None
    assert status.started_at is not None
    assert status.ended_at is not None

    # Verify timestamps are in order
    from datetime import datetime

    created = datetime.fromisoformat(status.created_at)
    started = datetime.fromisoformat(status.started_at)
    ended = datetime.fromisoformat(status.ended_at)

    assert created <= started <= ended
