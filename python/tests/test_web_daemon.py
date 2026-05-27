import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from aiohttp import ClientSession
from aiohttp.web import AppRunner, TCPSite

from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
from agent_runtime_cockpit.web.server import create_app

_TRUST = "agent_runtime_cockpit.web.routes.enforce_workspace_trust"


@pytest.fixture(autouse=True)
def _bypass_trust_for_daemon_integration_tests():
    """Phase 50: patch trust for all daemon integration tests.

    These tests exercise runtime routing, SSE, and run lifecycle behavior —
    not workspace trust enforcement. Trust is explicitly tested in
    tests/web/test_phase50_trust_surface_audit.py.
    """
    with patch(_TRUST):
        yield


def _write_swarmgraph_cli(tools_dir: Path) -> Path:
    cli = tools_dir / "swarmgraph"
    cli.parent.mkdir(parents=True, exist_ok=True)
    cli.write_text(
        "#!/usr/bin/env sh\n"
        'printf \'%s\n\' \'{"swarm_id":"sg-api","status":"completed","worker_count":0,"final_output":"ok"}\'\n'
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    return cli


def _write_langgraph_export(workspace: Path) -> None:
    sys.modules.pop("graph_module", None)
    (workspace / "graph_module.py").write_text(
        "class Graph:\n"
        "    def invoke(self, inputs):\n"
        "        return {'messages': ['langgraph-ok'], 'inputs': inputs}\n"
        "def build_graph():\n"
        "    return Graph()\n"
    )


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
                lines = [
                    line.removeprefix("data: ")
                    for line in body.splitlines()
                    if line.startswith("data: ")
                ]
                events = [json.loads(line) for line in lines]
                assert events[0]["type"] == "RUN_STARTED"
                assert events[1]["type"] == "RUN_COMPLETED"
                assert events[-1]["type"] == "STREAM_END"

            async with session.get(f"{base_url}/api/runs/missing-run/events") as response:
                body = await response.text()
                assert response.status == 200
                lines = [
                    line.removeprefix("data: ")
                    for line in body.splitlines()
                    if line.startswith("data: ")
                ]
                events = [json.loads(line) for line in lines]
                assert events[0]["type"] == "RUN_ERROR"
                assert events[0]["data"]["code"] == "RUN_NOT_FOUND"
                assert events[-1]["type"] == "STREAM_END"

            async with session.get(f"{base_url}/api/providers") as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["ok"] is True
                assert {provider["id"] for provider in payload["data"]} >= {
                    "openai",
                    "anthropic",
                    "openrouter",
                    "qwen",
                    "kimi",
                }

            async with session.get(f"{base_url}/api/providers/routing") as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["data"]["dry_run"] is True
                assert payload["data"]["allow_paid_calls"] is False

            async with session.get(f"{base_url}/api/runtimes/capabilities") as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["data"]["auto_priority"] == [
                    "swarmgraph",
                    "langgraph",
                    "crewai",
                    "lmarena",
                ]
                ids = {runtime["runtime_id"] for runtime in payload["data"]["runtimes"]}
                assert ids >= {"swarmgraph", "langgraph", "crewai", "lmarena"}
                assert all(
                    "requires_paid_calls" in runtime for runtime in payload["data"]["runtimes"]
                )
    finally:
        await runner.cleanup()


async def test_start_run_runtime_body_selects_langgraph(monkeypatch, tmp_path, unused_tcp_port):
    ws = tmp_path / "ws"
    ws.mkdir()
    cli = _write_swarmgraph_cli(tmp_path / "bin")
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))
    _write_langgraph_export(ws)
    monkeypatch.setenv("ARC_LANGGRAPH_EXPORT", "graph_module:build_graph")

    app = await create_app(ws)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    try:
        async with ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/start",
                json={
                    "workflow_id": "wf-lg",
                    "runtime": "langgraph",
                    "inputs": {"prompt": "hello"},
                },
            ) as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["data"]["runtime"] == "langgraph"
                assert payload["data"]["runtime_selection"]["runtime"] == "langgraph"
                assert payload["data"]["events"][-1]["data"]["state"]["messages"] == [
                    "langgraph-ok"
                ]
    finally:
        await runner.cleanup()


