"""Tests for the 'arc eval' CLI commands."""

from agent_runtime_cockpit.evals.golden import GoldenTrace, list_goldens, save_golden


def test_eval_run_help(run_cli):
    r = run_cli(["eval", "run", "--help"])
    assert r.exit_code == 0
    assert "Evaluate a run against a golden trace" in r.stdout


def test_eval_list_help(run_cli):
    r = run_cli(["eval", "list", "--help"])
    assert r.exit_code == 0
    assert "List saved golden traces" in r.stdout


def test_eval_save_delete_report(run_cli, tmp_path):
    save = run_cli(
        [
            "eval",
            "save",
            "golden-1",
            "--workspace",
            str(tmp_path),
            "--workflow-id",
            "wf-test",
            "--expected-final-output",
            "hello",
            "--expected-event-types",
            "RUN_STARTED,RUN_COMPLETED",
            "--json",
        ]
    )
    assert save.exit_code == 0, save.stdout + save.stderr

    report = run_cli(["eval", "report", "--workspace", str(tmp_path), "--json"])
    assert report.exit_code == 0, report.stdout + report.stderr
    assert '"count": 1' in report.stdout

    delete = run_cli(["eval", "delete", "golden-1", "--workspace", str(tmp_path), "--json"])
    assert delete.exit_code == 0, delete.stdout + delete.stderr
    assert '"deleted": true' in delete.stdout


def test_eval_run_missing_run(run_cli):
    r = run_cli(["eval", "run", "nonexistent-run-id"])
    assert r.exit_code != 0
    assert "Run not found" in r.stderr or "Run not found" in r.stdout


def test_save_and_list_goldens(tmp_path):
    """Test save_golden and list_goldens utility functions."""
    golden = GoldenTrace(
        id="test-golden-001",
        workflow_id="wf-test",
        expected_status="completed",
        expected_event_types=["RUN_STARTED", "RUN_COMPLETED"],
        expected_final_output_contains="hello",
        description="test golden",
    )
    save_golden(tmp_path, golden)
    goldens = list_goldens(tmp_path)
    assert len(goldens) == 1
    assert goldens[0].id == "test-golden-001"
    assert goldens[0].expected_final_output_contains == "hello"


def test_list_goldens_empty(tmp_path):
    goldens = list_goldens(tmp_path)
    assert goldens == []


def test_list_goldens_skips_invalid_files(tmp_path):
    goldens_dir = tmp_path / ".arc" / "goldens"
    goldens_dir.mkdir(parents=True, exist_ok=True)
    (goldens_dir / "not-json.txt").write_text("garbage")
    (goldens_dir / "bad.json").write_text("{invalid json}")
    goldens = list_goldens(tmp_path)
    assert goldens == []


def test_eval_batch_no_goldens(run_cli, tmp_path):
    """Arc eval run --batch fails when no goldens saved."""
    from agent_runtime_cockpit.protocol.schemas import RunRecord, RunStatus
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    run = RunRecord(
        id="batch-no-goldens-run",
        workflow_id="wf-test",
        runtime="stub",
        status=RunStatus.COMPLETED,
        started_at="2026-05-15T00:00:00Z",
    )
    store.save(run)

    r = run_cli(
        [
            "eval",
            "run",
            "batch-no-goldens-run",
            "--batch",
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert r.exit_code != 0
    assert "No saved golden traces" in r.stdout or "No saved golden traces" in r.stderr


def test_eval_batch_with_goldens(run_cli, tmp_path):
    """Arc eval run --batch runs against all saved goldens."""
    from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    run = RunRecord(
        id="batch-test-run",
        workflow_id="wf-test",
        runtime="stub",
        status=RunStatus.COMPLETED,
        started_at="2026-05-15T00:00:00Z",
        events=[
            RunEvent(
                run_id="batch-test-run",
                sequence=1,
                type="RUN_STARTED",
                timestamp="2026-05-15T00:00:00Z",
            ),
            RunEvent(
                run_id="batch-test-run",
                sequence=2,
                type="RUN_COMPLETED",
                timestamp="2026-05-15T00:00:01Z",
                data={"output": "hello world"},
            ),
        ],
    )
    store.save(run)

    save_golden(
        tmp_path,
        GoldenTrace(
            id="golden-pass",
            workflow_id="wf-test",
            expected_status="completed",
            expected_final_output_contains="hello",
        ),
    )
    save_golden(
        tmp_path,
        GoldenTrace(
            id="golden-fail",
            workflow_id="wf-test",
            expected_status="failed",
            expected_final_output_contains="goodbye",
        ),
    )

    r = run_cli(
        [
            "eval",
            "run",
            "batch-test-run",
            "--batch",
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    import json

    data = json.loads(r.stdout)["data"]
    assert data["batch"] is True
    assert data["total"] == 2
    assert data["passed"] >= 0
    assert data["failed"] >= 0
    assert len(data["results"]) == 2
