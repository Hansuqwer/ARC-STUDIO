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

from pathlib import Path
from typing import Optional

import typer
from rich.table import Table

from . import __version__ as arc_version
from .adapters.registry import default_registry
from .context.pack import ContextPackGenerator
from .protocol.event_envelope import ok, err
from .protocol.errors import ArcErrorCode

# Phase 25: decomposed CLI modules. Re-export for backward compatibility.
from .cli._app import app, main, console, err_console  # noqa: F401
from .cli._subapps import (  # noqa: F401
    accounts_app,
    adapter_app,
    config_app,
    context_app,
    doctor_app,
    eval_app,
    hitl_app,
    isolation_app,
    key_app,
    profiles_app,
    prompt_app,
    providers_app,
    quota_app,
    routing_app,
    storage_app,
    studio_app,
    studio_sessions_app,
    workspace_app,
)
from .cli._helpers import (  # noqa: F401
    JSON_FLAG,
    WORKSPACE_FLAG,
    DEBUG_FLAG,
    LOCAL_REAL_GATE_ENVS,
    _setup_logging,
    _workspace,
    _out,
    _profile_payload,
    _validate_runtime_mode,
    _local_real_gate_open,
    _local_real_gate_state,
    _run_preflight,
    check_swarmgraph_runtime,
)


# ─── version ──────────────────────────────────────────────────────────────────


