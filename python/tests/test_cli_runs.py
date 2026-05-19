import json


from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus


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


def test_run_unknown_profile_fails_closed(tmp_path):
    result = CliRunner().invoke(app, [
        "run", "wf-test", "--workspace", str(tmp_path), "--profile-id", "missing", "--json",
    ])
    assert result.exit_code == 2
    envelope = json.loads(result.output)
    assert envelope["ok"] is False
    assert envelope["error"]["details"]["code"] == "UNKNOWN_PROFILE"


def test_run_dry_run_crewai_swarmgraph_returns_blockers_no_trace(tmp_path):
    result = CliRunner().invoke(app, [
        "run", "crew.py",
        "--workspace", str(tmp_path),
        "--runtime", "crewai+swarmgraph",
        "--dry-run",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert payload["runtime"] == "crewai+swarmgraph"
    assert payload["dry_run"] is True
    assert payload["provider_call"] is False
    assert payload["runnable"] is False
    codes = {blocker["code"] for blocker in payload["blockers"]}
    assert "MISSING_CREWAI_EXPORT" in codes
    assert payload["dependency_status"]["runtime_mode"] == "fake/offline"
    assert not (tmp_path / ".arc" / "traces").exists()


def test_run_dry_run_crewai_swarmgraph_fake_ready_no_execution(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_CREWAI_EXPORT", "crew_module:crew")
    result = CliRunner().invoke(app, [
        "run", "crew.py",
        "--workspace", str(tmp_path),
        "--runtime", "crewai+swarmgraph",
        "--dry-run",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert payload["runnable"] is True
    assert payload["provider_call"] is False
    assert payload["export_target_status"]["present"] is True
    assert not (tmp_path / ".arc" / "traces").exists()


def test_run_dry_run_langgraph_swarmgraph_fake_offline_ready(monkeypatch, tmp_path):
    monkeypatch.delenv("ARC_REAL_RUNTIME_SMOKE", raising=False)
    monkeypatch.delenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", raising=False)
    result = CliRunner().invoke(app, [
        "run", "graph.py",
        "--workspace", str(tmp_path),
        "--runtime", "langgraph+swarmgraph",
        "--dry-run",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert payload["runtime"] == "langgraph+swarmgraph"
    assert payload["runtime_mode"] == "fake/offline"
    assert payload["dry_run"] is True
    assert payload["runnable"] is True
    assert payload["provider_call"] is False
    assert payload["dependency_status"]["runtime_mode"] == "fake/offline"
    assert payload["dependency_status"]["real_provider_call"] is False
    assert payload["dependency_status"]["real_runtime_gated"] is True
    assert payload["contract_status"]["state"] == "fake_offline"
    assert payload["contract_status"]["provider_backed_claim"] is False
    assert payload["gate_status"]["required"] is False
    assert not payload["blockers"]
    assert not (tmp_path / ".arc" / "traces").exists()


def test_run_dry_run_langgraph_swarmgraph_local_real_blocked_without_gate(monkeypatch, tmp_path):
    monkeypatch.delenv("ARC_REAL_RUNTIME_SMOKE", raising=False)
    monkeypatch.delenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", raising=False)
    result = CliRunner().invoke(app, [
        "run", "graph.py",
        "--workspace", str(tmp_path),
        "--runtime", "langgraph+swarmgraph",
        "--runtime-mode", "local-real",
        "--allow-paid-calls",
        "--dry-run",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert payload["runtime_mode"] == "local-real"
    assert payload["provider_call"] is False
    assert payload["dependency_status"]["runtime_mode"] == "local-real"
    assert payload["dependency_status"]["real_provider_call"] is False
    assert payload["contract_status"]["state"] == "local_real_gated"
    assert payload["gate_status"]["required"] is True
    assert payload["gate_status"]["open"] is False
    assert payload["provider_backed_claim"] is False
    assert payload["runnable"] is False
    codes = {blocker["code"] for blocker in payload["blockers"]}
    assert "LOCAL_REAL_GATE_REQUIRED" in codes
    assert not (tmp_path / ".arc" / "traces").exists()


def test_run_dry_run_langgraph_swarmgraph_local_real_blocked_with_partial_gate(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_REAL_RUNTIME_SMOKE", "1")
    monkeypatch.delenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", raising=False)
    result = CliRunner().invoke(app, [
        "run", "graph.py",
        "--workspace", str(tmp_path),
        "--runtime", "langgraph+swarmgraph",
        "--runtime-mode", "local-real",
        "--dry-run",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert payload["runnable"] is False
    assert payload["provider_call"] is False
    assert payload["dependency_status"]["real_provider_call"] is False
    codes = {blocker["code"] for blocker in payload["blockers"]}
    assert "LOCAL_REAL_GATE_REQUIRED" in codes
    assert not (tmp_path / ".arc" / "traces").exists()


def test_run_dry_run_langgraph_swarmgraph_local_real_ready_with_gate(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_REAL_RUNTIME_SMOKE", "1")
    monkeypatch.setenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", "1")
    result = CliRunner().invoke(app, [
        "run", "graph.py",
        "--workspace", str(tmp_path),
        "--runtime", "langgraph+swarmgraph",
        "--runtime-mode", "local-real",
        "--dry-run",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert payload["runtime_mode"] == "local-real"
    assert payload["runnable"] is True
    assert payload["provider_call"] is False
    assert payload["dependency_status"]["real_provider_call"] is False
    assert payload["dependency_status"]["real_runtime_gated"] is False
    assert payload["contract_status"]["state"] == "local_real_available"
    assert payload["gate_status"]["open"] is True
    assert payload["provider_backed_claim"] is False
    assert not payload["blockers"]
    assert not (tmp_path / ".arc" / "traces").exists()


def test_run_langgraph_swarmgraph_local_real_blocked_without_gate(tmp_path):
    result = CliRunner().invoke(app, [
        "run", "graph.py",
        "--workspace", str(tmp_path),
        "--runtime", "langgraph+swarmgraph",
        "--runtime-mode", "local-real",
        "--allow-paid-calls",
        "--json",
    ])
    assert result.exit_code == 2
    envelope = json.loads(result.output)
    assert envelope["ok"] is False
    assert envelope["error"]["details"]["code"] == "LOCAL_REAL_GATE_REQUIRED"
    assert not (tmp_path / ".arc" / "traces").exists()


def test_run_rejects_invalid_runtime_mode(tmp_path):
    result = CliRunner().invoke(app, [
        "run", "graph.py",
        "--workspace", str(tmp_path),
        "--runtime", "langgraph+swarmgraph",
        "--runtime-mode", "real",
        "--json",
    ])
    assert result.exit_code == 2
    envelope = json.loads(result.output)
    assert envelope["ok"] is False
    assert envelope["error"]["details"]["code"] == "INVALID_RUNTIME_MODE"


def test_run_crewai_swarmgraph_fake_offline_completes(monkeypatch, tmp_path):
    monkeypatch.setenv("ARC_CREWAI_EXPORT", "crew_module:crew")
    result = CliRunner().invoke(app, [
        "run", "crew.py",
        "--workspace", str(tmp_path),
        "--runtime", "crewai+swarmgraph",
        "--prompt", "offline prompt",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]
    assert data["runtime"] == "crewai+swarmgraph"
    assert data["status"] == "completed"
    assert data["metadata"]["runtime_mode"] == "fake/offline"
    assert data["metadata"]["adoption"] is True
    assert data["metadata"]["real_provider_call"] is False
    assert data["metadata"]["audit_absent_reason"]
    event_types = [event["type"] for event in data["events"]]
    assert event_types[0] == "RUN_STARTED"
    assert "STEP_STARTED" in event_types
    assert "STEP_COMPLETED" in event_types
    assert event_types[-1] == "RUN_COMPLETED"
    traces = list((tmp_path / ".arc" / "traces").glob("run-crewai-sg-*.jsonl"))
    assert len(traces) == 1


def test_run_langgraph_swarmgraph_fake_offline_deterministic_trace(tmp_path):
    args = [
        "run", "graph.py",
        "--workspace", str(tmp_path),
        "--runtime", "langgraph+swarmgraph",
        "--prompt", "offline prompt",
        "--json",
    ]

    first = CliRunner().invoke(app, args)
    second = CliRunner().invoke(app, args)
    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output

    first_data = json.loads(first.output)["data"]
    second_data = json.loads(second.output)["data"]
    assert first_data["runtime"] == "langgraph+swarmgraph"
    assert first_data["status"] == "completed"
    assert first_data["metadata"]["runtime_mode"] == "fake/offline"
    assert first_data["metadata"]["real_provider_call"] is False
    assert first_data["metadata"]["real_runtime_gated"] is True

    first_events = [event["type"] for event in first_data["events"]]
    second_events = [event["type"] for event in second_data["events"]]
    assert first_events == second_events
    assert "SWARMGRAPH_TOPOLOGY" in first_events
    assert "SWARMGRAPH_CONSENSUS" in first_events

    topology = next(event for event in first_data["events"] if event["type"] == "SWARMGRAPH_TOPOLOGY")
    consensus = next(event for event in first_data["events"] if event["type"] == "SWARMGRAPH_CONSENSUS")
    assert {node["id"] for node in topology["data"]["nodes"]} >= {"queen", "worker-1", "worker-2"}
    assert consensus["data"]["consensus_reached"] is True
    assert consensus["data"]["real_provider_call"] is False

    traces = list((tmp_path / ".arc" / "traces").glob("run-langgraph-sg-*.jsonl"))
    assert len(traces) == 2


def test_run_dry_run_unknown_profile_fails_closed(tmp_path):
    result = CliRunner().invoke(app, [
        "run", "crew.py",
        "--workspace", str(tmp_path),
        "--runtime", "crewai+swarmgraph",
        "--profile-id", "missing",
        "--dry-run",
        "--json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    codes = {blocker["code"] for blocker in payload["blockers"]}
    assert "UNKNOWN_PROFILE" in codes


def test_runtimes_capabilities_json(tmp_path):
    result = CliRunner().invoke(app, ["runtimes", "--workspace", str(tmp_path), "--capabilities", "--json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)["data"]
    assert payload["auto_priority"] == ["swarmgraph", "langgraph", "crewai", "lmarena"]
    ids = {runtime["runtime_id"] for runtime in payload["runtimes"]}
    assert ids >= {"swarmgraph", "langgraph", "crewai", "lmarena"}
    assert all("requires_paid_calls" in runtime for runtime in payload["runtimes"])
    langgraph_sg = next(runtime for runtime in payload["runtimes"] if runtime["runtime_id"] == "langgraph+swarmgraph")
    assert langgraph_sg["can_run"] is True
    assert langgraph_sg["availability"] == "runnable"
    assert langgraph_sg["requires_paid_calls"] is False
    assert "fake/offline" in langgraph_sg["reason"]
    assert "real" in langgraph_sg["reason"]
    assert "gated" in langgraph_sg["reason"]
    assert langgraph_sg["fake_offline_supported"] is True
    assert langgraph_sg["provider_backed"] is False


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


def test_runs_status_export_backfill_delete_contract(tmp_path):
    from datetime import datetime, timezone

    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
    from agent_runtime_cockpit.storage.sqlite import SqliteStore

    ws = tmp_path / "ws"
    traces = ws / ".arc" / "traces"
    traces.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat()
    run = RunRecord(
        id="run-cli-contract",
        workflow_id="wf-contract",
        runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at=now,
        ended_at=now,
    )
    JsonlTraceStore(traces).save(run)

    backfill = CliRunner().invoke(app, ["runs", "backfill", "--workspace", str(ws), "--json"])
    assert backfill.exit_code == 0, backfill.output
    assert json.loads(backfill.output)["data"]["indexed"] == 1

    status = CliRunner().invoke(app, ["runs", "status", run.id, "--workspace", str(ws), "--json"])
    assert status.exit_code == 0, status.output
    status_data = json.loads(status.output)["data"]
    assert status_data["run_id"] == run.id
    assert status_data["status"] == "completed"

    exported = CliRunner().invoke(app, ["runs", "export", run.id, "--workspace", str(ws), "--json"])
    assert exported.exit_code == 0, exported.output
    assert json.loads(exported.output)["data"]["id"] == run.id

    db = SqliteStore(ws / ".arc" / "arc.db")
    assert db.run_exists(run.id) is True
    deleted = CliRunner().invoke(app, ["runs", "delete", run.id, "--workspace", str(ws), "--json"])
    assert deleted.exit_code == 0, deleted.output
    assert not (traces / f"{run.id}.jsonl").exists()
    assert db.run_exists(run.id) is False


def test_isolation_cli_contracts():
    status = CliRunner().invoke(app, ["isolation", "status", "--json"])
    assert status.exit_code == 0, status.output
    provider_ids = {p["provider_id"] for p in json.loads(status.output)["data"]["providers"]}
    assert provider_ids == {"none", "subprocess", "docker"}

    listed = CliRunner().invoke(app, ["isolation", "list", "--json"])
    assert listed.exit_code == 0, listed.output
    listed_ids = {p["provider_id"] for p in json.loads(listed.output)["data"]["providers"]}
    assert listed_ids == {"none", "subprocess", "docker"}

    doctor = CliRunner().invoke(app, ["isolation", "doctor", "subprocess", "--json"])
    assert doctor.exit_code == 0, doctor.output
    diagnostics = json.loads(doctor.output)["data"]["diagnostics"]
    assert diagnostics[0]["provider_id"] == "subprocess"
    assert diagnostics[0]["healthy"] is True

    unknown = CliRunner().invoke(app, ["isolation", "doctor", "missing", "--json"])
    assert unknown.exit_code == 1
    assert json.loads(unknown.output)["error"]["code"] == "INVALID_INPUT"


def test_runs_import_and_replay(tmp_path):
    from datetime import datetime, timezone
    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunEvent, RunStatus

    ws = tmp_path / "ws"
    traces = ws / ".arc" / "traces"
    traces.mkdir(parents=True)
    now = datetime.now(timezone.utc).isoformat()
    run = RunRecord(
        id="run-replay",
        workflow_id="wf-replay",
        runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at=now,
        ended_at=now,
        events=[RunEvent(type="RUN_COMPLETED", timestamp=now, run_id="run-replay", sequence=0, data={"duration_ms": 1})],
    )
    export_path = tmp_path / "run-export.json"
    export_path.write_text(run.model_dump_json())

    imported = CliRunner().invoke(app, ["runs", "import", str(export_path), "--workspace", str(ws), "--json"])
    assert imported.exit_code == 0, imported.output
    assert json.loads(imported.output)["data"]["imported_run_id"] == run.id

    replayed = CliRunner().invoke(app, ["runs", "replay", run.id, "--workspace", str(ws), "--json"])
    assert replayed.exit_code == 0, replayed.output
    data = json.loads(replayed.output)["data"]
    assert data["event_count"] == 1
    assert data["events"][0]["type"] == "RUN_COMPLETED"


def test_hitl_cli_pending_and_approve(tmp_path):
    from agent_runtime_cockpit.audit.hitl import HitlPrompt
    from agent_runtime_cockpit.audit.hitl_store import save_prompt, get_token

    save_prompt(tmp_path, HitlPrompt(
        hitl_id="hitl-cli-1",
        run_id="run-1",
        step_id="step-1",
        prompt_text="Approve?",
    ))

    pending = CliRunner().invoke(app, ["hitl", "pending", "--workspace", str(tmp_path), "--json"])
    assert pending.exit_code == 0, pending.output
    data = json.loads(pending.output)["data"][0]
    assert data["hitl_id"] == "hitl-cli-1"
    assert "token" in data

    token = get_token(tmp_path, "hitl-cli-1")
    approved = CliRunner().invoke(app, [
        "hitl", "approve", "hitl-cli-1",
        "--token", token,
        "--workspace", str(tmp_path), "--json",
    ])
    assert approved.exit_code == 0, approved.output
    assert json.loads(approved.output)["data"]["decision"] == "approve"


def test_runs_links_returns_structured_event_chains(tmp_path):
    """`arc runs links <runId> --json` returns organized event chains by stable ID."""
    from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    ws = tmp_path / "ws"
    traces_dir = ws / ".arc" / "traces"
    traces_dir.mkdir(parents=True)

    events = [
        RunEvent(type="NODE_START", timestamp="2026-01-01T00:00:00Z", run_id="run-links-1", sequence=1,
                 data={"node_id": "node-a", "message_id": "msg-1"}),
        RunEvent(type="NODE_END", timestamp="2026-01-01T00:00:01Z", run_id="run-links-1", sequence=2,
                 data={"node_id": "node-a", "message_id": "msg-1", "tool_call_id": "tc-1"}),
        RunEvent(type="TOOL_START", timestamp="2026-01-01T00:00:02Z", run_id="run-links-1", sequence=3,
                 data={"tool_call_id": "tc-1", "message_id": "msg-1"}),
        RunEvent(type="TOOL_END", timestamp="2026-01-01T00:00:03Z", run_id="run-links-1", sequence=4,
                 data={"tool_call_id": "tc-1", "evidence_refs": [{"evidence_id": "ev-1"}]}),
        RunEvent(type="RUN_COMPLETED", timestamp="2026-01-01T00:00:04Z", run_id="run-links-1", sequence=5,
                 data={}),
    ]
    record = RunRecord(
        id="run-links-1",
        workflow_id="wf-links",
        runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:00:05Z",
        events=events,
    )
    store = JsonlTraceStore(traces_dir)
    store.save(record)

    result = CliRunner().invoke(app, ["runs", "links", "run-links-1", "--workspace", str(ws), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]

    assert data["has_stable_ids"] is True
    assert data["stable_id_count"] >= 2  # node-a, msg-1, tc-1, ev-1
    assert "node-a" in data["node_chains"]
    assert len(data["node_chains"]["node-a"]) >= 2  # NODE_START + NODE_END
    assert "msg-1" in data["message_chains"]
    assert "tc-1" in data["tool_call_chains"]
    assert "ev-1" in data["evidence_chains"]


def test_runs_links_returns_empty_for_run_without_stable_ids(tmp_path):
    """`arc runs links <runId> --json` returns empty chains when no stable IDs exist."""
    from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    ws = tmp_path / "ws2"
    traces_dir = ws / ".arc" / "traces"
    traces_dir.mkdir(parents=True)

    events = [
        RunEvent(type="RUN_STARTED", timestamp="2026-01-01T00:00:00Z", run_id="run-no-links", sequence=1, data={}),
        RunEvent(type="RUN_COMPLETED", timestamp="2026-01-01T00:00:01Z", run_id="run-no-links", sequence=2, data={}),
    ]
    record = RunRecord(
        id="run-no-links",
        workflow_id="wf-no-links",
        runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at="2026-01-01T00:00:00Z",
        ended_at="2026-01-01T00:00:01Z",
        events=events,
    )
    store = JsonlTraceStore(traces_dir)
    store.save(record)

    result = CliRunner().invoke(app, ["runs", "links", "run-no-links", "--workspace", str(ws), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]

    assert data["has_stable_ids"] is False
    assert data["stable_id_count"] == 0
    assert data["node_chains"] == {}
    assert data["message_chains"] == {}
    assert data["tool_call_chains"] == {}
    assert data["evidence_chains"] == {}


def test_runs_links_reports_not_found(tmp_path):
    """`arc runs links <runId> --json` exits 1 for missing run."""
    result = CliRunner().invoke(app, ["runs", "links", "missing-run", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["code"] == "RUN_NOT_FOUND"


# ─── runs fork ────────────────────────────────────────────────────────────────


def test_runs_fork_creates_new_run_from_existing(tmp_path):
    """`arc runs fork <runId>` creates a new pending run with fork metadata."""
    from agent_runtime_cockpit.orchestration.events import new_run_id, now, event
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    ws = tmp_path / "ws"
    ws.mkdir()
    traces_dir = ws / ".arc" / "traces"
    traces_dir.mkdir(parents=True)
    store = JsonlTraceStore(traces_dir)

    # Create a source run
    source_id = new_run_id(prefix="run")
    source_record = RunRecord(
        id=source_id,
        workflow_id="wf-test",
        runtime="swarmgraph",
        status=RunStatus.COMPLETED,
        started_at=now(),
        ended_at=now(),
        events=[
            event(source_id, 0, "RUN_STARTED", {"workflow_id": "wf-test", "runtime": "swarmgraph"}),
            event(source_id, 1, "STEP_STARTED", {"step_id": "s1", "step_name": "load"}),
        ],
        metadata={"original": True},
    )
    store.save(source_record)

    # Fork it
    result = CliRunner().invoke(app, ["runs", "fork", source_id, "--workspace", str(ws), "--json"])
    assert result.exit_code == 0, f"exit {result.exit_code}: {result.output[:500]}"
    data = json.loads(result.output)["data"]

    assert data["source_id"] == source_id
    assert data["workflow_id"] == "wf-test"
    assert data["runtime"] == "swarmgraph"
    assert data["event_count"] == 2  # Only RUN_STARTED + STEP_STARTED
    assert data["status"] == "pending"
    assert data["metadata"]["forked_from"] == source_id
    assert "forked_at" in data["metadata"]

    # Verify fork exists in store
    fork_id = data["fork_id"]
    fork_record = store.load(fork_id)
    assert fork_record is not None
    assert fork_record.status == RunStatus.PENDING
    assert fork_record.metadata["forked_from"] == source_id

    # Verify source has fork reference
    source_updated = store.load(source_id)
    assert source_updated is not None
    assert fork_id in source_updated.metadata.get("forked_to", [])


def test_runs_fork_reports_not_found(tmp_path):
    """`arc runs fork <missingId> --json` exits 1 for missing run."""
    result = CliRunner().invoke(app, ["runs", "fork", "missing-run", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 1
    data = json.loads(result.output)
    assert data["ok"] is False
    assert data["error"]["code"] == "RUN_NOT_FOUND"


def test_runs_fork_preserves_workflow_and_runtime(tmp_path):
    """Fork preserves workflow_id and runtime from source."""
    from agent_runtime_cockpit.orchestration.events import new_run_id, now, event
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    ws = tmp_path / "ws"
    ws.mkdir()
    traces_dir = ws / ".arc" / "traces"
    traces_dir.mkdir(parents=True)
    store = JsonlTraceStore(traces_dir)

    source_id = new_run_id(prefix="run")
    source_record = RunRecord(
        id=source_id,
        workflow_id="crewai-workflow",
        runtime="crewai+swarmgraph",
        status=RunStatus.FAILED,
        started_at=now(),
        ended_at=now(),
        events=[
            event(source_id, 0, "RUN_STARTED", {"workflow_id": "crewai-workflow", "runtime": "crewai+swarmgraph"}),
        ],
        metadata={"tag": "original"},
    )
    store.save(source_record)

    result = CliRunner().invoke(app, ["runs", "fork", source_id, "--workspace", str(ws), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)["data"]

    assert data["workflow_id"] == "crewai-workflow"
    assert data["runtime"] == "crewai+swarmgraph"
    assert data["source_event_count"] == 1
