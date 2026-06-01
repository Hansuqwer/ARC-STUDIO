from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from agent_runtime_cockpit.swarmgraph import runner as runner_module
from agent_runtime_cockpit.swarmgraph import (
    DurableNotificationOutbox,
    DurableWebhookNotificationHook,
    EventBrokerNotificationHook,
    NotificationConfig,
    WebhookNotificationHook,
    WebhookTargetConfig,
)
from agent_runtime_cockpit.swarmgraph.config import SwarmGraphConfig, SwarmTopology
from agent_runtime_cockpit.swarmgraph.consensus import ConsensusResult
from agent_runtime_cockpit.swarmgraph.decomposition import TrivialDecomposition
from agent_runtime_cockpit.swarmgraph.detectors import (
    detect_all_failed,
    detect_budget_warning,
    detect_empty_output,
    detect_protocol_mismatch,
    detect_provider_degraded,
    detect_stale_tasks,
    detect_worker_timeout,
)
from agent_runtime_cockpit.swarmgraph.events import SwarmGraphEvent, SwarmGraphEventKind
from agent_runtime_cockpit.swarmgraph.models import (
    ApprovalDecision,
    SwarmTask,
    TaskStatus,
    WorkerResult,
)
from agent_runtime_cockpit.swarmgraph.nodes.consensus import ConsensusRoundOutcome
from agent_runtime_cockpit.swarmgraph.runner import SwarmGraphRunner, SwarmRunResult
from agent_runtime_cockpit.swarmgraph.state import SwarmState


def _state() -> SwarmState:
    return SwarmState(config=SwarmGraphConfig())


def _result(task_id: str = "task-1", output: str = "ok", error: str | None = None) -> WorkerResult:
    return WorkerResult(worker_id="worker-1", task_id=task_id, output=output, error=error)


def _outcome(task_id: str = "task-1", reached: bool = False) -> ConsensusRoundOutcome:
    return ConsensusRoundOutcome(
        task_id=task_id,
        decision=ApprovalDecision(approved=reached, reason="test"),
        consensus_result=ConsensusResult(
            reached=reached,
            approved=reached,
            total_votes=1,
            approval_count=1 if reached else 0,
            rejection_count=0 if reached else 1,
            required=1,
        ),
    )


def test_phase107_detectors_4_to_10_emit_expected_failure_modes() -> None:
    state = _state()
    state.accumulated_cost_usd = 5.0
    stale = SwarmTask(prompt="stale", status=TaskStatus.assigned)
    failed = SwarmTask(prompt="failed", status=TaskStatus.failed)

    assert (
        detect_worker_timeout([_result(error="timeout")], state).data["failure_mode"]
        == "worker_timeout"
    )
    assert detect_budget_warning(state, 10.0).data["failure_mode"] == "budget_warning"

    state.current_round = 3
    state.tasks[stale.id] = stale
    assert detect_stale_tasks(state).data["failure_mode"] == "stale_tasks"

    assert (
        detect_protocol_mismatch([_outcome(reached=False)], state).data["failure_mode"]
        == "protocol_mismatch"
    )
    assert (
        detect_provider_degraded([_result(error="provider degraded")], state).data["failure_mode"]
        == "provider_degraded"
    )
    assert detect_empty_output([_result(output="")], state).data["failure_mode"] == "empty_output"

    state.tasks = {failed.id: failed}
    assert detect_all_failed(state).data["failure_mode"] == "all_failed"


def test_phase107_detectors_ignore_non_matching_inputs() -> None:
    state = _state()
    state.tasks["task-1"] = SwarmTask(prompt="pending")

    assert detect_worker_timeout([_result()], state) is None
    assert detect_budget_warning(state, None) is None
    assert detect_stale_tasks(state) is None
    assert detect_protocol_mismatch([_outcome(reached=True)], state) is None
    assert detect_provider_degraded([_result(error="boom")], state) is None
    assert detect_empty_output([_result(output="ok")], state) is None
    assert detect_all_failed(state) is None


