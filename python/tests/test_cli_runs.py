import json


from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app


def test_run_command_persists_trace_in_workspace(monkeypatch, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".arc" / "traces").mkdir(parents=True)
    (ws / ".arc" / "audit").mkdir(parents=True)
    tools = tmp_path / "bin"
    tools.mkdir(parents=True, exist_ok=True)
    cli = tools / "swarmgraph"
    cli.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\n' '{\"swarm_id\":\"sg-cli\",\"status\":\"completed\",\"worker_count\":0,\"final_output\":\"ok\"}'\n"
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(ws), "--prompt", "cli prompt", "--json"])

    assert result.exit_code == 0, f"exit {result.exit_code}: {result.stdout[:500]}"
    traces = list((ws / ".arc" / "traces").glob("run-sg-*.jsonl"))
    assert len(traces) == 1
    assert str(traces[0]) in result.output
    assert "cli prompt" in result.output


def test_run_command_rejects_unknown_runtime(tmp_path):
    result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(tmp_path), "--runtime", "nope", "--json"])

    assert result.exit_code == 2
    envelope = json.loads(result.output)
    assert envelope["ok"] is False
    assert envelope["error"]["details"]["code"] == "UNKNOWN_RUNTIME"


def test_run_command_reports_crewai_missing_target(tmp_path):
    result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(tmp_path), "--runtime", "crewai", "--json"])

    assert result.exit_code == 1
    envelope = json.loads(result.output)
    assert envelope["ok"] is False
    assert envelope["error"]["details"]["code"] == "RUNTIME_NOT_RUNNABLE"


def test_runtimes_capabilities_json(tmp_path):
    result = CliRunner().invoke(app, ["runtimes", "--workspace", str(tmp_path), "--capabilities", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert payload["auto_priority"] == ["swarmgraph", "langgraph", "crewai", "lmarena"]
    ids = {runtime["runtime_id"] for runtime in payload["runtimes"]}
    assert ids >= {"swarmgraph", "langgraph", "crewai", "lmarena"}
    assert all("requires_paid_calls" in runtime for runtime in payload["runtimes"])


def test_runtimes_capabilities_table(tmp_path):
    result = CliRunner().invoke(app, ["runtimes", "--workspace", str(tmp_path), "--capabilities"])

    assert result.exit_code == 0, result.output
    assert "auto priority: swarmgraph > langgraph > crewai > lmarena" in result.output
    assert "swarmgraph" in result.output
    assert "crewai" in result.output


def test_runs_command_reads_workspace_traces(monkeypatch, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".arc" / "traces").mkdir(parents=True)
    (ws / ".arc" / "audit").mkdir(parents=True)
    tools = tmp_path / "bin"
    tools.mkdir(parents=True, exist_ok=True)
    cli = tools / "swarmgraph"
    cli.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\n' '{\"swarm_id\":\"sg-list\",\"status\":\"completed\",\"worker_count\":0,\"final_output\":\"ok\"}'\n"
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    run_result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(ws), "--json"])
    assert run_result.exit_code == 0, run_result.output

    list_result = CliRunner().invoke(app, ["runs", "--workspace", str(ws), "--json"])
    assert list_result.exit_code == 0, list_result.output
    assert "sg-list" in list_result.output
    assert str(ws / ".arc" / "traces") in list_result.output

    run_id = json.loads(run_result.output)["data"]["id"]
    get_result = CliRunner().invoke(app, ["runs", "get", run_id, "--workspace", str(ws), "--json"])
    assert get_result.exit_code == 0, get_result.output
    assert json.loads(get_result.output)["data"]["id"] == run_id

    trace_result = CliRunner().invoke(app, ["runs", "trace", run_id, "--workspace", str(ws), "--tail", "1", "--json"])
    assert trace_result.exit_code == 0, trace_result.output
    trace_data = json.loads(trace_result.output)["data"]
    assert trace_data["run_id"] == run_id
    assert trace_data["line_count"] == 1
    assert len(trace_data["tail"]) == 1


def test_runs_get_missing_returns_error(tmp_path):
    result = CliRunner().invoke(app, ["runs", "get", "missing-run", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 1
    envelope = json.loads(result.output)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] == "RUN_NOT_FOUND"


def test_runs_trace_missing_returns_error(tmp_path):
    result = CliRunner().invoke(app, ["runs", "trace", "missing-run", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 1
    envelope = json.loads(result.output)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] == "RUN_NOT_FOUND"


def test_runs_command_lists_newest_first(monkeypatch, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".arc" / "traces").mkdir(parents=True)
    (ws / ".arc" / "audit").mkdir(parents=True)
    tools = tmp_path / "bin"
    tools.mkdir(parents=True, exist_ok=True)
    cli = tools / "swarmgraph"
    counter = tmp_path / "counter"
    cli.write_text(
        "#!/usr/bin/env sh\n"
        f"count=$(cat {counter} 2>/dev/null || printf 0)\n"
        "count=$((count + 1))\n"
        f"printf '%s' \"$count\" > {counter}\n"
        "printf '%s\n' \"{\\\"swarm_id\\\":\\\"sg-$count\\\",\\\"status\\\":\\\"completed\\\",\\\"worker_count\\\":0,\\\"final_output\\\":\\\"ok-$count\\\"}\"\n"
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    first = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(ws), "--json"])
    second = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(ws), "--json"])
    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output

    listed = CliRunner().invoke(app, ["runs", "--workspace", str(ws), "--json"])
    assert listed.exit_code == 0, listed.output
    data = json.loads(listed.output)["data"]
    assert data[0]["metadata"]["swarm_id"] == "sg-2"
    assert data[1]["metadata"]["swarm_id"] == "sg-1"


