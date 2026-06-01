"""Phase 109 / R25 — Event-Driven Audit/HITL Notification Hooks.

Provides a ``NotificationHook`` protocol and concrete implementations:

- ``WebhookNotificationHook``: POSTs events as JSON to an HTTP endpoint.
  Uses ``urllib`` (stdlib-only, no hard dependency). Falls back silently
  on connection errors; errors are logged, never re-raised.

- ``EventBrokerNotificationHook``: Forwards events to the ARC EventBroker
  when the integration gate ``ARC_SWARMGRAPH_EVENTBROKER=1`` is set.
  Import is deferred to avoid coupling swarmgraph-sdk to ARC internals in
  default (non-ARC) use.

Both are optional extensions — ``SwarmGraphRunner.notification_hooks`` is
empty by default and adding a hook has no effect on the core run contract.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncIterator, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from .events import SwarmGraphEvent

log = logging.getLogger(__name__)

DEFAULT_NOTIFICATION_CONFIG = Path(".arc") / "swarmgraph" / "notifications.json"
DEFAULT_NOTIFICATION_OUTBOX = Path(".arc") / "swarmgraph" / "notification-outbox.jsonl"
NOTIFICATION_CONFIG_ENV = "ARC_SWARMGRAPH_NOTIFICATION_CONFIG"


class NotificationHook(Protocol):
    """Protocol for async notification hooks wired into SwarmGraphRunner.

    Each hook is called once per emitted event. Errors must be caught
    internally; a hook must never propagate exceptions to the runner.
    """

    async def notify(self, event: SwarmGraphEvent) -> None: ...


class WebhookTargetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(default_factory=lambda: f"swarm-wh-{uuid.uuid4().hex[:12]}")
    url: str = Field(..., min_length=1)
    enabled_events: list[str] = Field(default_factory=lambda: ["*"])
    timeout_seconds: float = Field(default=5.0, ge=0.1, le=60)
    headers: dict[str, str] = Field(default_factory=dict)
    max_attempts: int = Field(default=3, ge=1, le=10)

    def matches(self, event_kind: str) -> bool:
        return "*" in self.enabled_events or event_kind in self.enabled_events


class NotificationConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    targets: list[WebhookTargetConfig] = Field(default_factory=list)
    outbox_path: str = Field(default=str(DEFAULT_NOTIFICATION_OUTBOX))

    @classmethod
    def load(cls, path: str | Path = DEFAULT_NOTIFICATION_CONFIG) -> NotificationConfig:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(raw)

    def target_by_id(self, target_id: str) -> WebhookTargetConfig | None:
        for target in self.targets:
            if target.id == target_id:
                return target
        return None


class NotificationDeliveryRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    target_id: str
    event_kind: str
    event: dict[str, Any]
    status: Literal["pending", "delivered", "failed", "abandoned"]
    attempt: int = Field(default=1, ge=1)
    error: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationServiceConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    enabled: bool = True
    interval_seconds: float = Field(default=5.0, ge=0.01, le=3600)
    max_batch: int = Field(default=100, ge=1, le=10000)


class NotificationServiceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    processed: int = Field(default=0, ge=0)
    delivered: int = Field(default=0, ge=0)
    failed: int = Field(default=0, ge=0)
    abandoned: int = Field(default=0, ge=0)


class NotificationServiceStatus(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    state: Literal["idle", "running", "stopped"]
    enabled: bool
    outbox_path: str


class DurableNotificationOutbox:
    """Append-only JSONL outbox for best-effort durable notification delivery."""

    def __init__(self, path: str | Path = DEFAULT_NOTIFICATION_OUTBOX) -> None:
        self.path = Path(path)

    def append(self, record: NotificationDeliveryRecord) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(record.model_dump_json() + "\n")

    def read(self, limit: int = 1000) -> list[NotificationDeliveryRecord]:
        if not self.path.exists():
            return []
        records: list[NotificationDeliveryRecord] = []
        with self.path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(NotificationDeliveryRecord.model_validate_json(line))
                except Exception:
                    log.warning("Skipping malformed notification outbox record")
                if len(records) >= limit:
                    break
        return records

    def outstanding(self) -> list[NotificationDeliveryRecord]:
        latest: dict[str, NotificationDeliveryRecord] = {}
        for record in self.read():
            latest[record.id] = record
        return [record for record in latest.values() if record.status in {"pending", "failed"}]


class WebhookNotificationHook:
    """POST each SwarmGraphEvent as JSON to a configurable HTTP endpoint.

    Uses only the Python standard library (``urllib.request``) so there is
    no additional dependency. Runs the network call in a thread to avoid
    blocking the event loop. On any error the exception is logged and
    swallowed — a broken sink must never interrupt the swarm run.

    Args:
        url:     Full HTTP/HTTPS URL to POST to.
        timeout: Request timeout in seconds (default 5).
        headers: Extra HTTP headers (e.g. auth tokens). Merged with the
                 default ``Content-Type: application/json`` header.
    """

    def __init__(
        self,
        url: str,
        timeout: float = 5.0,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.url = url
        self.timeout = timeout
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if headers:
            self._headers.update(headers)

    async def notify(self, event: SwarmGraphEvent) -> None:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._post_sync, event.to_dict())

    def _post_sync(self, payload: dict[str, Any]) -> bool:
        import urllib.request

        data = json.dumps(payload, default=str).encode()
        req = urllib.request.Request(
            self.url,
            data=data,
            headers=self._headers,
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout):
                pass
            return True
        except Exception as exc:
            log.warning("WebhookNotificationHook POST failed: %s", exc)
            return False


class DurableWebhookNotificationHook:
    """Configured webhook hook with append-only durable outbox and retry support."""

    def __init__(
        self,
        config: NotificationConfig,
        outbox: DurableNotificationOutbox | None = None,
    ) -> None:
        self.config = config
        self.outbox = outbox or DurableNotificationOutbox(config.outbox_path)

    @classmethod
    def from_file(
        cls,
        path: str | Path = DEFAULT_NOTIFICATION_CONFIG,
    ) -> DurableWebhookNotificationHook:
        return cls(NotificationConfig.load(path))

    @classmethod
    def from_env(cls) -> DurableWebhookNotificationHook | None:
        path = os.environ.get(NOTIFICATION_CONFIG_ENV)
        if not path:
            return None
        try:
            return cls.from_file(path)
        except Exception as exc:
            log.warning("Failed to load SwarmGraph notification config: %s", exc)
            return None

    async def notify(self, event: SwarmGraphEvent) -> None:
        event_kind = event.kind.value
        payload = event.to_dict()
        for target in self.config.targets:
            if target.matches(event_kind):
                delivery_id = f"swarm-delivery-{uuid.uuid4().hex[:12]}"
                await self._deliver_once(delivery_id, target, payload, event_kind, attempt=1)

    async def retry_outstanding_once(self) -> int:
        retried = 0
        for record in self.outbox.outstanding():
            target = self.config.target_by_id(record.target_id)
            if target is None:
                continue
            next_attempt = record.attempt + 1
            if next_attempt > target.max_attempts:
                self.outbox.append(
                    record.model_copy(
                        update={
                            "status": "abandoned",
                            "attempt": record.attempt,
                            "error": "max attempts exhausted",
                            "created_at": datetime.now(timezone.utc),
                        }
                    )
                )
                continue
            await self._deliver_once(
                record.id,
                target,
                record.event,
                record.event_kind,
                attempt=next_attempt,
            )
            retried += 1
        return retried

    async def _deliver_once(
        self,
        delivery_id: str,
        target: WebhookTargetConfig,
        payload: dict[str, Any],
        event_kind: str,
        attempt: int,
    ) -> None:
        pending = NotificationDeliveryRecord(
            id=delivery_id,
            target_id=target.id,
            event_kind=event_kind,
            event=payload,
            status="pending",
            attempt=attempt,
        )
        self.outbox.append(pending)
        loop = asyncio.get_running_loop()
        ok = await loop.run_in_executor(None, self._post_sync, target, payload)
        self.outbox.append(
            pending.model_copy(
                update={
                    "status": "delivered" if ok else "failed",
                    "error": None if ok else "webhook delivery failed",
                    "created_at": datetime.now(timezone.utc),
                }
            )
        )

    def _post_sync(self, target: WebhookTargetConfig, payload: dict[str, Any]) -> bool:
        headers = {"Content-Type": "application/json"}
        headers.update(target.headers)
        return WebhookNotificationHook(
            target.url,
            timeout=target.timeout_seconds,
            headers=headers,
        )._post_sync(payload)


class ManagedNotificationService:
    """Lifecycle-managed retry loop for durable SwarmGraph webhook outbox records."""

    def __init__(
        self,
        hook: DurableWebhookNotificationHook,
        config: NotificationServiceConfig | None = None,
    ) -> None:
        self.hook = hook
        self.config = config or NotificationServiceConfig()
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> NotificationServiceStatus:
        if self.running:
            state: Literal["idle", "running", "stopped"] = "running"
        elif self._stop.is_set():
            state = "stopped"
        else:
            state = "idle"
        return NotificationServiceStatus(
            state=state,
            enabled=self.config.enabled,
            outbox_path=str(self.hook.outbox.path),
        )

    async def start(self) -> NotificationServiceStatus:
        if not self.config.enabled:
            return self.status()
        if self.running:
            return self.status()
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="swarmgraph-notification-service")
        return self.status()

    async def stop(self) -> NotificationServiceStatus:
        self._stop.set()
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        return self.status()

    async def flush_once(self) -> NotificationServiceResult:
        processed = delivered = failed = abandoned = 0
        for record in self.hook.outbox.outstanding()[: self.config.max_batch]:
            target = self.hook.config.target_by_id(record.target_id)
            if target is None:
                continue
            next_attempt = record.attempt + 1
            if next_attempt > target.max_attempts:
                self.hook.outbox.append(
                    record.model_copy(
                        update={
                            "status": "abandoned",
                            "error": "max attempts exhausted",
                            "created_at": datetime.now(timezone.utc),
                        }
                    )
                )
                processed += 1
                abandoned += 1
                continue
            before = len(self.hook.outbox.read())
            try:
                await self.hook._deliver_once(
                    record.id,
                    target,
                    record.event,
                    record.event_kind,
                    attempt=next_attempt,
                )
            except Exception as exc:
                log.warning("ManagedNotificationService delivery failed: %s", exc)
                self.hook.outbox.append(
                    record.model_copy(
                        update={
                            "status": "failed",
                            "attempt": next_attempt,
                            "error": str(exc),
                            "created_at": datetime.now(timezone.utc),
                        }
                    )
                )
            after_records = self.hook.outbox.read()
            processed += 1
            new_records = after_records[before:]
            if any(item.status == "delivered" for item in new_records):
                delivered += 1
            else:
                failed += 1
        return NotificationServiceResult(
            processed=processed,
            delivered=delivered,
            failed=failed,
            abandoned=abandoned,
        )

    async def _run(self) -> None:
        try:
            while not self._stop.is_set():
                await self.flush_once()
                await asyncio.sleep(self.config.interval_seconds)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log.warning("ManagedNotificationService stopped after error: %s", exc)


class SwarmGraphEventBroadcaster:
    """In-memory bounded fanout for server-side SwarmGraph push hooks."""

    def __init__(self, queue_size: int = 1000) -> None:
        self.queue_size = queue_size
        self._subscribers: dict[str, list[asyncio.Queue[dict[str, Any] | None]]] = {}

    def subscribe(self, swarm_id: str) -> asyncio.Queue[dict[str, Any] | None]:
        queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=self.queue_size)
        self._subscribers.setdefault(swarm_id, []).append(queue)
        return queue

    def unsubscribe(self, swarm_id: str, queue: asyncio.Queue[dict[str, Any] | None]) -> None:
        subscribers = self._subscribers.get(swarm_id, [])
        if queue in subscribers:
            subscribers.remove(queue)
        if not subscribers:
            self._subscribers.pop(swarm_id, None)

    async def publish(self, event: SwarmGraphEvent) -> None:
        payload = event.to_dict()
        for queue in list(self._subscribers.get(event.swarm_id, [])):
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(payload)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    async def close(self, swarm_id: str) -> None:
        for queue in self._subscribers.pop(swarm_id, []):
            try:
                queue.put_nowait(None)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(None)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass

    async def stream(self, swarm_id: str) -> AsyncIterator[dict[str, Any]]:
        queue = self.subscribe(swarm_id)
        try:
            while True:
                payload = await queue.get()
                if payload is None:
                    break
                yield payload
        finally:
            self.unsubscribe(swarm_id, queue)


class PushNotificationHook:
    """Notification hook that forwards SwarmGraph events to an in-memory broadcaster."""

    def __init__(self, broadcaster: SwarmGraphEventBroadcaster) -> None:
        self.broadcaster = broadcaster

    async def notify(self, event: SwarmGraphEvent) -> None:
        await self.broadcaster.publish(event)


class EventBrokerNotificationHook:
    """Forward SwarmGraphEvents to the ARC EventBroker.

    Gated behind ``ARC_SWARMGRAPH_EVENTBROKER=1`` to avoid coupling
    swarmgraph-sdk to ARC internals in standalone use. The broker is
    imported lazily at first use so tests that don't set the env var
    never touch ARC code.

    Args:
        broker: Optional pre-constructed EventBroker instance. When None
                the hook defers to the ARC runtime default broker.
    """

    def __init__(self, broker: Any = None) -> None:
        self._broker = broker

    def _gate_enabled(self) -> bool:
        return os.environ.get("ARC_SWARMGRAPH_EVENTBROKER", "0") == "1"

    async def notify(self, event: SwarmGraphEvent) -> None:
        if not self._gate_enabled():
            return
        try:
            broker = self._broker or self._get_default_broker()
            if broker is None:
                return
            payload = event.to_dict()
            # EventBroker.publish accepts (event_type, data) — use the
            # swarm event kind as the type so the IDE can filter by kind.
            await broker.publish("swarmgraph_event", payload)
        except Exception as exc:
            log.warning("EventBrokerNotificationHook failed: %s", exc)

    def _get_default_broker(self) -> Any:
        try:
            from agent_runtime_cockpit.orchestration.event_broker import EventBroker  # type: ignore[import-not-found]

            return EventBroker.get_default()
        except Exception:
            return None


__all__ = [
    "DurableNotificationOutbox",
    "DurableWebhookNotificationHook",
    "EventBrokerNotificationHook",
    "ManagedNotificationService",
    "NotificationConfig",
    "NotificationDeliveryRecord",
    "NotificationServiceConfig",
    "NotificationServiceResult",
    "NotificationServiceStatus",
    "NotificationHook",
    "PushNotificationHook",
    "SwarmGraphEventBroadcaster",
    "WebhookNotificationHook",
    "WebhookTargetConfig",
]
