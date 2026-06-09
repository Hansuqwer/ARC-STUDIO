"""WebSocket + SSE event stream relay for R87 ARC Stream.

Provides:
  GlobalEventBroker  — in-memory pub/sub with asyncio.Queue per subscriber.
  global_sse_handler — aiohttp handler for GET /api/events/stream (SSE).
  TuiEventSource     — asyncio-based SSE client for the TUI.
  add_routes()       — register routes on the aiohttp app.

This is a stub: all method bodies raise NotImplementedError.
Kiro agents should fill the bodies without guessing the interface.

Dependencies:
  - orchestration/event_broker.py  (EventBroker, for hook_event_broker_publish)
  - web/server.py                  (aiohttp app, bearer_token_middleware)
  - web/routes.py                  (call add_routes(app) here)

Security constraints (must not be relaxed):
  - Bind to 127.0.0.1 only.
  - Bearer-token auth via ARC_DAEMON_TOKEN (reuse bearer_token_middleware).
  - No multi-tenant; single-user loopback-only.
  - Queue size 100: sufficient for system events (~1-10/min); prevents OOM.

Companion audit doc:
  docs/research-findings/r87-stream-relay-audit-2026-06-09.md
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator

from aiohttp import web

log = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────
# GlobalEventBroker
# ─────────────────────────────────────────────────────────────


class GlobalEventBroker:
    """Lightweight pub/sub for system-wide events.

    Publishes: HITL_PROMPT, HITL_RESPONSE, QUOTA_WARNING,
               RUN_STARTED, RUN_COMPLETED, RUN_FAILED, RUN_CANCELLED.

    Does NOT publish per-run detailed events (use EventBroker for those).
    """

    def __init__(self, max_queue_size: int = 100) -> None:
        self._max_queue_size = max_queue_size
        self._subscribers: list[asyncio.Queue[dict[str, Any]]] = []

    def publish(self, event: dict[str, Any]) -> None:
        """Publish an event to all subscribers. Drop oldest if queue full."""
        raise NotImplementedError

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Return a new subscriber queue and register it."""
        raise NotImplementedError

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber queue."""
        raise NotImplementedError


_global_broker: GlobalEventBroker | None = None


def get_global_broker() -> GlobalEventBroker:
    """Return the singleton GlobalEventBroker (lazy init)."""
    global _global_broker
    if _global_broker is None:
        _global_broker = GlobalEventBroker()
    return _global_broker


# ─────────────────────────────────────────────────────────────
# SSE handler
# ─────────────────────────────────────────────────────────────


async def global_sse_handler(request: web.Request) -> web.StreamResponse:
    """GET /api/events/stream — SSE endpoint for system-wide events.

    Auth: bearer_token_middleware (already applied in web/server.py).
    Heartbeat: every 30s (comment line).
    On client disconnect: unsubscribe and return cleanly.
    """
    raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# TUI SSE client
# ─────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StreamEvent:
    """Parsed SSE event for TUI consumption."""

    event_type: str
    data: dict[str, Any]
    event_id: str | None = None


class TuiEventSource:
    """asyncio SSE client for the TUI.

    Connects to http://127.0.0.1:7777/api/events/stream and yields
    parsed StreamEvent objects with exponential-backoff reconnect.

    Usage:
        source = TuiEventSource(token=os.environ.get("ARC_DAEMON_TOKEN"))
        async for event in source.connect():
            handle(event)
    """

    def __init__(
        self,
        url: str = "http://127.0.0.1:7777/api/events/stream",
        token: str | None = None,
        reconnect_base_delay: float = 2.0,
        max_reconnect_delay: float = 30.0,
        max_reconnect_attempts: int = 5,
    ) -> None:
        self._url = url
        self._token = token
        self._reconnect_base_delay = reconnect_base_delay
        self._max_reconnect_delay = max_reconnect_delay
        self._max_reconnect_attempts = max_reconnect_attempts
        self._last_event_id: str | None = None

    async def connect(self) -> AsyncIterator[StreamEvent]:
        """Yield StreamEvent instances; reconnect on connection loss."""
        raise NotImplementedError

    async def close(self) -> None:
        """Close the connection and release resources."""
        raise NotImplementedError

    def _parse_sse_line(self, line: str) -> tuple[str, str] | None:
        """Parse a single SSE line into (field, value). Returns None for comments."""
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────
# Wire helpers
# ─────────────────────────────────────────────────────────────


def hook_event_broker_publish(event_broker: Any) -> None:
    """Hook EventBroker.publish() to also forward terminal events to
    GlobalEventBroker. Call once from web/server.py on app startup.

    Terminal event types to forward:
        RUN_STARTED, RUN_COMPLETED, RUN_FAILED, RUN_CANCELLED,
        HITL_PROMPT, HITL_RESPONSE, QUOTA_WARNING.
    """
    raise NotImplementedError


def add_routes(app: web.Application) -> None:
    """Register /api/events/stream on the aiohttp app.

    Call from web/routes.py:
        from agent_runtime_cockpit.stream.websocket import add_routes
        add_routes(app)
    """
    raise NotImplementedError
