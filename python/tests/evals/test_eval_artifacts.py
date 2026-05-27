"""Tests for Phase 53 — Eval artifact schema and batch eval CLI."""

import json
import os
import time

from agent_runtime_cockpit.evals.artifact import (
    EvalArtifact,
    EvalArtifactStore,
    build_artifact,
    build_inspect_export,
)
from agent_runtime_cockpit.protocol.schemas import RunEvent, RunRecord, RunStatus


# ─── Model tests ──────────────────────────────────────────────────────────────


def test_eval_artifact_validates_and_serializes():
    art = EvalArtifact(
        run_id="run-123",
        golden_id="golden-abc",
        pass_count=5,
        fail_count=1,
        total=6,
        pass_rate=0.8333,
        failures=["golden-xyz: status mismatch"],
    )
    d = art.model_dump()
    assert d["run_id"] == "run-123"
    assert d["golden_id"] == "golden-abc"
    assert d["pass_count"] == 5
    assert d["fail_count"] == 1
    assert d["total"] == 6
    assert d["pass_rate"] == 0.8333
    assert len(d["failures"]) == 1
    assert "eval_timestamp" in d

    # roundtrip
    art2 = EvalArtifact.model_validate(d)
    assert art2.run_id == art.run_id
    assert art2.pass_rate == art.pass_rate


# ─── Store tests ──────────────────────────────────────────────────────────────


def test_artifact_store_write_and_load(tmp_path):
    store = EvalArtifactStore(tmp_path)
    art = EvalArtifact(run_id="run-1", golden_id="golden-1", pass_count=3, total=3, pass_rate=1.0)
    path = store.write(art)
    assert path.exists()
    assert "run-1" in str(path)
    assert path.suffix == ".json"

    loaded = store.load("run-1", "golden-1")
    assert loaded is not None
    assert loaded.run_id == "run-1"
    assert loaded.golden_id == "golden-1"
    assert loaded.pass_rate == 1.0


def test_artifact_path_deterministic(tmp_path):
    store = EvalArtifactStore(tmp_path)
    art = EvalArtifact(run_id="run-x", golden_id="golden-y")
    p1 = store.write(art)
    p2 = store.write(art)
    assert p1 == p2


def test_artifact_store_list_by_run(tmp_path):
    store = EvalArtifactStore(tmp_path)
    store.write(EvalArtifact(run_id="run-a", golden_id="g1"))
    store.write(EvalArtifact(run_id="run-a", golden_id="g2"))
    store.write(EvalArtifact(run_id="run-b", golden_id="g3"))

    run_a = store.list_by_run("run-a")
    assert len(run_a) == 2
    assert {a.golden_id for a in run_a} == {"g1", "g2"}

    run_b = store.list_by_run("run-b")
    assert len(run_b) == 1
    assert run_b[0].golden_id == "g3"


def test_artifact_store_list_empty(tmp_path):
    store = EvalArtifactStore(tmp_path)
    assert store.list_run_ids() == []


def test_artifact_store_prune(tmp_path):
    store = EvalArtifactStore(tmp_path)
    store.write(EvalArtifact(run_id="run-old", golden_id="golden-old"))

    # backdate the file
    old_path = tmp_path / ".arc" / "evals" / "run-old"
    for f in old_path.iterdir():
        old_mtime = time.time() - 100 * 86400  # 100 days ago
        os.utime(f, (old_mtime, old_mtime))

    # add a fresh one
    store.write(EvalArtifact(run_id="run-new", golden_id="golden-new"))

    removed = store.prune(max_age_days=30)
    assert removed >= 1
    assert store.load("run-old", "golden-old") is None
    assert store.load("run-new", "golden-new") is not None


# ─── build_artifact tests ─────────────────────────────────────────────────────


def test_build_artifact_all_pass():
    results = [
        {"golden_id": "g1", "passed": True, "details": "ok"},
        {"golden_id": "g2", "passed": True, "details": "ok"},
    ]
    art = build_artifact("run-1", "batch", results)
    assert art.pass_count == 2
    assert art.fail_count == 0
    assert art.total == 2
    assert art.pass_rate == 1.0
    assert art.failures == []


def test_build_artifact_some_fail():
    results = [
        {"golden_id": "g1", "passed": True, "details": "ok"},
        {"golden_id": "g2", "passed": False, "details": "status mismatch"},
        {"golden_id": "g3", "passed": False, "details": "output mismatch"},
    ]
    art = build_artifact("run-2", "batch", results)
    assert art.pass_count == 1
    assert art.fail_count == 2
    assert art.total == 3
    assert art.pass_rate == round(1 / 3, 4)
    assert len(art.failures) == 2


# ─── Inspect export tests ─────────────────────────────────────────────────────


def test_inspect_export_shape():
    arts = [
        EvalArtifact(golden_id="g1", run_id="r1", pass_count=1, total=1, pass_rate=1.0),
        EvalArtifact(
            golden_id="g2",
            run_id="r1",
            pass_count=0,
            total=1,
            fail_count=1,
            pass_rate=0.0,
            failures=["g2: failed"],
        ),
    ]
    export = build_inspect_export("r1", arts)
    assert export["version"] == "1"
    assert len(export["samples"]) == 2
    assert export["samples"][0]["id"] == "g1"
    assert export["samples"][0]["scores"]["pass_rate"] == 1.0
    assert export["samples"][1]["id"] == "g2"
    assert export["samples"][1]["output"]["fail_count"] == 1


# ─── CLI tests ────────────────────────────────────────────────────────────────


