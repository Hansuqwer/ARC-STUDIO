"""Native capability entry-gate for ARC Mobile Runtime (Phase 11).

Deterministic enablement gate for native capabilities. A capability is *eligible* only when
ALL of these hold (default = DENIED):
  1. its feature flag is ON (default OFF) and the global kill switch is OFF,
  2. a valid signed plan is presented (HMAC verified),
  3. a valid, unexpired, matching approval grant exists,
  4. a compliance artifact is present.

CRITICAL SAFETY INVARIANT: even when a capability is eligible, this build **always routes
to fixtures** (`route == "fixtures"`). Flipping execution to real device APIs is deliberately
out of scope and human-gated — it is not implemented here. The gate proves the enforcement
logic without enabling any real camera/microphone/contacts/calendar/photos/location access.
No LLM, no network.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .approval import get_grant
from .feature_flags import FeatureFlags
from .signing import SignedPlanEnvelope, verify_plan

# The only route this build will ever use. Real-device routing is intentionally absent.
FIXTURES_ROUTE = "fixtures"

_GATE_AUDIT_LOG = Path.home() / ".arc" / "mobile" / "gate_decisions.jsonl"
_log = logging.getLogger(__name__)


def _append_gate_audit(capability_id: str, decision: "GateDecision") -> None:
    """Append a gate decision entry to the audit log (gate 6: deterministic, non-blocking)."""
    try:
        _GATE_AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "capability_id": capability_id,
            "eligible": decision.eligible,
            "route": decision.route,
            "missing": decision.missing,
            "reason": decision.reason,
            "simulator_preview": decision.simulator_preview,
            "logged_at": datetime.now(timezone.utc).isoformat(),
        }
        with _GATE_AUDIT_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry) + "\n")
    except Exception as exc:  # noqa: BLE001
        _log.debug("Gate audit append failed (non-fatal): %s", exc)


@dataclass
class GateDecision:
    """The deterministic verdict of the capability entry-gate."""

    capability_id: str
    eligible: bool
    route: str  # always FIXTURES_ROUTE in this build
    missing: list[str] = field(default_factory=list)
    reason: str = ""
    simulator_preview: bool = True

    def as_dict(self) -> dict[str, Any]:
        return {
            "capability_id": self.capability_id,
            "eligible": self.eligible,
            "route": self.route,
            "missing": self.missing,
            "reason": self.reason,
            "simulator_preview": self.simulator_preview,
        }


class CapabilityEntryGate:
    """Enforces the native-capability entry criteria. Default-denied, fixtures-only."""

    def __init__(
        self, flags: FeatureFlags, signing_key: bytes, flag_prefix: str = "native."
    ) -> None:
        self.flags = flags
        self._key = signing_key
        self.flag_prefix = flag_prefix

    def flag_name(self, capability_id: str) -> str:
        return f"{self.flag_prefix}{capability_id}"

    def evaluate(
        self,
        capability_id: str,
        *,
        signed_plan: SignedPlanEnvelope | None = None,
        grant_id: str | None = None,
        compliance_present: bool = False,
    ) -> GateDecision:
        missing: list[str] = []

        # 1. feature flag ON + kill switch OFF (FeatureFlags.is_enabled already honours the kill switch)
        if not self.flags.is_enabled(self.flag_name(capability_id)):
            missing.append("feature_flag_off_or_kill_switch_engaged")

        # 2. valid signed plan
        if signed_plan is None or not verify_plan(signed_plan, self._key):
            missing.append("signed_plan_invalid")

        # 3. valid, unexpired, matching approval grant
        grant = get_grant(grant_id) if grant_id else None
        if grant is None or not grant.is_valid() or grant.capability_id != capability_id:
            missing.append("approval_grant_invalid")

        # 4. compliance artifact present
        if not compliance_present:
            missing.append("compliance_artifact_missing")

        eligible = not missing
        reason = (
            "all native entry-gate criteria met (still routed to fixtures in this build)"
            if eligible
            else "native capability denied: " + ", ".join(missing)
        )
        # Route is fixtures regardless of eligibility — real device access is not implemented.
        return GateDecision(capability_id, eligible, FIXTURES_ROUTE, missing, reason)

    def execute(self, capability_id: str, **kwargs: Any) -> dict[str, Any]:
        """Always returns a fixtures route descriptor. Even an eligible capability does NOT
        reach real device APIs in this build — that flip is human-gated and out of scope.

        Gate 6 (security): appends a deterministic audit entry to the decisions log on every
        execute call, whether eligible or denied.
        """
        decision = self.evaluate(capability_id, **kwargs)
        result = {
            "capability_id": capability_id,
            "route": FIXTURES_ROUTE,  # never real device
            "eligible": decision.eligible,
            "executed_real_device": False,
            "decision": decision.as_dict(),
        }
        # Append to decisions audit log (gate 6: audit on every execute)
        _append_gate_audit(capability_id, decision)
        return result
