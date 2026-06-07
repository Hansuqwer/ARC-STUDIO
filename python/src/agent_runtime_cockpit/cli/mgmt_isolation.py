"""ARC isolation management commands (split from mgmt.py — CR-026)."""

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
)
from ._subapps import isolation_app


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
