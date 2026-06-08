"""B2P-07 regression guard: task execution is real (no placeholders) and publishes lifecycle events.

The MCP task system executes real run/trace/audit/eval operations and publishes task lifecycle
events to the in-process event bus (subscribable — see test_task_sse_events.py), replacing the
earlier placeholder/polling baseline. These guards lock that against regression.
"""

from __future__ import annotations

import inspect

from agent_runtime_cockpit.tasks.executor import TaskExecutor


def test_execute_path_uses_real_operations_not_placeholders() -> None:
    for handler in (
        "_execute_run",
        "_execute_trace",
        "_execute_audit",
        "_execute_eval",
        "_execute_operation",
    ):
        assert callable(getattr(TaskExecutor, handler, None)), f"missing real handler {handler}"
    run_src = inspect.getsource(TaskExecutor._execute_run)
    assert "runtime_router" in run_src  # real routing, not a stub
    assert "JsonlTraceStore" in run_src  # real trace persistence
    op_src = inspect.getsource(TaskExecutor._execute_operation)
    assert "_execute_run" in op_src and "_execute_trace" in op_src and "_execute_audit" in op_src
    assert "placeholder" not in (run_src + op_src).lower()


def test_lifecycle_events_published_on_every_transition() -> None:
    sync_src = inspect.getsource(TaskExecutor._execute_task_sync)
    # running + completed + failed (+ cancelled) all publish a task event
    assert sync_src.count("_publish_task_event") >= 3
    publish_src = inspect.getsource(TaskExecutor._publish_task_event)
    for event_type in ("task_state_changed", "task_completed", "task_failed"):
        assert event_type in publish_src
