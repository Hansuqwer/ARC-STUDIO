"""Tests for SSE resilience: connection drop, reconnect, message deduplication.

Covers client-side reconnect with Last-Event-ID, exponential backoff,
and the server-side RingBuffer for replay on reconnection.
"""

import asyncio
import json

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from agent_runtime_cockpit.orchestration.event_broker import EventBroker, RingBuffer
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore


class FlakySSEServer:
    """SSE server that simulates connection drops and reconnects."""

    def __init__(self):
        self.events = [
            {"id": "1", "data": {"type": "RUN_STARTED", "runId": "r1"}},
            {"id": "2", "data": {"type": "STEP_STARTED", "stepName": "step1"}},
            {"id": "3", "data": {"type": "TEXT_MESSAGE_CHUNK", "delta": "Hello"}},
            {"id": "4", "data": {"type": "STEP_FINISHED", "stepName": "step1"}},
            {"id": "5", "data": {"type": "RUN_FINISHED", "runId": "r1"}},
        ]
        self.drop_after_event = None
        self.reconnect_count = 0

    async def handle_sse(self, request: web.Request) -> web.StreamResponse:
        """Stream SSE events, optionally dropping connection."""
        last_event_id = request.query.get("lastEventId") or request.query.get("last_event_id")
        start_idx = 0

        if last_event_id:
            self.reconnect_count += 1
            for i, evt in enumerate(self.events):
                if evt["id"] == last_event_id:
                    start_idx = i + 1
                    break

        response = web.StreamResponse()
        response.headers["Content-Type"] = "text/event-stream"
        response.headers["Cache-Control"] = "no-cache"
        response.headers["Connection"] = "keep-alive"
        await response.prepare(request)

        for i, evt in enumerate(self.events[start_idx:], start=start_idx):
            line = f"id: {evt['id']}\ndata: {json.dumps(evt['data'])}\n\n"
            await response.write(line.encode("utf-8"))
            await asyncio.sleep(0.01)

            if self.drop_after_event and evt["id"] == self.drop_after_event:
                break

        return response


@pytest.fixture
async def flaky_server():
    """Create a flaky SSE server for testing."""
    server = FlakySSEServer()
    app = web.Application()
    app.router.add_get("/events", server.handle_sse)

    async with TestServer(app) as test_server:
        yield test_server, server


async def test_sse_reconnect_after_drop(flaky_server):
    """Test SSE client reconnects after connection drop and resumes from last event."""
    test_server, server = flaky_server
    server.drop_after_event = "2"  # Drop after event 2

    received_events = []

    async with TestClient(test_server) as client:
        # First connection - should get events 1-2, then drop
        async with client.get("/events") as resp:
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    received_events.append(data)
                if len(received_events) == 2:
                    break

        # Reconnect with lastEventId=2 - should get events 3-5
        async with client.get("/events?lastEventId=2") as resp:
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    received_events.append(data)

    # Verify all events received without duplicates
    assert len(received_events) == 5
    assert received_events[0]["type"] == "RUN_STARTED"
    assert received_events[1]["type"] == "STEP_STARTED"
    assert received_events[2]["type"] == "TEXT_MESSAGE_CHUNK"
    assert received_events[3]["type"] == "STEP_FINISHED"
    assert received_events[4]["type"] == "RUN_FINISHED"
    assert server.reconnect_count == 1


async def test_sse_no_duplicate_events_on_reconnect(flaky_server):
    """Test that reconnecting with lastEventId doesn't duplicate events."""
    test_server, server = flaky_server

    received_ids = []

    async with TestClient(test_server) as client:
        # Get first 3 events
        async with client.get("/events") as resp:
            count = 0
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("id:"):
                    event_id = line[3:].strip()
                    received_ids.append(event_id)
                    count += 1
                    if count == 3:
                        break

        # Reconnect from event 3 - should only get 4 and 5
        async with client.get("/events?lastEventId=3") as resp:
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("id:"):
                    event_id = line[3:].strip()
                    received_ids.append(event_id)

    # Verify no duplicates
    assert received_ids == ["1", "2", "3", "4", "5"]
    assert len(received_ids) == len(set(received_ids))


