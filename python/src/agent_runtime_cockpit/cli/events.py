"""CLI commands for the event system: watch, webhook management (Phase 32 / R25)."""

from __future__ import annotations

import asyncio
import json
import signal
import sys
from typing import Optional

import typer
from rich import print as rprint
from rich.console import Console
from rich.json import JSON

from ..events.bus import get_bus
from ..events.models import WebhookConfig
from ..events.webhooks import WebhookManager
from ._helpers import _setup_logging
from ._subapps import events_app

err_console = Console(stderr=True)


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
