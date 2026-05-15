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
app.add_typer(context_app)
app.add_typer(adapter_app)
app.add_typer(doctor_app)
app.add_typer(workspace_app)
app.add_typer(isolation_app)

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


# ─── isolation ──────────────────────────────────────────────────────────────────

@isolation_app.command("status")
def isolation_status(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show available isolation providers and their health status."""
    _setup_logging(debug)
    from .isolation import NoneIsolationProvider, SubprocessIsolationProvider

    providers = [
        NoneIsolationProvider(),
        SubprocessIsolationProvider(),
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

    provider_map = {
        "none": NoneIsolationProvider(),
        "subprocess": SubprocessIsolationProvider(),
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

    providers = [
        NoneIsolationProvider().describe(),
        SubprocessIsolationProvider().describe(),
    ]
    _out(ok({"providers": providers}), json_output)


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
    from .evals.golden import GoldenTrace, eval_run as do_eval

    ws = _workspace(workspace)
    store = JsonlTraceStore(ws / ".arc" / "traces")
    run = store.load(run_id)
    if run is None:
        _out(err(ArcErrorCode.RUN_NOT_FOUND, f"Run not found: {run_id}"), json_output)
        raise typer.Exit(1)

    events = [t.strip() for t in expected_event_types.split(",") if t.strip()] if expected_event_types else []

    golden = GoldenTrace(
        id=golden_id or f"cli-{run_id}",
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
            table.add_row(g.id, g.workflow_id, g.expected_output[:60] if g.expected_output else "")
        console.print(table)


# ─── workspace trust ───────────────────────────────────────────────────────────

@workspace_app.command("trust-status")
def workspace_trust_status(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show workspace trust status (P1a advisory)."""
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


if __name__ == "__main__":
    app()
