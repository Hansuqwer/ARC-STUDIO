"""v0.7-alpha: Opt-in shared budget broker for team mode.

OFF by default (requires ARC_BUDGET_BROKER_URL + TOKEN + TEAM_ID).
Fail-closed pattern (same as capability_gates 1aa2da5):
  - broker unreachable + fallback_to_local=True  → approve locally
  - broker unreachable + fallback_to_local=False → DENY (explicit)
No LLM in path (CoSAI). No prompt/code data sent — only scope + amount.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
from dataclasses import dataclass
from decimal import Decimal

from ..events import get_bus
from ..events.types import ArcEvent

log = logging.getLogger("arc.cloud.budget_broker")


class BudgetBrokerSync(ArcEvent):
    """Emitted after a remote broker preflight check."""

    event_type: str = "budget_broker_sync"
    scope: str
    amount_usd: float
    local_approved: bool
    remote_approved: bool
    fell_back: bool


@dataclass(frozen=True)
class BrokerConfig:
    broker_url: str | None = None
    auth_token: str | None = None
    team_id: str | None = None
    fallback_to_local: bool = True
    timeout_seconds: int = 5

    @property
    def enabled(self) -> bool:
        return bool(self.broker_url and self.auth_token and self.team_id)

    @classmethod
    def from_env(cls) -> "BrokerConfig":
        return cls(
            broker_url=os.environ.get("ARC_BUDGET_BROKER_URL"),
            auth_token=os.environ.get("ARC_BUDGET_BROKER_TOKEN"),
            team_id=os.environ.get("ARC_BUDGET_TEAM_ID"),
            fallback_to_local=os.environ.get("ARC_BUDGET_BROKER_FALLBACK", "1") != "0",
        )


@dataclass
class BrokerCheckResult:
    approved: bool
    fell_back: bool
    remote_remaining: Decimal | None = None
    reason: str | None = None


class BudgetBrokerClient:
    """Shared team budget. Queries remote cap; falls back per config."""

    def __init__(self, config: BrokerConfig) -> None:
        self._config = config

    def remote_preflight(self, scope: str, amount: Decimal) -> BrokerCheckResult:
        if not self._config.enabled:
            return BrokerCheckResult(approved=True, fell_back=True, reason="broker_disabled")
        try:
            body = json.dumps(
                {
                    "team_id": self._config.team_id,
                    "scope": scope,
                    "amount": str(amount),
                }
            ).encode()
            req = urllib.request.Request(
                f"{self._config.broker_url.rstrip('/')}/preflight",
                data=body,
                headers={
                    "Authorization": f"Bearer {self._config.auth_token}",
                    "Content-Type": "application/json",
                    "User-Agent": "ARC-Studio/v0.7 budget-broker",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._config.timeout_seconds) as resp:
                result = json.loads(resp.read())
            approved = bool(result.get("approved", False))
            remaining = Decimal(str(result.get("remaining", "0")))
            self._emit(scope, amount, True, approved, False)
            return BrokerCheckResult(approved=approved, fell_back=False, remote_remaining=remaining)
        except Exception as exc:
            log.warning("[budget_broker] unreachable: %s", exc)
            if self._config.fallback_to_local:
                self._emit(scope, amount, True, True, True)
                return BrokerCheckResult(
                    approved=True,
                    fell_back=True,
                    reason=f"broker_unreachable: {type(exc).__name__}",
                )
            # fail-closed: no fallback → DENY
            return BrokerCheckResult(
                approved=False, fell_back=False, reason="broker_unreachable_no_fallback"
            )

    def _emit(
        self, scope: str, amount: Decimal, local: bool, remote: bool, fell_back: bool
    ) -> None:
        get_bus().publish(
            BudgetBrokerSync(
                scope=scope,
                amount_usd=float(amount),
                local_approved=local,
                remote_approved=remote,
                fell_back=fell_back,
            )
        )


def load_broker_config() -> BrokerConfig:
    return BrokerConfig.from_env()
