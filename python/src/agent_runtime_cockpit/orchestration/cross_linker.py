"""
CrossLinker — indexes graph events by stable ID for cross-referencing.

Maintains per-run in-memory indexes of events keyed by ``node_id``,
``message_id``, ``tool_call_id``, and ``evidence_refs``. Queries return
ordered lists of linked events forming chains.
"""
from __future__ import annotations

from ..protocol.schemas import RunEvent

LINK_FIELDS = frozenset({"node_id", "message_id", "tool_call_id", "evidence_refs"})


class CrossLinker:
    """In-memory cross-reference index for a single run.

    Usage::

        linker = CrossLinker()
        linker.index(event)
        chain = linker.get_node_chain(node_id)
    """

    def __init__(self) -> None:
        self._all_events: list[RunEvent] = []
        self._by_node_id: dict[str, list[RunEvent]] = {}
        self._by_message_id: dict[str, list[RunEvent]] = {}
        self._by_tool_call_id: dict[str, list[RunEvent]] = {}
        self._by_evidence_ref: dict[str, list[RunEvent]] = {}

    def index(self, event: RunEvent) -> None:
        """Index a single event by its stable ID fields."""
        self._all_events.append(event)
        data = event.data or {}
        if node_id := data.get("node_id"):
            self._by_node_id.setdefault(node_id, []).append(event)
        if message_id := data.get("message_id"):
            self._by_message_id.setdefault(message_id, []).append(event)
        if tool_call_id := data.get("tool_call_id"):
            self._by_tool_call_id.setdefault(tool_call_id, []).append(event)
        evidence_refs = data.get("evidence_refs")
        if evidence_refs and isinstance(evidence_refs, list):
            for ref in evidence_refs:
                if isinstance(ref, dict):
                    ev_id = ref.get("evidence_id") or ref.get("target", "")
                elif isinstance(ref, str):
                    ev_id = ref
                else:
                    continue
                if ev_id:
                    self._by_evidence_ref.setdefault(ev_id, []).append(event)

    def get_node_chain(self, node_id: str) -> list[RunEvent]:
        """Return all events linked to a node in sequence order."""
        return sorted(
            self._by_node_id.get(node_id, []),
            key=lambda e: e.sequence,
        )

    def get_message_chain(self, message_id: str) -> list[RunEvent]:
        """Return all events linked to a message."""
        return sorted(
            self._by_message_id.get(message_id, []),
            key=lambda e: e.sequence,
        )

    def get_tool_call_chain(self, tool_call_id: str) -> list[RunEvent]:
        """Return all events linked to a tool call."""
        return sorted(
            self._by_tool_call_id.get(tool_call_id, []),
            key=lambda e: e.sequence,
        )

    def get_evidence_events(self, evidence_id: str) -> list[RunEvent]:
        """Return all events referencing a given evidence ID."""
        return sorted(
            self._by_evidence_ref.get(evidence_id, []),
            key=lambda e: e.sequence,
        )

    def get_run_event_ids(self) -> list[str]:
        """Return set of all distinct stable IDs across indexed events."""
        ids: set[str] = set()
        ids.update(self._by_node_id.keys())
        ids.update(self._by_message_id.keys())
        ids.update(self._by_tool_call_id.keys())
        ids.update(self._by_evidence_ref.keys())
        return sorted(ids)

    def get_linked_events(self, stable_id: str) -> list[RunEvent]:
        """Return all events linked to *any* stable ID field."""
        for lookup in (
            self._by_node_id,
            self._by_message_id,
            self._by_tool_call_id,
            self._by_evidence_ref,
        ):
            if stable_id in lookup:
                return sorted(lookup[stable_id], key=lambda e: e.sequence)
        return []

    def get_ids(self, field: str) -> list[str]:
        """Return stable IDs for a supported link field."""
        lookups = {
            "node_id": self._by_node_id,
            "message_id": self._by_message_id,
            "tool_call_id": self._by_tool_call_id,
            "evidence_id": self._by_evidence_ref,
        }
        return sorted(lookups.get(field, {}).keys())

    def has_stable_ids(self) -> bool:
        """True if any event in this run has stable ID fields."""
        return bool(self._by_node_id or self._by_message_id or self._by_tool_call_id or self._by_evidence_ref)

    def index_all(self, events: list[RunEvent]) -> None:
        """Index multiple events at once."""
        for event in events:
            self.index(event)
