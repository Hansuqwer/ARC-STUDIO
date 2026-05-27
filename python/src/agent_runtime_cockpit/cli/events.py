"""CLI commands for the event system: query, watch, webhook management (Phase 32 / Phase 56)."""

from __future__ import annotations

import asyncio
import json
import signal
import sys
from pathlib import Path
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.json import JSON

from ..events.bus import get_bus
from ..events.models import WebhookConfig
from ..events.webhooks import WebhookManager
from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import events_app

err_console = Console(stderr=True)


@events_app.command("summary")
def events_summary(
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Summarize the local/recent event log."""
    _setup_logging(debug)
    from ..events.persistence import DEFAULT_EVENT_LOG_PATH

    log_path = Path.cwd() / DEFAULT_EVENT_LOG_PATH
    counts = {
        "hitl": 0,
        "runFailures": 0,
        "auditAlerts": 0,
        "taskFailures": 0,
        "evalFailures": 0,
    }
    malformed = 0
    unmatched_hitl_decisions = 0
    total = 0
    if log_path.exists():
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                malformed += 1
                continue
            total += 1
            event_type = event.get("event_type")
            if event_type == "hitl_required":
                counts["hitl"] += 1
            elif event_type == "hitl_decided" and counts["hitl"] > 0:
                counts["hitl"] -= 1
            elif event_type == "hitl_decided":
                unmatched_hitl_decisions += 1
            elif event_type == "run_failed":
                counts["runFailures"] += 1
            elif event_type == "audit_verified" and event.get("ok") is False:
                counts["auditAlerts"] += 1
            elif event_type == "task_failed":
                counts["taskFailures"] += 1
            elif event_type == "eval_completed" and int(event.get("failures_count", 0) or 0) > 0:
                counts["evalFailures"] += 1
    _out(
        ok(
            {
                **counts,
                "source": "local_event_log_recent",
                "protocol": "sse",
                "degraded": malformed > 0 or unmatched_hitl_decisions > 0,
                "malformed": malformed,
                "unmatched_hitl_decisions": unmatched_hitl_decisions,
                "summary_semantics": "local_recent_derived_compaction_may_drop_pairs",
                "total": total,
                "path": str(log_path),
            }
        ),
        json_output,
    )


@events_app.command("query")
def events_query(
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by event type"),
    since: Optional[str] = typer.Option(None, "--since", help="ISO timestamp start filter"),
    until: Optional[str] = typer.Option(None, "--until", help="ISO timestamp end filter"),
    limit: int = typer.Option(100, "--limit", "-n", help="Max events to return"),
    stats: bool = typer.Option(False, "--stats", help="Return event type counts instead of events"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Query the event log for stored events.

    Reads directly from the JSONL event log (not via daemon).
    Use --type to filter by event type, --since/--until for time range.
    Use --stats for event type counts instead of raw events.
    """
    _setup_logging(debug)

    from ..events.persistence import DEFAULT_EVENT_LOG_PATH

    log_path = Path.cwd() / DEFAULT_EVENT_LOG_PATH

    if not log_path.exists():
        _out(
            err(ArcErrorCode.RUN_NOT_FOUND, "Event log not found. No events have been persisted."),
            json_output,
        )
        raise typer.Exit(1)

    lines = log_path.read_text(encoding="utf-8").splitlines()
    events_list: list[dict] = []
    type_counts: dict[str, int] = {}
    oldest_ts: Optional[str] = None
    newest_ts: Optional[str] = None

    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Pop internal seq
        data.pop("seq", None)

        ts = data.get("timestamp", "")
        ev_type = data.get("event_type", "")

        # Track stats
        type_counts[ev_type] = type_counts.get(ev_type, 0) + 1
        if ts:
            if oldest_ts is None or ts < oldest_ts:
                oldest_ts = ts
            if newest_ts is None or ts > newest_ts:
                newest_ts = ts

        # Filter by type
        if event_type and ev_type != event_type:
            continue

        # Filter by since
        if since and ts and ts < since:
            continue

        # Filter by until
        if until and ts and ts > until:
            continue

        events_list.append(data)

    if stats:
        payload = {
            "total": len(lines),
            "filtered_count": len(events_list),
            "event_types": type_counts,
            "oldest_timestamp": oldest_ts,
            "newest_timestamp": newest_ts,
        }
        _out(ok(payload), json_output)
        return

    # Apply limit
    if limit > 0:
        events_list = events_list[-limit:]

    payload = {
        "count": len(events_list),
        "filters": {
            "type": event_type,
            "since": since,
            "until": until,
            "limit": limit,
        },
        "events": events_list,
    }
    _out(ok(payload), json_output)


@events_app.command("watch")
def watch_events(
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by event type"),
    since: int = typer.Option(0, "--since", help="Replay recent N events from ring buffer"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Stream typed events to stdout as they occur.

    Press Ctrl+C to stop watching.
    """
    _setup_logging(debug)
    bus = get_bus()

    def _handler(event) -> None:
        data = event.model_dump()
        if json_output:
            print(json.dumps(data, default=str))
        else:
            rprint(JSON(json.dumps(data, default=str)))

    handler_key = event_type or "*"

    if handler_key == "*":
        bus.subscribe_all(_handler)
    else:
        bus.subscribe(handler_key, _handler)

    try:
        if since > 0:
            for ev in bus._replay_since(max(0, len(bus._ring_buffer) - since)):
                _handler(ev)

        # Block until Ctrl+C
        if sys.platform != "win32":
            loop = asyncio.new_event_loop()
            # Set up signal handler for graceful shutdown
            for sig in (signal.SIGINT, signal.SIGTERM):
                try:
                    loop.add_signal_handler(sig, lambda: None)
                except (NotImplementedError, ValueError):
                    pass
            loop.run_forever()
        else:
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.pause()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        if handler_key == "*":
            bus.unsubscribe_all(_handler)
        else:
            bus.unsubscribe(handler_key, _handler)


# ---------------------------------------------------------------------------
# Webhook management sub-commands
# ---------------------------------------------------------------------------


@events_app.command("webhook-add")
def webhook_add(
    url: str = typer.Argument(..., help="Webhook URL"),
    secret: str = typer.Argument(..., help="HMAC signing secret"),
    events: Optional[str] = typer.Option(None, "--events", help="Comma-separated event types or *"),
    retry_max: int = typer.Option(5, "--retry-max", help="Max retry attempts"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Add a webhook endpoint."""
    _setup_logging(debug)
    manager = WebhookManager()
    enabled = [e.strip() for e in events.split(",")] if events else ["*"]
    config = WebhookConfig(
        url=url,
        secret=secret,
        enabled_events=enabled,
        retry_max=retry_max,
    )
    manager.add(config)
    err_console.print(f"[green]Webhook {config.id} added[/green]")
    err_console.print(f"  URL: {url}")
    err_console.print(f"  Events: {', '.join(enabled)}")
    err_console.print(
        "[yellow]Warning: Secret stored in config file with 0o600 permissions[/yellow]"
    )


@events_app.command("webhook-list")
def webhook_list(
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """List configured webhooks."""
    _setup_logging(debug)
    manager = WebhookManager()
    configs = manager.list()
    if not configs:
        err_console.print("[yellow]No webhooks configured[/yellow]")
        return
    for c in configs:
        rprint(JSON(json.dumps(c.model_dump(), default=str)))


@events_app.command("webhook-remove")
def webhook_remove(
    webhook_id: str = typer.Argument(..., help="Webhook ID to remove"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """Remove a webhook endpoint."""
    _setup_logging(debug)
    manager = WebhookManager()
    if manager.remove(webhook_id):
        err_console.print(f"[green]Webhook {webhook_id} removed[/green]")
    else:
        err_console.print(f"[red]Webhook {webhook_id} not found[/red]")


@events_app.command("dead-letter")
def dead_letter_list(
    limit: int = typer.Option(100, "--limit", "-l", help="Max entries to show"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug logging"),
) -> None:
    """List dead-letter entries for permanently failed deliveries."""
    _setup_logging(debug)
    manager = WebhookManager()
    entries = manager.read_dead_letter(limit=limit)
    if not entries:
        err_console.print("[yellow]No dead-letter entries[/yellow]")
        return
    for e in entries:
        rprint(JSON(json.dumps(e.model_dump(), default=str)))
