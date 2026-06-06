"""Management commands: doctor, eval, hitl, isolation, storage, config (Phase 25)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from .. import __version__ as arc_version
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
    check_swarmgraph_runtime,
)
from ._subapps import config_app, doctor_app, eval_app, hitl_app, isolation_app, storage_app

# ─── doctor ──────────────────────────────────────────────────────────────────


@doctor_app.command("swarmgraph")
def doctor_swarmgraph(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Check SwarmGraph runtime availability without executing a workflow."""
    _setup_logging(debug)
    report = check_swarmgraph_runtime()
    _out(ok(report), json_output)
    if not report["ok"]:
        raise typer.Exit(1)


@doctor_app.command("all")
def doctor_all(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Run all diagnostic checks and report overall health.

    Runs runtime detection, daemon connectivity, and environment checks
    without executing any workflow.
    """
    import os
    import sys

    _setup_logging(debug)

    checks: list[dict] = []
    all_ok = True

    # 1. Python environment
    checks.append(
        {
            "check": "python",
            "ok": True,
            "version": sys.version.split()[0],
        }
    )

    # 2. Package version
    checks.append(
        {
            "check": "cli",
            "ok": True,
            "version": arc_version,
        }
    )

    # 3. Runtime detection
    try:
        from pathlib import Path

        ws = Path.cwd()
        from ..adapters.registry import default_registry

        registry = default_registry()
        runtimes = registry.detect_all(ws)
        runtime_names = [r.adapter for r in runtimes]
        checks.append(
            {
                "check": "runtimes",
                "ok": True,
                "detected": runtime_names,
                "count": len(runtime_names),
            }
        )
    except Exception as e:
        all_ok = False
        checks.append(
            {
                "check": "runtimes",
                "ok": False,
                "error": str(e),
            }
        )

    # 4. Daemon connectivity (best-effort, non-blocking)
    daemon_url = os.environ.get("ARC_PYTHON_DAEMON_URL")
    if daemon_url:
        try:
            # enforcement: not-applicable - Internal diagnostic health check, not user-triggered network access
            import urllib.request

            health_url = f"{daemon_url.rstrip('/')}/health"
            # enforcement: not-applicable
            req = urllib.request.Request(health_url)
            # enforcement: not-applicable
            with urllib.request.urlopen(req, timeout=2) as resp:
                daemon_reachable = resp.status == 200
                checks.append(
                    {
                        "check": "daemon",
                        "ok": daemon_reachable,
                        "reachable": daemon_reachable,
                        "url": daemon_url,
                    }
                )
                if not daemon_reachable:
                    all_ok = False
        except Exception:
            checks.append(
                {
                    "check": "daemon",
                    "ok": False,
                    "reachable": False,
                    "url": daemon_url,
                    "note": "daemon not running (offline-first is normal)",
                }
            )
    else:
        daemon_host = os.environ.get("ARC_DAEMON_HOST", "127.0.0.1")
        daemon_port = os.environ.get("ARC_DAEMON_PORT", "7777")
        try:
            # enforcement: not-applicable - Internal diagnostic health check, not user-triggered network access
            import urllib.request

            # enforcement: not-applicable
            req = urllib.request.Request(f"http://{daemon_host}:{daemon_port}/health")
            # enforcement: not-applicable
            with urllib.request.urlopen(req, timeout=2) as resp:
                daemon_reachable = resp.status == 200
                checks.append(
                    {
                        "check": "daemon",
                        "ok": daemon_reachable,
                        "reachable": daemon_reachable,
                        "host": daemon_host,
                        "port": daemon_port,
                    }
                )
                if not daemon_reachable:
                    all_ok = False
        except Exception:
            checks.append(
                {
                    "check": "daemon",
                    "ok": False,
                    "reachable": False,
                    "host": daemon_host,
                    "port": daemon_port,
                    "note": "daemon not running (offline-first is normal)",
                }
            )

    # 5. SwarmGraph CLI availability
    try:
        sg = check_swarmgraph_runtime()
        sg_ok = sg.get("ok", False)
        checks.append(
            {
                "check": "swarmgraph_cli",
                "ok": sg_ok,
                "details": sg,
            }
        )
        if not sg_ok:
            all_ok = False
    except Exception as e:
        all_ok = False
        checks.append(
            {
                "check": "swarmgraph_cli",
                "ok": False,
                "error": str(e),
            }
        )

    # 6. Provider diagnostics (env presence only, no network calls)
    try:
        from ..provider_action import provider_statuses

        providers = provider_statuses(os.environ)
        configured_count = sum(1 for p in providers if p.api_key_configured)
        checks.append(
            {
                "check": "providers",
                "ok": True,
                "total": len(providers),
                "configured": configured_count,
                "providers": [p.model_dump() for p in providers],
            }
        )
    except Exception as e:
        checks.append(
            {
                "check": "providers",
                "ok": False,
                "error": str(e),
            }
        )

    # 7. Workspace storage (fast checks: dir existence, file count, DB size, index count)
    try:
        from pathlib import Path

        ws = Path.cwd()
        traces_dir = ws / ".arc" / "traces"
        db_path = ws / ".arc" / "arc.db"
        evals_dir = ws / ".arc" / "evals"
        storage_checks = []
        storage_checks.append(
            {
                "check": "traces_dir",
                "ok": traces_dir.exists(),
                "path": str(traces_dir),
                "trace_count": len(list(traces_dir.glob("*.jsonl"))) if traces_dir.exists() else 0,
            }
        )
        storage_checks.append(
            {
                "check": "sqlite_index",
                "ok": db_path.exists(),
                "path": str(db_path),
                "size_bytes": db_path.stat().st_size if db_path.exists() else 0,
            }
        )
        if db_path.exists():
            from ..storage.sqlite import SqliteStore

            store = SqliteStore(db_path)
            storage_checks.append(
                {
                    "check": "indexed_runs",
                    "ok": True,
                    "count": store.count_runs(),
                }
            )
        storage_checks.append(
            {
                "check": "evals_dir",
                "ok": evals_dir.exists(),
                "path": str(evals_dir),
            }
        )
        storage_all_ok = all(c["ok"] for c in storage_checks if c["check"] != "evals_dir")
        if not storage_all_ok:
            all_ok = False
        checks.append(
            {
                "check": "workspace_storage",
                "ok": storage_all_ok,
                "scope": "workspace_storage",
                "details": storage_checks,
            }
        )
    except Exception as e:
        checks.append(
            {
                "check": "workspace_storage",
                "ok": False,
                "error": str(e),
            }
        )

    # 8. Event log health check
    try:
        import json as _json

        from ..events.persistence import DEFAULT_EVENT_LOG_PATH

        event_log_path = ws / DEFAULT_EVENT_LOG_PATH
        event_log_ok = True
        event_log_details: list[dict] = []
        event_log_details.append(
            {
                "check": "event_log_exists",
                "ok": event_log_path.exists(),
                "path": str(event_log_path),
            }
        )
        if event_log_path.exists():
            try:
                event_lines = event_log_path.read_text(encoding="utf-8").splitlines()
                valid_lines = sum(1 for l in event_lines if l.strip())
                corrupted = 0
                for line in event_lines:
                    line = line.strip()
                    if line:
                        try:
                            _json.loads(line)
                        except _json.JSONDecodeError:
                            corrupted += 1
                event_log_ok = corrupted == 0
                event_log_details.append(
                    {
                        "check": "event_log_not_corrupted",
                        "ok": event_log_ok,
                        "total_lines": len(event_lines),
                        "valid_lines": valid_lines,
                        "corrupted_lines": corrupted,
                    }
                )
                # Check max_entries
                max_entries = 2000  # Default from EventPersistenceWriter
                event_log_details.append(
                    {
                        "check": "event_log_within_max_entries",
                        "ok": len(event_lines) <= max_entries,
                        "current_count": len(event_lines),
                        "max_entries": max_entries,
                    }
                )
            except Exception as exc:
                event_log_ok = False
                event_log_details.append(
                    {
                        "check": "event_log_read_error",
                        "ok": False,
                        "error": str(exc),
                    }
                )
        if not event_log_ok:
            all_ok = False
        checks.append(
            {
                "check": "event_log",
                "ok": event_log_ok,
                "details": event_log_details,
            }
        )
    except Exception as e:
        checks.append(
            {
                "check": "event_log",
                "ok": False,
                "error": str(e),
            }
        )

    data = {"ok": all_ok, "checks": checks}
    _out(ok(data), json_output)
    if not all_ok:
        raise typer.Exit(1)


@doctor_app.command("env")
def doctor_env(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Check environment variables and Python configuration."""
    import os
    import sys

    _setup_logging(debug)
    checks = []
    all_ok = True
    checks.append(
        {
            "check": "python_version",
            "ok": True,
            "version": sys.version.split()[0],
            "executable": sys.executable,
        }
    )
    checks.append(
        {
            "check": "arc_version",
            "ok": True,
            "version": arc_version,
        }
    )
    key_envs = [
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "OPENROUTER_API_KEY",
        "QWEN_API_KEY",
        "MOONSHOT_API_KEY",
        "KIMI_API_KEY",
    ]
    configured = [name for name in key_envs if os.environ.get(name)]
    checks.append(
        {
            "check": "provider_keys",
            "ok": True,
            "configured": configured,
            "count": len(configured),
            "total": len(key_envs),
        }
    )
    arc_envs = {k: v for k, v in os.environ.items() if k.startswith("ARC_")}
    checks.append(
        {
            "check": "arc_env_vars",
            "ok": True,
            "vars": list(arc_envs.keys()),
            "count": len(arc_envs),
        }
    )
    data = {"ok": all_ok, "checks": checks}
    _out(ok(data), json_output)


@doctor_app.command("network")
def doctor_network(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Check network connectivity to common provider endpoints."""
    # enforcement: not-applicable - Diagnostic network check, not user-triggered agent execution
    import urllib.request

    _setup_logging(debug)
    endpoints = [
        ("openai", "https://api.openai.com"),
        ("anthropic", "https://api.anthropic.com"),
        ("openrouter", "https://openrouter.ai"),
    ]
    checks = []
    all_ok = True
    for name, url in endpoints:
        try:
            # enforcement: not-applicable - Diagnostic network check
            req = urllib.request.Request(url, method="HEAD")
            # enforcement: not-applicable - Diagnostic network check
            with urllib.request.urlopen(req, timeout=5) as resp:
                reachable = resp.status < 500
                checks.append(
                    {
                        "check": name,
                        "ok": reachable,
                        "url": url,
                        "status": resp.status,
                    }
                )
                if not reachable:
                    all_ok = False
        except Exception as e:
            all_ok = False
            checks.append(
                {
                    "check": name,
                    "ok": False,
                    "url": url,
                    "error": str(e),
                }
            )
    data = {"ok": all_ok, "checks": checks}
    _out(ok(data), json_output)


@doctor_app.command("storage")
def doctor_storage(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Check workspace storage and trace files."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    traces_dir = ws / ".arc" / "traces"
    db_path = ws / ".arc" / "arc.db"
    evals_dir = ws / ".arc" / "evals"
    checks = []
    checks.append(
        {
            "check": "traces_dir",
            "ok": traces_dir.exists(),
            "path": str(traces_dir),
            "trace_count": len(list(traces_dir.glob("*.jsonl"))) if traces_dir.exists() else 0,
        }
    )
    checks.append(
        {
            "check": "sqlite_index",
            "ok": db_path.exists(),
            "path": str(db_path),
            "size_bytes": db_path.stat().st_size if db_path.exists() else 0,
        }
    )
    if db_path.exists():
        from ..storage.sqlite import SqliteStore

        store = SqliteStore(db_path)
        checks.append(
            {
                "check": "indexed_runs",
                "ok": True,
                "count": store.count_runs(),
            }
        )
    checks.append(
        {
            "check": "evals_dir",
            "ok": evals_dir.exists(),
            "path": str(evals_dir),
        }
    )
    all_ok = all(c["ok"] for c in checks if c["check"] != "evals_dir")
    data = {"ok": all_ok, "checks": checks, "workspace": str(ws)}
    _out(ok(data), json_output)


# ─── eval ─────────────────────────────────────────────────────────────────────


@eval_app.command("run")
def eval_run(
    run_id: str = typer.Argument(..., help="Run ID to evaluate"),
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
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Evaluate a run against a golden trace.

    Provide --golden to load a saved golden trace, or specify
    --expected-final-output/--expected-status/--expected-event-types inline.
    Use --batch to evaluate against all saved golden traces.

    Example:
        uv run arc eval run <run_id> --expected-final-output "hello" --expected-status completed
        uv run arc eval run <run_id> --golden my-golden-id
        uv run arc eval run <run_id> --batch

    """
    _setup_logging(debug)
    from ..evals.golden import GoldenTrace, list_goldens, load_golden
    from ..evals.golden import eval_run as do_eval
    from ..storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run = store.load(run_id)
    if run is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
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
            "run_id": run_id,
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
        id=f"cli-{run_id}",
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
    from pathlib import Path

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


# ─── hitl ──────────────────────────────────────────────────────────────────────


@hitl_app.command("pending")
def hitl_pending(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List pending workspace-local HITL prompts with single-use tokens."""
    _setup_logging(debug)
    from ..audit.hitl_store import get_token, list_prompts

    ws = _workspace(workspace)
    prompts = list_prompts(ws)
    results = []
    for prompt in prompts:
        token = get_token(ws, prompt.hitl_id)
        entry = prompt.model_dump()
        entry["token"] = token
        results.append(entry)
    _out(ok(results, workspace=str(ws)), json_output)
    if not json_output:
        if not results:
            console.print("[dim]No pending HITL prompts.[/dim]")
            return
        table = Table(title="Pending HITL Prompts")
        table.add_column("HITL ID")
        table.add_column("Run ID")
        table.add_column("Token")
        for r in results:
            table.add_row(r["hitl_id"][:12], r["run_id"][:12], r.get("token", "")[:8] + "...")
        console.print(table)


@hitl_app.command("respond")
def hitl_respond(
    hitl_id: str = typer.Argument(..., help="Pending HITL prompt ID"),
    decision: str = typer.Option(..., "--decision", help="approve | reject | modify | skip"),
    token: str = typer.Option(..., "--token", "-t", help="Single-use decision token"),
    notes: str = typer.Option("", "--notes", help="Operator notes"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Respond to a pending workspace-local HITL prompt.

    Requires the single-use token from 'arc hitl pending'.
    """
    _setup_logging(debug)
    from ..audit.hitl import HitlDecision
    from ..audit.hitl_store import respond

    ws = _workspace(workspace)
    try:
        parsed = HitlDecision(decision)
    except ValueError:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid HITL decision: {decision}"), json_output)
        raise typer.Exit(1)
    response = respond(ws, hitl_id, parsed, token=token, notes=notes)
    if response is None:
        _out(
            err(
                ArcErrorCode.RUN_NOT_FOUND,
                f"HITL prompt not found, expired, already responded, or token mismatch: {hitl_id}",
            ),
            json_output,
        )
        raise typer.Exit(1)
    _out(ok(response.model_dump(), workspace=str(ws)), json_output)
    if not json_output:
        console.print(f"[green]HITL {decision} recorded for {hitl_id[:12]}[/green]")


@hitl_app.command("approve")
def hitl_approve(
    hitl_id: str = typer.Argument(..., help="Pending HITL prompt ID"),
    token: str = typer.Option(..., "--token", "-t", help="Single-use decision token"),
    notes: str = typer.Option("", "--notes", help="Operator notes"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Approve a pending workspace-local HITL prompt."""
    hitl_respond(hitl_id, "approve", token, notes, workspace, json_output, debug)


@hitl_app.command("reject")
def hitl_reject(
    hitl_id: str = typer.Argument(..., help="Pending HITL prompt ID"),
    token: str = typer.Option(..., "--token", "-t", help="Single-use decision token"),
    notes: str = typer.Option("", "--notes", help="Operator notes"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Reject a pending workspace-local HITL prompt."""
    hitl_respond(hitl_id, "reject", token, notes, workspace, json_output, debug)


# ─── isolation ──────────────────────────────────────────────────────────────────


@isolation_app.command("status")
def isolation_status(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show the active isolation backend plus provider health."""
    _setup_logging(debug)
    from ..config.loader import load_config
    from ..isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from ..isolation.docker_provider import DockerIsolationProvider
    from ..isolation.selector import resolve_isolation_backend

    config = load_config(Path(workspace).expanduser() if workspace else None)
    configured = config.execution.isolation
    active = resolve_isolation_backend(config)

    providers = [
        NoneIsolationProvider(),
        SubprocessIsolationProvider(),
        DockerIsolationProvider(),
    ]
    results = []
    for p in providers:
        import asyncio

        try:
            healthy = asyncio.run(p.health_check())
        finally:
            close = getattr(p, "close", None)
            if callable(close):
                close()
        results.append(
            {
                "provider_id": p.provider_id,
                "healthy": healthy,
            }
        )
    _out(
        ok({"configured": configured, "active": active, "providers": results}),
        json_output,
    )


@isolation_app.command("use")
def isolation_use(
    backend: str = typer.Argument(..., help="Backend: auto, subprocess, docker, or microvm"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Persist the isolation backend choice (writes execution.isolation)."""
    _setup_logging(debug)
    from ..config.loader import USER_CONFIG_PATH, set_isolation_backend

    name = backend.strip().lower()
    selectable = ("auto", "subprocess", "docker", "microvm")
    if name not in selectable:
        hint = " (use `arc isolation off` to disable isolation)" if name == "none" else ""
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Invalid backend {backend!r}; choose one of {', '.join(selectable)}.{hint}",
            ),
            json_output,
        )
        raise typer.Exit(2)
    config_path = (
        Path(workspace).expanduser() / ".arc" / "config.yaml" if workspace else USER_CONFIG_PATH
    )
    written = set_isolation_backend(name, config_path=config_path)
    _out(ok({"isolation": name, "config_path": str(written)}), json_output)


@isolation_app.command("off")
def isolation_off(
    yes: bool = typer.Option(False, "--yes", help="Skip the interactive typed confirmation"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Disable isolation (execution.isolation = none). Requires confirmation."""
    _setup_logging(debug)
    from ..config.loader import USER_CONFIG_PATH, set_isolation_backend

    if not yes:
        if json_output:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Refusing to disable isolation without --yes in JSON mode",
                ),
                json_output,
            )
            raise typer.Exit(2)
        typer.echo(
            "WARNING: disabling isolation runs sandbox/agent commands with NO isolation layer.\n"
            "Deny-by-default policy checks still apply, but environment scrubbing and process\n"
            "confinement are removed. This is not recommended."
        )
        confirm = typer.prompt("Type 'disable isolation' to confirm")
        if confirm.strip().lower() != "disable isolation":
            _out(
                err(ArcErrorCode.INVALID_INPUT, "Confirmation text did not match; no change made"),
                json_output,
            )
            raise typer.Exit(2)
    config_path = (
        Path(workspace).expanduser() / ".arc" / "config.yaml" if workspace else USER_CONFIG_PATH
    )
    written = set_isolation_backend("none", config_path=config_path)
    _out(
        ok({"isolation": "none", "config_path": str(written), "warning": "isolation disabled"}),
        json_output,
    )


@isolation_app.command("doctor")
def isolation_doctor(
    provider: str = typer.Argument("all", help="Provider ID or 'all'"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run diagnostics on an isolation provider."""
    _setup_logging(debug)
    from ..isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from ..isolation.docker_provider import DockerIsolationProvider

    provider_map = {
        "none": NoneIsolationProvider(),
        "subprocess": SubprocessIsolationProvider(),
        "docker": DockerIsolationProvider(),
    }
    if provider != "all":
        if provider not in provider_map:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    f"Unknown provider: {provider}. Available: {', '.join(provider_map)}",
                ),
                json_output,
            )
            raise typer.Exit(1)
        provider_map = {provider: provider_map[provider]}

    import asyncio

    results = []
    for pid, p in provider_map.items():
        try:
            healthy = asyncio.run(p.health_check())
            results.append(
                {
                    "provider_id": pid,
                    "healthy": healthy,
                    "description": p.describe(),
                }
            )
        finally:
            close = getattr(p, "close", None)
            if callable(close):
                close()
    from ..config.loader import load_config
    from ..isolation.selector import resolve_isolation_backend

    config = load_config(None)
    _out(
        ok(
            {
                "configured": config.execution.isolation,
                "active": resolve_isolation_backend(config),
                "diagnostics": results,
            }
        ),
        json_output,
    )


@isolation_app.command("list")
def isolation_list(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List available isolation providers."""
    _setup_logging(debug)
    from ..isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from ..isolation.docker_provider import DockerIsolationProvider

    provider_objects = [
        NoneIsolationProvider(),
        SubprocessIsolationProvider(),
        DockerIsolationProvider(),
    ]
    providers = []
    for p in provider_objects:
        try:
            providers.append(p.describe())
        finally:
            close = getattr(p, "close", None)
            if callable(close):
                close()
    _out(ok({"providers": providers}), json_output)


@isolation_app.command("setup")
def isolation_setup(
    provider: str = typer.Argument(..., help="Provider to set up (docker)"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Set up an isolation provider.

    For Docker, checks if the daemon is reachable and provides guidance.
    """
    _setup_logging(debug)
    from ..isolation.docker_provider import DockerIsolationProvider

    if provider != "docker":
        _out(err(ArcErrorCode.INVALID_INPUT, f"Setup not available for: {provider}"), json_output)
        raise typer.Exit(1)

    docker = DockerIsolationProvider()
    try:
        runtime = docker.detect_runtime()
        import asyncio

        healthy = asyncio.run(docker.health_check())
    finally:
        docker.close()

    payload = {
        "provider": "docker",
        "healthy": healthy,
        "runtime": runtime,
        "installed": runtime["available"],
    }
    _out(ok(payload), json_output)
    if not json_output:
        if healthy:
            console.print(f"[green]Docker is available[/green] (runtime: {runtime['runtime']})")
            console.print(f"  Version: {runtime.get('version', 'unknown')}")
        else:
            console.print("[yellow]Docker is not available[/yellow]")
            if runtime.get("error"):
                console.print(f"  Error: {runtime['error']}")
            console.print("")
            console.print(
                "[dim]Install Docker Desktop, OrbStack, or Podman to enable container isolation.[/dim]"
            )


@isolation_app.command("test")
def isolation_test(
    provider: str = typer.Argument("subprocess", help="Provider to test"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Test an isolation provider with a simple command."""
    _setup_logging(debug)
    from ..isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from ..isolation.docker_provider import DockerIsolationProvider

    provider_map = {
        "none": NoneIsolationProvider(),
        "subprocess": SubprocessIsolationProvider(),
        "docker": DockerIsolationProvider(),
    }
    if provider not in provider_map:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Unknown provider: {provider}. Available: {', '.join(provider_map)}",
            ),
            json_output,
        )
        raise typer.Exit(1)

    p = provider_map[provider]
    import asyncio

    try:
        result = asyncio.run(p.execute(["echo", "ARC isolation test OK"]))
    finally:
        close = getattr(p, "close", None)
        if callable(close):
            close()
    payload = result.model_dump()
    _out(ok(payload), json_output)
    if not json_output:
        if result.exit_code == 0:
            console.print(f"[green]{provider} test passed[/green]")
            console.print(f"  Output: {result.stdout.strip()}")
            console.print(f"  Duration: {result.duration_ms}ms")
        else:
            console.print(f"[red]{provider} test failed[/red]")
            console.print(f"  Exit code: {result.exit_code}")
            console.print(f"  Error: {result.stderr.strip()}")


# ─── storage ──────────────────────────────────────────────────────────────────


@storage_app.command("vacuum")
def storage_vacuum(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Vacuum SQLite index to reclaim space after deletions."""
    _setup_logging(debug)
    import sqlite3

    ws = _workspace(workspace)
    db_path = ws / ".arc" / "arc.db"
    if not db_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, "SQLite index not found."), json_output)
        raise typer.Exit(1)
    size_before = db_path.stat().st_size
    try:
        with sqlite3.connect(str(db_path)) as conn:
            conn.execute("VACUUM")
        size_after = db_path.stat().st_size
        saved = size_before - size_after
        payload = {
            "workspace": str(ws),
            "db_path": str(db_path),
            "size_before": size_before,
            "size_after": size_after,
            "saved_bytes": saved,
        }
        _out(ok(payload, workspace=str(ws)), json_output)
        if not json_output:
            console.print(f"[green]Vacuumed[/green] {db_path}")
            console.print(f"  Before: {size_before:,} bytes")
            console.print(f"  After: {size_after:,} bytes")
            if saved > 0:
                console.print(f"  Saved: {saved:,} bytes")
    except Exception as e:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Vacuum failed: {e}"), json_output)
        raise typer.Exit(1)


@storage_app.command("status")
def storage_status(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show storage usage statistics."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    traces_dir = ws / ".arc" / "traces"
    db_path = ws / ".arc" / "arc.db"
    goldens_dir = ws / ".arc" / "goldens"
    hitl_dir = ws / ".arc" / "hitl"

    trace_count = len(list(traces_dir.glob("*.jsonl"))) if traces_dir.exists() else 0
    trace_size = (
        sum(p.stat().st_size for p in traces_dir.glob("*.jsonl")) if traces_dir.exists() else 0
    )
    db_size = db_path.stat().st_size if db_path.exists() else 0
    golden_count = len(list(goldens_dir.glob("*.json"))) if goldens_dir.exists() else 0
    hitl_pending = (
        len(list((hitl_dir / "pending").glob("*.json"))) if (hitl_dir / "pending").exists() else 0
    )

    payload = {
        "workspace": str(ws),
        "traces": {
            "count": trace_count,
            "size_bytes": trace_size,
            "dir": str(traces_dir),
        },
        "sqlite_index": {
            "exists": db_path.exists(),
            "size_bytes": db_size,
            "path": str(db_path),
        },
        "goldens": {
            "count": golden_count,
            "dir": str(goldens_dir),
        },
        "hitl": {
            "pending": hitl_pending,
            "dir": str(hitl_dir),
        },
    }
    _out(ok(payload, workspace=str(ws)), json_output)
    if not json_output:
        console.print(f"[bold]Storage Status[/bold] — {ws}")
        console.print(f"  Traces: {trace_count} files ({trace_size:,} bytes)")
        console.print(
            f"  SQLite: {'exists' if db_path.exists() else 'not found'} ({db_size:,} bytes)"
        )
        console.print(f"  Goldens: {golden_count}")
        console.print(f"  HITL pending: {hitl_pending}")


# ─── config (ADR-001) ──────────────────────────────────────────────────────────


@config_app.command("init")
def config_init(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate default .arc/config.yaml in the workspace."""
    _setup_logging(debug)
    from ..config import init_config

    ws = _workspace(workspace)
    config_path = init_config(ws)
    _out(ok({"config_path": str(config_path), "version": 1}, workspace=str(ws)), json_output)


@config_app.command("show")
def config_show(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show resolved ARC configuration for the workspace."""
    _setup_logging(debug)
    from ..config import load_config

    ws = _workspace(workspace)
    config = load_config(ws)
    _out(ok(config.flatten(), workspace=str(ws)), json_output)


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
