"""Stable ID generation for graph cockpit linkage.

Provides ULID-based ID generators for all cockpit surfaces:
- node_id, message_id, tool_call_id, approval_id, decision_id
- evidence_id, contract_id, receipt_id, run_id, session_id

All IDs follow the format: ``{prefix}_{ulid}``.
Missing IDs degrade safely — consumers treat absent IDs as opaque.
"""

from __future__ import annotations

import re
import secrets
import time
from typing import Optional

# ---------------------------------------------------------------------------
# ULID-like generator (no external dependency — 16-char hex fallback)
# ---------------------------------------------------------------------------


def _ulid_like() -> str:
    """Generate a ULID-like string using time + randomness.

    This is NOT a strict ULID implementation; it produces sortable
    26-character strings compatible with the cockpit ID format.
    If ``ulid-py`` is available, use it instead.
    """
    try:
        from ulid import ULID

        return str(ULID())
    except ImportError:
        pass

    # Fallback: timestamp-based prefix + random suffix
    # 10 hex chars from time (sortable) + 16 hex chars random
    ts = int(time.time() * 1000)
    time_part = format(ts, "010x")[-10:]
    rand_part = secrets.token_hex(8)
    return f"01{time_part}{rand_part}"[:26]


# ---------------------------------------------------------------------------
# ID prefixes per spec §13
# ---------------------------------------------------------------------------

ID_PREFIXES = {
    "message": "msg",
    "decision": "dec",
    "approval": "apr",
    "policy_decision": "pd",
    "node": None,  # node_id uses <workflow>.<node_name> format
    "tool_call": "tc",
    "edge": None,  # edge_id uses <from>→<to> format
    "run": "run",
    "contract": "ctr",
    "receipt": "rcpt",
    "evidence": "ev",
    "session": "sess",
    "hitl": "hitl",
}

_NODE_ID_RE = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}[-_0-9][A-Za-z0-9_-]*\.[A-Za-z0-9_-]{1,64}$"
)
_EDGE_ID_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}→[A-Za-z0-9_.-]{1,128}$")


def generate_stable_id(kind: str, suffix: Optional[str] = None) -> str:
    """Generate a stable ID with the appropriate prefix.

    Args:
        kind: One of the keys in ID_PREFIXES.
        suffix: Optional suffix to append (e.g., node name for node_id).

    Returns:
        A stable ID string like ``msg_01J...`` or ``reviewer_001``.

    Raises:
        ValueError: If ``kind`` is not a recognized prefix.

    """
    if kind not in ID_PREFIXES:
        raise ValueError(f"Unknown ID kind: {kind!r}. Must be one of {list(ID_PREFIXES.keys())}")

    prefix = ID_PREFIXES[kind]

    if kind == "node":
        # node_id uses <workflow>.<node_name> format
        if suffix:
            return suffix
        return f"node_{_ulid_like()}"

    if kind == "edge":
        # edge_id uses <from>→<to> format
        if suffix:
            return suffix
        return f"edge_{_ulid_like()}"

    ulid = _ulid_like()
    return f"{prefix}_{ulid}"


def generate_node_id(workflow_id: str, node_name: str) -> str:
    """Generate a stable node_id in ``<workflow>.<node_name>`` format."""
    return f"{workflow_id}.{node_name}"


def generate_edge_id(from_node: str, to_node: str) -> str:
    """Generate a stable edge_id in ``<from>→<to>`` format."""
    return f"{from_node}→{to_node}"


def ensure_stable_id(existing_id: Optional[str], kind: str, suffix: Optional[str] = None) -> str:
    """Return existing_id if present, otherwise generate a new stable ID.

    This ensures IDs are stable across re-renders and replays.
    """
    if existing_id:
        return existing_id
    return generate_stable_id(kind, suffix)


def parse_stable_id(stable_id: str) -> tuple[str, str]:
    """Parse a stable ID into (kind, ulid) components.

    Returns:
        Tuple of (prefix, ulid_part).

    Raises:
        ValueError: If the ID format is invalid.

    """
    if "_" not in stable_id:
        raise ValueError(f"Invalid stable ID format: {stable_id!r}")
    parts = stable_id.split("_", 1)
    return parts[0], parts[1]


def is_valid_stable_id(stable_id: str) -> bool:
    """Check if a string looks like a valid stable ID."""
    if not stable_id:
        return False
    if "→" in stable_id:
        return bool(_EDGE_ID_RE.fullmatch(stable_id))
    if "." in stable_id:
        return stable_id.count(".") == 1 and bool(_NODE_ID_RE.fullmatch(stable_id))
    if "_" not in stable_id:
        return False
    prefix = stable_id.split("_", 1)[0]
    valid_prefixes = {prefix for prefix in ID_PREFIXES.values() if prefix is not None}
    return prefix in valid_prefixes or prefix in {"node", "edge"}


# ---------------------------------------------------------------------------
# Degradation manifest
# ---------------------------------------------------------------------------


class DegradationManifest:
    """Tracks which stable ID fields are missing from events.

    When a runtime does not emit stable IDs, the cockpit degrades
    gracefully: cross-linking is disabled, but the graph still renders.
    """

    def __init__(self) -> None:
        self._missing_node_ids: int = 0
        self._missing_message_ids: int = 0
        self._missing_tool_call_ids: int = 0
        self._missing_evidence_refs: int = 0
        self._total_events: int = 0

    def record_event(self, event_data: dict) -> None:
        """Record an event's stable ID presence."""
        self._total_events += 1
        if "node_id" not in event_data:
            self._missing_node_ids += 1
        if "message_id" not in event_data:
            self._missing_message_ids += 1
        if "tool_call_id" not in event_data:
            self._missing_tool_call_ids += 1
        if "evidence_refs" not in event_data:
            self._missing_evidence_refs += 1

    def is_degraded(self) -> bool:
        """True if any stable ID fields are missing from >50% of events."""
        if self._total_events == 0:
            return False
        threshold = self._total_events * 0.5
        return (
            self._missing_node_ids > threshold
            or self._missing_message_ids > threshold
            or self._missing_tool_call_ids > threshold
        )

    def get_degradation_summary(self) -> dict:
        """Return a summary of degradation status."""
        return {
            "total_events": self._total_events,
            "missing_node_ids": self._missing_node_ids,
            "missing_message_ids": self._missing_message_ids,
            "missing_tool_call_ids": self._missing_tool_call_ids,
            "missing_evidence_refs": self._missing_evidence_refs,
            "is_degraded": self.is_degraded(),
            "cross_linking_available": not self.is_degraded(),
        }

    def __repr__(self) -> str:
        return f"DegradationManifest(total={self._total_events}, degraded={self.is_degraded()})"
