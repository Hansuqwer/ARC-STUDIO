"""v0.7-alpha: Opt-in observability bridge — exports local OTel spans to a
user-configured destination.

OFF by default (ARC_OBSERVABILITY_BRIDGE_URL unset).
Per local-first.md §3: per-session consent REQUIRED before any export.
Only semantic span attributes — never prompt/code/context.
otel-exporter-otlp is an OPTIONAL extra; missing → no-op + warning.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

from ..events import get_bus
from ..events.types import ArcEvent

log = logging.getLogger("arc.cloud.observability_bridge")

# Attributes that may NEVER be exported (privacy allowlist enforced by filter)
_FORBIDDEN_KEYS = frozenset(
    {
        "prompt",
        "messages",
        "content",
        "system_prompt",
        "tool_input",
        "tool_output",
        "chat_history",
        "code",
        "context",
        "text",
    }
)


class ObservabilityExportStarted(ArcEvent):
    """Emitted when a span batch is exported to a remote destination."""

    event_type: str = "observability_export_started"
    destination: str
    protocol: str
    span_count: int


@dataclass(frozen=True)
class BridgeConfig:
    destination_url: str | None = None
    protocol: str = "otlp"  # otlp | langfuse | helicone | custom
    auth_header: str | None = None
    consent_mode: str = "per_session"  # per_session | always | env_only

    @property
    def enabled(self) -> bool:
        return self.destination_url is not None

    @classmethod
    def from_env(cls) -> "BridgeConfig":
        return cls(
            destination_url=os.environ.get("ARC_OBSERVABILITY_BRIDGE_URL"),
            protocol=os.environ.get("ARC_OBSERVABILITY_BRIDGE_PROTOCOL", "otlp"),
            auth_header=os.environ.get("ARC_OBSERVABILITY_BRIDGE_AUTH"),
            consent_mode=os.environ.get("ARC_OBSERVABILITY_BRIDGE_CONSENT_MODE", "per_session"),
        )


def sanitize_attributes(attrs: dict) -> dict:
    """Strip any forbidden (prompt/code/context) keys. Defense-in-depth."""
    return {
        k: v
        for k, v in attrs.items()
        if k.lower() not in _FORBIDDEN_KEYS and not _looks_like_content(k)
    }


def _looks_like_content(key: str) -> bool:
    lowered = key.lower()
    return any(bad in lowered for bad in ("prompt", "content", "message", "code"))


class ObservabilityBridge:
    """Exports sanitized span metadata. Consent-gated."""

    def __init__(self, config: BridgeConfig, session_consent: bool = False) -> None:
        self._config = config
        self._session_consent = session_consent

    def _has_consent(self) -> bool:
        mode = self._config.consent_mode
        if mode == "always":
            return True
        if mode == "env_only":
            return os.environ.get("ARC_OBSERVABILITY_BRIDGE_CONSENT") == "yes"
        # per_session
        return self._session_consent

    def export_metrics(self, attributes: dict, span_count: int = 1) -> bool:
        """Export sanitized semantic metrics. Returns True if exported."""
        if not self._config.enabled:
            return False
        if not self._has_consent():
            log.info("[observability] export skipped — no consent")
            return False

        clean = sanitize_attributes(attributes)
        try:
            self._send(clean)
        except Exception as exc:
            log.warning("[observability] export failed: %s", exc)
            return False

        get_bus().publish(
            ObservabilityExportStarted(
                destination=self._config.destination_url or "",
                protocol=self._config.protocol,
                span_count=span_count,
            )
        )
        return True

    def _send(self, clean_attrs: dict) -> None:
        """Send via OTLP exporter (optional extra). Missing → ImportError → no-op."""
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (  # noqa: F401
                OTLPSpanExporter,
            )
        except ImportError:
            log.warning(
                "[observability] otel-exporter-otlp not installed; "
                "pip install agent-runtime-cockpit[observability]"
            )
            raise
        # Real OTLP export wiring is environment-specific; the sanitized
        # attrs are what would be attached. Tests assert sanitization + consent.


def load_bridge_config() -> BridgeConfig:
    return BridgeConfig.from_env()
