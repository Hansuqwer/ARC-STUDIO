"""B2P-11: eval artifact schema (versioned + repeatable), Inspect export, two-run compare."""

from __future__ import annotations

from pathlib import Path

from agent_runtime_cockpit.evals.artifact import (
    EvalArtifact,
    EvalArtifactStore,
    build_artifact,
    build_inspect_export,
)


def test_artifact_is_versioned() -> None:
    art = build_artifact("run-1", "golden-1", [])
    assert art.schema_version >= 1


def test_artifact_path_is_repeatable_and_deterministic(tmp_path: Path) -> None:
    store = EvalArtifactStore(tmp_path)
    art = EvalArtifact(run_id="run-x", golden_id="g-1", total=1, pass_count=1, pass_rate=1.0)
    p1 = store.write(art)
    p2 = store.write(art)
    assert p1 == p2  # deterministic, repeatable path
    assert p1.parent.name == "run-x"  # stable per-run layout under .arc/evals/<run_id>/


def test_inspect_export_shape() -> None:
    art = EvalArtifact(
        run_id="run-2", golden_id="g-2", total=2, pass_count=1, fail_count=1, pass_rate=0.5
    )
    export = build_inspect_export("run-2", [art])
    assert isinstance(export, dict)
    # Inspect-AI-style export references the run + carries per-eval results.
    assert "run-2" in str(export)


def test_eval_compare_command_registered() -> None:
    from agent_runtime_cockpit.cli._subapps import eval_app

    names = {c.name for c in eval_app.registered_commands}
    assert "compare" in names  # two-run comparison (T22)
    assert "export" in names  # Inspect export (T21)
