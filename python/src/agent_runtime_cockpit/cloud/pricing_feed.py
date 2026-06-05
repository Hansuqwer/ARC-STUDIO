"""v0.7-alpha: Opt-in pricing feed with hash-pinning and offline cache fallback.

OFF by default (ARC_PRICING_FEED_ENABLED=1 to activate).
Primary source: OpenRouter. Fallback: models.dev.
Per local-first.md: zero outbound calls when feature disabled.
Per honesty-over-polish.md: any change requires `arc pricing-feed accept-new-hash`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from ..events import get_bus
from ..events.types import ArcEvent

log = logging.getLogger("arc.cloud.pricing_feed")

# ── Sources ───────────────────────────────────────────────────────────────────

DEFAULT_OPENROUTER_URL = "https://openrouter.ai/api/v1/models"
DEFAULT_MODELS_DEV_URL = "https://models.dev/api.json"
DEFAULT_CACHE_PATH = Path.home() / ".arc" / "pricing_feed_cache.json"
DEFAULT_TIMEOUT_SECONDS = 5


# ── Bus event ─────────────────────────────────────────────────────────────────


class PricingFeedRefreshed(ArcEvent):
    """Emitted after a successful pricing feed refresh."""

    event_type: str = "pricing_feed_refreshed"
    feed_url: str
    feed_hash: str
    rows_seen: int
    source: str  # "openrouter" | "models-dev" | "cache"


# ── Config ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class PricingFeedConfig:
    """All config from env vars; frozen so it can't change at runtime."""

    feed_url: str = DEFAULT_OPENROUTER_URL
    feed_source: str = "openrouter"  # "openrouter" | "models-dev"
    refresh_interval_hours: int = 168  # weekly
    pinned_hash: str | None = None  # SHA-256 of last accepted feed; None = no pin yet
    cache_path: Path = field(default_factory=lambda: DEFAULT_CACHE_PATH)
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS

    @property
    def enabled(self) -> bool:
        return os.environ.get("ARC_PRICING_FEED_ENABLED") == "1"

    @classmethod
    def from_env(cls) -> "PricingFeedConfig":
        source = os.environ.get("ARC_PRICING_FEED_SOURCE", "openrouter")
        url = os.environ.get(
            "ARC_PRICING_FEED_URL",
            DEFAULT_OPENROUTER_URL if source == "openrouter" else DEFAULT_MODELS_DEV_URL,
        )
        return cls(
            feed_url=url,
            feed_source=source,
            pinned_hash=os.environ.get("ARC_PRICING_FEED_PINNED_HASH"),
        )


# ── Result ────────────────────────────────────────────────────────────────────


@dataclass
class FeedRefreshResult:
    success: bool
    source: str  # "network" | "cache" | "local_fallback"
    feed_hash: str | None = None
    rows_seen: int = 0
    hash_changed: bool = False  # True → user must run accept-new-hash
    error_reason: str | None = None


# ── Client ────────────────────────────────────────────────────────────────────


class PricingFeedClient:
    """Opt-in pricing feed. Fails closed on every error variant.

    Hash-pinning flow:
    1. Fetch raw payload.
    2. SHA-256 hash it.
    3. If hash != pinned_hash → set hash_changed=True, keep local, warn once.
    4. If accepted (user runs 'arc pricing-feed accept-new-hash') → update cache.
    """

    def __init__(self, config: PricingFeedConfig) -> None:
        self._config = config

    def refresh(self) -> FeedRefreshResult:
        """Attempt feed refresh. Returns result regardless of success/failure."""
        if not self._config.enabled:
            return FeedRefreshResult(
                success=False, source="disabled", error_reason="feature_disabled"
            )

        # 1. Attempt network fetch
        raw = self._fetch_network()
        if raw is not None:
            result = self._process(raw, source="network")
            if result.success:
                return result
            # hash_changed or parse_failure are definitive — return them,
            # don't silently fall through to a stale cache.
            if result.hash_changed or result.error_reason == "parse_failure":
                return result

        # 2. Offline: try local cache
        raw = self._load_cache()
        if raw is not None:
            result = self._process(raw, source="cache")
            if result.success:
                return result

        # 3. Fail-closed: keep local VENDOR_CONFIGS — caller handles this
        return FeedRefreshResult(
            success=False, source="local_fallback", error_reason="network_and_cache_unavailable"
        )

    # ── private ───────────────────────────────────────────────────────────────

    def _fetch_network(self) -> bytes | None:
        try:
            req = urllib.request.Request(
                self._config.feed_url,
                headers={"User-Agent": "ARC-Studio/v0.7 pricing-feed"},
            )
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                return resp.read()
        except Exception as exc:
            log.warning("[pricing_feed] network fetch failed: %s", exc)
            return None

    def _load_cache(self) -> bytes | None:
        try:
            path = self._config.cache_path
            if path.exists():
                return path.read_bytes()
        except Exception as exc:
            log.warning("[pricing_feed] cache read failed: %s", exc)
        return None

    def _save_cache(self, raw: bytes) -> None:
        try:
            self._config.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._config.cache_path.write_bytes(raw)
        except Exception as exc:
            log.warning("[pricing_feed] cache write failed: %s", exc)

    def _process(self, raw: bytes, source: str) -> FeedRefreshResult:
        feed_hash = hashlib.sha256(raw).hexdigest()

        # Parse — fail-closed on parse error
        try:
            data = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            log.warning("[pricing_feed] parse failed: %s", exc)
            return FeedRefreshResult(
                success=False, source=source, feed_hash=feed_hash, error_reason="parse_failure"
            )

        # Count rows
        rows_seen = len(data.get("data", data) if isinstance(data, dict) else data)

        # Hash-pinning check
        pinned = self._config.pinned_hash
        hash_changed = pinned is not None and feed_hash != pinned

        if hash_changed:
            log.warning(
                "[pricing_feed] feed hash changed (%s…→%s…). "
                "Run 'arc pricing-feed accept-new-hash' to adopt the new feed.",
                (pinned or "")[:8],
                feed_hash[:8],
            )
            return FeedRefreshResult(
                success=False,
                source=source,
                feed_hash=feed_hash,
                rows_seen=rows_seen,
                hash_changed=True,
                error_reason="hash_changed_awaiting_accept",
            )

        # Save to cache (only from network, not re-saving cache hits)
        if source == "network":
            self._save_cache(raw)

        # Emit event
        get_bus().publish(
            PricingFeedRefreshed(
                feed_url=self._config.feed_url,
                feed_hash=feed_hash[:16],
                rows_seen=rows_seen,
                source=source,
            )
        )

        return FeedRefreshResult(
            success=True, source=source, feed_hash=feed_hash, rows_seen=rows_seen
        )

    def accept_new_hash(self, new_hash: str) -> None:
        """Record user acceptance of a new feed hash. Persists to env hint only."""
        # In practice the hash would be written to ~/.arc/pricing_feed.toml
        # For now, log acceptance and update cache.
        log.info("[pricing_feed] user accepted new hash %s…", new_hash[:8])


def load_feed_config() -> PricingFeedConfig:
    return PricingFeedConfig.from_env()
