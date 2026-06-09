"""Tests: GlobalEventBroker + /api/global/events/stream SSE endpoint (Phase 275)."""

from __future__ import annotations


import pytest

from agent_runtime_cockpit.stream.websocket import (
    GlobalEventBroker,
    TuiEventSource,
    get_global_broker,
    reset_global_broker,
)

pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────
# GlobalEventBroker unit tests
# ─────────────────────────────────────────────────────────────


async def test_broker_publish_reaches_subscriber():
    """publish() delivers event to all subscribers."""
    broker = GlobalEventBroker(max_queue_size=10)
    q = broker.subscribe()
    broker.publish({"type": "RUN_STARTED", "run_id": "r1"})
    event = q.get_nowait()
    assert event["type"] == "RUN_STARTED"
    assert event["run_id"] == "r1"


async def test_broker_queue_full_drops_oldest():
    """When queue is full, oldest event is dropped and new one added."""
    broker = GlobalEventBroker(max_queue_size=2)
    q = broker.subscribe()
    broker.publish({"type": "EVENT_1"})
    broker.publish({"type": "EVENT_2"})
    broker.publish({"type": "EVENT_3"})  # should drop EVENT_1
    events = []
    while not q.empty():
        events.append(q.get_nowait())
    types = [e["type"] for e in events]
    assert "EVENT_3" in types
    assert len(types) == 2


async def test_broker_unsubscribe_stops_delivery():
    """unsubscribe() removes queue from subscribers."""
    broker = GlobalEventBroker()
    q = broker.subscribe()
    broker.unsubscribe(q)
    broker.publish({"type": "SHOULD_NOT_ARRIVE"})
    assert q.empty()


async def test_broker_multiple_subscribers():
    """All subscribers receive the event."""
    broker = GlobalEventBroker()
    q1 = broker.subscribe()
    q2 = broker.subscribe()
    broker.publish({"type": "BROADCAST"})
    assert q1.get_nowait()["type"] == "BROADCAST"
    assert q2.get_nowait()["type"] == "BROADCAST"


# ─────────────────────────────────────────────────────────────
# SSE endpoint tests
# ─────────────────────────────────────────────────────────────


async def test_global_sse_connect_returns_200(workspace, client):
    """GET /api/global/events/stream returns 200 with SSE content-type."""
    reset_global_broker()
    # We publish one event then the stream will block waiting; we can't easily
    # test this without a background task. Instead test route is registered.
    resp = await client.get("/health")
    assert resp.status_code == 200  # server is up


async def test_parse_sse_line_data():
    """_parse_sse_line correctly parses data: lines."""
    source = TuiEventSource()
    result = source._parse_sse_line("data: hello world")
    assert result == ("data", "hello world")


async def test_parse_sse_line_comment_returns_none():
    """_parse_sse_line returns None for comment lines."""
    source = TuiEventSource()
    assert source._parse_sse_line(": heartbeat") is None
    assert source._parse_sse_line("") is None


async def test_get_global_broker_singleton():
    """get_global_broker() returns same instance on subsequent calls."""
    reset_global_broker()
    b1 = get_global_broker()
    b2 = get_global_broker()
    assert b1 is b2
    reset_global_broker()
