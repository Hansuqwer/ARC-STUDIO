"""
Tests: CrossLinker — stable ID cross-referencing for graph events.
"""
from __future__ import annotations

from datetime import datetime, timezone

from agent_runtime_cockpit.orchestration.cross_linker import CrossLinker
from agent_runtime_cockpit.protocol.schemas import RunEvent


def _event(
    seq: int,
    event_type: str = "MESSAGE",
    node_id: str | None = None,
    message_id: str | None = None,
    tool_call_id: str | None = None,
    evidence_refs: list | None = None,
) -> RunEvent:
    data: dict = {}
    if node_id:
        data["node_id"] = node_id
    if message_id:
        data["message_id"] = message_id
    if tool_call_id:
        data["tool_call_id"] = tool_call_id
    if evidence_refs:
        data["evidence_refs"] = evidence_refs
    return RunEvent(
        type=event_type,
        timestamp=datetime.now(timezone.utc).isoformat(),
        run_id="test-run",
        sequence=seq,
        data=data,
    )


class TestCrossLinkerIndex:
    """Indexing events by stable IDs."""

    def test_index_node_id(self):
        linker = CrossLinker()
        ev = _event(0, node_id="node_01HABCDEFGHIJKLMNOPQRST")
        linker.index(ev)
        chain = linker.get_node_chain("node_01HABCDEFGHIJKLMNOPQRST")
        assert len(chain) == 1
        assert chain[0].sequence == 0

    def test_index_message_id(self):
        linker = CrossLinker()
        ev = _event(1, message_id="msg_01HABCDEFGHIJKLMNOPQRST")
        linker.index(ev)
        chain = linker.get_message_chain("msg_01HABCDEFGHIJKLMNOPQRST")
        assert len(chain) == 1

    def test_index_tool_call_id(self):
        linker = CrossLinker()
        ev = _event(2, tool_call_id="tc_01HABCDEFGHIJKLMNOPQRST")
        linker.index(ev)
        chain = linker.get_tool_call_chain("tc_01HABCDEFGHIJKLMNOPQRST")
        assert len(chain) == 1

    def test_index_evidence_refs(self):
        linker = CrossLinker()
        ev = _event(3, evidence_refs=[
            {"evidence_id": "ev_abcdefghijklmnopqrst123456"},
        ])
        linker.index(ev)
        chain = linker.get_evidence_events("ev_abcdefghijklmnopqrst123456")
        assert len(chain) == 1

    def test_index_evidence_refs_string(self):
        linker = CrossLinker()
        ev = _event(4, evidence_refs=["ev_abcdefghijklmnopqrst123456"])
        linker.index(ev)
        chain = linker.get_evidence_events("ev_abcdefghijklmnopqrst123456")
        assert len(chain) == 1

    def test_index_multiple_events_same_node(self):
        linker = CrossLinker()
        nid = "node_01HABCDEFGHIJKLMNOPQRST"
        for i in range(3):
            linker.index(_event(i, node_id=nid))
        chain = linker.get_node_chain(nid)
        assert len(chain) == 3
        assert chain[0].sequence == 0
        assert chain[2].sequence == 2


class TestCrossLinkerQueries:
    """Query methods."""

    def test_get_linked_events_node(self):
        linker = CrossLinker()
        ev = _event(0, node_id="node_01HABCDEFGHIJKLMNOPQRST")
        linker.index(ev)
        events = linker.get_linked_events("node_01HABCDEFGHIJKLMNOPQRST")
        assert len(events) == 1

    def test_get_linked_events_message(self):
        linker = CrossLinker()
        ev = _event(0, message_id="msg_01HABCDEFGHIJKLMNOPQRST")
        linker.index(ev)
        events = linker.get_linked_events("msg_01HABCDEFGHIJKLMNOPQRST")
        assert len(events) == 1

    def test_get_linked_events_not_found(self):
        linker = CrossLinker()
        events = linker.get_linked_events("nonexistent_id")
        assert events == []

    def test_get_run_event_ids(self):
        linker = CrossLinker()
        linker.index(_event(0, node_id="n1"))
        linker.index(_event(1, message_id="m1"))
        linker.index(_event(2, tool_call_id="t1"))
        ids = linker.get_run_event_ids()
        assert "n1" in ids
        assert "m1" in ids
        assert "t1" in ids

    def test_has_stable_ids_true(self):
        linker = CrossLinker()
        assert linker.has_stable_ids() is False
        linker.index(_event(0, node_id="n1"))
        assert linker.has_stable_ids() is True

    def test_has_stable_ids_false(self):
        linker = CrossLinker()
        ev = _event(0)
        ev.data = {}
        linker.index(ev)
        assert linker.has_stable_ids() is False


class TestCrossLinkerIndexAll:
    """Batch indexing."""

    def test_index_all(self):
        linker = CrossLinker()
        events = [
            _event(0, node_id="n1"),
            _event(1, message_id="m1"),
            _event(2, tool_call_id="t1"),
        ]
        linker.index_all(events)
        assert len(linker.get_node_chain("n1")) == 1
        assert len(linker.get_message_chain("m1")) == 1
        assert len(linker.get_tool_call_chain("t1")) == 1

    def test_index_all_empty(self):
        linker = CrossLinker()
        linker.index_all([])
        assert linker.has_stable_ids() is False


class TestCrossLinkerEdgeCases:
    """Edge cases and robustness."""

    def test_event_without_stable_ids(self):
        linker = CrossLinker()
        ev = _event(0)
        ev.data = {}
        linker.index(ev)
        assert linker.has_stable_ids() is False
        assert linker.get_run_event_ids() == []

    def test_evidence_ref_missing_evidence_id(self):
        linker = CrossLinker()
        ev = _event(0, evidence_refs=[{"target": "some_file.py:42"}])
        linker.index(ev)
        chain = linker.get_evidence_events("some_file.py:42")
        assert len(chain) == 1

    def test_evidence_ref_empty_list(self):
        linker = CrossLinker()
        ev = _event(0, evidence_refs=[])
        linker.index(ev)
        assert linker.has_stable_ids() is False

    def test_empty_evidence_ref_skipped(self):
        linker = CrossLinker()
        ev = _event(0, evidence_refs=[""])
        linker.index(ev)
        assert linker.has_stable_ids() is False

    def test_sequences_preserved_in_chain_order(self):
        linker = CrossLinker()
        nid = "node_seq_test"
        linker.index(_event(5, node_id=nid))
        linker.index(_event(1, node_id=nid))
        linker.index(_event(3, node_id=nid))
        chain = linker.get_node_chain(nid)
        assert [e.sequence for e in chain] == [1, 3, 5]
