"""Tests for task storage."""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

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


def test_storage_init(storage, temp_db):
    """Test storage initialization."""
    assert storage.db_path == temp_db
    # Init should create the database
    storage.init_db()
    assert temp_db.exists()


def test_create_task(storage):
    """Test creating a task."""
    task = Task(type=TaskType.RUN, operation="test_op")
    storage.create_task(task)

    # Verify task was created
    retrieved = storage.get_task(task.id)
    assert retrieved is not None
    assert retrieved.id == task.id
    assert retrieved.type == task.type
    assert retrieved.operation == task.operation
    assert retrieved.status == TaskStatus.PENDING


def test_get_task_not_found(storage):
    """Test getting a non-existent task."""
    result = storage.get_task("nonexistent_id")
    assert result is None


def test_update_task(storage):
    """Test updating a task."""
    task = Task(type=TaskType.RUN, operation="test_op")
    storage.create_task(task)

    # Update task
    task.transition_to(TaskStatus.RUNNING)
    task.result = {"output": "success"}
    storage.update_task(task)

    # Verify update
    retrieved = storage.get_task(task.id)
    assert retrieved.status == TaskStatus.RUNNING
    assert retrieved.result == {"output": "success"}
    assert retrieved.started_at is not None


def test_list_tasks_no_filter(storage):
    """Test listing all tasks."""
    # Create multiple tasks
    task1 = Task(type=TaskType.RUN, operation="op1")
    task2 = Task(type=TaskType.TRACE, operation="op2")
    task3 = Task(type=TaskType.AUDIT, operation="op3")

    storage.create_task(task1)
    storage.create_task(task2)
    storage.create_task(task3)

    # List all tasks
    tasks = storage.list_tasks()
    assert len(tasks) == 3
    task_ids = {t.id for t in tasks}
    assert task1.id in task_ids
    assert task2.id in task_ids
    assert task3.id in task_ids


def test_list_tasks_filter_by_status(storage):
    """Test listing tasks filtered by status."""
    # Create tasks with different statuses
    task1 = Task(type=TaskType.RUN, operation="op1")
    task2 = Task(type=TaskType.RUN, operation="op2")
    task3 = Task(type=TaskType.RUN, operation="op3")

    storage.create_task(task1)
    storage.create_task(task2)
    storage.create_task(task3)

    # Update task2 to running
    task2.transition_to(TaskStatus.RUNNING)
    storage.update_task(task2)

    # Update task3 to completed
    task3.transition_to(TaskStatus.RUNNING)
    task3.transition_to(TaskStatus.COMPLETED)
    storage.update_task(task3)

    # Filter by pending
    pending_tasks = storage.list_tasks(status=TaskStatus.PENDING)
    assert len(pending_tasks) == 1
    assert pending_tasks[0].id == task1.id

    # Filter by running
    running_tasks = storage.list_tasks(status=TaskStatus.RUNNING)
    assert len(running_tasks) == 1
    assert running_tasks[0].id == task2.id

    # Filter by completed
    completed_tasks = storage.list_tasks(status=TaskStatus.COMPLETED)
    assert len(completed_tasks) == 1
    assert completed_tasks[0].id == task3.id


def test_list_tasks_filter_by_type(storage):
    """Test listing tasks filtered by type."""
    # Create tasks with different types
    task1 = Task(type=TaskType.RUN, operation="op1")
    task2 = Task(type=TaskType.TRACE, operation="op2")
    task3 = Task(type=TaskType.AUDIT, operation="op3")

    storage.create_task(task1)
    storage.create_task(task2)
    storage.create_task(task3)

    # Filter by RUN
    run_tasks = storage.list_tasks(task_type=TaskType.RUN)
    assert len(run_tasks) == 1
    assert run_tasks[0].type == TaskType.RUN

    # Filter by TRACE
    trace_tasks = storage.list_tasks(task_type=TaskType.TRACE)
    assert len(trace_tasks) == 1
    assert trace_tasks[0].type == TaskType.TRACE

    # Filter by AUDIT
    audit_tasks = storage.list_tasks(task_type=TaskType.AUDIT)
    assert len(audit_tasks) == 1
    assert audit_tasks[0].type == TaskType.AUDIT


def test_list_tasks_with_limit(storage):
    """Test listing tasks with limit."""
    # Create 5 tasks
    for i in range(5):
        task = Task(type=TaskType.RUN, operation=f"op{i}")
        storage.create_task(task)

    # List with limit
    tasks = storage.list_tasks(limit=3)
    assert len(tasks) == 3


