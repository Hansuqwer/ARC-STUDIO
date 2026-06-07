"""ARC eval management commands (split from mgmt.py — CR-026)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._app import console
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    WORKSPACE_FLAG,
    _out,
    _setup_logging,
    _workspace,
)
from ._subapps import eval_app


@eval_app.command("save")
def eval_save(
    golden_id: str = typer.Argument(..., help="Golden trace ID to save"),
    workflow_id: str = typer.Option("", "--workflow-id", help="Expected workflow id"),
    expected_output: str = typer.Option(
        "", "--expected-final-output", help="Expected substring in final output"
    ),
    expected_event_types: str = typer.Option(
        "", "--expected-event-types", help="Comma-separated expected event types"
    ),
    expected_status: str = typer.Option(
        "completed", "--expected-status", help="Expected run status"
    ),
    description: str = typer.Option("", "--description", help="Golden description"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Save a golden trace expectation."""
    _setup_logging(debug)
    from ..evals.golden import GoldenTrace, save_golden

    ws = _workspace(workspace)
    events = (
        [t.strip() for t in expected_event_types.split(",") if t.strip()]
        if expected_event_types
        else []
    )
    golden = GoldenTrace(
        id=golden_id,
        workflow_id=workflow_id or "*",
        expected_status=expected_status,
        expected_event_types=events,
        expected_final_output_contains=expected_output,
        description=description,
    )
    save_golden(ws, golden)
    _out(ok(golden.model_dump(), workspace=str(ws)), json_output)


