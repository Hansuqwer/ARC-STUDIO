"""Management commands: doctor, eval, hitl, isolation, storage, config (Phase 25)."""

from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

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

from .. import __version__ as arc_version
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok


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
            import urllib.request

            health_url = f"{daemon_url.rstrip('/')}/health"
            req = urllib.request.Request(health_url)
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
            import urllib.request

            req = urllib.request.Request(f"http://{daemon_host}:{daemon_port}/health")
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
            req = urllib.request.Request(url, method="HEAD")
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
    from ..evals.golden import GoldenTrace, eval_run as do_eval, load_golden, list_goldens
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
            f"Eval [bold {color}]{'PASS' if result.passed else 'FAIL'}[/bold {color}]  score={result.score}"
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
        table = Table(title="Golden Traces")
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
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show available isolation providers and their health status."""
    _setup_logging(debug)
    from ..isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from ..isolation.docker_provider import DockerIsolationProvider

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
    _out(ok({"providers": results}), json_output)


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
    _out(ok({"diagnostics": results}), json_output)


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
