"""Tests for Phase 54 — Task SSE event publishing."""


def test_task_state_changed_event_on_transition():
    """TaskExecutor publishes TaskStateChanged on state transition."""
    from unittest.mock import MagicMock, patch

    from agent_runtime_cockpit.events.bus import get_bus
    from agent_runtime_cockpit.events.types import TaskStateChanged
    from agent_runtime_cockpit.tasks.executor import TaskExecutor
    from agent_runtime_cockpit.tasks.models import Task, TaskType
    from agent_runtime_cockpit.tasks.storage import TaskStorage

    bus = get_bus()
    received = []

    def handler(ev):
        if isinstance(ev, TaskStateChanged):
            received.append(ev)

    bus.subscribe("task_state_changed", handler)

    storage = MagicMock(spec=TaskStorage)
    executor = TaskExecutor(storage)

    task = Task(type=TaskType.TRACE, operation="test-trace")

    with patch.object(executor, "_execute_operation", return_value={"ok": True}):
        executor._execute_task_sync(task)

    # Should get at least pending→running event
    assert len(received) >= 1
    assert received[0].event_type == "task_state_changed"
    assert received[0].task_id == task.id

    bus.unsubscribe("task_state_changed", handler)


def test_task_completed_event():
    """TaskExecutor publishes TaskCompleted on success."""
    from unittest.mock import MagicMock, patch

    from agent_runtime_cockpit.events.bus import get_bus
    from agent_runtime_cockpit.events.types import TaskCompleted
    from agent_runtime_cockpit.tasks.executor import TaskExecutor
    from agent_runtime_cockpit.tasks.models import Task, TaskType
    from agent_runtime_cockpit.tasks.storage import TaskStorage

    bus = get_bus()
    received = []

    def handler(ev):
        if isinstance(ev, TaskCompleted):
            received.append(ev)

    bus.subscribe("task_completed", handler)

    storage = MagicMock(spec=TaskStorage)
    executor = TaskExecutor(storage)

    task = Task(type=TaskType.TRACE, operation="test-trace-complete")

    # Need to ensure it completes, not fails
    with patch.object(executor, "_execute_operation", return_value={"ok": True}):
        executor._execute_task_sync(task)

    assert len(received) >= 1
    assert received[0].event_type == "task_completed"
    assert received[0].task_id == task.id

    bus.unsubscribe("task_completed", handler)


def test_task_failed_event():
    """TaskExecutor publishes TaskFailed on failure."""
    from unittest.mock import MagicMock, patch

    from agent_runtime_cockpit.events.bus import get_bus
    from agent_runtime_cockpit.events.types import TaskFailed
    from agent_runtime_cockpit.tasks.executor import TaskExecutor
    from agent_runtime_cockpit.tasks.models import Task, TaskType
    from agent_runtime_cockpit.tasks.storage import TaskStorage

    bus = get_bus()
    received = []

    def handler(ev):
        if isinstance(ev, TaskFailed):
            received.append(ev)

    bus.subscribe("task_failed", handler)

    storage = MagicMock(spec=TaskStorage)
    executor = TaskExecutor(storage)

    task = Task(type=TaskType.RUN, operation="test-run-fail")

    # Force failure
    with patch.object(executor, "_execute_operation", side_effect=ValueError("test error")):
        executor._execute_task_sync(task)

    assert len(received) >= 1
    assert received[0].event_type == "task_failed"
    assert received[0].task_id == task.id
    assert "test error" in received[0].error

    bus.unsubscribe("task_failed", handler)


def test_task_state_changed_in_sse_push_types():
    """Verify task_state_changed is in _SSE_PUSH_EVENT_TYPES."""
    from agent_runtime_cockpit.web.routes import _SSE_PUSH_EVENT_TYPES

    assert "task_state_changed" in _SSE_PUSH_EVENT_TYPES
    assert "task_completed" in _SSE_PUSH_EVENT_TYPES
    assert "task_failed" in _SSE_PUSH_EVENT_TYPES


def test_task_event_types_in_event_type_map():
    """Verify task event types are in EVENT_TYPE_MAP."""
    from agent_runtime_cockpit.events.types import (
        EVENT_TYPE_MAP,
        TaskStateChanged,
        TaskCompleted,
        TaskFailed,
    )

    assert "task_state_changed" in EVENT_TYPE_MAP
    assert EVENT_TYPE_MAP["task_state_changed"] == TaskStateChanged
    assert "task_completed" in EVENT_TYPE_MAP
    assert EVENT_TYPE_MAP["task_completed"] == TaskCompleted
    assert "task_failed" in EVENT_TYPE_MAP
    assert EVENT_TYPE_MAP["task_failed"] == TaskFailed
