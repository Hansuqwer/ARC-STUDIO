"""
Tests: EventBroker — in-memory event pub/sub (PR 19).

Tests publish/subscribe, event IDs, bounded queues, end-of-run signaling,
replay, and reconnection. The SSE handler is tested separately via web
tests (see tests/web/).
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from agent_runtime_cockpit.orchestration.event_broker import EventBroker
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore


@pytest.fixture
def broker(tmp_path: Path) -> EventBroker:
    store = JsonlTraceStore(base_dir=tmp_path / "traces")
    return EventBroker(store=store)


class TestPublishSubscribe:
    """Core publish/subscribe semantics."""

    def test_publish_to_subscribers(self, broker: EventBroker):
        queue = broker.subscribe("run-001")
        event_id = broker.publish("run-001", {"type": "RUN_STARTED", "data": {}})
        assert event_id == 1
        event = queue.get_nowait()
        assert event is not None
        assert event["type"] == "RUN_STARTED"
        assert event["event_id"] == 1

    def test_publish_increments_event_id(self, broker: EventBroker):
        broker.subscribe("run-001")
        assert broker.publish("run-001", {"type": "A"}) == 1
        assert broker.publish("run-001", {"type": "B"}) == 2
        assert broker.publish("run-001", {"type": "C"}) == 3

    def test_end_run_signals_subscribers(self, broker: EventBroker):
        queue = broker.subscribe("run-001")
        broker.publish("run-001", {"type": "RUN_STARTED"})
        broker.end_run("run-001")
        event1 = queue.get_nowait()
        assert event1 is not None
        end_signal = queue.get_nowait()
        assert end_signal is None

    def test_unsubscribe_removes_queue(self, broker: EventBroker):
        queue = broker.subscribe("run-001")
        broker.unsubscribe("run-001", queue)
        broker.publish("run-001", {"type": "A"})
        assert queue.empty()

    def test_multiple_subscribers_all_receive(self, broker: EventBroker):
        q1 = broker.subscribe("run-001")
        q2 = broker.subscribe("run-001")
        broker.publish("run-001", {"type": "EVENT"})
        assert q1.get_nowait()["type"] == "EVENT"
        assert q2.get_nowait()["type"] == "EVENT"

    def test_end_run_clears_subscribers(self, broker: EventBroker):
        broker.subscribe("run-001")
        broker.end_run("run-001")
        # After end_run, the subscribers list should be empty
        assert broker._subscribers.get("run-001") is None or \
               len(broker._subscribers.get("run-001", [])) == 0


class TestBoundedQueue:
    """Slow-client policy: bounded queues drop oldest when full."""

    def test_queue_has_maxsize(self, broker: EventBroker):
        queue = broker.subscribe("run-001")
        assert queue.maxsize == 1000

    def test_slow_client_drops_oldest(self, broker: EventBroker):
        """When the subscriber queue is full, the oldest event is dropped."""
        # Fill the queue by setting a small maxsize temporarily
        queue: asyncio.Queue = asyncio.Queue(maxsize=2)
        run_id = "slow-run"
        broker._subscribers[run_id] = [queue]

        broker.publish(run_id, {"type": "FIRST"})
        broker.publish(run_id, {"type": "SECOND"})
        # Queue is now full (2 items). Next publish should drop oldest.
        broker.publish(run_id, {"type": "THIRD"})

        # FIRST was dropped; SECOND and THIRD should remain
        assert queue.qsize() == 2
        assert queue.get_nowait()["type"] == "SECOND"
        assert queue.get_nowait()["type"] == "THIRD"


class TestStreamLive:
    """Live event streaming."""

    @pytest.mark.asyncio
    async def test_stream_live_receives_events(self, broker: EventBroker):
        events_received: list[dict] = []

        async def publisher():
            await asyncio.sleep(0.01)
            broker.publish("run-002", {"type": "RUN_STARTED"})
            broker.publish("run-002", {"type": "STEP_STARTED"})
            broker.end_run("run-002")

        asyncio.create_task(publisher())
        async for event in broker.stream_live("run-002"):
            events_received.append(event)

        assert len(events_received) == 2
        assert events_received[0]["type"] == "RUN_STARTED"
        assert events_received[1]["type"] == "STEP_STARTED"


class TestReplay:
    """Replay stored events from JSONL."""

    def _write_trace(self, tmp_path: Path, run_id: str, events: list[dict]):
        store = JsonlTraceStore(base_dir=tmp_path / "traces")
        for event in events:
            path = store.trace_path(run_id)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a") as f:
                f.write(json.dumps(event) + "\n")

    @pytest.mark.asyncio
    async def test_replay_stored(self, tmp_path: Path):
        store = JsonlTraceStore(base_dir=tmp_path / "traces")
        trace_path = store.trace_path("replay-run")
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        stored = [
            {"type": "RUN_STARTED", "event_id": 1},
            {"type": "STEP_STARTED", "event_id": 2},
            {"type": "RUN_COMPLETED", "event_id": 3},
        ]
        with open(trace_path, "w") as f:
            for event in stored:
                f.write(json.dumps(event) + "\n")

        broker = EventBroker(store=store)
        replayed: list[dict] = []
        async for event in broker._replay_stored("replay-run"):
            replayed.append(event)
        assert len(replayed) == 3
        assert replayed[0]["type"] == "RUN_STARTED"
        assert replayed[2]["type"] == "RUN_COMPLETED"

    @pytest.mark.asyncio
    async def test_replay_stored_run_record_events(self, tmp_path: Path):
        """Replay handles JsonlTraceStore files containing a full RunRecord."""
        from datetime import datetime, timezone
        from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus

        store = JsonlTraceStore(base_dir=tmp_path / "traces")
        now = datetime.now(timezone.utc).isoformat()
        run = RunRecord(
            id="record-run",
            workflow_id="wf",
            runtime="swarmgraph",
            status=RunStatus.COMPLETED,
            started_at=now,
            ended_at=now,
            events=[
                RunEvent(type="RUN_STARTED", timestamp=now, run_id="record-run", sequence=0, data={}),
                RunEvent(type="RUN_COMPLETED", timestamp=now, run_id="record-run", sequence=1, data={}),
            ],
        )
        store.save(run)

        broker = EventBroker(store=store)
        replayed: list[dict] = []
        async for event in broker._replay_stored("record-run"):
            replayed.append(event)

        assert [event["type"] for event in replayed] == ["RUN_STARTED", "RUN_COMPLETED"]
        assert [event["event_id"] for event in replayed] == [1, 2]

    @pytest.mark.asyncio
    async def test_replay_from_event_id(self, tmp_path: Path):
        """Replay from a specific event ID (reconnection)."""
        store = JsonlTraceStore(base_dir=tmp_path / "traces")
        trace_path = store.trace_path("reconnect-run")
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        stored = [
            {"type": "A", "event_id": 1},
            {"type": "B", "event_id": 2},
            {"type": "C", "event_id": 3},
            {"type": "D", "event_id": 4},
        ]
        with open(trace_path, "w") as f:
            for event in stored:
                f.write(json.dumps(event) + "\n")

        broker = EventBroker(store=store)
        replayed: list[dict] = []
        async for event in broker._replay_from("reconnect-run", from_event_id=2):
            replayed.append(event)
        assert len(replayed) == 2
        assert replayed[0]["type"] == "C"
        assert replayed[1]["type"] == "D"

    @pytest.mark.asyncio
    async def test_replay_missing_trace_is_noop(self, broker: EventBroker):
        replayed: list[dict] = []
        async for event in broker._replay_stored("nonexistent"):
            replayed.append(event)
        assert len(replayed) == 0
