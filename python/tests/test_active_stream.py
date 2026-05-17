import asyncio
import json

from aiohttp import ClientSession
from aiohttp.web import AppRunner, TCPSite

from agent_runtime_cockpit.orchestration.event_broker import EventBroker
from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
from agent_runtime_cockpit.web.keys import EVENT_BROKER_KEY
from agent_runtime_cockpit.web.server import create_app


async def _read_sse_events(response) -> list[dict]:
    events = []
    async for raw in response.content:
        line = raw.decode().strip()
        if not line.startswith("data: "):
            continue
        event = json.loads(line.removeprefix("data: "))
        events.append(event)
        if event.get("type") == "STREAM_END":
            break
    return events


async def test_active_run_sse_live_closes_on_terminal_event(tmp_path, unused_tcp_port):
    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    app = await create_app(tmp_path)
    broker = EventBroker(store)
    app[EVENT_BROKER_KEY] = broker
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    run_id = "run-live-contract"
    try:
        async with ClientSession() as session:
            async with session.get(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/{run_id}/events?mode=live",
            ) as response:
                assert response.status == 200
                await asyncio.sleep(0.01)
                broker.publish(run_id, {
                    "type": "RUN_STARTED",
                    "run_id": run_id,
                    "sequence": 0,
                    "data": {"workflow_id": "wf-live"},
                })
                broker.publish(run_id, {
                    "type": "RUN_COMPLETED",
                    "run_id": run_id,
                    "sequence": 1,
                    "data": {"ok": True},
                })
                events = await _read_sse_events(response)

        assert [event["type"] for event in events] == ["RUN_STARTED", "RUN_COMPLETED", "STREAM_END"]
        assert events[0]["run_id"] == run_id
        assert events[0]["sequence"] == 0
        assert events[0]["data"] == {"workflow_id": "wf-live"}
        assert events[-1]["mode"] == "live"
    finally:
        await runner.cleanup()


async def test_active_run_sse_replay_is_distinct_from_live(tmp_path, unused_tcp_port):
    run_id = "run-replay-contract"
    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    store.save(RunRecord(
        id=run_id,
        workflow_id="wf-replay",
        runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:00:01Z",
        events=[
            RunEvent(
                type="RUN_STARTED",
                timestamp="2026-01-01T00:00:00Z",
                run_id=run_id,
                sequence=0,
                data={"workflow_id": "wf-replay"},
            ),
            RunEvent(
                type="RUN_COMPLETED",
                timestamp="2026-01-01T00:00:01Z",
                run_id=run_id,
                sequence=1,
                data={"ok": True},
            ),
        ],
        metadata={},
    ))

    app = await create_app(tmp_path)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    try:
        async with ClientSession() as session:
            async with session.get(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/{run_id}/events?mode=replay",
            ) as response:
                assert response.status == 200
                events = await _read_sse_events(response)

        assert [event["type"] for event in events] == ["RUN_STARTED", "RUN_COMPLETED", "STREAM_END"]
        assert events[0]["run_id"] == run_id
        assert events[0]["sequence"] == 0
        assert events[0]["data"] == {"workflow_id": "wf-replay"}
        assert events[-1]["mode"] == "replay"
    finally:
        await runner.cleanup()


async def test_active_run_sse_client_disconnect_is_safe(tmp_path, unused_tcp_port):
    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    app = await create_app(tmp_path)
    broker = EventBroker(store)
    app[EVENT_BROKER_KEY] = broker
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    run_id = "run-disconnect-contract"
    try:
        async with ClientSession() as session:
            response = await session.get(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/{run_id}/events?mode=live",
            )
            await asyncio.sleep(0.01)
            response.close()
            broker.publish(run_id, {
                "type": "RUN_STARTED",
                "run_id": run_id,
                "sequence": 0,
                "data": {},
            })
            broker.publish(run_id, {
                "type": "RUN_CANCELLED",
                "run_id": run_id,
                "sequence": 1,
                "data": {},
            })
            await asyncio.sleep(0.01)
    finally:
        await runner.cleanup()
