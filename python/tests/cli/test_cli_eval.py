"""Tests for the 'arc eval' CLI commands."""


from agent_runtime_cockpit.evals.golden import GoldenTrace, save_golden, list_goldens


def test_eval_run_help(run_cli):
    r = run_cli(["eval", "run", "--help"])
    assert r.exit_code == 0
    assert "Evaluate a run against a golden trace" in r.stdout


def test_eval_list_help(run_cli):
    r = run_cli(["eval", "list", "--help"])
    assert r.exit_code == 0
    assert "List saved golden traces" in r.stdout


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
