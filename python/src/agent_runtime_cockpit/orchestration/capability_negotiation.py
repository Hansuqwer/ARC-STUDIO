"""
CapabilityNegotiation — pure-function capability matching for runtime selection.

Determines whether a set of ``RuntimeCapabilities`` satisfies a requested
capability profile. Pure function with no network or side effects.
"""
from __future__ import annotations

from typing import Any

from ..protocol.capabilities import RuntimeCapabilities


class CapabilityNegotiation:
    """Pure-function capability matching for runtime selection."""

    @staticmethod
    def satisfies(
        capabilities: RuntimeCapabilities,
        required: dict[str, Any],
    ) -> tuple[bool, list[str]]:
        """Check if *capabilities* satisfy *required* profile.

        Returns ``(satisfied, reasons)`` where *reasons* lists any
        missing or mismatched capabilities.
        """
        reasons: list[str] = []
        for key, expected_value in required.items():
            actual = getattr(capabilities, key, None)
            if actual is None:
                reasons.append(f"Capability '{key}' not found on RuntimeCapabilities")
                continue
            if isinstance(expected_value, bool):
                if actual is True and expected_value is not True:
                    continue
                if actual is False and expected_value is True:
                    reasons.append(
                        f"Runtime lacks required capability '{key}' "
                        f"(expected {expected_value}, got {actual})"
                    )
            elif isinstance(expected_value, str):
                if actual != expected_value:
                    reasons.append(
                        f"Capability '{key}' mismatch: "
                        f"expected {expected_value!r}, got {actual!r}"
                    )
            elif isinstance(expected_value, (list, set)):
                if expected_value and not any(
                    v in actual for v in expected_value
                ):
                    reasons.append(
                        f"Runtime does not support any of "
                        f"required execution modes: {expected_value}"
                    )
            else:
                if actual != expected_value:
                    reasons.append(
                        f"Capability '{key}' mismatch: "
                        f"expected {expected_value}, got {actual}"
                    )
        return len(reasons) == 0, reasons

    @staticmethod
    def best_match(
        candidates: list[tuple[str, RuntimeCapabilities]],
        required: dict[str, Any],
    ) -> tuple[str | None, list[str]]:
        """Find the best matching runtime from *candidates*.

        Returns ``(runtime_id, reasons)``. If no candidate fully satisfies,
        the first with the most matched capabilities is returned with
        the reasons for each failure.
        """
        best_id: str | None = None
        best_reasons: list[str] = []
        best_score = -1

        for runtime_id, caps in candidates:
            satisfied, reasons = CapabilityNegotiation.satisfies(caps, required)
            matched = len(required) - len(reasons)
            if satisfied:
                return runtime_id, []
            if matched > best_score:
                best_id = runtime_id
                best_reasons = reasons
                best_score = matched

        return best_id, best_reasons

    @staticmethod
    def cockpit_primitive_profile(
        emit_contract: bool = False,
        emit_receipt: bool = False,
        emit_autopsy: bool = False,
        emit_evidence: bool = False,
        require_stable_ids: bool = False,
    ) -> dict[str, Any]:
        """Build a required profile dict for cockpit primitives."""
        profile: dict[str, Any] = {}
        if emit_contract:
            profile["can_emit_contract"] = True
        if emit_receipt:
            profile["can_emit_receipt"] = True
        if emit_autopsy:
            profile["can_emit_autopsy"] = True
        if emit_evidence:
            profile["can_emit_evidence"] = True
        if require_stable_ids:
            profile["has_stable_ids"] = True
        return profile
