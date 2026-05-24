"""Profile commands: list, show, create (Phase 25.4)."""

from __future__ import annotations

from typing import Optional

import typer
from rich.table import Table

from ..gating import BackendMode
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import (
    DEBUG_FLAG,
    JSON_FLAG,
    _out,
    _profile_payload,
    _setup_logging,
)
from ._subapps import profiles_app


@profiles_app.command("list")
def profiles_list(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """List available run profiles."""
    _setup_logging(debug)
    from ..security.profiles import list_profiles

    profiles = [_profile_payload(p) for p in list_profiles().values()]
    _out(ok(profiles), json_output)
    if not json_output:
        from ._app import console

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
    from ..security.profiles import ProfileNotFound, resolve_profile_strict

    try:
        profile = resolve_profile_strict(profile_id)
    except ProfileNotFound:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Profile '{profile_id}' does not exist",
                details={"code": "UNKNOWN_PROFILE"},
            ),
            json_output,
        )
        raise typer.Exit(2)
    payload = _profile_payload(profile)
    _out(ok(payload), json_output)
    if not json_output:
        from ._app import console

        console.print(f"[bold]{profile.name}[/bold] ({profile.id})")
        console.print(
            f"  Backend: {profile.backend.value}  Paid: {'yes' if profile.allow_paid_calls else 'no'}"
        )
        console.print(
            f"  Network: {'yes' if profile.allow_network else 'no'}  Shell: {'yes' if profile.allow_shell else 'no'}"
        )


@profiles_app.command("create")
def profiles_create(
    profile_id: str = typer.Argument(..., help="Profile id"),
    allow_paid_calls: bool = typer.Option(
        False, "--allow-paid-calls", help="Allow paid/provider calls"
    ),
    allow_network: bool = typer.Option(False, "--allow-network", help="Allow network access"),
    allow_shell: bool = typer.Option(False, "--allow-shell", help="Allow shell/tool execution"),
    allow_secrets: bool = typer.Option(False, "--allow-secrets", help="Allow secret env exposure"),
    provider: Optional[str] = typer.Option(
        None, "--provider", help="Default provider metadata only"
    ),
    default_model: Optional[str] = typer.Option(
        None, "--default-model", help="Default model metadata only"
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Create an external run profile in ~/.arc/profiles.json."""
    _setup_logging(debug)
    from ..security.profiles import RunProfile, save_custom_profile

    backend = BackendMode.LOCAL if allow_paid_calls or allow_network else BackendMode.STUB
    profile = RunProfile(
        id=profile_id,
        name=profile_id,
        allow_paid_calls=allow_paid_calls,
        allow_network=allow_network or allow_paid_calls,
        allow_shell=allow_shell,
        allow_secrets=allow_secrets,
        backend=backend,
    )
    try:
        path = save_custom_profile(profile)
    except ValueError as exc:
        _out(
            err(ArcErrorCode.INVALID_INPUT, str(exc), details={"code": "PROFILE_EXISTS"}),
            json_output,
        )
        raise typer.Exit(2)
    payload = _profile_payload(profile)
    payload.update(
        {
            "path": str(path),
            "provider": provider,
            "default_model": default_model,
            "stores_secrets": False,
        }
    )
    _out(ok(payload), json_output)