def test_get_tasks_for_retry(storage):
    """Test getting tasks ready for retry."""
    # Create tasks
    task1 = Task(type=TaskType.RUN, operation="op1", max_retries=3)
    task2 = Task(type=TaskType.RUN, operation="op2", max_retries=3)
    task3 = Task(type=TaskType.RUN, operation="op3", max_retries=3)

    storage.create_task(task1)
    storage.create_task(task2)
    storage.create_task(task3)

    # Fail task1 (should be ready for retry)
    task1.transition_to(TaskStatus.RUNNING)
    task1.transition_to(TaskStatus.FAILED)
    task1.retry_count = 0
    storage.update_task(task1)

    # Fail task2 but set next_retry_at to future (not ready yet)
    task2.transition_to(TaskStatus.RUNNING)
    task2.transition_to(TaskStatus.FAILED)
    task2.retry_count = 1
    task2.next_retry_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    storage.update_task(task2)

    # Fail task3 and max out retries (should not retry)
    task3.transition_to(TaskStatus.RUNNING)
    task3.transition_to(TaskStatus.FAILED)
    task3.retry_count = 3
    storage.update_task(task3)

    # Get tasks for retry
    retry_tasks = storage.get_tasks_for_retry()
    assert len(retry_tasks) == 1
    assert retry_tasks[0].id == task1.id


def test_get_tasks_for_retry_with_past_next_retry(storage):
    """Test getting tasks with past next_retry_at."""
    task = Task(type=TaskType.RUN, operation="op1", max_retries=3)
    storage.create_task(task)

    # Fail task and set next_retry_at to past
    task.transition_to(TaskStatus.RUNNING)
    task.transition_to(TaskStatus.FAILED)
    task.retry_count = 1
    task.next_retry_at = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    storage.update_task(task)

    # Should be ready for retry
    retry_tasks = storage.get_tasks_for_retry()
    assert len(retry_tasks) == 1
    assert retry_tasks[0].id == task.id


def test_delete_expired_tasks(storage):
    """Test deleting expired tasks."""
    # Create tasks with different expiry times
    task1 = Task(type=TaskType.RUN, operation="op1")
    task2 = Task(type=TaskType.RUN, operation="op2")
    task3 = Task(type=TaskType.RUN, operation="op3")

    # Set task1 to expired
    task1.expires_at = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()

    # Set task2 to expired
    task2.expires_at = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()

    # task3 not expired (default 24 hours)

    storage.create_task(task1)
    storage.create_task(task2)
    storage.create_task(task3)

    # Delete expired tasks
    deleted_count = storage.delete_expired_tasks()
    assert deleted_count == 2

    # Verify only task3 remains
    tasks = storage.list_tasks()
    assert len(tasks) == 1
    assert tasks[0].id == task3.id


def test_delete_task(storage):
    """Test deleting a specific task."""
    task = Task(type=TaskType.RUN, operation="op1")
    storage.create_task(task)

    # Verify task exists
    assert storage.get_task(task.id) is not None

    # Delete task
    deleted = storage.delete_task(task.id)
    assert deleted is True

    # Verify task is gone
    assert storage.get_task(task.id) is None


def test_delete_task_not_found(storage):
    """Test deleting a non-existent task."""
    deleted = storage.delete_task("nonexistent_id")
    assert deleted is False


def test_task_params_serialization(storage):
    """Test that task params are properly serialized/deserialized."""
    params = {
        "workflow_id": "test_workflow",
        "runtime": "swarmgraph",
        "config": {"timeout": 300, "retries": 3},
    }
    task = Task(type=TaskType.RUN, operation="execute", params=params)
    storage.create_task(task)

    # Retrieve and verify params
    retrieved = storage.get_task(task.id)
    assert retrieved.params == params
    assert retrieved.params["config"]["timeout"] == 300


def test_task_result_serialization(storage):
    """Test that task result is properly serialized/deserialized."""
    task = Task(type=TaskType.RUN, operation="execute")
    storage.create_task(task)

    # Update with result
    task.transition_to(TaskStatus.RUNNING)
    task.result = {
        "run_id": "run_123",
        "status": "completed",
        "audit_chain_ref": "audit_456",
        "cost_breakdown": {"total": 0.05, "provider": "openai"},
    }
    task.transition_to(TaskStatus.COMPLETED)
    storage.update_task(task)

    # Retrieve and verify result
    retrieved = storage.get_task(task.id)
    assert retrieved.result == task.result
    assert retrieved.result["cost_breakdown"]["total"] == 0.05


def test_multiple_storage_instances(temp_db):
    """Test that multiple storage instances can access the same database."""
    storage1 = TaskStorage(temp_db)
    storage2 = TaskStorage(temp_db)

    # Create task with storage1
    task = Task(type=TaskType.RUN, operation="test")
    storage1.create_task(task)

    # Retrieve with storage2
    retrieved = storage2.get_task(task.id)
    assert retrieved is not None
    assert retrieved.id == task.id
