"""Release intelligence and snapshot CLI commands."""

from __future__ import annotations

from pathlib import Path

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ..release_intelligence import generate_release_intelligence
from ..release_snapshots import (
    SnapshotError,
    list_snapshots,
    save_snapshot,
    verify_snapshot_immutability,
)
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import release_app, release_snapshot_app


@release_app.command("intelligence")
def release_intelligence_cmd(
    version: str = typer.Option("", "--version", help="Version label to include"),
    since: str | None = typer.Option(None, "--since", help="Optional git --since value"),
    markdown: bool = typer.Option(
        False, "--markdown", help="Emit markdown instead of envelope text"
    ),
    as_json: bool = JSON_FLAG,
    workspace: str | None = WORKSPACE_FLAG,
) -> None:
    """Generate local release intelligence from git metadata."""
    report = generate_release_intelligence(_workspace(workspace), version=version, since=since)
    if markdown and not as_json:
        typer.echo(report.to_markdown())
        return
    payload = report.to_dict()
    if markdown:
        payload["markdown"] = report.to_markdown()
    _out(ok(payload), as_json)


@release_snapshot_app.command("create")
def release_snapshot_create(
    output_dir: str = typer.Option("docs/RELEASE_SNAPSHOTS", "--output-dir", "-o"),
    filename: str | None = typer.Option(None, "--filename"),
    version: str = typer.Option("", "--version"),
    as_json: bool = JSON_FLAG,
    workspace: str | None = WORKSPACE_FLAG,
) -> None:
    """Create an immutable release snapshot markdown file."""
    ws = _workspace(workspace)
    report = generate_release_intelligence(ws, version=version)
    try:
        path = save_snapshot(report, Path(output_dir), filename=filename)
    except SnapshotError as exc:
        _out(err(ArcErrorCode.PERMISSION_DENIED, str(exc), {"output_dir": output_dir}), as_json)
        raise typer.Exit(1) from exc
    _out(ok({"path": str(path), "state": "success"}), as_json)


@release_snapshot_app.command("list")
def release_snapshot_list(
    snapshot_dir: str = typer.Option("docs/RELEASE_SNAPSHOTS", "--snapshot-dir", "-d"),
    as_json: bool = JSON_FLAG,
) -> None:
    """List release snapshots."""
    snapshots = list_snapshots(Path(snapshot_dir))
    _out(
        ok(
            {
                "snapshots": [snapshot.to_dict() for snapshot in snapshots],
                "state": "empty" if not snapshots else "success",
            }
        ),
        as_json,
    )


@release_snapshot_app.command("verify")
def release_snapshot_verify(
    snapshot_dir: str = typer.Option("docs/RELEASE_SNAPSHOTS", "--snapshot-dir", "-d"),
    as_json: bool = JSON_FLAG,
) -> None:
    """Verify release snapshot immutability status."""
    results = verify_snapshot_immutability(Path(snapshot_dir))
    _out(ok({"results": results, "state": "empty" if not results else "success"}), as_json)


__all__ = ["release_app"]