async def test_start_run_runtime_body_rejects_unknown(tmp_path, unused_tcp_port):
    app = await create_app(tmp_path)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    try:
        async with ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/start",
                json={"workflow_id": "wf-bad", "runtime": "garbage"},
            ) as response:
                payload = await response.json()
                assert response.status == 400
                assert payload["error"]["code"] == "invalid_runtime"
    finally:
        await runner.cleanup()


async def test_start_run_get_runtime_query_uses_same_router(monkeypatch, tmp_path, unused_tcp_port):
    _write_langgraph_export(tmp_path)
    monkeypatch.setenv("ARC_LANGGRAPH_EXPORT", "graph_module:build_graph")

    app = await create_app(tmp_path)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    try:
        async with ClientSession() as session:
            async with session.get(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/start?workflow_id=wf-get-lg&runtime=langgraph",
            ) as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["data"]["runtime"] == "langgraph"
                assert payload["data"]["runtime_selection"]["runtime"] == "langgraph"
    finally:
        await runner.cleanup()


async def test_start_run_allow_paid_calls_true_does_not_change_swarmgraph_stub(
    monkeypatch, tmp_path, unused_tcp_port
):
    ws = tmp_path / "ws"
    ws.mkdir()
    cli = _write_swarmgraph_cli(tmp_path / "bin")
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))
    monkeypatch.delenv("ARC_LANGGRAPH_EXPORT", raising=False)

    app = await create_app(ws)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    try:
        async with ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/start",
                json={"workflow_id": "wf-paid-flag", "runtime": "auto", "allow_paid_calls": True},
            ) as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["data"]["runtime"] == "swarmgraph"
                assert payload["data"]["metadata"]["cost_allowed"] is False
    finally:
        await runner.cleanup()


async def test_start_run_runtime_body_crewai_not_runnable(tmp_path, unused_tcp_port):
    app = await create_app(tmp_path)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    try:
        async with ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/start",
                json={"workflow_id": "wf-ca", "runtime": "crewai"},
            ) as response:
                payload = await response.json()
                assert response.status == 501
                assert payload["error"]["details"]["code"] == "RUNTIME_NOT_RUNNABLE"
    finally:
        await runner.cleanup()


async def test_start_run_runtime_body_omitted_uses_auto(monkeypatch, tmp_path, unused_tcp_port):
    ws = tmp_path / "ws"
    ws.mkdir()
    cli = _write_swarmgraph_cli(tmp_path / "bin")
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))
    monkeypatch.delenv("ARC_LANGGRAPH_EXPORT", raising=False)

    app = await create_app(ws)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    try:
        async with ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/start",
                json={"workflow_id": "wf-auto"},
            ) as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["data"]["runtime_selection"]["chosen_by"] == "auto"
                assert payload["data"]["runtime_selection"]["runtime"] == "swarmgraph"
    finally:
        await runner.cleanup()


async def test_start_run_runtime_body_auto_selects_only_langgraph(
    monkeypatch, tmp_path, unused_tcp_port
):
    _write_langgraph_export(tmp_path)
    monkeypatch.setenv("ARC_LANGGRAPH_EXPORT", "graph_module:build_graph")

    app = await create_app(tmp_path)
    runner = AppRunner(app)
    await runner.setup()
    site = TCPSite(runner, "127.0.0.1", unused_tcp_port)
    await site.start()
    try:
        async with ClientSession() as session:
            async with session.post(
                f"http://127.0.0.1:{unused_tcp_port}/api/runs/start",
                json={"workflow_id": "wf-auto-lg", "runtime": "auto"},
            ) as response:
                payload = await response.json()
                assert response.status == 200
                assert payload["data"]["runtime_selection"]["chosen_by"] == "auto"
                assert payload["data"]["runtime_selection"]["runtime"] == "langgraph"
    finally:
        await runner.cleanup()
