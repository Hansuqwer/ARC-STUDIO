"""Webhook delivery with HMAC signing, retry, and dead-letter log (Phase 32 / R25).

Stores configs in ``.arc/events/webhooks.json``.
Dead-letter entries in ``.arc/events/dead-letter.jsonl``.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import stat
from pathlib import Path
from typing import Optional

from ..security.redaction import Redactor
from .bus import EventBus, get_bus
from .models import DeadLetterEntry, WebhookConfig
from .types import ArcEvent

_redactor = Redactor()

log = logging.getLogger(__name__)

DEFAULT_CONFIG_DIR = Path(".arc") / "events"
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "webhooks.json"
DEFAULT_DEAD_LETTER_PATH = DEFAULT_CONFIG_DIR / "dead-letter.jsonl"

RETRY_DELAY_CAP = 60.0
HTTP_TIMEOUT = 5.0


def sign_payload(payload: bytes, secret: str) -> str:
    """HMAC-SHA256 signature in X-ARC-Signature header format."""
    return hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()


def verify_signature(payload: bytes, secret: str, signature: str) -> bool:
    """Verify HMAC-SHA256 signature."""
    expected = sign_payload(payload, secret)
    return hmac.compare_digest(expected, signature)


class WebhookManager:
    """Manages webhook configs, subscribes to event bus, delivers payloads.

    :param config_path: Path to webhooks JSON config file.
    :param dead_letter_path: Path to dead-letter JSONL file.
    :param bus: EventBus instance (default: module-level singleton).
    """

    def __init__(
        self,
        config_path: Path = DEFAULT_CONFIG_PATH,
        dead_letter_path: Path = DEFAULT_DEAD_LETTER_PATH,
        bus: Optional[EventBus] = None,
    ) -> None:
        self._config_path = config_path
        self._dead_letter_path = dead_letter_path
        self._bus = bus or get_bus()
        self._configs: list[WebhookConfig] = []
        self._load_configs()

    # ------------------------------------------------------------------
    # Config CRUD
    # ------------------------------------------------------------------

    def _load_configs(self) -> None:
        if self._config_path.exists():
            try:
                raw = json.loads(self._config_path.read_text())
                self._configs = [WebhookConfig(**c) for c in raw]
            except Exception as e:
                log.warning("Failed to load webhook configs: %s", e)
                self._configs = []

    def _save_configs(self) -> None:
        self._config_path.parent.mkdir(parents=True, exist_ok=True)
        data = [c.model_dump() for c in self._configs]
        self._config_path.write_text(json.dumps(data, indent=2))
        # Restrict permissions
        try:
            self._config_path.chmod(stat.S_IRUSR | stat.S_IWUSR)
        except Exception:
            pass

    def add(self, config: WebhookConfig) -> WebhookConfig:
        self._configs.append(config)
        self._save_configs()
        return config

    def list(self) -> list[WebhookConfig]:
        return list(self._configs)

    def remove(self, webhook_id: str) -> bool:
        before = len(self._configs)
        self._configs = [c for c in self._configs if c.id != webhook_id]
        if len(self._configs) < before:
            self._save_configs()
            return True
        return False

    def get(self, webhook_id: str) -> Optional[WebhookConfig]:
        for c in self._configs:
            if c.id == webhook_id:
                return c
        return None

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    def _should_deliver(self, config: WebhookConfig, event_type: str) -> bool:
        if "*" in config.enabled_events:
            return True
        return event_type in config.enabled_events

    async def deliver(self, config: WebhookConfig, event: ArcEvent) -> None:
        """Deliver a single event to a webhook with retry and dead-letter on failure."""
        payload_dict = event.model_dump()
        payload_bytes = json.dumps(payload_dict).encode("utf-8")
        signature = sign_payload(payload_bytes, config.secret)

        for attempt in range(config.retry_max):
            try:
                import httpx

                async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                    resp = await client.post(
                        config.url,
                        content=payload_bytes,
                        headers={
                            "Content-Type": "application/json",
                            "X-ARC-Signature": signature,
                            "X-ARC-Event-Type": event.event_type,
                        },
                    )
                    resp.raise_for_status()
                log.info(
                    "Webhook %s delivered %s (attempt %d)", config.id, event.event_type, attempt + 1
                )
                return
            except Exception as e:
                log.warning(
                    "Webhook %s delivery attempt %d failed: %s",
                    config.id,
                    attempt + 1,
                    e,
                )
                if attempt < config.retry_max - 1:
                    delay = min(
                        RETRY_DELAY_CAP,
                        config.retry_base_delay_s * (2**attempt),
                    )
                    await asyncio.sleep(delay)

        # All retries exhausted — dead letter (Phase 52: redact payload, add attempt_count)
        redacted_payload = _redactor.redact_dict(payload_dict)
        self._write_dead_letter(
            DeadLetterEntry(
                webhook_id=config.id,
                url=config.url,
                event_type=event.event_type,
                payload=redacted_payload,
                error=f"Failed after {config.retry_max} attempts",
                attempt_count=config.retry_max,
            )
        )

    def _write_dead_letter(self, entry: DeadLetterEntry) -> None:
        try:
            self._dead_letter_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._dead_letter_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry.model_dump(), sort_keys=True) + "\n")
        except Exception as e:
            log.error("Failed to write dead-letter entry: %s", e)

    def read_dead_letter(self, limit: int = 100) -> list[DeadLetterEntry]:
        if not self._dead_letter_path.exists():
            return []
        entries: list[DeadLetterEntry] = []
        try:
            with open(self._dead_letter_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entries.append(DeadLetterEntry(**json.loads(line)))
                    except Exception:
                        continue
                    if len(entries) >= limit:
                        break
        except Exception as e:
            log.warning("Failed to read dead-letter log: %s", e)
        return entries

    # ------------------------------------------------------------------
    # Event bus subscription
    # ------------------------------------------------------------------

    def start_delivery(self) -> None:
        """Subscribe to all event bus events and deliver to matching webhooks."""
        self._bus.subscribe_all(self._on_event)

    def stop_delivery(self) -> None:
        self._bus.unsubscribe_all(self._on_event)

    def _on_event(self, event: ArcEvent) -> None:
        for config in self._configs:
            if self._should_deliver(config, event.event_type):
                asyncio.ensure_future(self.deliver(config, event))
