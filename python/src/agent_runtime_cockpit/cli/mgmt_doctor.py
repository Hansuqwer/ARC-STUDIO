"""ARC doctor management commands (split from mgmt.py — CR-026)."""

from __future__ import annotations

from typing import Optional

import typer

from .. import __version__ as arc_version
from ..protocol.event_envelope import ok
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    WORKSPACE_FLAG,
    _out,
    _setup_logging,
    _workspace,
    check_swarmgraph_runtime,
)
from ._subapps import doctor_app


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


# CR-025: the legacy `eval run` command was removed here; `eval_run_new` below
# is the single `@eval_app.command("run")` registration (Typer last-wins meant
# this older definition was already shadowed/dead).


@doctor_app.command("providers")
def doctor_providers(json_output: bool = JSON_FLAG, debug: bool = DEBUG_FLAG) -> None:
    """Show key-configuration status for all bundled providers.

    Reports key_source (env | stored | none) and whether the provider is free-tier
    (LOCAL auth — no key required). Does not make network calls.
    """
    import os

    _setup_logging(debug)
    from ..auth.manager import get_credential
    from ..provider_action import PROVIDERS, ProviderAuthKind, provider_statuses

    env_status = {s.provider: s for s in provider_statuses(os.environ)}

    entries = []
    for p in PROVIDERS:
        is_free = p.auth_kind == ProviderAuthKind.LOCAL
        env_s = env_status.get(p.id)
        key_source: str
        if is_free:
            key_source = "local"
        elif env_s and env_s.api_key_configured:
            key_source = "env"
        elif get_credential(p.id, trust_check=False) is not None:
            key_source = "stored"
        else:
            key_source = "none"
        entries.append(
            {
                "provider_id": p.id,
                "display_name": p.display_name,
                "key_source": key_source,
                "is_free_tier": is_free,
                "configured": key_source != "none",
            }
        )

    configured = sum(1 for e in entries if e["configured"])
    _out(
        ok({"total": len(entries), "configured": configured, "providers": entries}),
        json_output,
    )