def test_run_golden_file_single_trace(run_cli, tmp_path):
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    run = RunRecord(
        id="cli-run-1",
        workflow_id="wf-test",
        runtime="stub",
        status=RunStatus.COMPLETED,
        started_at="2026-05-15T00:00:00Z",
        events=[
            RunEvent(
                run_id="cli-run-1", sequence=1, type="RUN_STARTED", timestamp="2026-05-15T00:00:00Z"
            ),
            RunEvent(
                run_id="cli-run-1",
                sequence=2,
                type="RUN_COMPLETED",
                timestamp="2026-05-15T00:00:01Z",
                data={"output": "hello"},
            ),
        ],
    )
    store.save(run)

    golden_path = tmp_path / "golden.json"
    golden_path.write_text(
        json.dumps(
            {
                "id": "golden-cli",
                "workflow_id": "wf-test",
                "expected_status": "completed",
                "expected_final_output_contains": "hello",
            }
        )
    )

    r = run_cli(
        [
            "eval",
            "run",
            "--golden-file",
            str(golden_path),
            "--run-id",
            "cli-run-1",
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["passed"] == 1
    assert data["failed"] == 0
    assert data["total"] == 1
    assert len(data["artifacts"]) == 1


def test_run_golden_file_list(run_cli, tmp_path):
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore

    store = JsonlTraceStore(tmp_path / ".arc" / "traces")
    run = RunRecord(
        id="cli-run-2",
        workflow_id="wf-test",
        runtime="stub",
        status=RunStatus.COMPLETED,
        started_at="2026-05-15T00:00:00Z",
        events=[
            RunEvent(
                run_id="cli-run-2", sequence=1, type="RUN_STARTED", timestamp="2026-05-15T00:00:00Z"
            ),
            RunEvent(
                run_id="cli-run-2",
                sequence=2,
                type="RUN_COMPLETED",
                timestamp="2026-05-15T00:00:01Z",
                data={"output": "hello"},
            ),
        ],
    )
    store.save(run)

    golden_path = tmp_path / "goldens.json"
    golden_path.write_text(
        json.dumps(
            [
                {
                    "id": "g-pass",
                    "workflow_id": "wf-test",
                    "expected_status": "completed",
                    "expected_final_output_contains": "hello",
                },
                {
                    "id": "g-fail",
                    "workflow_id": "wf-test",
                    "expected_status": "failed",
                    "expected_final_output_contains": "goodbye",
                },
            ]
        )
    )

    r = run_cli(
        [
            "eval",
            "run",
            "--golden-file",
            str(golden_path),
            "--run-id",
            "cli-run-2",
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["passed"] == 1
    assert data["failed"] == 1
    assert data["total"] == 2
    assert len(data["artifacts"]) == 2


def test_run_golden_file_no_run_id(run_cli, tmp_path):
    golden_path = tmp_path / "golden.json"
    golden_path.write_text(json.dumps({"id": "g", "workflow_id": "wf"}))
    r = run_cli(
        [
            "eval",
            "run",
            "--golden-file",
            str(golden_path),
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert r.exit_code != 0
    assert "--run-id is required" in r.stdout or "--run-id is required" in r.stderr


def test_compare_detects_delta(run_cli, tmp_path):
    from agent_runtime_cockpit.evals.artifact import EvalArtifactStore, EvalArtifact

    store = EvalArtifactStore(tmp_path)
    store.write(EvalArtifact(run_id="run-a", golden_id="g1", pass_count=1, total=1, pass_rate=1.0))
    store.write(
        EvalArtifact(
            run_id="run-a",
            golden_id="g2",
            pass_count=0,
            total=1,
            fail_count=1,
            pass_rate=0.0,
            failures=["g2: failed in A"],
        )
    )
    store.write(EvalArtifact(run_id="run-b", golden_id="g1", pass_count=1, total=1, pass_rate=1.0))
    store.write(EvalArtifact(run_id="run-b", golden_id="g2", pass_count=1, total=1, pass_rate=1.0))

    r = run_cli(
        [
            "eval",
            "compare",
            "--run-a",
            "run-a",
            "--run-b",
            "run-b",
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["delta_pass_rate"] > 0
    assert "g2" in data["fixed_failures"]


def test_compare_missing_run(run_cli, tmp_path):
    r = run_cli(
        [
            "eval",
            "compare",
            "--run-a",
            "nonexistent",
            "--run-b",
            "also-missing",
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert r.exit_code != 0


def test_export_inspect_shape(run_cli, tmp_path):
    from agent_runtime_cockpit.evals.artifact import EvalArtifactStore, EvalArtifact

    store = EvalArtifactStore(tmp_path)
    store.write(EvalArtifact(run_id="run-x", golden_id="g1", pass_count=1, total=1, pass_rate=1.0))
    store.write(
        EvalArtifact(
            run_id="run-x",
            golden_id="g2",
            pass_count=0,
            total=1,
            fail_count=1,
            pass_rate=0.0,
            failures=["g2: failed"],
        )
    )

    r = run_cli(
        [
            "eval",
            "export",
            "run-x",
            "--format",
            "inspect",
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert r.exit_code == 0, r.stdout + r.stderr
    data = json.loads(r.stdout)["data"]
    assert data["format"] == "inspect"
    assert data["sample_count"] == 2

    export_path = tmp_path / ".arc" / "evals" / "run-x" / "inspect-export.json"
    assert export_path.exists()
    export_data = json.loads(export_path.read_text())
    assert export_data["version"] == "1"
    assert len(export_data["samples"]) == 2


def test_export_no_artifacts(run_cli, tmp_path):
    r = run_cli(
        [
            "eval",
            "export",
            "nonexistent",
            "--workspace",
            str(tmp_path),
            "--json",
        ]
    )
    assert r.exit_code != 0
