"""WebSocket + SSE event stream relay for R87 ARC Stream.

Provides:
  GlobalEventBroker  — in-memory pub/sub with asyncio.Queue per subscriber.
  global_sse_handler — aiohttp handler for GET /api/global/events/stream (SSE).
  TuiEventSource     — asyncio-based SSE client for the TUI.
  add_routes()       — register routes on the aiohttp app.

Dependencies:
  - orchestration/event_broker.py  (EventBroker, for hook_event_broker_publish)
  - web/server.py                  (aiohttp app, bearer_token_middleware)
  - web/routes.py                  (call add_routes(app) here)

Security constraints:
  - Bind to 127.0.0.1 only.
  - No multi-tenant; single-user loopback-only.
  - Queue size 100: sufficient for system events; prevents OOM.
"""

from __future__ import annotations

import asyncio
import json
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
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Drop oldest, then add new
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        """Return a new subscriber queue and register it."""
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=self._max_queue_size)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        """Remove a subscriber queue."""
        try:
            self._subscribers.remove(queue)
        except ValueError:
            pass


_global_broker: GlobalEventBroker | None = None


def get_global_broker() -> GlobalEventBroker:
    """Return the singleton GlobalEventBroker (lazy init)."""
    global _global_broker
    if _global_broker is None:
        _global_broker = GlobalEventBroker()
    return _global_broker


def reset_global_broker() -> None:
    """Reset the singleton (for testing only)."""
    global _global_broker
    _global_broker = None


# ─────────────────────────────────────────────────────────────
# SSE handler
# ─────────────────────────────────────────────────────────────


async def global_sse_handler(request: web.Request) -> web.StreamResponse:
    """GET /api/global/events/stream — SSE endpoint for system-wide events.

    Heartbeat: every 30s (comment line).
    On client disconnect: unsubscribe and return cleanly.
    """
    response = web.StreamResponse(
        headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )
    await response.prepare(request)

    broker = get_global_broker()
    queue = broker.subscribe()

    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                payload = json.dumps(event, default=str)
                event_type = event.get("type", "message")
                await response.write(f"event: {event_type}\ndata: {payload}\n\n".encode())
            except asyncio.TimeoutError:
                # Heartbeat to keep connection alive
                await response.write(b": heartbeat\n\n")
            except asyncio.CancelledError:
                break
    except (ConnectionResetError, asyncio.CancelledError):
        log.debug("Global SSE client disconnected")
    finally:
        broker.unsubscribe(queue)

    return response


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
        self._closed = False

    async def connect(self) -> AsyncIterator[StreamEvent]:
        """Yield StreamEvent instances; reconnect on connection loss."""
        import aiohttp

        delay = self._reconnect_base_delay
        attempts = 0
        while not self._closed and attempts <= self._max_reconnect_attempts:
            headers: dict[str, str] = {}
            if self._token:
                headers["Authorization"] = f"Bearer {self._token}"
            if self._last_event_id:
                headers["Last-Event-ID"] = self._last_event_id
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(self._url, headers=headers) as resp:
                        if resp.status != 200:
                            log.warning("SSE connect failed: HTTP %s", resp.status)
                            break
                        # Reset delay on successful connect
                        delay = self._reconnect_base_delay
                        attempts = 0
                        async for raw_line in resp.content:
                            line = raw_line.decode("utf-8", errors="replace").rstrip("\n")
                            if self._closed:
                                return
                            parsed = self._parse_sse_line(line)
                            if parsed is None:
                                continue
                            field, value = parsed
                            if field == "id":
                                self._last_event_id = value
                            elif field == "data":
                                try:
                                    data = json.loads(value)
                                    yield StreamEvent(
                                        event_type=data.get("type", "message"),
                                        data=data,
                                        event_id=self._last_event_id,
                                    )
                                except json.JSONDecodeError:
                                    pass
            except Exception as exc:
                log.warning("SSE connection error (attempt %d): %s", attempts + 1, exc)
                if self._closed:
                    return
                attempts += 1
                if attempts > self._max_reconnect_attempts:
                    break
                await asyncio.sleep(min(delay, self._max_reconnect_delay))
                delay = min(delay * 2, self._max_reconnect_delay)

    async def close(self) -> None:
        """Close the connection and release resources."""
        self._closed = True

    def _parse_sse_line(self, line: str) -> tuple[str, str] | None:
        """Parse a single SSE line into (field, value). Returns None for comments/empty."""
        if not line or line.startswith(":"):
            return None
        colon_pos = line.find(":")
        if colon_pos == -1:
            return (line.strip(), "")
        field = line[:colon_pos].strip()
        value = line[colon_pos + 1 :]
        if value.startswith(" "):
            value = value[1:]
        return (field, value)


# ─────────────────────────────────────────────────────────────
# Wire helpers
# ─────────────────────────────────────────────────────────────

_GLOBAL_FORWARD_TYPES = frozenset(
    {"RUN_STARTED", "RUN_COMPLETED", "RUN_FAILED", "RUN_CANCELLED", "HITL_PROMPT", "QUOTA_WARNING"}
)


def hook_event_broker_publish(event_broker: Any) -> None:
    """Hook EventBroker.publish() to also forward terminal events to
    GlobalEventBroker. Call once from web/server.py on app startup.
    """
    original_publish = event_broker.publish

    def patched_publish(run_id: str, event: dict[str, Any]) -> int:
        result = original_publish(run_id, event)
        event_type = event.get("type", "")
        if event_type in _GLOBAL_FORWARD_TYPES:
            import time

            get_global_broker().publish(
                {
                    "type": event_type,
                    "run_id": run_id,
                    "timestamp": event.get("timestamp", time.time()),
                }
            )
        return result

    event_broker.publish = patched_publish


def add_routes(app: web.Application) -> None:
    """Register /api/global/events/stream on the aiohttp app.

    Note: /api/events/stream is already registered in web/routes.py via events_stream.
    This adds a separate GlobalEventBroker-backed stream endpoint.
    """
    app.router.add_get("/api/global/events/stream", global_sse_handler)