@eval_app.command("delete")
def eval_delete(
    golden_id: str = typer.Argument(..., help="Golden trace ID to delete"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete a saved golden trace."""
    _setup_logging(debug)
    from ..evals.golden import delete_golden

    ws = _workspace(workspace)
    deleted = delete_golden(ws, golden_id)
    _out(ok({"golden_id": golden_id, "deleted": deleted}, workspace=str(ws)), json_output)


@eval_app.command("report")
def eval_report(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Report saved golden trace inventory."""
    _setup_logging(debug)
    from ..evals.golden import list_goldens

    ws = _workspace(workspace)
    goldens = list_goldens(ws)
    data = {"count": len(goldens), "goldens": [golden.model_dump() for golden in goldens]}
    _out(ok(data, workspace=str(ws)), json_output)


@eval_app.command("run")
def eval_run_new(
    run_id: str = typer.Argument(None, help="Run ID to evaluate (defaults to --run-id)"),
    golden_file: str = typer.Option("", "--golden-file", "-f", help="Path to golden JSON file"),
    golden_dir: str = typer.Option("", "--golden-dir", "-d", help="Directory of golden JSON files"),
    golden_id: str = typer.Option("", "--golden", "-g", help="Golden trace ID"),
    expected_output: str = typer.Option(
        "", "--expected-final-output", help="Expected substring in final output"
    ),
    expected_event_types: str = typer.Option(
        "", "--expected-event-types", help="Comma-separated expected event types"
    ),
    expected_status: str = typer.Option(
        "completed", "--expected-status", help="Expected run status"
    ),
    batch: bool = typer.Option(False, "--batch", "-b", help="Run against all saved golden traces"),
    run_id_opt: str = typer.Option("", "--run-id", help="Run ID (alternative to positional arg)"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Evaluate a run against a golden trace.

    Provide --golden to load a saved golden trace, or specify
    --expected-final-output/--expected-status/--expected-event-types inline.

    Use --golden-file <path> to batch-evaluate from a golden JSON file (list or single GoldenTrace).
    Use --golden-dir <dir> to batch-evaluate from a directory of golden JSON files.
    Use --batch to evaluate against all saved golden traces.

    Example:
        uv run arc eval run <run_id> --expected-final-output "hello"
        uv run arc eval run <run_id> --golden my-golden-id
        uv run arc eval run --golden-file goldens.json --run-id my-run
        uv run arc eval run --golden-dir goldens/ --run-id my-run
        uv run arc eval run <run_id> --batch

    """
    _setup_logging(debug)
    import json as _json

    from ..evals.artifact import EvalArtifactStore, build_artifact
    from ..evals.golden import GoldenTrace, list_goldens, load_golden
    from ..evals.golden import eval_run as do_eval
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    rid = run_id or run_id_opt or ""

    # Resolve store
    store = JsonlTraceStore(ws / ".arc" / "traces")

    # --golden-file batch mode
    if golden_file:
        gf_path = Path(golden_file)
        if not gf_path.exists():
            _out(
                err(ArcErrorCode.INVALID_INPUT, f"Golden file not found: {golden_file}"),
                json_output,
            )
            raise typer.Exit(1)
        try:
            raw = _json.loads(gf_path.read_text())
        except Exception as e:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid golden JSON: {e}"), json_output)
            raise typer.Exit(1)
        if isinstance(raw, dict):
            goldens_list = [GoldenTrace.model_validate(raw)]
        elif isinstance(raw, list):
            goldens_list = [GoldenTrace.model_validate(g) for g in raw]
        else:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Golden file must contain a GoldenTrace object or list",
                ),
                json_output,
            )
            raise typer.Exit(1)

        if not rid:
            _out(
                err(ArcErrorCode.INVALID_INPUT, "--run-id is required when using --golden-file"),
                json_output,
            )
            raise typer.Exit(1)

        run = store.load(rid)
        if run is None:
            _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {rid}"), json_output)
            raise typer.Exit(1)

        art_store = EvalArtifactStore(ws)
        all_results = []
        for golden in goldens_list:
            result = do_eval(run, golden)
            all_results.append(result.model_dump())
            art_store.write(build_artifact(rid, golden.id, [result.model_dump()]))

        passed = sum(1 for r in all_results if r.get("passed"))
        failed = len(all_results) - passed
        artifacts = [
            build_artifact(rid, r.get("golden_id", "?"), [r]).model_dump() for r in all_results
        ]
        payload = {
            "passed": passed,
            "failed": failed,
            "total": len(all_results),
            "artifacts": artifacts,
        }
        _out(ok(payload, workspace=str(ws)), json_output)
        if not json_output:
            console.print(f"[bold]Batch Eval:[/bold] {passed}/{len(all_results)} passed")
            for r in all_results:
                color = "green" if r.get("passed") else "red"
                console.print(
                    f"  [{color}]{'PASS' if r.get('passed') else 'FAIL'}[/{color}] {r.get('golden_id', '?')} score={r.get('score', 0)}"
                )
        return

    # --golden-dir batch mode
    if golden_dir:
        gd_path = Path(golden_dir)
        if not gd_path.is_dir():
            _out(
                err(ArcErrorCode.INVALID_INPUT, f"Golden directory not found: {golden_dir}"),
                json_output,
            )
            raise typer.Exit(1)

        if not rid:
            _out(
                err(ArcErrorCode.INVALID_INPUT, "--run-id is required when using --golden-dir"),
                json_output,
            )
            raise typer.Exit(1)

        run = store.load(rid)
        if run is None:
            _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {rid}"), json_output)
            raise typer.Exit(1)

        # Load all .json files from directory as GoldenTraces
        goldens_list = []
        for gf in sorted(gd_path.glob("*.json")):
            try:
                raw = _json.loads(gf.read_text())
                if isinstance(raw, dict):
                    goldens_list.append(GoldenTrace.model_validate(raw))
                elif isinstance(raw, list):
                    for item in raw:
                        goldens_list.append(GoldenTrace.model_validate(item))
            except Exception:
                continue

        if not goldens_list:
            _out(
                err(ArcErrorCode.INVALID_INPUT, f"No valid golden traces found in {golden_dir}"),
                json_output,
            )
            raise typer.Exit(1)

        art_store = EvalArtifactStore(ws)
        all_results = []
        for golden in goldens_list:
            result = do_eval(run, golden)
            all_results.append(result.model_dump())
            art_store.write(build_artifact(rid, golden.id, [result.model_dump()]))

        passed = sum(1 for r in all_results if r.get("passed"))
        failed = len(all_results) - passed
        artifacts = [
            build_artifact(rid, r.get("golden_id", "?"), [r]).model_dump() for r in all_results
        ]
        payload = {
            "source": "golden_dir",
            "golden_dir": str(gd_path),
            "golden_count": len(goldens_list),
            "passed": passed,
            "failed": failed,
            "total": len(all_results),
            "artifacts": artifacts,
        }
        _out(ok(payload, workspace=str(ws)), json_output)
        if not json_output:
            console.print(f"[bold]Batch Eval (dir):[/bold] {passed}/{len(all_results)} passed")
            for r in all_results:
                color = "green" if r.get("passed") else "red"
                console.print(
                    f"  [{color}]{'PASS' if r.get('passed') else 'FAIL'}[/{color}] {r.get('golden_id', '?')} score={r.get('score', 0)}"
                )
        return

    if not rid:
        _out(err(ArcErrorCode.INVALID_INPUT, "Run ID is required"), json_output)
        raise typer.Exit(1)

    run = store.load(rid)
    if run is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {rid}"), json_output)
        raise typer.Exit(1)

    if batch:
        goldens = list_goldens(ws)
        if not goldens:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "No saved golden traces found. Use 'arc eval save' first.",
                ),
                json_output,
            )
            raise typer.Exit(1)
        results = []
        for golden in goldens:
            result = do_eval(run, golden)
            results.append(result.model_dump())
        passed = sum(1 for r in results if r["passed"])
        payload = {
            "run_id": rid,
            "batch": True,
            "total": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "results": results,
        }
        _out(ok(payload, workspace=str(ws)), json_output)
        if not json_output:
            console.print(f"[bold]Batch Eval:[/bold] {passed}/{len(results)} passed")
            for r in results:
                color = "green" if r["passed"] else "red"
                console.print(
                    f"  [{color}]{'PASS' if r['passed'] else 'FAIL'}[/{color}] {r['golden_id']} score={r['score']}"
                )
        return

    events = (
        [t.strip() for t in expected_event_types.split(",") if t.strip()]
        if expected_event_types
        else []
    )

    golden = load_golden(ws, golden_id) if golden_id else None
    if golden_id and golden is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Golden not found: {golden_id}"), json_output)
        raise typer.Exit(1)
    golden = golden or GoldenTrace(
        id=f"cli-{rid}",
        workflow_id=run.workflow_id,
        expected_status=expected_status,
        expected_event_types=events,
        expected_final_output_contains=expected_output,
    )
    result = do_eval(run, golden)
    _out(ok(result.model_dump(), workspace=str(ws)), json_output)

    if not json_output:
        color = "green" if result.passed else "red"
        console.print(
            f"{'[synthetic/simulated] ' if getattr(result, 'synthetic', True) else ''}Eval [bold {color}]{'PASS' if result.passed else 'FAIL'}[/bold {color}]  score={result.score}"
        )
        console.print(
            f"  status_match={result.status_match}  event_type_match={result.event_type_match}  output_contains_match={result.output_contains_match}"
        )


@eval_app.command("compare")
def eval_compare(
    run_a: str = typer.Option("", "--run-a", help="First eval run ID"),
    run_b: str = typer.Option("", "--run-b", help="Second eval run ID"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Compare two eval runs and report delta."""
    _setup_logging(debug)
    from ..evals.artifact import EvalArtifactStore

    ws = _workspace(workspace)
    store = EvalArtifactStore(ws)

    artifacts_a = store.list_by_run(run_a)
    artifacts_b = store.list_by_run(run_b)

    if not artifacts_a:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"No eval artifacts for run: {run_a}"), json_output)
        raise typer.Exit(1)
    if not artifacts_b:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"No eval artifacts for run: {run_b}"), json_output)
        raise typer.Exit(1)

    a_map = {a.golden_id: a for a in artifacts_a}
    b_map = {b.golden_id: b for b in artifacts_b}
    all_ids = set(a_map.keys()) | set(b_map.keys())

    a_total = sum(a.total for a in artifacts_a)
    a_passed = sum(a.pass_count for a in artifacts_a)
    b_total = sum(b.total for b in artifacts_b)
    b_passed = sum(b.pass_count for b in artifacts_b)
    a_pass_rate = round(a_passed / a_total, 4) if a_total > 0 else 0.0
    b_pass_rate = round(b_passed / b_total, 4) if b_total > 0 else 0.0

    new_failures = []
    fixed_failures = []
    for gid in sorted(all_ids):
        a_failed = gid in a_map and a_map[gid].fail_count > 0
        b_failed = gid in b_map and b_map[gid].fail_count > 0
        if not a_failed and b_failed:
            new_failures.append(gid)
        elif a_failed and not b_failed:
            fixed_failures.append(gid)

    delta = round(b_pass_rate - a_pass_rate, 4)
    payload = {
        "delta_pass_rate": delta,
        "run_a_pass_rate": a_pass_rate,
        "run_b_pass_rate": b_pass_rate,
        "new_failures": new_failures,
        "fixed_failures": fixed_failures,
        "total_goldens_run_a": len(artifacts_a),
        "total_goldens_run_b": len(artifacts_b),
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@eval_app.command("export")
def eval_export(
    run_id: str = typer.Argument(..., help="Eval run ID to export"),
    format: str = typer.Option("inspect", "--format", help="Export format (inspect)"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export eval artifacts in Inspect-AI-compatible format."""
    _setup_logging(debug)
    from ..evals.artifact import EvalArtifactStore, build_inspect_export

    ws = _workspace(workspace)
    store = EvalArtifactStore(ws)
    artifacts = store.list_by_run(run_id)

    if not artifacts:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"No eval artifacts for run: {run_id}"), json_output)
        raise typer.Exit(1)

    if format == "inspect":
        export = build_inspect_export(run_id, artifacts)
        export_path = ws / ".arc" / "evals" / run_id / "inspect-export.json"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        import json as _json

        export_path.write_text(_json.dumps(export, indent=2))
        payload = {
            "format": "inspect",
            "path": str(export_path),
            "sample_count": len(artifacts),
        }
        _out(ok(payload, workspace=str(ws)), json_output)
    else:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Unsupported export format: {format}"), json_output)
        raise typer.Exit(1)


@eval_app.command("list")
def eval_list(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List saved golden traces."""
    _setup_logging(debug)
    from ..evals.golden import list_goldens

    ws = _workspace(workspace)
    goldens = list_goldens(ws)
    _out(ok([g.model_dump() for g in goldens]), json_output)
    if not json_output:
        from ._app import console

        table = __import__("rich").table.Table(title="Golden Traces")
        table.add_column("ID")
        table.add_column("Workflow")
        table.add_column("Expected Output (truncated)")
        for g in goldens:
            table.add_row(
                g.id,
                g.workflow_id,
                g.expected_final_output_contains[:60] if g.expected_final_output_contains else "",
            )
        console.print(table)


@eval_app.command("trending")
def eval_trending(
    run_ids: str = typer.Option("", "--run-ids", help="Comma-separated eval run IDs"),
    baseline: str = typer.Option("", "--baseline", help="Baseline run ID for delta"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Compute cross-session eval trending data."""
    _setup_logging(debug)
    from ..evals.artifact import EvalArtifactStore, compute_trending

    ws = _workspace(workspace)
    store = EvalArtifactStore(ws)

    if not run_ids:
        # Default: all runs
        all_run_ids = store.list_run_ids()
    else:
        all_run_ids = [rid.strip() for rid in run_ids.split(",") if rid.strip()]

    if not all_run_ids:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, "No eval runs found."), json_output)
        raise typer.Exit(1)

    artifacts_by_run: dict[str, list] = {}
    for rid in all_run_ids:
        artifacts = store.list_by_run(rid)
        if artifacts:
            artifacts_by_run[rid] = artifacts

    trending = compute_trending(artifacts_by_run, baseline_run_id=baseline or None)
    _out(ok(trending.model_dump(), workspace=str(ws)), json_output)

    if not json_output:
        from ._app import console

        console.print(f"[bold]Eval Trending:[/bold] {len(trending.run_ids)} runs")
        for i, rid in enumerate(trending.run_ids):
            console.print(
                f"  {rid[:16]}  pass_rate={trending.pass_rates[i]:.2%}  "
                f"({trending.timestamps[i][:19]})"
            )
        if baseline:
            console.print(f"  Delta from baseline: {trending.delta_from_baseline:+.4f}")


@eval_app.command("dashboard")
def eval_dashboard(
    last: int = typer.Option(10, "--last", "-n", help="Number of recent eval runs to show"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show eval dashboard with latest run summaries."""
    _setup_logging(debug)
    from ..evals.artifact import EvalArtifactStore

    ws = _workspace(workspace)
    store = EvalArtifactStore(ws)
    all_run_ids = store.list_run_ids()

    if not all_run_ids:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, "No eval runs found."), json_output)
        raise typer.Exit(1)

    recent = all_run_ids[-last:]
    runs_data = []
    for rid in recent:
        artifacts = store.list_by_run(rid)
        if artifacts:
            total = sum(a.total for a in artifacts)
            passed = sum(a.pass_count for a in artifacts)
            pass_rate = round(passed / total, 4) if total > 0 else 0.0
            runs_data.append(
                {
                    "run_id": rid,
                    "pass_rate": pass_rate,
                    "total": total,
                    "passed": passed,
                    "golden_count": len(artifacts),
                    "timestamp": artifacts[0].eval_timestamp,
                }
            )

    payload = {"count": len(runs_data), "runs": runs_data}
    _out(ok(payload, workspace=str(ws)), json_output)

    if not json_output:
        from ._app import console

        console.print(f"[bold]Eval Dashboard:[/bold] last {len(runs_data)} runs")
        for r in runs_data:
            color = (
                "green" if r["pass_rate"] >= 0.8 else "yellow" if r["pass_rate"] >= 0.5 else "red"
            )
            console.print(
                f"  [{color}]{r['run_id'][:16]}[/{color}]  "
                f"pass_rate={r['pass_rate']:.2%}  "
                f"goldens={r['golden_count']}  "
                f"({r['timestamp'][:19]})"
            )


@eval_app.command("recommend-policy")
def eval_recommend_policy(
    dataset: str = typer.Option(
        ...,
        "--dataset",
        "-d",
        help="Path to JSONL eval results or directory of EvalResult JSON files.",
    ),
    min_failure_rate: float = typer.Option(0.2, "--min-failure-rate"),
    min_sample: int = typer.Option(3, "--min-sample"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Analyse eval results and recommend policy adjustments."""
    _setup_logging(debug)
    import json as _json
    from pathlib import Path as _Path
    from ..evals.golden import EvalResult
    from ..evals.policy_recommend import recommend_policy, save_recommendations

    ds = _Path(dataset)
    results: list = []

    if ds.is_file() and ds.suffix == ".jsonl":
        for line in ds.read_text().splitlines():
            line = line.strip()
            if line:
                try:
                    results.append(EvalResult.model_validate(_json.loads(line)))
                except Exception:
                    pass
    elif ds.is_dir():
        for f in sorted(ds.glob("*.json")):
            try:
                results.append(EvalResult.model_validate_json(f.read_text()))
            except Exception:
                pass

    if not results:
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"No valid EvalResult records found in: {dataset}"),
            json_output,
        )
        raise typer.Exit(1)

    report = recommend_policy(results, min_failure_rate=min_failure_rate, min_sample=min_sample)
    ws = _workspace(workspace)
    saved = save_recommendations(report, ws)

    from ..flight_recorder import EventType, record_cli_event

    record_cli_event(
        EventType.EVAL_RECOMMENDATION_GENERATED,
        {
            "total_runs": report.total_runs,
            "failed_runs": report.failed_runs,
            "failure_rate": report.failure_rate,
            "recommendations_count": len(report.recommendations),
            "saved_to": str(saved),
        },
        source="arc.evals.recommend-policy",
    )

    payload = {**report.model_dump(), "saved_to": str(saved)}
    _out(ok(payload), json_output)
