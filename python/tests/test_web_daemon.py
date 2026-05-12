import json

from aiohttp import ClientSession
from aiohttp.web import AppRunner, TCPSite

from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
from agent_runtime_cockpit.web.server import create_app


async def test_runs_api_and_sse_events(tmp_path, unused_tcp_port):
    trace_dir = tmp_path / ".arc" / "traces"
    run = RunRecord(
        id="run-daemon-test",
        workflow_id="wf-test",
        runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:00:01Z",
        events=[
            RunEvent(
                type="RUN_STARTED",
                timestamp="2026-01-01T00:00:00Z",
                run_id="run-daemon-test",
                sequence=0,
                data={"workflow_id": "wf-test"},
            ),
            RunEvent(
                type="RUN_COMPLETED",
                timestamp="2026-01-01T00:00:01Z",
                run_id="run-daemon-test",
                sequence=1,
                data={"ok": True},
            ),
        ],
        metadata={},
    )
    JsonlTraceStore(trace_dir).save(run)

    app = await create_app(tmp_path)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    base_url = f"http://127.0.0.1:{unused_tcp_port}"
    try:
        async with ClientSession() as session:
            async with session.get(f"{base_url}/api/runs") as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["ok"] is True
                assert payload["data"][0]["id"] == "run-daemon-test"

            async with session.get(f"{base_url}/api/runs/run-daemon-test/events") as response:
                body = await response.text()
                assert response.status == 200
                lines = [line.removeprefix("data: ") for line in body.splitlines() if line.startswith("data: ")]
                events = [json.loads(line) for line in lines]
                assert events[0]["type"] == "RUN_STARTED"
                assert events[1]["type"] == "RUN_COMPLETED"
                assert events[-1]["type"] == "STREAM_END"

            async with session.get(f"{base_url}/api/providers") as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["ok"] is True
                assert {provider["id"] for provider in payload["data"]} >= {"openai", "anthropic", "openrouter", "qwen", "kimi"}

            async with session.get(f"{base_url}/api/providers/routing") as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["data"]["dry_run"] is True
                assert payload["data"]["allow_paid_calls"] is False

            async with session.get(f"{base_url}/api/runtimes/capabilities") as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["data"]["auto_priority"] == ["swarmgraph", "langgraph", "crewai"]
                ids = {runtime["runtime_id"] for runtime in payload["data"]["runtimes"]}
                assert ids >= {"swarmgraph", "langgraph", "crewai"}
                assert all("requires_paid_calls" in runtime for runtime in payload["data"]["runtimes"])
    finally:
        await runner.cleanup()
