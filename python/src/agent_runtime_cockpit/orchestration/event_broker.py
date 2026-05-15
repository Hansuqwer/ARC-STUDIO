"""
EventBroker — in-memory event pub/sub with SSE delivery (PR 19).

Uses bounded ``asyncio.Queue`` per subscriber with a documented
slow-client policy (drop-oldest when queue is full). No external
SSE dependency — delivers via ``aiohttp.web.StreamResponse``.
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, AsyncIterator, Optional

from aiohttp import web

from ..storage.jsonl import JsonlTraceStore

log = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 15.0
QUEUE_MAX_SIZE = 1000


class EventBroker:
    """In-memory event broker with SSE delivery.

    Supports live streaming (from active runs) and replay (from stored traces).
    Handles heartbeat and reconnection via Last-Event-ID.
    """

    def __init__(self, store: JsonlTraceStore) -> None:
        self.store = store
        self._subscribers: dict[str, list[asyncio.Queue[Optional[dict[str, Any]]]]] = {}
        self._event_ids: dict[str, int] = {}

    def publish(self, run_id: str, event: dict[str, Any]) -> int:
        """Publish an event to all subscribers of a run. Returns event ID."""
        event_id = self._event_ids.get(run_id, 0) + 1
        self._event_ids[run_id] = event_id
        event_with_id = {**event, "event_id": event_id}
        for queue in self._subscribers.get(run_id, []):
            try:
                queue.put_nowait(event_with_id)
            except asyncio.QueueFull:
                # Slow-client policy: drop oldest event, then push new one.
                try:
                    queue.get_nowait()
                    queue.put_nowait(event_with_id)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
        return event_id

    def subscribe(self, run_id: str) -> asyncio.Queue[Optional[dict[str, Any]]]:
        """Subscribe to events for a run. Queue receives ``None`` when the run ends."""
        queue: asyncio.Queue[Optional[dict[str, Any]]] = asyncio.Queue(maxsize=QUEUE_MAX_SIZE)
        self._subscribers.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        """Remove a subscriber queue."""
        subs = self._subscribers.get(run_id, [])
        if queue in subs:
            subs.remove(queue)

    def end_run(self, run_id: str) -> None:
        """Signal end of run to all subscribers."""
        for queue in self._subscribers.pop(run_id, []):
            queue.put_nowait(None)

    async def stream_live(
        self, run_id: str, last_event_id: int = 0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield live events for an active run, optionally replaying missed events."""
        if last_event_id > 0:
            async for event in self._replay_from(run_id, last_event_id):
                yield event
        queue = self.subscribe(run_id)
        try:
            while True:
                event = await queue.get()
                if event is None:
                    break
                yield event
        finally:
            self.unsubscribe(run_id, queue)

    async def _replay_from(
        self, run_id: str, from_event_id: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay missed events from stored trace."""
        trace_path = self.store.trace_path(run_id)
        if not trace_path.exists():
            return
        with open(trace_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    eid = event.get("event_id", 0)
                    if eid > from_event_id:
                        yield event
                except json.JSONDecodeError:
                    continue

    async def _replay_stored(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        """Replay all events from stored trace."""
        trace_path = self.store.trace_path(run_id)
        if not trace_path.exists():
            return
        with open(trace_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue

    async def sse_handler(self, request: web.Request) -> web.StreamResponse:
        """HTTP handler for SSE event streaming with heartbeat.

        Query params:
          - ``mode``: ``"live"`` (subscribe to active run) or ``"replay"`` (default)
          - ``last_event_id``: for reconnection

        Header ``Last-Event-ID`` is respected for reconnection.
        """
        run_id = request.match_info["run_id"]
        mode = request.query.get("mode", "replay")
        last_event_id = int(request.headers.get("Last-Event-ID", "0"))

        response = web.StreamResponse(headers={
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
        })
        await response.prepare(request)

        try:
            heartbeat_task = asyncio.create_task(
                self._send_heartbeats(response), name=f"heartbeat-{run_id}",
            )
            try:
                if mode == "live":
                    stream = self.stream_live(run_id, last_event_id)
                else:
                    stream = self._replay_stored(run_id)
                async for event in stream:
                    event_id = event.get("event_id")
                    event_type = event.get("type", "message")
                    payload = json.dumps(event, default=str)
                    # SSE format: event + data + optional id
                    lines = []
                    if event_type:
                        lines.append(f"event: {event_type}")
                    if event_id is not None:
                        lines.append(f"id: {event_id}")
                    lines.append(f"data: {payload}")
                    await response.write(("\n".join(lines) + "\n\n").encode())

                await response.write(
                    b"event: stream_end\ndata: "
                    b'{"type": "STREAM_END"}\n\n'
                )
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
        except asyncio.CancelledError:
            log.info("SSE stream cancelled for run %s", run_id)
            raise
        except Exception as e:
            log.error("SSE stream error for run %s: %s", run_id, e)
            await response.write(
                f"event: stream_error\ndata: "
                f'{json.dumps({"type": "STREAM_ERROR", "error": str(e)})}\n\n'
                .encode()
            )
        return response

    @staticmethod
    async def _send_heartbeats(response: web.StreamResponse) -> None:
        """Send periodic heartbeat comments to keep the connection alive."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                await response.write(b": heartbeat\n\n")
        except asyncio.CancelledError:
            pass
