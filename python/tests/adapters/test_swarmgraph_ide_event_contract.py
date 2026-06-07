"""CR-016: lock the SwarmGraph SDK-event → IDE-insight event-type contract.

The vendored SwarmGraph SDK emits ``SwarmGraphEvent``s; the adapter's
``_map_swarmgraph_event`` translates them to ARC ``RunEvent``s that the IDE
persists and renders. The IDE's ``buildSwarmGraphInsight``
(swarmgraph-insight-model.ts ``isInsightEvent``) matches insight panels by the
*lowercased* marker ``swarmgraph_topology`` / ``swarmgraph_consensus``.

If the adapter's emitted event ``type`` is renamed, the IDE topology/consensus
panels silently fall back to a degraded state. These tests fail closed on that
cross-language drift, and assert producer-truth: a non-insight SDK event must
NOT masquerade as a topology/consensus insight.
"""

from __future__ import annotations

from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter
from swarmgraph import SwarmGraphEvent, SwarmGraphEventKind

# Markers the IDE's isInsightEvent() accepts (lowercased event.type / data.kind).
_IDE_TOPOLOGY_MARKER = "swarmgraph_topology"
_IDE_CONSENSUS_MARKER = "swarmgraph_consensus"


def _map(kind: SwarmGraphEventKind, data: dict | None = None):
    adapter = SwarmGraphAdapter()
    evt = SwarmGraphEvent(kind=kind, swarm_id="s1", data=data or {})
    return adapter._map_swarmgraph_event(evt, run_id="r1", sequence=0)


def test_topology_event_matches_ide_marker():
    events = _map(SwarmGraphEventKind.topology, {"nodes": [], "edges": []})
    assert events, "topology SDK event must produce a RunEvent"
    assert events[0].type.lower() == _IDE_TOPOLOGY_MARKER


def test_consensus_event_matches_ide_marker():
    events = _map(SwarmGraphEventKind.consensus, {"decision": "approve"})
    assert events
    assert events[0].type.lower() == _IDE_CONSENSUS_MARKER


def test_non_insight_event_does_not_masquerade_as_insight():
    # producer-truth: a worker event must not surface as topology/consensus,
    # so the IDE keeps those panels degraded until real insight events arrive.
    events = _map(SwarmGraphEventKind.worker, {"worker_id": "w1"})
    assert events
    markers = {e.type.lower() for e in events}
    assert _IDE_TOPOLOGY_MARKER not in markers
    assert _IDE_CONSENSUS_MARKER not in markers
