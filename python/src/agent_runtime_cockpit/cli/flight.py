"""CLI commands for the Local Agent Flight Recorder.

Sub-commands:
    arc flight status           — Show recorder status and index summary.
    arc flight verify           — Verify all segment integrity + hash chain.
    arc flight export           — Export a run bundle to a .tar.gz.
    arc flight prune --dry-run  — Show what retention would delete.
    arc flight prune --apply    — Apply retention policy.
    arc flight inspect          — Inspect events for a specific run.
    arc flight record (dev)     — Manually inject a test event.

All commands:
  - Local-only.
  - No network I/O.
  - No model calls.
  - No MCP server startup.
  - Support ``--json`` for machine-readable output.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Optional

import typer

from ._subapps import flight_app  # noqa: F401 — registers the sub-app
from ..flight_recorder import FlightRecorder, FlightRecorderConfig
from ..flight_recorder import index as _index
from ..flight_recorder.export import export_run
from ..flight_recorder.models import EventType
from ..flight_recorder.retention import prune
from ..flight_recorder.verify import verify

# Re-export flight_app for registration in _app.py
app = flight_app


def _default_config(workspace: Optional[str]) -> FlightRecorderConfig:
    base = (Path(workspace) if workspace else Path.cwd()) / ".arc" / "flight"
    return FlightRecorderConfig(base_dir=str(base))


def _out(data: object, as_json: bool) -> None:
    if as_json or not sys.stdout.isatty():
        typer.echo(json.dumps(data, indent=2, default=str))
    else:
        typer.echo(json.dumps(data, indent=2, default=str))


# ---------------------------------------------------------------------------
# arc flight status
# ---------------------------------------------------------------------------


@flight_app.command("status")
def flight_status(
    workspace: Optional[str] = typer.Option(None, "--workspace", help="ARC workspace path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Show Flight Recorder status and index summary."""
    cfg = _default_config(workspace)
    recorder = FlightRecorder(config=cfg)
    status = recorder.status()
    _out({"ok": True, "status": status}, json_output)


# ---------------------------------------------------------------------------
# arc flight verify
# ---------------------------------------------------------------------------


@flight_app.command("verify")
def flight_verify(
    workspace: Optional[str] = typer.Option(None, "--workspace", help="ARC workspace path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Verify integrity of all flight recorder segments."""
    cfg = _default_config(workspace)
    base_dir = Path(cfg.base_dir)
    report = verify(base_dir)
    data = report.model_dump()
    _out({"ok": report.ok, "report": data}, json_output)
    if not report.ok:
        raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# arc flight export
# ---------------------------------------------------------------------------


@flight_app.command("export")
def flight_export(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to export"),
    out: str = typer.Option(..., "--out", help="Output path for .tar.gz bundle"),
    workspace: Optional[str] = typer.Option(None, "--workspace", help="ARC workspace path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    no_redact: bool = typer.Option(False, "--no-redact", help="Skip secret check (dangerous)"),
) -> None:
    """Export a run's flight recorder data as a local forensic bundle."""
    cfg = _default_config(workspace)
    base_dir = Path(cfg.base_dir)
    out_path = Path(out)

    try:
        bundle = export_run(
            base_dir,
            run_id,
            out_path,
            redact_secrets=not no_redact,
        )
        _out(
            {
                "ok": True,
                "bundle_id": bundle.bundle_id,
                "out": str(out_path),
                "total_events": bundle.total_events,
                "segments": bundle.segments,
            },
            json_output,
        )
    except ValueError as exc:
        _out({"ok": False, "error": str(exc)}, json_output)
        raise typer.Exit(code=2)


# ---------------------------------------------------------------------------
# arc flight prune
# ---------------------------------------------------------------------------


@flight_app.command("prune")
def flight_prune(
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Dry-run (default) or apply"),
    workspace: Optional[str] = typer.Option(None, "--workspace", help="ARC workspace path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """Run retention policy (dry-run by default; use --apply to delete)."""
    cfg = _default_config(workspace)
    base_dir = Path(cfg.base_dir)
    # No active runs known to CLI (conservative — never delete anything active)
    result = prune(base_dir, cfg, active_run_ids=set(), dry_run=dry_run)
    _out({"ok": True, **result}, json_output)


# ---------------------------------------------------------------------------
# arc flight inspect
# ---------------------------------------------------------------------------


@flight_app.command("inspect")
def flight_inspect(
    run_id: str = typer.Option(..., "--run-id", help="Run ID to inspect"),
    workspace: Optional[str] = typer.Option(None, "--workspace", help="ARC workspace path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
    limit: int = typer.Option(50, "--limit", help="Maximum events to show"),
) -> None:
    """Inspect flight recorder events for a specific run."""
    cfg = _default_config(workspace)
    base_dir = Path(cfg.base_dir)
    seg_refs = _index.segments_for_run(base_dir, run_id)

    if not seg_refs:
        _out({"ok": False, "error": f"No segments found for run {run_id!r}"}, json_output)
        raise typer.Exit(code=2)

    from ..flight_recorder.segments import read_segment_events

    all_events = []
    for seg_ref in sorted(seg_refs, key=lambda s: s.created_at):
        ep = Path(seg_ref.events_path)
        if not ep.is_absolute():
            ep = base_dir / seg_ref.events_path
        events = read_segment_events(ep)
        all_events.extend(events)
        if len(all_events) >= limit:
            break

    _out(
        {
            "ok": True,
            "run_id": run_id,
            "segments": len(seg_refs),
            "total_events_loaded": len(all_events),
            "events": all_events[:limit],
        },
        json_output,
    )


# ---------------------------------------------------------------------------
# arc flight record  (dev-only — hidden from help)
# ---------------------------------------------------------------------------


@flight_app.command("record", hidden=True)
def flight_record(
    run_id: str = typer.Option(..., "--run-id", help="Run ID"),
    event: str = typer.Option(..., "--event", help="Event type (e.g. run.started)"),
    json_payload: str = typer.Option("{}", "--json-payload", help="JSON payload string"),
    workspace: Optional[str] = typer.Option(None, "--workspace", help="ARC workspace path"),
    json_output: bool = typer.Option(False, "--json", help="Output as JSON"),
) -> None:
    """[DEV] Inject a synthetic event into the flight recorder (testing/debug only)."""
    cfg = _default_config(workspace)
    recorder = FlightRecorder(config=cfg)

    try:
        et = EventType(event)
    except ValueError:
        _out({"ok": False, "error": f"Unknown event type: {event!r}"}, json_output)
        raise typer.Exit(code=2)

    try:
        payload = json.loads(json_payload)
    except json.JSONDecodeError as exc:
        _out({"ok": False, "error": f"Invalid JSON payload: {exc}"}, json_output)
        raise typer.Exit(code=2)

    recorded = recorder.record(run_id, et, payload=payload)
    if recorded:
        _out({"ok": True, "event_id": recorded.event_id, "hash": recorded.hash}, json_output)
    else:
        _out({"ok": False, "error": "Event not recorded (disabled or fail_closed)"}, json_output)
        raise typer.Exit(code=2)
