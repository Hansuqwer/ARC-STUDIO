"""Token-aware adaptive consensus early-stop (moonshot #2, first slice).

Pure, deterministic decision helper — no LLM, no I/O, no provider calls.

When a SwarmGraph consensus node dispatches N workers one at a time, the
outcome is often mathematically settled before all N have voted:

- **Settled PASS**: ``approved >= required`` — enough approvals already;
  remaining workers cannot change a majority/quorum decision.
- **Settled FAIL**: ``approved + remaining < required`` — the required approval
  count is now unreachable even if every remaining worker approves.

In either case the orchestrator can skip the remaining ``total - voted``
workers, saving ``(total - voted) / total`` of the per-worker model cost.

This module is the foundational primitive. Wiring it into the worker-dispatch
loop (which lives in the separately-versioned swarmgraph SDK) is a later slice;
this slice ships the decision logic + tests so the math is pinned and reusable.
It lives under ``evals/`` rather than ``swarmgraph/`` because the latter is a
MetaPathFinder bridge to the external SDK and cannot host new in-repo modules.

Truth: this only short-circuits **majority/quorum** style counting consensus.
Byzantine-fault-tolerant (BFT) protocols that need every vote for fault
detection MUST NOT early-stop — callers gate on protocol via
``protocol_allows_early_stop`` before using this.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

EarlyStopOutcome = Literal["settled_pass", "settled_fail", "undecided"]


@dataclass(frozen=True)
class EarlyStopDecision:
    """Result of an early-stop evaluation."""

    can_stop: bool
    outcome: EarlyStopOutcome
    voted: int  # votes counted so far (approved + rejected)
    total: int  # total workers planned
    required: int  # approvals required to pass
    workers_saved: int  # how many remaining workers can be skipped
    reason: str


def required_for_majority(total: int) -> int:
    """Approvals required for a simple majority of ``total`` workers."""
    return total // 2 + 1


def can_stop_early(
    *,
    approved: int,
    rejected: int,
    total: int,
    required: int | None = None,
) -> EarlyStopDecision:
    """Decide whether remaining consensus workers can be skipped.

    Args:
        approved: approvals counted so far.
        rejected: rejections counted so far.
        total: total number of workers planned for this consensus round.
        required: approvals required to pass. Defaults to a simple majority
            (``total // 2 + 1``).

    Returns an :class:`EarlyStopDecision`. ``can_stop`` is True only when the
    outcome is mathematically settled regardless of how the remaining workers
    vote. Never early-stops on inconsistent inputs (fail-safe → undecided).
    """
    if required is None:
        required = required_for_majority(total)

    voted = approved + rejected
    remaining = max(0, total - voted)

    # Fail-safe on inconsistent inputs: never claim a stop we can't justify.
    if (
        total <= 0
        or voted > total
        or required <= 0
        or required > total
        or approved < 0
        or rejected < 0
    ):
        return EarlyStopDecision(
            can_stop=False,
            outcome="undecided",
            voted=voted,
            total=total,
            required=required,
            workers_saved=0,
            reason="inconsistent inputs; not stopping",
        )

    # Settled PASS: enough approvals already; remaining cannot un-pass it.
    if approved >= required:
        return EarlyStopDecision(
            can_stop=True,
            outcome="settled_pass",
            voted=voted,
            total=total,
            required=required,
            workers_saved=remaining,
            reason=f"{approved} approvals >= {required} required",
        )

    # Settled FAIL: even if every remaining worker approves, required is unreachable.
    if approved + remaining < required:
        return EarlyStopDecision(
            can_stop=True,
            outcome="settled_fail",
            voted=voted,
            total=total,
            required=required,
            workers_saved=remaining,
            reason=(
                f"max reachable approvals {approved + remaining} < {required} required "
                f"({rejected} rejected)"
            ),
        )

    return EarlyStopDecision(
        can_stop=False,
        outcome="undecided",
        voted=voted,
        total=total,
        required=required,
        workers_saved=0,
        reason=f"undecided: {approved} approved, {rejected} rejected, {remaining} pending",
    )


# Protocols whose counting semantics make early-stop sound. BFT-family
# protocols need every vote for fault detection and are intentionally excluded.
EARLY_STOP_SAFE_PROTOCOLS = frozenset({"majority", "quorum"})


def protocol_allows_early_stop(protocol: str) -> bool:
    """True if a protocol's semantics permit skipping remaining workers."""
    return protocol.lower() in EARLY_STOP_SAFE_PROTOCOLS


__all__ = [
    "EarlyStopDecision",
    "EarlyStopOutcome",
    "can_stop_early",
    "required_for_majority",
    "protocol_allows_early_stop",
    "EARLY_STOP_SAFE_PROTOCOLS",
]