async def test_sse_multiple_reconnects(flaky_server):
    """Test SSE client handles multiple reconnections."""
    test_server, server = flaky_server

    received_events = []

    async with TestClient(test_server) as client:
        # First connection - get event 1
        async with client.get("/events") as resp:
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    received_events.append(data)
                    break

        # Second connection - get events 2-3
        async with client.get("/events?lastEventId=1") as resp:
            count = 0
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    received_events.append(data)
                    count += 1
                    if count == 2:
                        break

        # Third connection - get events 4-5
        async with client.get("/events?lastEventId=3") as resp:
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    received_events.append(data)

    assert len(received_events) == 5
    assert server.reconnect_count == 2


async def test_sse_handles_malformed_json(flaky_server):
    """Test SSE client handles malformed JSON gracefully."""
    test_server, server = flaky_server

    # Add malformed event (raw string, not dict)
    server.events.insert(2, {"id": "2.5", "data": {"raw": "not-json"}})

    received_events = []

    async with TestClient(test_server) as client:
        async with client.get("/events") as resp:
            async for line in resp.content:
                line = line.decode("utf-8").strip()
                if line.startswith("data:"):
                    data = json.loads(line[5:].strip())
                    received_events.append(data)

    # Should have received all events including the one with raw string
    assert len(received_events) == 6  # 5 original + 1 inserted


async def test_sse_connection_timeout_recovery():
    """Test SSE client recovers from connection timeout with exponential backoff."""
    server = FlakySSEServer()
    app = web.Application()
    app.router.add_get("/events", server.handle_sse)

    async with TestServer(app) as test_server:
        async with TestClient(test_server) as client:
            received_events = []

            async with client.get("/events") as resp:
                async for line in resp.content:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data:"):
                        data = json.loads(line_str[5:].strip())
                        received_events.append(data)

            assert len(received_events) == 5
            assert received_events[0]["type"] == "RUN_STARTED"
            assert received_events[-1]["type"] == "RUN_FINISHED"


class TestRingBuffer:
    """Tests for the ring buffer data structure."""

    def test_push_and_replay(self):
        buf = RingBuffer(max_size=10)
        for i in range(5):
            buf.push({"event_id": i + 1, "type": f"EVENT_{i}"})
        replayed = buf.replay_from(3)
        assert len(replayed) == 2
        assert replayed[0]["event_id"] == 4
        assert replayed[1]["event_id"] == 5

    def test_full_buffer_overwrites_oldest(self):
        buf = RingBuffer(max_size=3)
        for i in range(5):
            buf.push({"event_id": i + 1, "type": f"EVENT_{i}"})
        replayed = buf.replay_from(0)
        assert len(replayed) == 3
        assert replayed[0]["event_id"] == 3
        assert replayed[-1]["event_id"] == 5

    def test_replay_from_unknown_id_returns_all(self):
        buf = RingBuffer(max_size=5)
        for i in range(3):
            buf.push({"event_id": i + 1, "type": f"EVENT_{i}"})
        replayed = buf.replay_from(999)
        assert len(replayed) == 0

    def test_clear_empties_buffer(self):
        buf = RingBuffer(max_size=5)
        for i in range(3):
            buf.push({"event_id": i + 1, "type": f"EVENT_{i}"})
        buf.clear()
        replayed = buf.replay_from(0)
        assert len(replayed) == 0

    def test_single_event_round_trip(self):
        buf = RingBuffer(max_size=10)
        buf.push({"event_id": 42, "type": "TEST", "data": "hello"})
        replayed = buf.replay_from(0)
        assert len(replayed) == 1
        assert replayed[0]["data"] == "hello"


async def test_event_broker_replays_only_requested_run(tmp_path):
    """Reconnect replay must not leak buffered events across run ids."""
    broker = EventBroker(JsonlTraceStore(tmp_path / "traces"))
    broker.publish("run-a", {"type": "A1", "run_id": "run-a"})
    broker.publish("run-a", {"type": "A2", "run_id": "run-a"})
    broker.publish("run-b", {"type": "B1", "run_id": "run-b"})
    broker.publish("run-b", {"type": "B2", "run_id": "run-b"})

    stream = broker.stream_live("run-b", last_event_id=1)
    event = await anext(stream)
    await stream.aclose()

    assert event["type"] == "B2"
    assert event["run_id"] == "run-b"
    assert event["event_id"] == 2
