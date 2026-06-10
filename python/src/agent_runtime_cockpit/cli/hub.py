"""CLI commands for ARC Hub — local-first config/policy/template sharing (R91).

Commands:
  arc hub list      List installed hub items.
  arc hub add       Add a hub item from a local file or directory.
  arc hub remove    Remove an installed hub item.
  arc hub verify    Verify installed item checksum.
  arc hub inspect   Show details of an installed hub item.

All commands accept --json for machine-readable envelope output.
No command opens a network connection.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import hub_app


@hub_app.command("list")
def hub_list(
    item_type: Optional[str] = typer.Option(
        None,
        "--type",
        "-t",
        help="Filter by item type (provider-preset, policy-template, swarm-def, eval-suite, theme)",
    ),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """List all installed hub items."""
    from ..hub import VALID_ITEM_TYPES, create_catalog

    if item_type and item_type not in VALID_ITEM_TYPES:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Unknown type '{item_type}'. Valid: {sorted(VALID_ITEM_TYPES)}",
            ),
            as_json,
        )
        raise typer.Exit(1)

    ws = _workspace(workspace)
    catalog = create_catalog(ws)
    items = catalog.list_items(item_type=item_type)
    _out(
        ok(
            {
                "count": len(items),
                "items": [i.to_dict() for i in items],
            }
        ),
        as_json,
    )


@hub_app.command("add")
def hub_add(
    source: str = typer.Argument(..., help="Path to a YAML/JSON file or directory to add."),
    force: bool = typer.Option(False, "--force", help="Overwrite if already installed."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Add a hub item from a local file or directory."""
    from ..hub import HubError, HubInvalidType, create_catalog

    ws = _workspace(workspace)
    catalog = create_catalog(ws)
    try:
        item = catalog.add(Path(source), force=force)
        _out(
            ok(
                {
                    "id": item.id,
                    "name": item.name,
                    "item_type": item.item_type,
                    "version": item.version,
                    "sha256": item.sha256,
                    "installed_at": item.installed_at,
                    "message": f"Hub item '{item.id}' added successfully.",
                }
            ),
            as_json,
        )
    except HubInvalidType as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), as_json)
        raise typer.Exit(1)
    except HubError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), as_json)
        raise typer.Exit(1)


@hub_app.command("remove")
def hub_remove(
    item_id: str = typer.Argument(..., help="Hub item ID to remove."),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Remove an installed hub item.

    This is a destructive action that requires confirmation unless --yes is provided.
    """
    from ..hub import HubError, create_catalog

    ws = _workspace(workspace)
    catalog = create_catalog(ws)

    if not yes and not as_json:
        from ._app import console

        console.print(
            f"[yellow]Warning:[/yellow] This will remove hub item '{item_id}' and all its files."
        )
        if not typer.confirm("Are you sure?"):
            console.print("[dim]Aborted.[/dim]")
            raise typer.Exit(0)

    try:
        catalog.remove(item_id)
        _out(ok({"id": item_id, "message": f"Hub item '{item_id}' removed."}), as_json)
    except HubError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), as_json)
        raise typer.Exit(1)


@hub_app.command("verify")
def hub_verify(
    item_id: str = typer.Argument(..., help="Hub item ID to verify."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Verify installed item checksum against recorded sha256."""
    from ..hub import HubError, create_catalog

    ws = _workspace(workspace)
    catalog = create_catalog(ws)
    try:
        result = catalog.verify(item_id)
        if result["ok"]:
            _out(ok(result), as_json)
        else:
            _out(
                err(
                    ArcErrorCode.CONFORMANCE_FAILED,
                    f"Checksum verification failed for '{item_id}': {result.get('reason')}",
                    result,
                ),
                as_json,
            )
            raise typer.Exit(1)
    except HubError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), as_json)
        raise typer.Exit(1)


@hub_app.command("inspect")
def hub_inspect(
    item_id: str = typer.Argument(..., help="Hub item ID to inspect."),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Show details of an installed hub item."""
    from ..hub import HubError, create_catalog

    ws = _workspace(workspace)
    catalog = create_catalog(ws)
    try:
        item = catalog.get(item_id)
        _out(ok(item.to_dict()), as_json)
    except HubError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), as_json)
        raise typer.Exit(1)


__all__ = ["hub_app"]
