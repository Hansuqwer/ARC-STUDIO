"""In-memory event bus with typed publish/subscribe (Phase 32 / R25).

Bounded async queue per subscriber, ring buffer for --since replay.
Fire-and-forget publish — never blocks the producer.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

from .types import ArcEvent

log = logging.getLogger(__name__)

Handler = Callable[[ArcEvent], None]
AsyncHandler = Callable[[ArcEvent], "asyncio.Future[None]"]

RING_BUFFER_SIZE = 100
QUEUE_MAX_SIZE = 100


class EventBus:
    """In-process event bus with typed publish/subscribe.

    Producers call ``publish(event)`` to emit events.
    Consumers call ``subscribe(event_type, handler)`` or use ``stream()``.

    Bounded async queues with drop-oldest when full.
    Optional ring buffer (last N=100 events) for --since replay on connect.
    """

    def __init__(
        self, maxsize: int = QUEUE_MAX_SIZE, ring_buffer_size: int = RING_BUFFER_SIZE
    ) -> None:
        self._maxsize = maxsize
        self._ring_buffer_size = ring_buffer_size
        self._ring_buffer: list[ArcEvent] = []
        self._ring_start = 0
        self._handlers: dict[str, list[Handler]] = {}
        self._async_queues: dict[str, list[asyncio.Queue[Optional[ArcEvent]]]] = {}
        self._drain_handlers: list[Handler] = []

    def publish(self, event: ArcEvent) -> None:
        """Publish an event to all matching subscribers. Fire-and-forget."""
        self._push_ring(event)
        et = event.event_type
        for handler in self._handlers.get(et, []):
            try:
                handler(event)
            except Exception:
                log.warning("Handler failed for event %s", et, exc_info=True)
        for handler in self._drain_handlers:
            try:
                handler(event)
            except Exception:
                log.warning("Drain handler failed for event %s", et, exc_info=True)
        for queue in self._async_queues.get(et, []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
        for queue in self._async_queues.get("*", []):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(event)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    def subscribe(self, event_type: str, handler: Handler) -> None:
        """Subscribe a sync handler to a specific event type."""
        self._handlers.setdefault(event_type, []).append(handler)

    def subscribe_all(self, handler: Handler) -> None:
        """Subscribe a sync handler to ALL event types."""
        self._drain_handlers.append(handler)

    def unsubscribe(self, event_type: str, handler: Handler) -> None:
        """Remove a sync handler from a specific event type."""
        handlers = self._handlers.get(event_type, [])
        if handler in handlers:
            handlers.remove(handler)

    def unsubscribe_all(self, handler: Handler) -> None:
        """Remove a sync handler from all-event drain."""
        if handler in self._drain_handlers:
            self._drain_handlers.remove(handler)

    def stream(
        self,
        event_type: str = "*",
        since_index: int = 0,
    ) -> asyncio.Queue[Optional[ArcEvent]]:
        """Create an async queue subscriber.

        Returns a queue that receives events of the given type
        (or all types if ``*``). ``None`` is sent when the stream ends.

        If ``since_index > 0``, replays events from the ring buffer first.
        """
        replay = self._replay_since(since_index) if since_index > 0 else []
        queue: asyncio.Queue[Optional[ArcEvent]] = asyncio.Queue(maxsize=self._maxsize)
        for ev in replay:
            try:
                queue.put_nowait(ev)
            except asyncio.QueueFull:
                break
        self._async_queues.setdefault(event_type, []).append(queue)
        return queue

    def close_stream(self, event_type: str, queue: asyncio.Queue[Optional[ArcEvent]]) -> None:
        """Remove and terminate a stream queue."""
        queues = self._async_queues.get(event_type, [])
        if queue in queues:
            queues.remove(queue)
            queue.put_nowait(None)

    def close_all(self) -> None:
        """Terminate all streams."""
        for et, queues in self._async_queues.items():
            for q in queues:
                q.put_nowait(None)
        self._async_queues.clear()

    def _push_ring(self, event: ArcEvent) -> None:
        if len(self._ring_buffer) < self._ring_buffer_size:
            self._ring_buffer.append(event)
        else:
            idx = self._ring_start % self._ring_buffer_size
            self._ring_buffer[idx] = event
            self._ring_start += 1

    def _replay_since(self, index: int) -> list[ArcEvent]:
        if not self._ring_buffer:
            return []
        if index >= len(self._ring_buffer):
            return []
        return self._ring_buffer[index:]


# Module-level singleton
_bus: Optional[EventBus] = None


def get_bus() -> EventBus:
    global _bus
    if _bus is None:
        _bus = EventBus()
    return _bus


def reset_bus() -> None:
    global _bus
    if _bus is not None:
        _bus.close_all()
    _bus = None


def set_bus(bus: EventBus) -> EventBus:
    global _bus
    _bus = bus
    return _bus
