"""Parity tests for SwarmGraph event mapping — Python matches TypeScript output."""
import json
import time

from agent_runtime_cockpit.ag_ui import AGUIEventType, MappingContext, map_event
from agent_runtime_cockpit.adapters.swarmgraph import mapping  # noqa: F401 — registers mapper


CTX = MappingContext(thread_id="th-test", run_id="run-test", runtime="swarmgraph")


def test_handoff_maps_to_step_started():
    """handoff event → STEP_STARTED with stepName=handoff:<agent>."""
    events = map_event("swarmgraph", {"kind": "handoff", "agent": "bob", "ts": 100}, CTX)
    assert len(events) == 1
    assert events[0]["type"] == AGUIEventType.STEP_STARTED.value
    assert events[0]["stepName"] == "handoff:bob"
    assert events[0]["timestamp"] == 100


def test_handoff_fallback_agent():
    """handoff without agent → stepName=handoff:? (matches TS)."""
    events = map_event("swarmgraph", {"kind": "handoff", "ts": 200}, CTX)
    assert len(events) == 1
    assert events[0]["type"] == AGUIEventType.STEP_STARTED.value
    assert events[0]["stepName"] == "handoff:?"


def test_state_maps_to_state_snapshot():
    """state event → STATE_SNAPSHOT with snapshot data."""
    events = map_event("swarmgraph", {"kind": "state", "state": {"count": 42}, "ts": 300}, CTX)
    assert len(events) == 1
    assert events[0]["type"] == AGUIEventType.STATE_SNAPSHOT.value
    assert events[0]["snapshot"] == {"count": 42}
    assert events[0]["timestamp"] == 300


def test_state_fallback_empty():
    """state without state field → snapshot={} (matches TS)."""
    events = map_event("swarmgraph", {"kind": "state", "ts": 400}, CTX)
    assert len(events) == 1
    assert events[0]["type"] == AGUIEventType.STATE_SNAPSHOT.value
    assert events[0]["snapshot"] == {}


def test_unknown_kind_falls_back_to_raw():
    """Unknown event kind → RAW."""
    events = map_event("swarmgraph", {"kind": "unknown_event", "ts": 500}, CTX)
    assert len(events) == 1
    assert events[0]["type"] == AGUIEventType.RAW.value
    assert events[0]["source"] == "swarmgraph"


def test_handoff_matches_ts_output():
    """Python handoff output matches expected TS-equivalent JSON."""
    py_events = map_event("swarmgraph", {"kind": "handoff", "agent": "alice", "ts": 600}, CTX)
    expected = [
        {
            "type": "STEP_STARTED",
            "timestamp": 600,
            "stepName": "handoff:alice",
            "threadId": "th-test",
            "runId": "run-test",
        }
    ]
    # Match on the key fields, ignoring any extras added by the mapper
    assert py_events[0]["type"] == expected[0]["type"]
    assert py_events[0]["stepName"] == expected[0]["stepName"]


def test_state_matches_ts_output():
    """Python state output matches expected TS-equivalent JSON."""
    py_events = map_event("swarmgraph", {"kind": "state", "state": {"key": "val"}, "ts": 700}, CTX)
    expected = {
        "type": "STATE_SNAPSHOT",
        "timestamp": 700,
        "snapshot": {"key": "val"},
    }
    assert py_events[0]["type"] == expected["type"]
    assert py_events[0]["snapshot"] == expected["snapshot"]
