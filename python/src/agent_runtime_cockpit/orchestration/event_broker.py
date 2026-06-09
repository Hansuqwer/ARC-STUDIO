"""EventBroker — in-memory event pub/sub with SSE delivery (PR 19).

Uses a ring buffer for replay on reconnection and bounded
``asyncio.Queue`` per subscriber with a documented slow-client
policy (drop-oldest when queue is full). No external SSE
dependency — delivers via ``aiohttp.web.StreamResponse``.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator, Optional

from aiohttp import web

from ..storage.jsonl import JsonlTraceStore

log = logging.getLogger(__name__)

HEARTBEAT_INTERVAL = 15.0
QUEUE_MAX_SIZE = 1000
RING_BUFFER_SIZE = 1000
TERMINAL_EVENT_TYPES = {"RUN_COMPLETED", "RUN_FAILED", "RUN_CANCELLED"}
DEGRADED_EVENT_TYPE = "STREAM_DEGRADED"


class RingBuffer:
    """Fixed-size ring buffer for replay on SSE reconnection.

    Maintains the last N events per run. Oldest events are overwritten
    when the buffer is full.
    """

    def __init__(self, max_size: int = RING_BUFFER_SIZE) -> None:
        self._max_size = max_size
        self._buffer: list[dict[str, Any]] = []
        self._start = 0

    def push(self, event: dict[str, Any]) -> None:
        if len(self._buffer) < self._max_size:
            self._buffer.append(event)
        else:
            self._buffer[self._start % self._max_size] = event
            self._start += 1

    def replay_from(self, from_event_id: int) -> list[dict[str, Any]]:
        """Return all events with event_id > from_event_id, in chronological order."""
        if not self._buffer:
            return []
        return sorted(
            [e for e in self._buffer if e.get("event_id", 0) > from_event_id],
            key=lambda e: e.get("event_id", 0),
        )

    def clear(self) -> None:
        self._buffer.clear()
        self._start = 0


class EventBroker:
    """In-memory event broker with SSE delivery.

    Supports live streaming (from active runs) and replay (from stored traces).
    Handles heartbeat and reconnection via Last-Event-ID with a ring buffer.
    """

    def __init__(self, store: JsonlTraceStore) -> None:
        self.store = store
        self._subscribers: dict[str, list[asyncio.Queue[Optional[dict[str, Any]]]]] = {}
        self._event_ids: dict[str, int] = {}
        self._active_runs: set[str] = set()
        self._ring_buffers: dict[str, RingBuffer] = {}

    def _ring_buffer_for(self, run_id: str) -> RingBuffer:
        return self._ring_buffers.setdefault(run_id, RingBuffer(RING_BUFFER_SIZE))

    def mark_active(self, run_id: str) -> None:
        """Mark a run as actively publishing live events."""
        self._active_runs.add(run_id)

    def mark_inactive(self, run_id: str) -> None:
        """Mark a run as no longer actively publishing live events."""
        self._active_runs.discard(run_id)

    def is_active(self, run_id: str) -> bool:
        """Return whether this broker has a live producer for the run."""
        return run_id in self._active_runs

    def publish(self, run_id: str, event: dict[str, Any]) -> int:
        """Publish an event to all subscribers of a run. Returns event ID."""
        event_id = self._event_ids.get(run_id, 0) + 1
        self._event_ids[run_id] = event_id
        event_with_id = {**event, "event_id": event_id}
        self._ring_buffer_for(run_id).push(event_with_id)
        for queue in self._subscribers.get(run_id, []):
            try:
                queue.put_nowait(event_with_id)
            except asyncio.QueueFull:
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
        self.mark_inactive(run_id)
        for queue in self._subscribers.pop(run_id, []):
            queue.put_nowait(None)

    def degraded_event(self, run_id: str, reason: str) -> dict[str, Any]:
        """Create a structured degraded/disconnected live-stream event."""
        return {
            "type": DEGRADED_EVENT_TYPE,
            "run_id": run_id,
            "data": {
                "state": "disconnected",
                "reason": reason,
            },
        }

    async def stream_live(
        self,
        run_id: str,
        last_event_id: int = 0,
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield live events for an active run, replaying missed events from ring buffer."""
        if last_event_id > 0:
            for event in self._ring_buffer_for(run_id).replay_from(last_event_id):
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
        self,
        run_id: str,
        from_event_id: int,
    ) -> AsyncIterator[dict[str, Any]]:
        """Replay missed events from stored trace."""
        async for event in self._iter_trace_events(run_id):
            eid = event.get("event_id", 0)
            if eid > from_event_id:
                yield event

    async def _replay_stored(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        """Replay all events from stored trace."""
        async for event in self._iter_trace_events(run_id):
            yield event

    async def _iter_trace_events(self, run_id: str) -> AsyncIterator[dict[str, Any]]:
        """Yield events from either event-per-line JSONL or stored RunRecord JSONL.

        R-PERF6: Uses mmap for files > 10 MB to avoid loading the entire trace
        into memory. This enables 1 GB trace < 5s on local SSD.
        """
        import mmap

        trace_path = self.store.trace_path(run_id)
        if not trace_path.exists():
            return

        file_size = trace_path.stat().st_size
        USE_MMAP_THRESHOLD = 10 * 1024 * 1024  # 10 MB

        if file_size > USE_MMAP_THRESHOLD:
            # Memory-mapped read for large files
            with open(trace_path, "rb") as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    pos = 0
                    while pos < mm.size():
                        end = mm.find(b"\n", pos)
                        if end == -1:
                            end = mm.size()
                        raw = mm[pos:end]
                        pos = end + 1
                        if not raw.strip():
                            continue
                        try:
                            item = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        events = item.get("events")
                        if isinstance(events, list):
                            for index, event in enumerate(events, start=1):
                                if isinstance(event, dict):
                                    event.setdefault("event_id", index)
                                    yield event
                            continue
                        yield item
        else:
            with open(trace_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        item = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    events = item.get("events")
                    if isinstance(events, list):
                        for index, event in enumerate(events, start=1):
                            if isinstance(event, dict):
                                event.setdefault("event_id", index)
                                yield event
                        continue
                    yield item

    async def sse_handler(self, request: web.Request) -> web.StreamResponse:
        """HTTP handler for SSE event streaming with heartbeat.

        Query params:
          - ``mode``: ``"live"`` (subscribe to active run) or ``"replay"`` (default)
          - ``last_event_id``: for reconnection

        Header ``Last-Event-ID`` is respected for reconnection.
        """
        run_id = request.match_info["run_id"]
        mode = request.query.get("mode", "replay")
        last_event_id = int(
            request.query.get("last_event_id") or request.headers.get("Last-Event-ID", "0"),
        )

        response = web.StreamResponse(
            headers={
                "Content-Type": "text/event-stream",
                "Cache-Control": "no-cache",
            }
        )
        await response.prepare(request)

        try:
            heartbeat_task = asyncio.create_task(
                self._send_heartbeats(response),
                name=f"heartbeat-{run_id}",
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
                    if mode == "live" and event_type in TERMINAL_EVENT_TYPES:
                        break

                await response.write(
                    f"event: stream_end\ndata: "
                    f"{json.dumps({'type': 'STREAM_END', 'mode': mode})}\n\n".encode()
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
        except ConnectionResetError:
            log.info("SSE client disconnected for run %s", run_id)
        except Exception as e:
            log.error("SSE stream error for run %s: %s", run_id, e)
            try:
                await response.write(
                    f"event: stream_error\ndata: "
                    f"{json.dumps({'type': 'STREAM_ERROR', 'error': str(e)})}\n\n".encode()
                )
            except ConnectionResetError:
                log.info("SSE client disconnected while reporting error for run %s", run_id)
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
