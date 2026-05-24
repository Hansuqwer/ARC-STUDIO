import json
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.protocol.schemas import RunRecord
from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

runner = CliRunner()


def test_runs_budget_complete(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    store = JsonlTraceStore(ws / ".arc" / "traces")

    rec = RunRecord(
        id="run-budget-1",
        workflow_id="wf1",
        runtime="test",
        started_at="2024-01-01T00:00:00Z",
        events=[],
        status="completed",
        metadata={
            "budget": {"max_tokens": 1000, "max_cost": 5.0},
            "usage": {"total_tokens": 400, "total_cost": 0.5, "latency_ms": 1200},
        },
    )
    store.save(rec)

    result = runner.invoke(
        app, ["runs", "budget", "run-budget-1", "--workspace", str(ws), "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["ok"] is True
    assert data["data"]["budget"]["max_tokens"] == 1000
    assert data["data"]["usage"]["tokens"] == {"status": "available", "value": 400}
    assert data["data"]["usage"]["cost_usd"] == {"status": "available", "value": 0.5}
    assert data["data"]["usage"]["latency_ms"] == {"status": "available", "value": 1200}


def test_runs_budget_complete_over_limit(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    store = JsonlTraceStore(ws / ".arc" / "traces")
    rec = RunRecord(
        id="run-budget-over",
        workflow_id="wf-over",
        runtime="test",
        started_at="2024-01-01T00:00:00Z",
        events=[],
        status="completed",
        metadata={
            "budget": {"max_tokens": 100},
            "usage": {"total_tokens": 250, "total_cost": 1.0, "latency_ms": 50},
        },
    )
    store.save(rec)

    result = runner.invoke(
        app, ["runs", "budget", "run-budget-over", "--workspace", str(ws), "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["data"]["budget"]["max_tokens"] == 100
    assert data["data"]["usage"]["tokens"] == {"status": "available", "value": 250}


def test_runs_budget_partial(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    store = JsonlTraceStore(ws / ".arc" / "traces")

    rec = RunRecord(
        id="run-budget-2",
        workflow_id="wf2",
        runtime="test",
        started_at="2024-01-01T00:00:00Z",
        events=[],
        status="completed",
        metadata={"budget": {"max_cost": 10.0}, "usage": {"total_tokens": 150}},
    )
    store.save(rec)

    result = runner.invoke(
        app, ["runs", "budget", "run-budget-2", "--workspace", str(ws), "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["data"]["budget"]["max_cost"] == 10.0
    assert data["data"]["budget"].get("max_tokens") is None
    assert data["data"]["usage"]["tokens"] == {"status": "available", "value": 150}
    assert data["data"]["usage"]["cost_usd"] == {"status": "absent"}
    assert data["data"]["usage"]["latency_ms"] == {"status": "absent"}


def test_runs_budget_malformed(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    store = JsonlTraceStore(ws / ".arc" / "traces")
    rec = RunRecord(
        id="run-budget-bad",
        workflow_id="wf-bad",
        runtime="test",
        started_at="2024-01-01T00:00:00Z",
        events=[],
        status="completed",
        metadata={"usage": {"total_tokens": "many", "total_cost": -1, "latency_ms": 100}},
    )
    store.save(rec)

    result = runner.invoke(
        app, ["runs", "budget", "run-budget-bad", "--workspace", str(ws), "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["data"]["usage"]["tokens"] == {
        "status": "degraded",
        "raw": "many",
        "reason": "non_numeric",
    }
    assert data["data"]["usage"]["cost_usd"] == {
        "status": "degraded",
        "raw": -1,
        "reason": "negative_value",
    }
    assert data["data"]["usage"]["latency_ms"] == {"status": "available", "value": 100}


def test_runs_budget_missing(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    store = JsonlTraceStore(ws / ".arc" / "traces")

    rec = RunRecord(
        id="run-budget-3",
        workflow_id="wf3",
        runtime="test",
        started_at="2024-01-01T00:00:00Z",
        events=[],
        status="completed",
    )
    store.save(rec)

    result = runner.invoke(
        app, ["runs", "budget", "run-budget-3", "--workspace", str(ws), "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["data"]["budget"] == {}
    assert data["data"]["usage"]["tokens"] == {"status": "absent"}
    assert data["data"]["usage"]["cost_usd"] == {"status": "absent"}
    assert data["data"]["usage"]["latency_ms"] == {"status": "absent"}


def test_runs_budget_no_config_limits(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    store = JsonlTraceStore(ws / ".arc" / "traces")
    rec = RunRecord(
        id="run-budget-no-limits",
        workflow_id="wf-no-limits",
        runtime="test",
        started_at="2024-01-01T00:00:00Z",
        events=[],
        status="completed",
        metadata={"usage": {"total_tokens": 1, "total_cost": 0.01, "latency_ms": 5}},
    )
    store.save(rec)

    result = runner.invoke(
        app, ["runs", "budget", "run-budget-no-limits", "--workspace", str(ws), "--json"]
    )
    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["data"]["budget"] == {}
    assert data["data"]["usage"]["cost_usd"] == {"status": "available", "value": 0.01}


def test_runs_budget_not_found(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    result = runner.invoke(app, ["runs", "budget", "run-none", "--workspace", str(ws), "--json"])
    assert result.exit_code == 1
    data = json.loads(result.stdout)
    assert data["ok"] is False
    assert "not found" in data["error"]["message"].lower()


def test_runs_budget_cli_output(tmp_path: Path):
    ws = tmp_path / "ws"
    ws.mkdir()
    store = JsonlTraceStore(ws / ".arc" / "traces")

    rec = RunRecord(
        id="run-budget-4",
        workflow_id="wf4",
        runtime="test",
        started_at="2024-01-01T00:00:00Z",
        events=[],
        status="completed",
        metadata={"budget": {"max_cost": 5.0}, "usage": {"total_tokens": 400}},
    )
    store.save(rec)

    result = runner.invoke(app, ["runs", "budget", "run-budget-4", "--workspace", str(ws)])
    assert result.exit_code == 0
    assert "Budget & Usage:" in result.stdout
    assert "Max Cost:   $5.0000" in result.stdout
    assert "Total Tokens: 400" in result.stdout
    assert "Total Cost: n/a" in result.stdout
    assert "Latency: n/a" in result.stdout
