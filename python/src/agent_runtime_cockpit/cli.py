"""
ARC CLI — Agent Runtime Cockpit command-line interface.

Commands:
  arc version    — print ARC version information
  arc health     — check ARC daemon and environment health
  arc status     — show ARC workspace and runtime status overview
  arc inspect    — inspect workspace, detect runtimes
  arc runtimes   — list detected runtimes
  arc workflows  — list detected workflows
  arc schemas    — list detected schemas
  arc serve      — start HTTP daemon
  arc run        — execute a workflow
  arc runs       — list stored runs
  arc doctor     — diagnostics (swarmgraph, all)
  arc context    — context retrieval commands
  arc adapter    — adapter management and conformance testing
"""
from __future__ import annotations

import logging
import shutil
import subprocess
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.json import JSON
from rich import print as rprint

from . import __version__ as arc_version
from .adapters.registry import default_registry
from .context.pack import ContextPackGenerator
from .gating import GatingError
from .orchestration import runtime_router
from .protocol.envelope import ok, err, ArcEnvelope
from .protocol.errors import ArcErrorCode
from .security.validation import validate_workspace_path
from .workspace import iter_workspace_files

app = typer.Typer(
    name="arc",
    help="ARC — Agent Runtime Cockpit CLI",
    no_args_is_help=True,
)

context_app = typer.Typer(name="context", help="Context retrieval commands")
adapter_app = typer.Typer(name="adapter", help="Adapter management commands")
doctor_app = typer.Typer(name="doctor", help="ARC diagnostics")
workspace_app = typer.Typer(name="workspace", help="Workspace configuration and trust management")
isolation_app = typer.Typer(name="isolation", help="Execution isolation providers")
config_app = typer.Typer(name="config", help="ARC workspace configuration (ADR-001)")
hitl_app = typer.Typer(name="hitl", help="Human-in-the-loop approval commands")
app.add_typer(context_app)
app.add_typer(adapter_app)
app.add_typer(doctor_app)
app.add_typer(workspace_app)
app.add_typer(isolation_app)
app.add_typer(config_app)
app.add_typer(hitl_app)

console = Console()
err_console = Console(stderr=True)

JSON_FLAG = typer.Option(False, "--json", help="Output raw JSON envelope")
WORKSPACE_FLAG = typer.Option(None, "--workspace", "-w", help="Workspace path (default: cwd)")
DEBUG_FLAG = typer.Option(False, "--debug", envvar="ARC_DEBUG", help="Enable debug logging")


def _setup_logging(debug: bool) -> None:
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(level=level, format="%(name)s %(levelname)s %(message)s")


def _workspace(workspace: Optional[str]) -> Path:
    if workspace:
        try:
            return validate_workspace_path(workspace)
        except ValueError as e:
            err_console.print(f"[red]Invalid workspace: {e}[/red]")
            raise typer.Exit(1)
    return Path.cwd()


def _out(envelope: ArcEnvelope, as_json: bool) -> None:
    if as_json:
        print(envelope.model_dump_json(indent=2))
    else:
        if not envelope.ok:
            err_console.print(f"[red]Error [{envelope.error.code}]: {envelope.error.message}[/red]")
        else:
            rprint(JSON(envelope.model_dump_json()))