def test_mesh_decomposition_creates_independent_workers() -> None:
    cfg = SwarmGraphConfig(num_workers=3, topology=SwarmTopology.mesh)

    tasks = TrivialDecomposition().decompose("analyze", 3, cfg)

    assert len(tasks) == 3
    assert [task.metadata["worker_index"] for task in tasks] == [0, 1, 2]
    assert all(task.metadata["topology"] == "mesh" for task in tasks)
    assert all(task.parent_task_id is None for task in tasks)


def test_tree_decomposition_links_leaves_to_root() -> None:
    cfg = SwarmGraphConfig(num_workers=3, topology=SwarmTopology.tree)

    tasks = TrivialDecomposition().decompose("analyze", 3, cfg)

    root, *leaves = tasks

    assert root.metadata["role"] == "root"
    assert [leaf.parent_task_id for leaf in leaves] == [root.id, root.id]
    assert [leaf.metadata["leaf_index"] for leaf in leaves] == [0, 1]


@pytest.mark.asyncio
async def test_runner_executes_child_after_parent_dependency(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_order: list[str] = []

    async def fake_worker(task, mode, timeout, cancellation_token=None):
        execution_order.append(task.metadata["role"])
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="ok",
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", fake_worker)
    cfg = SwarmGraphConfig(
        num_workers=2,
        max_rounds=3,
        topology=SwarmTopology.tree,
        fan_out_threshold=0,
        max_parallel_workers=2,
    )

    result = await SwarmGraphRunner(config=cfg).run_async("Do A. Do B. Do C.")

    assert result["completed_tasks"] == 2
    assert execution_order == ["root", "leaf"]


@pytest.mark.asyncio
async def test_runner_executes_task_after_all_dag_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    execution_order: list[str] = []
    first = SwarmTask(prompt="first", metadata={"name": "first"})
    second = SwarmTask(prompt="second", metadata={"name": "second"})
    join = SwarmTask(
        prompt="join",
        dependency_task_ids=[first.id, second.id],
        metadata={"name": "join"},
    )

    class _DagDecomposition:
        def decompose(self, prompt: str, num_workers: int, config: SwarmGraphConfig):
            return [first, second, join]

    async def fake_worker(task, mode, timeout, cancellation_token=None):
        execution_order.append(task.metadata["name"])
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="ok",
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", fake_worker)
    cfg = SwarmGraphConfig(
        num_workers=3,
        max_rounds=3,
        fan_out_threshold=0,
        max_parallel_workers=3,
    )

    result = await SwarmGraphRunner(
        config=cfg,
        decomposition_strategy=_DagDecomposition(),
    ).run_async("Do A. Do B. Join C.")

    assert result["completed_tasks"] == 3
    assert set(execution_order[:2]) == {"first", "second"}
    assert execution_order[2] == "join"


@pytest.mark.asyncio
async def test_runner_keeps_dag_task_pending_until_every_dependency_completes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    first = SwarmTask(prompt="first", metadata={"name": "first"})
    second = SwarmTask(prompt="second", metadata={"name": "second"})
    join = SwarmTask(
        prompt="join",
        dependency_task_ids=[first.id, second.id],
        metadata={"name": "join"},
    )

    class _DagDecomposition:
        def decompose(self, prompt: str, num_workers: int, config: SwarmGraphConfig):
            return [first, second, join]

    async def fake_worker(task, mode, timeout, cancellation_token=None):
        error = "boom" if task.id == second.id else None
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown",
            task_id=task.id,
            output="" if error else "ok",
            error=error,
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", fake_worker)
    cfg = SwarmGraphConfig(
        num_workers=3,
        max_rounds=2,
        fan_out_threshold=0,
        max_parallel_workers=3,
    )

    result = await SwarmGraphRunner(
        config=cfg,
        decomposition_strategy=_DagDecomposition(),
    ).run_async("Do A. Do B. Join C.")

    assert result["completed_tasks"] == 1
    assert result["failed_tasks"] == 1
    assert join.status == TaskStatus.pending


@pytest.mark.asyncio
async def test_guardrail_accept_allows_result(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_worker(task, mode, timeout, cancellation_token=None):
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown", task_id=task.id, output="ok"
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", fake_worker)

    result = await SwarmGraphRunner(
        config=SwarmGraphConfig(max_rounds=1),
        guardrail=lambda _task, _result: True,
    ).run_async("Explain consensus")

    assert result["completed_tasks"] == 1
    assert result["failed_tasks"] == 0


@pytest.mark.asyncio
async def test_guardrail_reject_marks_task_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_worker(task, mode, timeout, cancellation_token=None):
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown", task_id=task.id, output="bad"
        )

    monkeypatch.setattr(runner_module, "worker_execute_async", fake_worker)

    result = await SwarmGraphRunner(
        config=SwarmGraphConfig(max_rounds=1),
        guardrail=lambda _task, _result: False,
    ).run_async("Explain consensus")

    assert result["completed_tasks"] == 0
    assert result["failed_tasks"] == 1
    assert any(
        event["data"].get("failure_mode") == "guardrail_rejected" for event in result["events"]
    )


@pytest.mark.asyncio
async def test_guardrail_exception_marks_task_failed(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_worker(task, mode, timeout, cancellation_token=None):
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown", task_id=task.id, output="bad"
        )

    def broken_guardrail(_task: SwarmTask, _result: WorkerResult) -> bool:
        raise RuntimeError("broken")

    monkeypatch.setattr(runner_module, "worker_execute_async", fake_worker)

    result = await SwarmGraphRunner(
        config=SwarmGraphConfig(max_rounds=1),
        guardrail=broken_guardrail,
    ).run_async("Explain consensus")

    assert result["failed_tasks"] == 1
    assert any(
        event["data"].get("failure_mode") == "guardrail_rejected" for event in result["events"]
    )


def test_json_model_round_trip_stays_stable() -> None:
    event = SwarmGraphEvent(
        kind=SwarmGraphEventKind.audit,
        swarm_id="swarm-test",
        data={"phase": "107"},
    )
    result = SwarmRunResult(
        swarm_id="swarm-test",
        status="completed",
        rounds=1,
        total_tasks=1,
        completed_tasks=1,
        events=[event.to_dict()],
    )

    payload = json.loads(result.model_dump_json())

    assert SwarmRunResult.from_dict(payload).to_dict() == result.to_dict()


@pytest.mark.asyncio
async def test_webhook_notification_hook_posts_event(monkeypatch: pytest.MonkeyPatch) -> None:
    posted: dict[str, Any] = {}

    def fake_urlopen(req, timeout):
        posted["url"] = req.full_url
        posted["timeout"] = timeout
        posted["payload"] = json.loads(req.data.decode())

        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

        return _Response()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    event = SwarmGraphEvent(kind=SwarmGraphEventKind.audit, swarm_id="swarm-test")

    await WebhookNotificationHook("https://example.test/hook", timeout=1).notify(event)

    assert posted["url"] == "https://example.test/hook"
    assert posted["timeout"] == 1
    assert posted["payload"]["kind"] == "audit"


@pytest.mark.asyncio
async def test_eventbroker_notification_hook_respects_gate(monkeypatch: pytest.MonkeyPatch) -> None:
    published: list[tuple[str, dict[str, Any]]] = []

    class _Broker:
        async def publish(self, event_type: str, data: dict[str, Any]) -> None:
            published.append((event_type, data))

    hook = EventBrokerNotificationHook(broker=_Broker())
    event = SwarmGraphEvent(kind=SwarmGraphEventKind.audit, swarm_id="swarm-test")

    monkeypatch.delenv("ARC_SWARMGRAPH_EVENTBROKER", raising=False)
    await hook.notify(event)
    assert published == []

    monkeypatch.setenv("ARC_SWARMGRAPH_EVENTBROKER", "1")
    await hook.notify(event)
    assert published == [("swarmgraph_event", event.to_dict())]


@pytest.mark.asyncio
async def test_runner_drains_notification_hooks(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_worker(task, mode, timeout, cancellation_token=None):
        return WorkerResult(
            worker_id=task.assigned_agent_id or "unknown", task_id=task.id, output="ok"
        )

    class _Hook:
        def __init__(self) -> None:
            self.events: list[SwarmGraphEvent] = []

        async def notify(self, event: SwarmGraphEvent) -> None:
            self.events.append(event)

    monkeypatch.setattr(runner_module, "worker_execute_async", fake_worker)
    hook = _Hook()

    await SwarmGraphRunner(
        config=SwarmGraphConfig(max_rounds=1),
        notification_hooks=[hook],
    ).run_async("Explain consensus")

    assert [event.kind for event in hook.events]
    assert any(event.kind == SwarmGraphEventKind.worker for event in hook.events)


def test_notification_config_loads_webhook_targets(tmp_path: Path) -> None:
    path = tmp_path / "notifications.json"
    outbox = tmp_path / "outbox.jsonl"
    path.write_text(
        json.dumps(
            {
                "outbox_path": str(outbox),
                "targets": [
                    {
                        "id": "wh-audit",
                        "url": "https://example.test/hook",
                        "enabled_events": ["audit"],
                    }
                ],
            }
        )
    )

    config = NotificationConfig.load(path)

    assert config.outbox_path == str(outbox)
    assert config.targets[0].id == "wh-audit"
    assert config.targets[0].matches("audit")
    assert not config.targets[0].matches("worker")


@pytest.mark.asyncio
async def test_durable_webhook_hook_records_delivery_outbox(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def fake_post(self, target, payload):
        calls.append(payload["kind"])
        return True

    monkeypatch.setattr(DurableWebhookNotificationHook, "_post_sync", fake_post)
    outbox_path = tmp_path / "outbox.jsonl"
    config = NotificationConfig(
        outbox_path=str(outbox_path),
        targets=[WebhookTargetConfig(id="wh-all", url="https://example.test/hook")],
    )
    hook = DurableWebhookNotificationHook(config)
    event = SwarmGraphEvent(kind=SwarmGraphEventKind.audit, swarm_id="swarm-test")

    await hook.notify(event)

    records = DurableNotificationOutbox(outbox_path).read()
    assert calls == ["audit"]
    assert [record.status for record in records] == ["pending", "delivered"]
    assert records[0].event["kind"] == "audit"


@pytest.mark.asyncio
async def test_durable_webhook_hook_retries_failed_records(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    attempts = 0

    def fake_post(self, target, payload):
        nonlocal attempts
        attempts += 1
        return attempts > 1

    monkeypatch.setattr(DurableWebhookNotificationHook, "_post_sync", fake_post)
    outbox_path = tmp_path / "outbox.jsonl"
    config = NotificationConfig(
        outbox_path=str(outbox_path),
        targets=[
            WebhookTargetConfig(
                id="wh-all",
                url="https://example.test/hook",
                max_attempts=2,
            )
        ],
    )
    hook = DurableWebhookNotificationHook(config)
    event = SwarmGraphEvent(kind=SwarmGraphEventKind.audit, swarm_id="swarm-test")

    await hook.notify(event)
    retried = await hook.retry_outstanding_once()

    records = DurableNotificationOutbox(outbox_path).read()
    assert retried == 1
    assert attempts == 2
    assert [record.status for record in records] == [
        "pending",
        "failed",
        "pending",
        "delivered",
    ]
    assert records[-1].attempt == 2