def test_runs_prune_is_dry_run_by_default(monkeypatch, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".arc" / "traces").mkdir(parents=True)
    (ws / ".arc" / "audit").mkdir(parents=True)
    tools = tmp_path / "bin"
    tools.mkdir(parents=True, exist_ok=True)
    cli = tools / "swarmgraph"
    cli.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\n' '{\"swarm_id\":\"sg-prune\",\"status\":\"completed\",\"worker_count\":0,\"final_output\":\"ok\"}'\n"
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    for _ in range(3):
        result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(ws), "--json"])
        assert result.exit_code == 0, result.output

    prune = CliRunner().invoke(app, ["runs", "prune", "--workspace", str(ws), "--keep", "1", "--json"])
    assert prune.exit_code == 0, prune.output
    payload = json.loads(prune.output)["data"]
    assert payload["dry_run"] is True
    assert len(payload["would_delete"]) == 2
    assert len(list((ws / ".arc" / "traces").glob("*.jsonl"))) == 3


def test_runs_prune_deletes_only_with_yes(monkeypatch, tmp_path):
    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / ".arc" / "traces").mkdir(parents=True)
    (ws / ".arc" / "audit").mkdir(parents=True)
    tools = tmp_path / "bin"
    tools.mkdir(parents=True, exist_ok=True)
    cli = tools / "swarmgraph"
    cli.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\n' '{\"swarm_id\":\"sg-prune\",\"status\":\"completed\",\"worker_count\":0,\"final_output\":\"ok\"}'\n"
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    for _ in range(3):
        result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(ws), "--json"])
        assert result.exit_code == 0, result.output

    prune = CliRunner().invoke(app, ["runs", "prune", "--workspace", str(ws), "--keep", "1", "--yes", "--json"])
    assert prune.exit_code == 0, prune.output
    payload = json.loads(prune.output)["data"]
    assert payload["dry_run"] is False
    assert len(payload["deleted"]) == 2
    assert len(list((ws / ".arc" / "traces").glob("*.jsonl"))) == 1


def test_runs_diff_compares_two_runs(tmp_path):
    """arc runs diff produces a RunDiff for two stored traces."""
    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunEvent, RunStatus
    from datetime import datetime, timezone
    ws = tmp_path / "ws"
    traces = ws / ".arc" / "traces"
    traces.mkdir(parents=True)
    now = datetime.now(timezone.utc)

    def _write(run):
        (traces / f"{run.id}.jsonl").write_text(run.model_dump_json())

    a = RunRecord(
        id="run-a", workflow_id="wf", runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at=now.isoformat(), ended_at=now.isoformat(),
        events=[RunEvent(type="RUN_STARTED", timestamp=now.isoformat(), run_id="run-a", sequence=0, data={}),
                RunEvent(type="TOOL_CALL", timestamp=now.isoformat(), run_id="run-a", sequence=1, data={}),
                RunEvent(type="RUN_COMPLETED", timestamp=now.isoformat(), run_id="run-a", sequence=2, data={})],
    )
    b = RunRecord(
        id="run-b", workflow_id="wf", runtime="langgraph",
        status=RunStatus.FAILED,
        started_at=now.isoformat(), ended_at=now.isoformat(),
        events=[RunEvent(type="RUN_STARTED", timestamp=now.isoformat(), run_id="run-b", sequence=0, data={}),
                RunEvent(type="RUN_FAILED", timestamp=now.isoformat(), run_id="run-b", sequence=1, data={})],
    )
    _write(a)
    _write(b)

    result = CliRunner().invoke(app, ["runs", "diff", "run-a", "run-b", "--workspace", str(ws), "--json"])
    assert result.exit_code == 0, result.output
    diff = json.loads(result.output)["data"]
    assert diff["run_a_id"] == "run-a"
    assert diff["run_b_id"] == "run-b"
    assert diff["status_a"] == "completed"
    assert diff["status_b"] == "failed"
    assert diff["event_count_a"] == 3
    assert diff["event_count_b"] == 2
    assert "TOOL_CALL" in diff["types_only_in_a"]
    assert "RUN_FAILED" in diff["types_only_in_b"]
    assert "RUN_STARTED" in diff["types_common"]
    assert diff["tool_calls_a"] == 1
    assert diff["tool_calls_b"] == 0


def test_runs_diff_missing_run_returns_error(tmp_path):
    """arc runs diff with missing run IDs returns RUN_NOT_FOUND."""
    ws = tmp_path / "ws"
    (ws / ".arc" / "traces").mkdir(parents=True)
    result = CliRunner().invoke(app, ["runs", "diff", "missing-a", "missing-b", "--workspace", str(ws), "--json"])
    assert result.exit_code == 1
    envelope = json.loads(result.output)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] == "RUN_NOT_FOUND"


def test_runs_prune_rejects_negative_keep(tmp_path):
    result = CliRunner().invoke(app, ["runs", "prune", "--workspace", str(tmp_path), "--keep", "-1", "--json"])
    assert result.exit_code != 0


def test_runs_prune_refuses_symlink_outside_trace_dir(tmp_path):
    trace_dir = tmp_path / ".arc" / "traces"
    trace_dir.mkdir(parents=True)
    outside = tmp_path / "outside.jsonl"
    outside.write_text("{}\n")
    (trace_dir / "a.jsonl").write_text("{}\n")
    (trace_dir / "b.jsonl").symlink_to(outside)

    result = CliRunner().invoke(app, ["runs", "prune", "--workspace", str(tmp_path), "--keep", "0", "--yes", "--json"])
    assert result.exit_code != 0
    assert outside.exists()