def check_swarmgraph_runtime(timeout: float = 5.0) -> dict[str, object]:
    """Check local SwarmGraph CLI availability without network calls."""
    candidates = [
        ("swarmgraph", ["--version"]),
        ("arc-swarmgraph", ["--version"]),
        ("arc", ["run", "--help"]),
    ]
    checks: list[dict[str, object]] = []
    for command, args in candidates:
        resolved = shutil.which(command)
        if not resolved:
            checks.append({"command": command, "available": False, "reason": "not_found"})
            continue
        try:
            result = subprocess.run(
                [resolved, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            checks.append({"command": command, "path": resolved, "available": False, "reason": "timeout"})
            continue
        output = (result.stdout or result.stderr).strip().splitlines()
        checks.append({
            "command": command,
            "path": resolved,
            "available": result.returncode == 0,
            "exit_code": result.returncode,
            "version": output[0][:200] if output else "",
        })
    return {"ok": any(bool(check.get("available")) for check in checks), "checks": checks}


# ─── version ──────────────────────────────────────────────────────────────────


@app.command()
def version(
    json_output: bool = JSON_FLAG,
) -> None:
    """Print ARC version information."""
    import sys
    data = {
        "version": arc_version,
        "python": sys.version.split()[0],
        "platform": sys.platform,
    }
    envelope = ok(data)
    _out(envelope, json_output)


# ─── health ───────────────────────────────────────────────────────────────────


@app.command()
def health(
    json_output: bool = JSON_FLAG,
) -> None:
    """Check ARC daemon and environment health."""
    import os
    import sys
    import time
    t0 = time.time()

    checks: list[dict] = []
    all_ok = True

    # Check daemon reachability (optional, non-blocking)
    daemon_host = os.environ.get("ARC_DAEMON_HOST", "127.0.0.1")
    daemon_port = os.environ.get("ARC_DAEMON_PORT", "7777")
    try:
        import urllib.request
        req = urllib.request.Request(f"http://{daemon_host}:{daemon_port}/health")
        with urllib.request.urlopen(req, timeout=2) as resp:
            daemon_ok = resp.status == 200
            if not daemon_ok:
                all_ok = False
            checks.append({
                "check": "daemon",
                "ok": daemon_ok,
                "status": resp.status if daemon_ok else "unhealthy",
            })
    except Exception as exc:
        all_ok = False
        checks.append({
            "check": "daemon",
            "ok": False,
            "status": f"unreachable: {type(exc).__name__}",
        })

    # Check Python environment
    checks.append({
        "check": "python",
        "ok": True,
        "version": sys.version.split()[0],
    })

    # Check CLI available
    checks.append({
        "check": "cli",
        "ok": True,
        "version": arc_version,
    })

    data = {
        "ok": all_ok,
        "checks": checks,
    }
    envelope = ok(data, duration_ms=(time.time() - t0) * 1000)
    _out(envelope, json_output)


# ─── status ───────────────────────────────────────────────────────────────────


@app.command()
def status(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show ARC workspace and runtime status overview."""
    import time
    _setup_logging(debug)
    ws = _workspace(workspace)
    t0 = time.time()

    # Detect runtimes
    registry = default_registry()
    runtimes = registry.detect_all(ws)
    runtime_list = []
    for rt in runtimes:
        adapter = registry.get(rt.adapter)
        if adapter is not None:
            report = adapter.capability_report(ws)
            runtime_list.append({
                "id": rt.adapter,
                "detected": True,
                "can_run": report.can_run,
                "paid": report.requires_paid_calls,
            })
        else:
            runtime_list.append({
                "id": rt.adapter,
                "detected": True,
                "can_run": False,
                "note": "adapter not found in registry",
            })

    # Trace count
    from .storage.jsonl import JsonlTraceStore
    store = JsonlTraceStore(ws / ".arc" / "traces")
    trace_ids = store.list_runs()

    # Python files in workspace
    py_files = len(list(ws.rglob("*.py"))) if ws.is_dir() else 0

    data = {
        "workspace": str(ws),
        "runtimes": runtime_list,
        "runtime_count": len(runtime_list),
        "trace_count": len(trace_ids),
        "python_files": py_files,
    }
    envelope = ok(data, workspace=str(ws), duration_ms=(time.time() - t0) * 1000)
    _out(envelope, json_output)


# ─── inspect ──────────────────────────────────────────────────────────────────

@app.command()
def inspect(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Inspect a workspace and detect agent runtimes."""
    _setup_logging(debug)
    import time
    ws = _workspace(workspace)
    t0 = time.time()

    registry = default_registry()
    runtimes = registry.detect_all(ws)

    py_count = len(iter_workspace_files(ws, (".py",)))
    ts_count = len(iter_workspace_files(ws, (".ts",)))

    from .protocol.schemas import WorkspaceInfo
    info = WorkspaceInfo(
        path=str(ws),
        runtimes=runtimes,
        files_scanned=py_count + ts_count,
        detection_warnings=[] if runtimes else ["No runtimes detected"],
    )

    envelope = ok(info.model_dump(), workspace=str(ws),
                  duration_ms=(time.time() - t0) * 1000)
    _out(envelope, json_output)

    if not json_output:
        table = Table(title="Detected Runtimes")
        table.add_column("ID")
        table.add_column("Adapter")
        table.add_column("Confidence")
        table.add_column("Evidence")
        for r in runtimes:
            table.add_row(r.id, r.adapter, r.confidence, " | ".join(r.evidence[:2]))
        console.print(table)
        console.print(f"[dim]Files scanned: {info.files_scanned}[/dim]")


# ─── runtimes ─────────────────────────────────────────────────────────────────

@app.command()
def runtimes(
    workspace: Optional[str] = WORKSPACE_FLAG,
    capabilities: bool = typer.Option(False, "--capabilities", help="List all adapter capability reports"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List detected runtimes in a workspace."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    if capabilities:
        reports = runtime_router.list_runtimes(ws)
        payload = {
            "workspace": str(ws),
            "auto_priority": list(runtime_router.AUTO_PRIORITY),
            "runtimes": [report.model_dump() for report in reports],
        }
        if json_output:
            _out(ok(payload, workspace=str(ws)), json_output)
            return
        console.print(f"workspace: {ws}")
        console.print(f"auto priority: {' > '.join(runtime_router.AUTO_PRIORITY)}")
        table = Table(title="Runtime Capabilities")
        table.add_column("Runtime")
        table.add_column("Detected")
        table.add_column("Can Run")
        table.add_column("Paid")
        table.add_column("Availability")
        table.add_column("Reason")
        for report in reports:
            table.add_row(
                report.runtime_id,
                "yes" if report.detected else "no",
                "yes" if report.can_run else "no",
                "yes" if report.requires_paid_calls else "no",
                report.availability,
                (report.reason or "")[:80],
            )
        console.print(table)
        return
    registry = default_registry()
    detected = registry.detect_all(ws)
    envelope = ok([r.model_dump() for r in detected], workspace=str(ws))
    _out(envelope, json_output)


# ─── workflows ────────────────────────────────────────────────────────────────

@app.command()
def workflows(
    workspace: Optional[str] = WORKSPACE_FLAG,
    runtime: Optional[str] = typer.Option(None, "--runtime", "-r"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List detected workflows in a workspace."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    registry = default_registry()
    detected = registry.detect_all(ws)
    results = []
    for rt in detected:
        if runtime and rt.adapter != runtime:
            continue
        adapter = registry.get(rt.adapter)
        if adapter and adapter.capabilities().can_export_workflow:
            try:
                wfs = adapter.export_workflow(ws)
                results.extend(w.model_dump() for w in wfs)
            except Exception as e:
                err_console.print(f"[yellow]Warning: {rt.adapter} workflow export failed: {e}[/yellow]")

    _out(ok(results, workspace=str(ws)), json_output)


# ─── schemas ──────────────────────────────────────────────────────────────────

@app.command()
def schemas(
    workspace: Optional[str] = WORKSPACE_FLAG,
    runtime: Optional[str] = typer.Option(None, "--runtime", "-r"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List detected schemas in a workspace."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    registry = default_registry()
    detected = registry.detect_all(ws)
    results = []
    for rt in detected:
        if runtime and rt.adapter != runtime:
            continue
        adapter = registry.get(rt.adapter)
        if adapter and adapter.capabilities().can_export_schema:
            try:
                ss = adapter.export_schemas(ws)
                results.extend(s.model_dump_api() for s in ss)
            except Exception as e:
                err_console.print(f"[yellow]Warning: {rt.adapter} schema export failed: {e}[/yellow]")

    _out(ok(results, workspace=str(ws)), json_output)


# ─── serve ────────────────────────────────────────────────────────────────────

@app.command()
def serve(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(7777, "--port"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Start the ARC HTTP daemon."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    console.print(f"[bold cyan]ARC[/bold cyan] daemon starting on http://{host}:{port}")
    from .web.server import run_server
    run_server(host=host, port=port, workspace=ws)


# ─── run ──────────────────────────────────────────────────────────────────────

@app.command("run")
def run_workflow(
    workflow: str = typer.Argument("wf-swarmgraph-fixture", help="Workflow ID"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    runtime: str = typer.Option("auto", "--runtime", "-r", help="Runtime: auto, swarmgraph, langgraph, crewai, lmarena"),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="Prompt passed to runnable adapters"),
    allow_paid_calls: bool = typer.Option(False, "--allow-paid-calls", help="Allow runtimes to make provider calls"),
    profile_id: str = typer.Option("local-safe", "--profile-id", help="Run profile ID"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Execute a workflow and return the run record."""
    import asyncio
    _setup_logging(debug)
    ws = _workspace(workspace)
    try:
        requested_runtime = [part.strip().lower() for part in runtime.split(",") if part.strip()] if "," in runtime else runtime.lower()
        routed = runtime_router.resolve(ws, requested_runtime, allow_paid_calls=allow_paid_calls)
    except runtime_router.UnknownRuntime as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": exc.code}), json_output)
        raise typer.Exit(2)
    except runtime_router.RuntimeRouterError as exc:
        _out(err(ArcErrorCode.NOT_IMPLEMENTED, str(exc), details={"code": exc.code}), json_output)
        raise typer.Exit(1)

    if not json_output:
        console.print(f"[dim]Runtime:[/dim] {routed.adapter.adapter_id} ({routed.chosen_by})")

    inputs = {"workspace": str(ws), "allow_paid_calls": allow_paid_calls, "profile_id": profile_id}
    if prompt:
        inputs["prompt"] = prompt
    try:
        run_record = asyncio.run(routed.adapter.run_workflow(workflow, inputs))
    except GatingError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": "DUAL_GATE_REQUIRED"}), json_output)
        raise typer.Exit(2)

    from .storage.jsonl import JsonlTraceStore
    store = JsonlTraceStore(ws / ".arc" / "traces")
    trace_path = store.trace_path(run_record.id)
    run_record.metadata["trace_path"] = str(trace_path)
    store.save(run_record)

    _out(ok(run_record.model_dump()), json_output)
    if not json_output:
        console.print(f"[green]Run completed:[/green] {run_record.id} ({len(run_record.events)} events)")


# ─── runs ─────────────────────────────────────────────────────────────────────

runs_app = typer.Typer(name="runs", help="List and manage stored run records", invoke_without_command=True)
app.add_typer(runs_app)

eval_app = typer.Typer(name="eval", help="Evaluate runs against golden traces")
app.add_typer(eval_app)

providers_app = typer.Typer(name="providers", help="Provider definitions and dry-run routing")
app.add_typer(providers_app)


@providers_app.command("list")
def providers_list(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """List built-in provider definitions. No network calls are made."""
    _setup_logging(debug)
    from .providers import PROVIDERS
    _out(ok([provider.model_dump() for provider in PROVIDERS]), json_output)


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
    checks.append({
        "check": "python",
        "ok": True,
        "version": sys.version.split()[0],
    })

    # 2. Package version
    checks.append({
        "check": "cli",
        "ok": True,
        "version": arc_version,
    })

    # 3. Runtime detection
    try:
        ws = Path.cwd()
        registry = default_registry()
        runtimes = registry.detect_all(ws)
        runtime_names = [r.adapter for r in runtimes]
        checks.append({
            "check": "runtimes",
            "ok": True,
            "detected": runtime_names,
            "count": len(runtime_names),
        })
    except Exception as e:
        all_ok = False
        checks.append({
            "check": "runtimes",
            "ok": False,
            "error": str(e),
        })

    # 4. Daemon connectivity (best-effort, non-blocking)
    daemon_host = os.environ.get("ARC_DAEMON_HOST", "127.0.0.1")
    daemon_port = os.environ.get("ARC_DAEMON_PORT", "7777")
    try:
        import urllib.request
        req = urllib.request.Request(f"http://{daemon_host}:{daemon_port}/health")
        with urllib.request.urlopen(req, timeout=2) as resp:
            daemon_reachable = resp.status == 200
            checks.append({
                "check": "daemon",
                "ok": daemon_reachable,
                "reachable": daemon_reachable,
            })
            if not daemon_reachable:
                all_ok = False
    except Exception:
        checks.append({
            "check": "daemon",
            "ok": False,
            "reachable": False,
            "note": "daemon not running (offline-first is normal)",
        })

    # 5. SwarmGraph CLI availability
    try:
        sg = check_swarmgraph_runtime()
        sg_ok = sg.get("ok", False)
        checks.append({
            "check": "swarmgraph_cli",
            "ok": sg_ok,
            "details": sg,
        })
        if not sg_ok:
            all_ok = False
    except Exception as e:
        all_ok = False
        checks.append({
            "check": "swarmgraph_cli",
            "ok": False,
            "error": str(e),
        })

    # 6. Provider diagnostics (env presence only, no network calls)
    try:
        from .providers import provider_statuses
        providers = provider_statuses(os.environ)
        configured_count = sum(1 for p in providers if p.api_key_configured)
        checks.append({
            "check": "providers",
            "ok": True,
            "total": len(providers),
            "configured": configured_count,
            "providers": [p.model_dump() for p in providers],
        })
    except Exception as e:
        checks.append({
            "check": "providers",
            "ok": False,
            "error": str(e),
        })

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
    checks.append({
        "check": "python_version",
        "ok": True,
        "version": sys.version.split()[0],
        "executable": sys.executable,
    })
    checks.append({
        "check": "arc_version",
        "ok": True,
        "version": arc_version,
    })
    key_envs = [
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "OPENROUTER_API_KEY",
        "QWEN_API_KEY", "MOONSHOT_API_KEY", "KIMI_API_KEY",
    ]
    configured = [name for name in key_envs if os.environ.get(name)]
    checks.append({
        "check": "provider_keys",
        "ok": True,
        "configured": configured,
        "count": len(configured),
        "total": len(key_envs),
    })
    arc_envs = {k: v for k, v in os.environ.items() if k.startswith("ARC_")}
    checks.append({
        "check": "arc_env_vars",
        "ok": True,
        "vars": list(arc_envs.keys()),
        "count": len(arc_envs),
    })
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
                checks.append({
                    "check": name,
                    "ok": reachable,
                    "url": url,
                    "status": resp.status,
                })
                if not reachable:
                    all_ok = False
        except Exception as e:
            all_ok = False
            checks.append({
                "check": name,
                "ok": False,
                "url": url,
                "error": str(e),
            })
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
    checks.append({
        "check": "traces_dir",
        "ok": traces_dir.exists(),
        "path": str(traces_dir),
        "trace_count": len(list(traces_dir.glob("*.jsonl"))) if traces_dir.exists() else 0,
    })
    checks.append({
        "check": "sqlite_index",
        "ok": db_path.exists(),
        "path": str(db_path),
        "size_bytes": db_path.stat().st_size if db_path.exists() else 0,
    })
    if db_path.exists():
        from .storage.sqlite import SqliteStore
        store = SqliteStore(db_path)
        checks.append({
            "check": "indexed_runs",
            "ok": True,
            "count": store.count_runs(),
        })
    checks.append({
        "check": "evals_dir",
        "ok": evals_dir.exists(),
        "path": str(evals_dir),
    })
    all_ok = all(c["ok"] for c in checks if c["check"] != "evals_dir")
    data = {"ok": all_ok, "checks": checks, "workspace": str(ws)}
    _out(ok(data), json_output)


@app.command("bug-report")
def bug_report(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Collect diagnostic information for a bug report.

    Gathers environment, runtime, storage, and config info.
    All secrets are redacted.
    """
    import os
    import sys
    _setup_logging(debug)
    from .providers import redacted_diagnostics
    from .config.loader import load_config
    ws = _workspace(workspace)
    config = load_config(workspace=ws)
    traces_dir = ws / ".arc" / "traces"
    db_path = ws / ".arc" / "arc.db"
    trace_count = len(list(traces_dir.glob("*.jsonl"))) if traces_dir.exists() else 0
    indexed_count = 0
    if db_path.exists():
        from .storage.sqlite import SqliteStore
        indexed_count = SqliteStore(db_path).count_runs()
    payload = {
        "arc_version": arc_version,
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "workspace": str(ws),
        "traces": trace_count,
        "indexed_runs": indexed_count,
        "config": {
            "version": config.version,
            "runtime_default": config.runtime.default,
            "isolation": config.execution.isolation,
        },
        "providers": redacted_diagnostics(os.environ),
    }
    _out(ok(payload), json_output)
    if not json_output:
        console.print("[bold]ARC Bug Report[/bold]")
        console.print(f"  Version: {arc_version}")
        console.print(f"  Python: {sys.version.split()[0]}")
        console.print(f"  Platform: {sys.platform}")
        console.print(f"  Workspace: {ws}")
        console.print(f"  Traces: {trace_count}")
        console.print(f"  Indexed: {indexed_count}")
        console.print("")
        console.print("[dim]Include this output when reporting bugs.[/dim]")


@providers_app.command("status")
def providers_status(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return dry-run provider status from environment presence only."""
    import os
    _setup_logging(debug)
    from .providers import provider_statuses
    _out(ok([status.model_dump() for status in provider_statuses(os.environ)]), json_output)


@providers_app.command("diagnostics")
def providers_diagnostics(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return redacted provider diagnostics (statuses, routing, accounts, quota).

    No network calls are made. All secrets are redacted.
    """
    import os
    _setup_logging(debug)
    from .providers import redacted_diagnostics
    _out(ok(redacted_diagnostics(os.environ)), json_output)


@providers_app.command("proxy")
def providers_proxy(
    provider: Optional[str] = typer.Option(None, "--provider", help="Provider id (default: routing default)"),
    model: Optional[str] = typer.Option(None, "--model", help="Model name (default: routing default)"),
    prompt: str = typer.Option("Hello", "--prompt", help="Prompt text for dry-run proxy"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Dry-run provider proxy. No network call is made.

    Validates routing, quota reservation, and gating without
    invoking any LLM API. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true
    and --allow-paid-calls for a live proxy call.
    """
    _setup_logging(debug)
    from .providers import ProviderRequest, ProviderResponse, dry_run_proxy
    from .providers import ProviderRoutingStore
    routing = ProviderRoutingStore().get()
    req = ProviderRequest(
        provider=provider or routing.default_provider,
        model=model or routing.default_model,
        prompt=prompt,
        dry_run=True,
        allow_paid_calls=False,
    )
    try:
        resp = dry_run_proxy(req)
        _out(ok(resp.model_dump()), json_output)
    except RuntimeError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1)


accounts_app = typer.Typer(name="accounts", help="Provider account metadata")
providers_app.add_typer(accounts_app)


@accounts_app.command("list")
def providers_accounts_list(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """List provider accounts without exposing secrets."""
    _setup_logging(debug)
    from .providers import ProviderAccountStore
    accounts = ProviderAccountStore().list_accounts()
    _out(ok([account.model_dump() for account in accounts]), json_output)


@accounts_app.command("add")
def providers_accounts_add(
    provider: str = typer.Option(..., "--provider", help="Provider id"),
    label: str = typer.Option(..., "--label", help="Account label"),
    api_key_env: str = typer.Option(..., "--api-key-env", help="Environment variable containing the key"),
    default_model: Optional[str] = typer.Option(None, "--model", help="Default model"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Add an env-var-backed provider account. The key is never printed."""
    _setup_logging(debug)
    from .providers import ProviderAccountStore
    account = ProviderAccountStore().add_env_account(provider, label, api_key_env, default_model)
    _out(ok(account.model_dump()), json_output)


@accounts_app.command("disable")
def providers_accounts_disable(
    account_id: str = typer.Argument(..., help="Account id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Disable a provider account."""
    _setup_logging(debug)
    from .providers import ProviderAccountStore
    account = ProviderAccountStore().set_enabled(account_id, False)
    if account is None:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Provider account not found: {account_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(account.model_dump()), json_output)


@accounts_app.command("delete")
def providers_accounts_delete(
    account_id: str = typer.Argument(..., help="Account id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete a provider account metadata record."""
    _setup_logging(debug)
    from .providers import ProviderAccountStore
    deleted = ProviderAccountStore().delete(account_id)
    _out(ok({"deleted": deleted, "account_id": account_id}), json_output)


quota_app = typer.Typer(name="quota", help="Provider quota management")
providers_app.add_typer(quota_app)


@quota_app.command("show")
def providers_quota_show(
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show today's provider quota usage."""
    _setup_logging(debug)
    from .providers import ProviderQuotaStore
    store = ProviderQuotaStore()
    usage = store.usage()
    if provider:
        filtered = {k: v for k, v in usage.get("counters", {}).items() if f":{provider}" in k}
        payload = {"date": usage["date"], "provider": provider, "counters": filtered}
    else:
        payload = usage
    _out(ok(payload), json_output)


@quota_app.command("reset")
def providers_quota_reset(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Reset today's provider quota counters."""
    _setup_logging(debug)
    from .providers import ProviderQuotaStore
    store = ProviderQuotaStore()
    store.reset()
    _out(ok({"reset": True}), json_output)


routing_app = typer.Typer(name="routing", help="Provider routing policy")
providers_app.add_typer(routing_app)


@routing_app.command("get")
def providers_routing_get(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return persisted dry-run routing policy."""
    _setup_logging(debug)
    from .providers import ProviderRoutingStore
    _out(ok(ProviderRoutingStore().get().model_dump()), json_output)


@routing_app.command("set")
def providers_routing_set(
    mode: str = typer.Option("manual", "--mode", help="manual | priority | fallback"),
    provider: str = typer.Option("openai", "--provider", help="Default provider"),
    model: str = typer.Option("gpt-4.1-mini", "--model", help="Default model"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Persist provider routing policy. Live calls remain gated."""
    _setup_logging(debug)
    from .providers import ProviderRoutingPolicy, ProviderRoutingStore
    policy = ProviderRoutingPolicy(mode=mode, default_provider=provider, default_model=model)
    _out(ok(ProviderRoutingStore().set(policy).model_dump()), json_output)


@runs_app.callback(invoke_without_command=True)
def runs(
    ctx: typer.Context,
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List stored run records."""
    if ctx.invoked_subcommand is not None:
        return
    _setup_logging(debug)
    from .storage.jsonl import JsonlTraceStore
    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run_ids = store.list_runs()
    run_list = [r for rid in run_ids if (r := store.load(rid)) is not None]
    _out(ok([r.model_dump() for r in run_list]), json_output)


@runs_app.command("prune")
def runs_prune(
    workspace: Optional[str] = WORKSPACE_FLAG,
    keep: int = typer.Option(20, "--keep", min=0, help="Number of newest traces to keep"),
    yes: bool = typer.Option(False, "--yes", help="Delete files instead of dry-run"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Prune oldest workspace trace files beyond --keep."""
    _setup_logging(debug)
    from .storage.jsonl import JsonlTraceStore
    ws = _workspace(workspace)
    trace_dir = ws / ".arc" / "traces"
    store = JsonlTraceStore(trace_dir)
    victims = store.prune(keep=keep, dry_run=not yes)
    payload = {
        "workspace": str(ws),
        "trace_dir": str(trace_dir),
        "keep": keep,
        "dry_run": not yes,
        "deleted": [] if not yes else [str(path) for path in victims],
        "would_delete": [str(path) for path in victims] if not yes else [],
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("get")
def runs_get(
    run_id: str = typer.Argument(..., help="Run ID to load"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Load one stored run record."""
    _setup_logging(debug)
    from .storage.jsonl import JsonlTraceStore
    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(run_record.model_dump(), workspace=str(ws)), json_output)


@runs_app.command("diff")
def runs_diff(
    run_a: str = typer.Argument(..., help="First run ID"),
    run_b: str = typer.Argument(..., help="Second run ID"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Compare two stored run records."""
    _setup_logging(debug)
    from .storage.jsonl import JsonlTraceStore
    from .evals.diff import diff_runs
    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    rec_a = store.load(run_a)
    rec_b = store.load(run_b)
    if rec_a is None or rec_b is None:
        missing = [r for r, rec in [(run_a, rec_a), (run_b, rec_b)] if rec is None]
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run(s) not found: {', '.join(missing)}"), json_output)
        raise typer.Exit(1)
    result = diff_runs(rec_a, rec_b)
    _out(ok(result.model_dump(), workspace=str(ws)), json_output)


@runs_app.command("trace")
def runs_trace(
    run_id: str = typer.Argument(..., help="Run ID to inspect"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    tail: int = typer.Option(20, "--tail", min=0, help="Number of trace lines to return"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Return trace file metadata and optional tail lines for one run."""
    _setup_logging(debug)
    from .storage.jsonl import JsonlTraceStore
    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    path = store.trace_path(run_id)
    if not path.exists():
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Trace not found: {run_id}"), json_output)
        raise typer.Exit(1)
    lines = path.read_text().splitlines()
    payload = {
        "run_id": run_id,
        "trace_path": str(path),
        "line_count": len(lines),
        "tail": lines[-tail:] if tail else [],
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("status")
def runs_status(
    run_id: str = typer.Argument(..., help="Run ID to check"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show status of a stored run record."""
    _setup_logging(debug)
    from .storage.indexed_store import IndexedTraceStore
    ws = _workspace(workspace)
    store = IndexedTraceStore(
        trace_dir=ws / ".arc" / "traces",
        db_path=ws / ".arc" / "arc.db",
    )
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    payload = {
        "run_id": run_record.id,
        "status": run_record.status.value,
        "workflow_id": run_record.workflow_id,
        "runtime": run_record.runtime,
        "started_at": run_record.started_at,
        "ended_at": run_record.ended_at,
        "event_count": len(run_record.events),
        "audit_path": run_record.audit_path,
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("delete")
def runs_delete(
    run_id: str = typer.Argument(..., help="Run ID to delete"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete a stored run record and its trace file."""
    _setup_logging(debug)
    from .storage.indexed_store import IndexedTraceStore
    ws = _workspace(workspace)
    store = IndexedTraceStore(
        trace_dir=ws / ".arc" / "traces",
        db_path=ws / ".arc" / "arc.db",
    )
    trace_path = store.trace_path(run_id)
    if not trace_path.exists():
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    trace_path.unlink()
    store.sqlite.delete_run(run_id)
    payload = {
        "deleted_run_id": run_id,
        "trace_path": str(trace_path),
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("export")
def runs_export(
    run_id: str = typer.Argument(..., help="Run ID to export"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export a run record as JSON."""
    _setup_logging(debug)
    from .storage.indexed_store import IndexedTraceStore
    ws = _workspace(workspace)
    store = IndexedTraceStore(
        trace_dir=ws / ".arc" / "traces",
        db_path=ws / ".arc" / "arc.db",
    )
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(run_record.model_dump(), workspace=str(ws)), json_output)


@runs_app.command("import")
def runs_import(
    path: str = typer.Argument(..., help="Path to exported run JSON"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Import a run record JSON into the workspace trace store."""
    _setup_logging(debug)
    import json
    from .protocol.schemas import RunRecord
    from .storage.indexed_store import IndexedTraceStore

    ws = _workspace(workspace)
    source = Path(path).expanduser().resolve()
    if not source.exists():
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Import file not found: {source}"), json_output)
        raise typer.Exit(1)
    try:
        run_record = RunRecord.model_validate(json.loads(source.read_text()))
    except Exception as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid run export: {exc}"), json_output)
        raise typer.Exit(1)
    store = IndexedTraceStore(trace_dir=ws / ".arc" / "traces", db_path=ws / ".arc" / "arc.db")
    store.init()
    store.save(run_record)
    _out(ok({"imported_run_id": run_record.id}, workspace=str(ws)), json_output)


@runs_app.command("replay")
def runs_replay(
    run_id: str = typer.Argument(..., help="Run ID to replay from stored trace"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Replay stored trace events without re-executing the runtime."""
    _setup_logging(debug)
    from .storage.jsonl import JsonlTraceStore

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run_record = store.load(run_id)
    if run_record is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)
    payload = {
        "run_id": run_record.id,
        "event_count": len(run_record.events),
        "events": [event.model_dump() for event in run_record.events],
    }
    _out(ok(payload, workspace=str(ws)), json_output)


@runs_app.command("backfill")
def runs_backfill(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Backfill SQLite index from existing JSONL traces. Idempotent."""
    _setup_logging(debug)
    from .storage.indexed_store import IndexedTraceStore
    ws = _workspace(workspace)
    store = IndexedTraceStore(
        trace_dir=ws / ".arc" / "traces",
        db_path=ws / ".arc" / "arc.db",
    )
    store.init()
    indexed, skipped, failed = store.backfill_index()
    payload = {
        "indexed": indexed,
        "skipped": skipped,
        "failed": failed,
    }
    _out(ok(payload, workspace=str(ws)), json_output)
    if not json_output and failed > 0:
        err_console.print(f"[yellow]Warning: {failed} trace(s) failed to index[/yellow]")


@runs_app.command("search")
def runs_search(
    workflow: Optional[str] = typer.Option(None, "--workflow", "-f", help="Filter by workflow ID"),
    runtime: Optional[str] = typer.Option(None, "--runtime", "-r", help="Filter by runtime"),
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum results"),
    offset: int = typer.Option(0, "--offset", "-o", help="Result offset"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Search runs using the SQLite index."""
    _setup_logging(debug)
    from .storage.sqlite import SqliteStore
    ws = _workspace(workspace)
    db_path = ws / ".arc" / "arc.db"
    if not db_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, "SQLite index not found. Run 'arc runs backfill' first."), json_output)
        raise typer.Exit(1)
    store = SqliteStore(db_path)
    results = store.list_runs(
        status=status,
        runtime=runtime,
        workflow_id=workflow,
        limit=limit,
        offset=offset,
    )
    total = store.count_runs()
    payload = {
        "results": results,
        "count": len(results),
        "total_indexed": total,
        "filters": {
            "workflow": workflow,
            "runtime": runtime,
            "status": status,
        },
    }
    _out(ok(payload, workspace=str(ws)), json_output)
    if not json_output:
        if not results:
            console.print("[dim]No matching runs found.[/dim]")
            return
        table = Table(title=f"Runs ({len(results)} of {total} indexed)")
        table.add_column("Run ID")
        table.add_column("Workflow")
        table.add_column("Runtime")
        table.add_column("Status")
        table.add_column("Started")
        for run in results:
            table.add_row(
                run["id"][:12],
                run.get("workflow_id", "")[:20],
                run.get("runtime", ""),
                run.get("status", ""),
                run.get("started_at", "")[:19],
            )
        console.print(table)


# ─── isolation ──────────────────────────────────────────────────────────────────

@isolation_app.command("status")
def isolation_status(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show available isolation providers and their health status."""
    _setup_logging(debug)
    from .isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from .isolation.docker_provider import DockerIsolationProvider

    providers = [
        NoneIsolationProvider(),
        SubprocessIsolationProvider(),
        DockerIsolationProvider(),
    ]
    results = []
    for p in providers:
        import asyncio
        healthy = asyncio.run(p.health_check())
        results.append({
            "provider_id": p.provider_id,
            "healthy": healthy,
        })
    _out(ok({"providers": results}), json_output)


@isolation_app.command("doctor")
def isolation_doctor(
    provider: str = typer.Argument("all", help="Provider ID or 'all'"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run diagnostics on an isolation provider."""
    _setup_logging(debug)
    from .isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from .isolation.docker_provider import DockerIsolationProvider

    provider_map = {
        "none": NoneIsolationProvider(),
        "subprocess": SubprocessIsolationProvider(),
        "docker": DockerIsolationProvider(),
    }
    if provider != "all":
        if provider not in provider_map:
            _out(err(ArcErrorCode.INVALID_INPUT, f"Unknown provider: {provider}. Available: {', '.join(provider_map)}"), json_output)
            raise typer.Exit(1)
        provider_map = {provider: provider_map[provider]}

    import asyncio
    results = []
    for pid, p in provider_map.items():
        healthy = asyncio.run(p.health_check())
        results.append({
            "provider_id": pid,
            "healthy": healthy,
            "description": p.describe(),
        })
    _out(ok({"diagnostics": results}), json_output)


@isolation_app.command("list")
def isolation_list(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List available isolation providers."""
    _setup_logging(debug)
    from .isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from .isolation.docker_provider import DockerIsolationProvider

    providers = [
        NoneIsolationProvider().describe(),
        SubprocessIsolationProvider().describe(),
        DockerIsolationProvider().describe(),
    ]
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
    from .isolation.docker_provider import DockerIsolationProvider

    if provider != "docker":
        _out(err(ArcErrorCode.INVALID_INPUT, f"Setup not available for: {provider}"), json_output)
        raise typer.Exit(1)

    docker = DockerIsolationProvider()
    runtime = docker.detect_runtime()
    import asyncio
    healthy = asyncio.run(docker.health_check())

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
            console.print("[dim]Install Docker Desktop, OrbStack, or Podman to enable container isolation.[/dim]")


@isolation_app.command("test")
def isolation_test(
    provider: str = typer.Argument("subprocess", help="Provider to test"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Test an isolation provider with a simple command."""
    _setup_logging(debug)
    from .isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from .isolation.docker_provider import DockerIsolationProvider

    provider_map = {
        "none": NoneIsolationProvider(),
        "subprocess": SubprocessIsolationProvider(),
        "docker": DockerIsolationProvider(),
    }
    if provider not in provider_map:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Unknown provider: {provider}. Available: {', '.join(provider_map)}"), json_output)
        raise typer.Exit(1)

    p = provider_map[provider]
    import asyncio
    result = asyncio.run(p.execute(["echo", "ARC isolation test OK"]))
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


# ─── context pack ─────────────────────────────────────────────────────────────

@context_app.command("pack")
def context_pack(
    task: str = typer.Option(..., "--task", "-t", help="Task description for context retrieval"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate a context pack for a task."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    gen = ContextPackGenerator()
    entries = gen.generate(task, ws, save=True)
    _out(ok([e.model_dump() for e in entries]), json_output)
    if not json_output:
        console.print(f"[green]Context pack:[/green] {len(entries)} entries for task: {task!r}")


# ─── adapter test ─────────────────────────────────────────────────────────────

@adapter_app.command("test")
def adapter_test(
    adapter_id: str = typer.Argument(..., help="Adapter ID: swarmgraph | langgraph"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run conformance tests against an adapter."""
    _setup_logging(debug)
    ws = _workspace(workspace)
    registry = default_registry()
    adapter = registry.get(adapter_id)

    if not adapter:
        _out(err(ArcErrorCode.ADAPTER_NOT_SUPPORTED, f"Adapter not found: {adapter_id!r}"), json_output)
        raise typer.Exit(1)

    from .adapters.conformance import run_conformance
    result = run_conformance(adapter, ws)

    summary = {
        "adapter": adapter_id,
        "passed": result.passed,
        "failed": result.failed,
        "skipped": result.skipped,
        "ok": result.ok,
        "errors": result.errors,
        "details": result.details,
    }
    _out(ok(summary), json_output)

    if not json_output:
        table = Table(title=f"Conformance: {adapter_id}")
        table.add_column("Test")
        table.add_column("Result")
        table.add_column("Reason")
        for d in result.details:
            color = {"PASS": "green", "FAIL": "red", "SKIP": "yellow"}.get(d["result"], "white")
            table.add_row(d["test"], f"[{color}]{d['result']}[/{color}]", d.get("reason", ""))
        console.print(table)
        status = "[green]ALL PASS[/green]" if result.ok else f"[red]{result.failed} FAILED[/red]"
        console.print(f"Summary: {result.passed} passed · {result.failed} failed · {result.skipped} skipped → {status}")

    if not result.ok:
        raise typer.Exit(1)


@adapter_app.command("list")
def adapter_list(debug: bool = DEBUG_FLAG) -> None:
    """List all registered adapters."""
    _setup_logging(debug)
    registry = default_registry()
    table = Table(title="Registered Adapters")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("Capabilities")
    for a in registry.all():
        caps = a.capabilities()
        cap_str = " ".join(k.replace("can_", "") for k, v in caps.model_dump().items() if v)
        table.add_row(a.adapter_id, a.adapter_name, cap_str)
    console.print(table)


# ─── eval ─────────────────────────────────────────────────────────────────────

@eval_app.command("run")
def eval_run(
    run_id: str = typer.Argument(..., help="Run ID to evaluate"),
    golden_id: str = typer.Option("", "--golden", "-g", help="Golden trace ID"),
    expected_output: str = typer.Option("", "--expected-final-output", help="Expected substring in final output"),
    expected_event_types: str = typer.Option("", "--expected-event-types", help="Comma-separated expected event types"),
    expected_status: str = typer.Option("completed", "--expected-status", help="Expected run status"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Evaluate a run against a golden trace.

    Provide --golden to load a saved golden trace, or specify
    --expected-final-output/--expected-status/--expected-event-types inline.

    Example:
        uv run arc eval run <run_id> --expected-final-output "hello" --expected-status completed
        uv run arc eval run <run_id> --golden my-golden-id
    """
    _setup_logging(debug)
    from .storage.jsonl import JsonlTraceStore
    from .evals.golden import GoldenTrace, eval_run as do_eval, load_golden

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run = store.load(run_id)
    if run is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)

    events = [t.strip() for t in expected_event_types.split(",") if t.strip()] if expected_event_types else []

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
        console.print(f"Eval [bold {color}]{'PASS' if result.passed else 'FAIL'}[/bold {color}]  score={result.score}")
        console.print(f"  status_match={result.status_match}  event_type_match={result.event_type_match}  output_contains_match={result.output_contains_match}")


@eval_app.command("save")
def eval_save(
    golden_id: str = typer.Argument(..., help="Golden trace ID to save"),
    workflow_id: str = typer.Option("", "--workflow-id", help="Expected workflow id"),
    expected_output: str = typer.Option("", "--expected-final-output", help="Expected substring in final output"),
    expected_event_types: str = typer.Option("", "--expected-event-types", help="Comma-separated expected event types"),
    expected_status: str = typer.Option("completed", "--expected-status", help="Expected run status"),
    description: str = typer.Option("", "--description", help="Golden description"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Save a golden trace expectation."""
    _setup_logging(debug)
    from .evals.golden import GoldenTrace, save_golden

    ws = _workspace(workspace)
    events = [t.strip() for t in expected_event_types.split(",") if t.strip()] if expected_event_types else []
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
    from .evals.golden import delete_golden

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
    from .evals.golden import list_goldens

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
    from .evals.golden import list_goldens
    ws = _workspace(workspace)
    goldens = list_goldens(ws)
    _out(ok([g.model_dump() for g in goldens]), json_output)
    if not json_output:
        table = Table(title="Golden Traces")
        table.add_column("ID")
        table.add_column("Workflow")
        table.add_column("Expected Output (truncated)")
        for g in goldens:
            table.add_row(g.id, g.workflow_id, g.expected_final_output_contains[:60] if g.expected_final_output_contains else "")
        console.print(table)


# ─── workspace trust ───────────────────────────────────────────────────────────


@hitl_app.command("pending")
def hitl_pending(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List pending workspace-local HITL prompts."""
    _setup_logging(debug)
    from .audit.hitl_store import list_prompts

    ws = _workspace(workspace)
    prompts = list_prompts(ws)
    _out(ok([prompt.model_dump() for prompt in prompts], workspace=str(ws)), json_output)


@hitl_app.command("respond")
def hitl_respond(
    hitl_id: str = typer.Argument(..., help="Pending HITL prompt ID"),
    decision: str = typer.Option(..., "--decision", help="approve | reject | modify | skip"),
    notes: str = typer.Option("", "--notes", help="Operator notes"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Respond to a pending workspace-local HITL prompt."""
    _setup_logging(debug)
    from .audit.hitl import HitlDecision
    from .audit.hitl_store import respond

    ws = _workspace(workspace)
    try:
        parsed = HitlDecision(decision)
    except ValueError:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid HITL decision: {decision}"), json_output)
        raise typer.Exit(1)
    response = respond(ws, hitl_id, parsed, notes=notes)
    if response is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"HITL prompt not found: {hitl_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(response.model_dump(), workspace=str(ws)), json_output)


@hitl_app.command("approve")
def hitl_approve(
    hitl_id: str = typer.Argument(..., help="Pending HITL prompt ID"),
    notes: str = typer.Option("", "--notes", help="Operator notes"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Approve a pending workspace-local HITL prompt."""
    hitl_respond(hitl_id, "approve", notes, workspace, json_output, debug)


@hitl_app.command("reject")
def hitl_reject(
    hitl_id: str = typer.Argument(..., help="Pending HITL prompt ID"),
    notes: str = typer.Option("", "--notes", help="Operator notes"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Reject a pending workspace-local HITL prompt."""
    hitl_respond(hitl_id, "reject", notes, workspace, json_output, debug)

@workspace_app.command("trust-status")
def workspace_trust_status(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show workspace trust status used for execution enforcement."""
    _setup_logging(debug)
    from .security.trust import resolve_trust
    ws = _workspace(workspace)
    resolution = resolve_trust(ws)
    _out(ok(resolution.model_dump(), workspace=str(ws)), json_output)


@workspace_app.command("trust")
def workspace_trust(
    note: str = typer.Option("", "--note", help="Optional note for trust entry"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Mark the workspace as trusted (external DB, outside repo)."""
    _setup_logging(debug)
    from .security.trust import trust_workspace
    ws = _workspace(workspace)
    resolution = trust_workspace(ws, note=note)
    _out(ok(resolution.model_dump(), workspace=str(ws)), json_output)


@workspace_app.command("untrust")
def workspace_untrust(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Remove workspace from the external trust database."""
    _setup_logging(debug)
    from .security.trust import untrust_workspace
    ws = _workspace(workspace)
    resolution = untrust_workspace(ws)
    _out(ok(resolution.model_dump(), workspace=str(ws)), json_output)


# ─── config (ADR-001) ──────────────────────────────────────────────────────────

@config_app.command("init")
def config_init(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate default .arc/config.yaml in the workspace."""
    _setup_logging(debug)
    from .config import init_config
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
    from .config import load_config
    ws = _workspace(workspace)
    config = load_config(ws)
    _out(ok(config.flatten(), workspace=str(ws)), json_output)


# ─── audit (ADR-005) ─────────────────────────────────────────────────────────


audit_app = typer.Typer(name="audit", help="Audit chain verification and key management (ADR-005)")
app.add_typer(audit_app)


@audit_app.command("verify")
def audit_verify(
    run_id: str = typer.Argument(..., help="Run ID to verify audit chain for"),
    chain_path: str = typer.Option(
        "", "--chain", "-c", help="Path to audit chain file (default: .arc/audit/{run_id}.jsonl)"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Verify HMAC-SHA256 audit chain integrity for a run.

    Authenticates every record in the chain and checks chain continuity.
    Requires ARC_AUDIT_HMAC_KEY env var or keychain-stored key.
    """
    _setup_logging(debug)
    from pathlib import Path
    from .audit.key_manager import AuditKeyManager
    from .audit.hmac_chain import verify_hmac_chain

    mgr = AuditKeyManager()
    key, status = mgr.get_key()
    if not status.available:
        _out(err(ArcErrorCode.INVALID_INPUT, status.warning), json_output)
        raise typer.Exit(1)

    ws = Path.cwd()
    chain = Path(chain_path) if chain_path else ws / ".arc" / "audit" / f"{run_id}.jsonl"

    ok, reason = verify_hmac_chain(chain, key)
    payload = {
        "run_id": run_id,
        "chain_path": str(chain),
        "verified": ok,
        "reason": reason,
        "key_source": status.source,
        "key_degraded": status.degraded,
    }
    _out(ok(payload), json_output)
    if not json_output:
        color = "green" if ok else "red"
        console.print(f"Audit chain: [bold {color}]{'VERIFIED' if ok else 'FAILED'}[/bold {color}]")
        console.print(f"  Path: {chain}")
        console.print(f"  Reason: {reason}")
        if status.degraded:
            console.print(f"[yellow]Warning:[/yellow] {status.warning}")
    if not ok:
        raise typer.Exit(1)


@audit_app.command("export")
def audit_export(
    run_id: str = typer.Argument(..., help="Run ID to export audit records for"),
    chain_path: str = typer.Option(
        "", "--chain", "-c", help="Path to audit chain file (default: .arc/audit/{run_id}.jsonl)"
    ),
    format: str = typer.Option("jsonl", "--format", help="Output format: jsonl, json"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Export audit chain records for a run."""
    _setup_logging(debug)
    import json as json_mod
    from pathlib import Path

    ws = Path.cwd()
    chain = Path(chain_path) if chain_path else ws / ".arc" / "audit" / f"{run_id}.jsonl"
    if not chain.exists():
        _out(
            err(ArcErrorCode.RUN_NOT_FOUND, f"Audit chain not found: {chain}"),
            json_output,
        )
        raise typer.Exit(1)

    lines = chain.read_text(encoding="utf-8").splitlines()
    records = [json_mod.loads(l) for l in lines if l.strip()]

    if format == "json":
        payload = {"run_id": run_id, "record_count": len(records), "records": records}
    else:
        payload = {"run_id": run_id, "record_count": len(records), "chain_path": str(chain)}

    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"Audit records for {run_id}: {len(records)} records at {chain}")
        if format == "jsonl":
            for r in records:
                console.print(json_mod.dumps(r, sort_keys=True))


key_app = typer.Typer(name="key", help="HMAC audit key management")
audit_app.add_typer(key_app)


@key_app.command("init")
def audit_key_init(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Generate and store a new HMAC audit key in keychain."""
    _setup_logging(debug)
    from .audit.key_manager import AuditKeyManager

    mgr = AuditKeyManager()
    new_key = mgr.generate_key()
    stored = mgr.set_key(new_key)
    payload = {
        "generated": True,
        "stored_to_keychain": stored,
        "key_hint": new_key[:8] + "..." if stored else new_key,
    }
    _out(ok(payload), json_output)
    if not json_output:
        if stored:
            console.print("[green]Audit key generated and stored in keychain.[/green]")
        else:
            console.print("[yellow]Key generated but could not store in keychain. Set via env:[/yellow]")
            console.print(f"  export ARC_AUDIT_HMAC_KEY={new_key}")


@key_app.command("show")
def audit_key_show(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show audit key status (key is never printed)."""
    _setup_logging(debug)
    from .audit.key_manager import AuditKeyManager

    mgr = AuditKeyManager()
    key, status = mgr.get_key()
    payload = status.model_dump()
    _out(ok(payload), json_output)
    if not json_output:
        if status.available:
            console.print(f"Audit key: [green]available[/green] (source: {status.source})")
        else:
            console.print(f"Audit key: [red]not available[/red]")
            console.print(f"  {status.warning}")


@key_app.command("delete")
def audit_key_delete(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete the stored HMAC audit key from keychain."""
    _setup_logging(debug)
    from .audit.key_manager import AuditKeyManager

    mgr = AuditKeyManager()
    deleted = mgr.delete_key()
    payload = {"deleted_from_keychain": deleted}
    _out(ok(payload), json_output)
    if not json_output:
        if deleted:
            console.print("[green]Audit key deleted from keychain.[/green]")
        else:
            console.print("[yellow]No key found in keychain or keychain unavailable.[/yellow]")


# ─── run profiles ─────────────────────────────────────────────────────────────


profiles_app = typer.Typer(name="profiles", help="Run profile management")
app.add_typer(profiles_app)


@profiles_app.command("list")
def profiles_list(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List available run profiles."""
    _setup_logging(debug)
    from .security.profiles import BUILTIN_PROFILES
    profiles = [
        {
            "id": p.id,
            "name": p.name,
            "allow_paid_calls": p.allow_paid_calls,
            "allow_network": p.allow_network,
            "allow_shell": p.allow_shell,
            "allow_secrets": p.allow_secrets,
            "backend": p.backend.value,
        }
        for p in BUILTIN_PROFILES.values()
    ]
    _out(ok(profiles), json_output)
    if not json_output:
        table = Table(title="Run Profiles")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Backend")
        table.add_column("Paid")
        table.add_column("Network")
        for p in profiles:
            table.add_row(
                p["id"],
                p["name"],
                p["backend"],
                "yes" if p["allow_paid_calls"] else "no",
                "yes" if p["allow_network"] else "no",
            )
        console.print(table)


@profiles_app.command("show")
def profiles_show(
    profile_id: str = typer.Argument(..., help="Profile id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show details for a specific run profile."""
    _setup_logging(debug)
    from .security.profiles import resolve_profile
    profile = resolve_profile(profile_id)
    payload = {
        "id": profile.id,
        "name": profile.name,
        "allow_paid_calls": profile.allow_paid_calls,
        "allow_network": profile.allow_network,
        "allow_shell": profile.allow_shell,
        "allow_secrets": profile.allow_secrets,
        "env_allowlist": list(profile.env_allowlist),
        "backend": profile.backend.value,
    }
    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"[bold]{profile.name}[/bold] ({profile.id})")
        console.print(f"  Backend: {profile.backend.value}")
        console.print(f"  Paid calls: {'yes' if profile.allow_paid_calls else 'no'}")
        console.print(f"  Network: {'yes' if profile.allow_network else 'no'}")
        console.print(f"  Shell: {'yes' if profile.allow_shell else 'no'}")
        console.print(f"  Secrets: {'yes' if profile.allow_secrets else 'no'}")
        if profile.env_allowlist:
            console.print(f"  Env allowlist: {', '.join(profile.env_allowlist)}")


# ─── workspace init/info/config ───────────────────────────────────────────────


@workspace_app.command("init")
def workspace_init(
    workspace: Optional[str] = WORKSPACE_FLAG,
    name: Optional[str] = typer.Option(None, "--name", help="Workspace name"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Initialize ARC configuration in a workspace."""
    _setup_logging(debug)
    from .config.loader import init_config, load_config
    ws = _workspace(workspace)
    config_path = ws / ".arc" / "config.yaml"
    if config_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Config already exists at {config_path}"), json_output)
        raise typer.Exit(1)
    init_config(ws)
    if name:
        import yaml
        data = yaml.safe_load(config_path.read_text()) or {}
        data.setdefault("workspace", {})["name"] = name
        config_path.write_text(yaml.dump(data, default_flow_style=False))
    payload = {"created": str(config_path), "workspace": str(ws)}
    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"[green]Created[/green] {config_path}")


@workspace_app.command("info")
def workspace_info(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show workspace information including config and trust status."""
    _setup_logging(debug)
    from .config.loader import load_config
    from .security.trust import resolve_trust
    ws = _workspace(workspace)
    config = load_config(workspace=ws)
    trust_status = resolve_trust(ws)
    config_path = ws / ".arc" / "config.yaml"
    payload = {
        "workspace": str(ws),
        "name": config.workspace.name,
        "config_exists": config_path.exists(),
        "trust_level": trust_status.level.value,
        "trust_reason": trust_status.reason,
    }
    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"[bold]Workspace:[/bold] {ws}")
        if config.workspace.name:
            console.print(f"[bold]Name:[/bold] {config.workspace.name}")
        console.print(f"[bold]Config:[/bold] {'exists' if config_path.exists() else 'not found'}")
        console.print(f"[bold]Trust:[/bold] {trust_status.level.value}")
        console.print(f"[dim]{trust_status.reason}[/dim]")


@workspace_app.command("config")
def workspace_config_cmd(
    workspace: Optional[str] = WORKSPACE_FLAG,
    key: Optional[str] = typer.Option(None, "--key", "-k", help="Config key to set (e.g. runtime.default)"),
    value: Optional[str] = typer.Option(None, "--value", "-v", help="Config value"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show or update workspace configuration."""
    _setup_logging(debug)
    from .config.loader import load_config
    ws = _workspace(workspace)
    config_path = ws / ".arc" / "config.yaml"
    if key and value:
        if not config_path.exists():
            _out(err(ArcErrorCode.INVALID_INPUT, "Config file not found. Run 'arc workspace init' first."), json_output)
            raise typer.Exit(1)
        import yaml
        data = yaml.safe_load(config_path.read_text()) or {}
        parts = key.split(".")
        target = data
        for part in parts[:-1]:
            target = target.setdefault(part, {})
        target[parts[-1]] = value
        config_path.write_text(yaml.dump(data, default_flow_style=False))
        payload = {"updated": key, "value": value, "config_path": str(config_path)}
        _out(ok(payload), json_output)
        if not json_output:
            console.print(f"[green]Updated[/green] {key} = {value}")
    else:
        config = load_config(workspace=ws)
        _out(ok(config.flatten()), json_output)


# ─── prompt optimizer ─────────────────────────────────────────────────────────


prompt_app = typer.Typer(name="prompt", help="Prompt optimization commands (P1b local)")
app.add_typer(prompt_app)


@prompt_app.command("optimize")
def prompt_optimize(
    prompt: str = typer.Argument(..., help="Prompt text to optimize"),
    model: str = typer.Option("gpt-4o", "--model", "-m", help="Model for token counting"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Apply rule-based optimization to a prompt.

    No provider calls are made. Uses tiktoken for counting (falls back to
    word estimate if tiktoken is not installed).
    """
    _setup_logging(debug)
    from .optimizer import optimize_prompt, estimate_cost

    result = optimize_prompt(prompt, model=model)
    payload = {
        "original_length": len(prompt),
        "optimized_length": len(result.optimized),
        "original_tokens": result.original_tokens.count,
        "optimized_tokens": result.optimized_tokens.count,
        "tokens_saved": result.tokens_saved,
        "changes": result.changes,
        "encoding": result.original_tokens.encoding,
    }

    # Add cost estimate if pricing is known
    cost = estimate_cost(result.original_tokens.count, model)
    if cost is not None:
        payload["estimated_cost_usd"] = round(cost, 6)
        cost_after = estimate_cost(result.optimized_tokens.count, model)
        if cost_after is not None:
            payload["estimated_cost_after_usd"] = round(cost_after, 6)
            payload["estimated_savings_usd"] = round(cost - cost_after, 6)

    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"[dim]Original:[/dim] {result.original_tokens.count} tokens ({result.original_tokens.encoding})")
        console.print(f"[green]Optimized:[/green] {result.optimized_tokens.count} tokens")
        console.print(f"[bold]Saved:[/bold] {result.tokens_saved} tokens")
        if result.changes:
            console.print(f"[dim]Rules applied:[/dim] {', '.join(result.changes)}")
        else:
            console.print("[dim]No changes needed[/dim]")
        if cost is not None:
            console.print(f"[dim]Est. cost before:[/dim] ${payload['estimated_cost_usd']:.6f}")
            console.print(f"[green]Est. cost after:[/green] ${payload['estimated_cost_after_usd']:.6f}")


@prompt_app.command("diff")
def prompt_diff(
    prompt_a: str = typer.Argument(..., help="First prompt text"),
    prompt_b: str = typer.Argument(..., help="Second prompt text"),
    context_lines: int = typer.Option(3, "--context", "-c", help="Context lines for diff"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Compare two prompts using unified diff."""
    _setup_logging(debug)
    from .optimizer import diff_prompts, count_tokens

    diff_text = diff_prompts(prompt_a, prompt_b, context_lines=context_lines)
    tokens_a = count_tokens(prompt_a)
    tokens_b = count_tokens(prompt_b)

    payload = {
        "prompt_a_tokens": tokens_a.count,
        "prompt_b_tokens": tokens_b.count,
        "token_diff": tokens_b.count - tokens_a.count,
        "diff": diff_text,
    }
    _out(ok(payload), json_output)
    if not json_output:
        console.print(f"Prompt A: {tokens_a.count} tokens")
        console.print(f"Prompt B: {tokens_b.count} tokens")
        console.print(f"Token diff: {payload['token_diff']:+d}")
        console.print("")
        if diff_text:
            console.print(diff_text)
        else:
            console.print("[dim]No differences[/dim]")


if __name__ == "__main__":
    app()
