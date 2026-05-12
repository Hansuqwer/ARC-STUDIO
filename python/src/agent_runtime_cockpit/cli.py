"""
ARC CLI — Agent Runtime Cockpit command-line interface.

Commands:
  arc inspect    — inspect workspace, detect runtimes
  arc runtimes   — list detected runtimes
  arc workflows  — list detected workflows
  arc schemas    — list detected schemas
  arc serve      — start HTTP daemon
  arc run        — execute a workflow
  arc runs       — list stored runs
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

from .adapters.registry import default_registry
from .context.pack import ContextPackGenerator
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
app.add_typer(context_app)
app.add_typer(adapter_app)
app.add_typer(doctor_app)

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
    runtime: str = typer.Option("auto", "--runtime", "-r", help="Runtime: auto, swarmgraph, langgraph, crewai"),
    prompt: Optional[str] = typer.Option(None, "--prompt", help="Prompt passed to runnable adapters"),
    allow_paid_calls: bool = typer.Option(False, "--allow-paid-calls", help="Allow runtimes to make provider calls"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Execute a workflow and return the run record."""
    import asyncio
    _setup_logging(debug)
    ws = _workspace(workspace)
    try:
        routed = runtime_router.resolve(ws, runtime.lower(), allow_paid_calls=allow_paid_calls)
    except runtime_router.UnknownRuntime as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": exc.code}), json_output)
        raise typer.Exit(2)
    except runtime_router.ComboNotImplemented as exc:
        _out(err(ArcErrorCode.NOT_IMPLEMENTED, str(exc), details={"code": exc.code}), json_output)
        raise typer.Exit(1)
    except runtime_router.RuntimeRouterError as exc:
        _out(err(ArcErrorCode.NOT_IMPLEMENTED, str(exc), details={"code": exc.code}), json_output)
        raise typer.Exit(1)

    if not json_output:
        console.print(f"[dim]Runtime:[/dim] {routed.adapter.adapter_id} ({routed.chosen_by})")

    inputs = {"workspace": str(ws), "allow_paid_calls": allow_paid_calls}
    if prompt:
        inputs["prompt"] = prompt
    run_record = asyncio.run(routed.adapter.run_workflow(workflow, inputs))

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


@providers_app.command("status")
def providers_status(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return dry-run provider status from environment presence only."""
    import os
    _setup_logging(debug)
    from .providers import provider_statuses
    _out(ok([status.model_dump() for status in provider_statuses(os.environ)]), json_output)


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


if __name__ == "__main__":
    app()