@providers_app.command("list")
def providers_list(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """List built-in provider definitions. No network calls are made."""
    _setup_logging(debug)
    from .provider_action import PROVIDERS

    _out(ok([provider.model_dump() for provider in PROVIDERS]), json_output)


@providers_app.command("catalog")
def providers_catalog(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """List provider auth catalog entries. No secrets or network calls."""
    _setup_logging(debug)
    from .provider_action import PROVIDERS

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
        ws = Path.cwd()
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
    # Check both ARC_PYTHON_DAEMON_URL and legacy ARC_DAEMON_HOST/PORT
    daemon_url = os.environ.get("ARC_PYTHON_DAEMON_URL")
    if daemon_url:
        try:
            # enforcement: not-applicable - Internal daemon health check, not user-triggered network access
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
        # Fallback to legacy ARC_DAEMON_HOST/PORT
        daemon_host = os.environ.get("ARC_DAEMON_HOST", "127.0.0.1")
        daemon_port = os.environ.get("ARC_DAEMON_PORT", "7777")
        try:
            # enforcement: not-applicable - Internal daemon health check, not user-triggered network access
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
        from .provider_action import provider_statuses

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
            from .storage.sqlite import SqliteStore

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
    # enforcement: not-applicable - Diagnostic command for checking provider connectivity, not actual API calls
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
            # enforcement: not-applicable - Diagnostic command for checking provider connectivity
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
        from .storage.sqlite import SqliteStore

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


@providers_app.command("status")
def providers_status(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return dry-run provider status from environment presence only."""
    import os

    _setup_logging(debug)
    from .provider_action import provider_statuses

    _out(ok([status.model_dump() for status in provider_statuses(os.environ)]), json_output)


@providers_app.command("diagnostics")
def providers_diagnostics(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return redacted provider diagnostics (statuses, routing, accounts, quota).

    No network calls are made. All secrets are redacted.
    """
    import os

    _setup_logging(debug)
    from .provider_action import redacted_diagnostics

    _out(ok(redacted_diagnostics(os.environ)), json_output)


@providers_app.command("proxy")
def providers_proxy(
    provider: Optional[str] = typer.Option(
        None, "--provider", help="Provider id (default: routing default)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help="Model name (default: routing default)"
    ),
    prompt: str = typer.Option("Hello", "--prompt", help="Prompt text for dry-run proxy"),
    live: bool = typer.Option(
        False,
        "--live",
        help="Request live provider mode; still requires env gate and --allow-paid-calls",
    ),
    allow_paid_calls: bool = typer.Option(
        False, "--allow-paid-calls", help="Allow paid provider calls when --live is set"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Dry-run provider proxy. No network call is made.

    Validates routing, quota reservation, and gating without
    invoking any LLM API. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true
    and --allow-paid-calls for a live proxy call.
    """
    _setup_logging(debug)
    import os
    from .provider_action import ProviderRequest, check_provider_cost_gate, dry_run_proxy
    from .provider_action import ProviderRoutingStore

    routing = ProviderRoutingStore().get()
    req = ProviderRequest(
        provider=provider or routing.default_provider,
        model=model or routing.default_model,
        prompt=prompt,
        dry_run=not live,
        allow_paid_calls=allow_paid_calls,
    )
    try:
        gate = check_provider_cost_gate(req, os.environ)
        if not gate.allowed:
            messages = {
                "live_provider_calls_disabled": "Live provider calls disabled. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true and pass --live --allow-paid-calls.",
                "paid_provider_calls_disabled": "Paid provider calls disabled. Pass --allow-paid-calls with --live.",
            }
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    messages.get(
                        gate.reason or "", gate.reason or "Provider cost gate blocked request"
                    ),
                ),
                json_output,
            )
            raise typer.Exit(1)
        if live:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Live provider proxy is gated but not implemented in this CLI path; no network call was made.",
                ),
                json_output,
            )
            raise typer.Exit(1)
        resp = dry_run_proxy(req)
        _out(ok(resp.model_dump()), json_output)
    except RuntimeError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1)


@providers_app.command("action")
def providers_action(
    provider: Optional[str] = typer.Option(
        None, "--provider", help="Provider id (default: routing default)"
    ),
    model: Optional[str] = typer.Option(
        None, "--model", help="Model name (default: routing default)"
    ),
    prompt: str = typer.Option(
        "ARC provider action smoke", "--prompt", help="Prompt text for smoke contract"
    ),
    live: bool = typer.Option(False, "--live", help="Request gated live smoke scaffold"),
    allow_paid_calls: bool = typer.Option(
        False, "--allow-paid-calls", help="Allow paid provider calls when --live is set"
    ),
    confirm: Optional[str] = typer.Option(
        None, "--confirm", help="Required value: RUN_PROVIDER_ACTION:<provider>:<model>"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run narrow provider action contract; live path is gated closed smoke scaffold."""
    _setup_logging(debug)
    import os
    from .provider_action import ProviderActionRequest, ProviderRoutingStore, run_provider_action

    routing = ProviderRoutingStore().get()
    req = ProviderActionRequest(
        provider=provider or routing.default_provider,
        model=model or routing.default_model,
        prompt=prompt,
        dry_run=not live,
        allow_paid_calls=allow_paid_calls,
        confirmation=confirm,
    )
    try:
        result = run_provider_action(req, os.environ)
    except RuntimeError as exc:
        messages = {
            "live_provider_calls_disabled": "Live provider action disabled. Set ARC_ALLOW_LIVE_PROVIDER_TESTS=true and pass --live --allow-paid-calls plus --confirm.",
            "paid_provider_calls_disabled": "Paid provider calls disabled. Pass --allow-paid-calls with --live.",
            "provider_key_env_missing": "Provider key env var missing. Configure an env ref; raw keys are not accepted.",
        }
        raw_message = str(exc)
        message = messages.get(raw_message, raw_message)
        _out(err(ArcErrorCode.INVALID_INPUT, message), json_output)
        raise typer.Exit(1)
    _out(ok(result.model_dump()), json_output)


providers_app.add_typer(accounts_app)
providers_app.add_typer(key_app)


@key_app.command("status")
def providers_key_status(
    provider: Optional[str] = typer.Argument(None, help="Provider id filter"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show provider key status from env vars and saved env-ref accounts."""
    import os

    _setup_logging(debug)
    from .provider_action import PROVIDERS, ProviderAccountStore, provider_statuses

    env_status = {status.provider: status.model_dump() for status in provider_statuses(os.environ)}
    accounts = ProviderAccountStore().list_accounts()
    entries = []
    for definition in PROVIDERS:
        if provider and definition.id != provider:
            continue
        matching_accounts = [a for a in accounts if a.provider == definition.id]
        status = env_status.get(definition.id, {})
        entries.append(
            {
                "provider": definition.id,
                "display_name": definition.display_name,
                "auth_kind": definition.auth_kind.value,
                "credential_label": definition.credential_label,
                "status": definition.status,
                "configured": bool(status.get("api_key_configured"))
                or any(a.enabled for a in matching_accounts)
                or definition.auth_kind.value == "local",
                "source": status.get("api_key_source")
                and "env"
                or (
                    "account_ref"
                    if matching_accounts
                    else ("local" if definition.auth_kind.value == "local" else "unset")
                ),
                "env_key_names": definition.env_key_names,
                "accounts": [a.model_dump() for a in matching_accounts],
                "warnings": definition.warnings,
            }
        )
    _out(ok(entries), json_output)


@key_app.command("set")
def providers_key_set(
    provider: str = typer.Argument(..., help="Provider id"),
    env_var: str = typer.Option(..., "--env", help="Environment variable containing the key"),
    label: Optional[str] = typer.Option(None, "--label", help="Account label"),
    model: Optional[str] = typer.Option(None, "--model", help="Default model"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Save an env-var-backed provider key reference. Never stores raw keys."""
    _setup_logging(debug)
    from .provider_action import PROVIDERS, ProviderAccountStore, validate_env_var_name

    provider_ids = {p.id for p in PROVIDERS}
    if provider not in provider_ids:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Unknown provider: {provider}"), json_output)
        raise typer.Exit(2)
    try:
        validate_env_var_name(env_var)
        account = ProviderAccountStore().add_env_account(
            provider, label or "default", env_var, model
        )
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(2)
    _out(ok(account.model_dump()), json_output)


@key_app.command("unset")
def providers_key_unset(
    provider_or_account_id: str = typer.Argument(..., help="Provider id or account id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Delete saved provider key references. Does not modify environment variables."""
    _setup_logging(debug)
    from .provider_action import ProviderAccountStore

    store = ProviderAccountStore()
    accounts = store.list_accounts()
    deleted: list[str] = []
    for account in accounts:
        if account.id == provider_or_account_id or account.provider == provider_or_account_id:
            if store.delete(account.id):
                deleted.append(account.id)
    _out(ok({"deleted": deleted, "count": len(deleted)}), json_output)


@accounts_app.command("list")
def providers_accounts_list(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """List provider accounts without exposing secrets."""
    _setup_logging(debug)
    from .provider_action import ProviderAccountStore

    accounts = ProviderAccountStore().list_accounts()
    _out(ok([account.model_dump() for account in accounts]), json_output)


@accounts_app.command("add")
def providers_accounts_add(
    provider: str = typer.Option(..., "--provider", help="Provider id"),
    label: str = typer.Option(..., "--label", help="Account label"),
    api_key_env: str = typer.Option(
        ..., "--api-key-env", help="Environment variable containing the key"
    ),
    default_model: Optional[str] = typer.Option(None, "--model", help="Default model"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Add an env-var-backed provider account. The key is never printed."""
    _setup_logging(debug)
    from .provider_action import ProviderAccountStore

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
    from .provider_action import ProviderAccountStore

    account = ProviderAccountStore().set_enabled(account_id, False)
    if account is None:
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Provider account not found: {account_id}"),
            json_output,
        )
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
    from .provider_action import ProviderAccountStore

    deleted = ProviderAccountStore().delete(account_id)
    _out(ok({"deleted": deleted, "account_id": account_id}), json_output)


providers_app.add_typer(quota_app)


@quota_app.command("show")
def providers_quota_show(
    provider: Optional[str] = typer.Option(None, "--provider", help="Filter by provider id"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Show today's provider quota usage."""
    _setup_logging(debug)
    from .provider_action import ProviderQuotaStore

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
    """Reset today's local provider quota counters only."""
    _setup_logging(debug)
    from .provider_action import ProviderQuotaStore

    store = ProviderQuotaStore()
    store.reset()
    _out(ok({"reset": True, "scope": "local_quota_counters_only"}), json_output)


providers_app.add_typer(routing_app)


@routing_app.command("get")
def providers_routing_get(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Return persisted dry-run routing policy."""
    _setup_logging(debug)
    from .provider_action import ProviderRoutingStore

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
    from .provider_action import ProviderRoutingPolicy, ProviderRoutingStore

    policy = ProviderRoutingPolicy(mode=mode, default_provider=provider, default_model=model)
    _out(ok(ProviderRoutingStore().set(policy).model_dump()), json_output)


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
    from .isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from .isolation.docker_provider import DockerIsolationProvider

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
    from .isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from .isolation.docker_provider import DockerIsolationProvider

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
    from .isolation.docker_provider import DockerIsolationProvider

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
    from .isolation import NoneIsolationProvider, SubprocessIsolationProvider
    from .isolation.docker_provider import DockerIsolationProvider

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
        _out(
            err(ArcErrorCode.ADAPTER_NOT_SUPPORTED, f"Adapter not found: {adapter_id!r}"),
            json_output,
        )
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
        console.print(
            f"Summary: {result.passed} passed · {result.failed} failed · {result.skipped} skipped → {status}"
        )

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
    from .storage.jsonl import JsonlTraceStore
    from .evals.golden import GoldenTrace, eval_run as do_eval, load_golden, list_goldens

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
    from .evals.golden import GoldenTrace, save_golden

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
            table.add_row(
                g.id,
                g.workflow_id,
                g.expected_final_output_contains[:60] if g.expected_final_output_contains else "",
            )
        console.print(table)


# ─── workspace trust ───────────────────────────────────────────────────────────


@hitl_app.command("pending")
def hitl_pending(
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List pending workspace-local HITL prompts with single-use tokens."""
    _setup_logging(debug)
    from .audit.hitl_store import list_prompts, get_token

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
    from .audit.hitl import HitlDecision
    from .audit.hitl_store import respond

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


# ─── studio (Chat REPL) ──────────────────────────────────────────────────────


@studio_app.command("chat")
def studio_chat(
    prompt: Optional[str] = typer.Argument(None, help="Initial prompt"),
    session: Optional[str] = typer.Option(None, "--session", "-s", help="Resume session ID"),
    non_interactive: bool = typer.Option(
        False, "--non-interactive", "-n", help="Run once and exit"
    ),
    debug: bool = DEBUG_FLAG,
) -> None:
    """Launch the ARC Studio chat REPL with the native SwarmGraph runtime.

    Starts an interactive chat session. Provide an initial prompt to run
    once, or omit it to enter the REPL loop.
    """
    _setup_logging(debug)
    from .cli_repl.chat_repl import run_chat_repl

    run_chat_repl(
        initial_prompt=prompt,
        session_id=session,
        non_interactive=non_interactive,
    )


@studio_sessions_app.callback(invoke_without_command=True)
def studio_sessions(
    ctx: typer.Context,
    json_output: bool = JSON_FLAG,
) -> None:
    """List saved chat sessions."""
    if ctx.invoked_subcommand is not None:
        return
    from .cli_repl.session import ChatSession

    sessions = ChatSession.list_sessions()
    if json_output:
        _out(ok([s.model_dump() for s in sessions]), json_output)
        return
    if not sessions:
        console.print("[dim]No saved sessions.[/dim]")
        return
    table = Table("ID", "Messages", "Updated")
    for s in sessions[:20]:
        table.add_row(s.id[:16], str(len(s.history)), s.updated_at[:19])
    console.print(table)


@studio_sessions_app.command("migrate")
def studio_sessions_migrate(
    json_output: bool = JSON_FLAG,
) -> None:
    """Migrate legacy flat sessions to canonical format."""
    from .cli_repl.session import (
        _get_sessions_dir,
        _list_legacy_session_ids,
        migrate_legacy_session,
    )

    legacy_ids = _list_legacy_session_ids()
    newly_migrated: list[str] = []
    failed: list[str] = []
    for sid in legacy_ids:
        canonical_path = _get_sessions_dir() / sid / "session.json"
        if canonical_path.exists():
            # Already migrated — skip
            continue
        result = migrate_legacy_session(sid)
        if result is not None:
            newly_migrated.append(sid)
        else:
            failed.append(sid)

    if json_output:
        _out(
            ok(
                {
                    "total_legacy": len(legacy_ids),
                    "newly_migrated": len(newly_migrated),
                    "already_migrated": len(legacy_ids) - len(newly_migrated) - len(failed),
                    "failed": len(failed),
                    "session_ids": newly_migrated,
                }
            ),
            json_output,
        )
        return

    if not legacy_ids:
        console.print("[dim]No legacy sessions found to migrate.[/dim]")
        return

    console.print(f"Migration complete: {len(newly_migrated)} migrated, {len(failed)} failed.")
    if newly_migrated:
        console.print(f"  Migrated: {', '.join(newly_migrated[:10])}")
    if failed:
        console.print(f"[yellow]  Failed: {', '.join(failed[:5])}[/yellow]")


@studio_app.command("sessions-migrate")
def studio_sessions_migrate_deprecated(
    json_output: bool = JSON_FLAG,
) -> None:
    """Deprecated alias for `arc studio sessions migrate`."""
    if not json_output:
        console.print("[yellow]Deprecated:[/yellow] use `arc studio sessions migrate`.")
    studio_sessions_migrate(json_output=json_output)


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
        console.print(
            f"[dim]Original:[/dim] {result.original_tokens.count} tokens ({result.original_tokens.encoding})"
        )
        console.print(f"[green]Optimized:[/green] {result.optimized_tokens.count} tokens")
        console.print(f"[bold]Saved:[/bold] {result.tokens_saved} tokens")
        if result.changes:
            console.print(f"[dim]Rules applied:[/dim] {', '.join(result.changes)}")
        else:
            console.print("[dim]No changes needed[/dim]")
        if cost is not None:
            console.print(f"[dim]Est. cost before:[/dim] ${payload['estimated_cost_usd']:.6f}")
            console.print(
                f"[green]Est. cost after:[/green] ${payload['estimated_cost_after_usd']:.6f}"
            )


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


@workspace_app.command("init")
def workspace_init(
    workspace: Optional[str] = WORKSPACE_FLAG,
    name: Optional[str] = typer.Option(None, "--name", help="Workspace name"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Initialize ARC configuration in a workspace."""
    _setup_logging(debug)
    from .config.loader import init_config

    ws = _workspace(workspace)
    config_path = ws / ".arc" / "config.yaml"
    if config_path.exists():
        _out(
            err(ArcErrorCode.INVALID_INPUT, f"Config already exists at {config_path}"), json_output
        )
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
    key: Optional[str] = typer.Option(
        None, "--key", "-k", help="Config key to set (e.g. runtime.default)"
    ),
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
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "Config file not found. Run 'arc workspace init' first.",
                ),
                json_output,
            )
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
