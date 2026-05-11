import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app


def test_run_command_persists_trace_in_workspace(monkeypatch, tmp_path):
    cli = tmp_path / "swarmgraph"
    cli.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\n' '{\"swarm_id\":\"sg-cli\",\"status\":\"completed\",\"worker_count\":0,\"final_output\":\"ok\"}'\n"
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(tmp_path), "--prompt", "cli prompt", "--json"])

    assert result.exit_code == 0, result.output
    traces = list((tmp_path / ".arc" / "traces").glob("run-sg-*.jsonl"))
    assert len(traces) == 1
    assert str(traces[0]) in result.output
    assert "cli prompt" in result.output


def test_runs_command_reads_workspace_traces(monkeypatch, tmp_path):
    cli = tmp_path / "swarmgraph"
    cli.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\n' '{\"swarm_id\":\"sg-list\",\"status\":\"completed\",\"worker_count\":0,\"final_output\":\"ok\"}'\n"
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    run_result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(tmp_path), "--json"])
    assert run_result.exit_code == 0, run_result.output

    list_result = CliRunner().invoke(app, ["runs", "--workspace", str(tmp_path), "--json"])
    assert list_result.exit_code == 0, list_result.output
    assert "sg-list" in list_result.output
    assert str(tmp_path / ".arc" / "traces") in list_result.output

    run_id = json.loads(run_result.output)["data"]["id"]
    get_result = CliRunner().invoke(app, ["runs", "get", run_id, "--workspace", str(tmp_path), "--json"])
    assert get_result.exit_code == 0, get_result.output
    assert json.loads(get_result.output)["data"]["id"] == run_id


def test_runs_get_missing_returns_error(tmp_path):
    result = CliRunner().invoke(app, ["runs", "get", "missing-run", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 1
    envelope = json.loads(result.output)
    assert envelope["ok"] is False
    assert envelope["error"]["code"] == "RUN_NOT_FOUND"


def test_runs_command_lists_newest_first(monkeypatch, tmp_path):
    cli = tmp_path / "swarmgraph"
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

    first = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(tmp_path), "--json"])
    second = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(tmp_path), "--json"])
    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output

    listed = CliRunner().invoke(app, ["runs", "--workspace", str(tmp_path), "--json"])
    assert listed.exit_code == 0, listed.output
    data = json.loads(listed.output)["data"]
    assert data[0]["metadata"]["swarm_id"] == "sg-2"
    assert data[1]["metadata"]["swarm_id"] == "sg-1"


def test_runs_prune_is_dry_run_by_default(monkeypatch, tmp_path):
    cli = tmp_path / "swarmgraph"
    cli.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\n' '{\"swarm_id\":\"sg-prune\",\"status\":\"completed\",\"worker_count\":0,\"final_output\":\"ok\"}'\n"
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    for _ in range(3):
        result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(tmp_path), "--json"])
        assert result.exit_code == 0, result.output

    prune = CliRunner().invoke(app, ["runs", "prune", "--workspace", str(tmp_path), "--keep", "1", "--json"])
    assert prune.exit_code == 0, prune.output
    payload = json.loads(prune.output)["data"]
    assert payload["dry_run"] is True
    assert len(payload["would_delete"]) == 2
    assert len(list((tmp_path / ".arc" / "traces").glob("*.jsonl"))) == 3


def test_runs_prune_deletes_only_with_yes(monkeypatch, tmp_path):
    cli = tmp_path / "swarmgraph"
    cli.write_text(
        "#!/usr/bin/env sh\n"
        "printf '%s\n' '{\"swarm_id\":\"sg-prune\",\"status\":\"completed\",\"worker_count\":0,\"final_output\":\"ok\"}'\n"
    )
    cli.chmod(cli.stat().st_mode | 0o111)
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))

    for _ in range(3):
        result = CliRunner().invoke(app, ["run", "wf-test", "--workspace", str(tmp_path), "--json"])
        assert result.exit_code == 0, result.output

    prune = CliRunner().invoke(app, ["runs", "prune", "--workspace", str(tmp_path), "--keep", "1", "--yes", "--json"])
    assert prune.exit_code == 0, prune.output
    payload = json.loads(prune.output)["data"]
    assert payload["dry_run"] is False
    assert len(payload["deleted"]) == 2
    assert len(list((tmp_path / ".arc" / "traces").glob("*.jsonl"))) == 1


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
