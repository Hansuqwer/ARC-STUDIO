import pytest

from agent_runtime_cockpit.protocol.stable_ids import (
    DegradationManifest,
    ensure_stable_id,
    generate_edge_id,
    generate_node_id,
    generate_stable_id,
    is_valid_stable_id,
    parse_stable_id,
)


class TestGenerateStableId:
    def test_generates_message_id(self):
        mid = generate_stable_id("message")
        assert mid.startswith("msg_")
        assert len(mid) > 4

    def test_generates_tool_call_id(self):
        tid = generate_stable_id("tool_call")
        assert tid.startswith("tc_")

    def test_generates_contract_id(self):
        cid = generate_stable_id("contract")
        assert cid.startswith("ctr_")

    def test_generates_receipt_id(self):
        rid = generate_stable_id("receipt")
        assert rid.startswith("rcpt_")

    def test_generates_evidence_id(self):
        eid = generate_stable_id("evidence")
        assert eid.startswith("ev_")

    def test_generates_run_id(self):
        rid = generate_stable_id("run")
        assert rid.startswith("run_")

    def test_generates_session_id(self):
        sid = generate_stable_id("session")
        assert sid.startswith("sess_")

    def test_generates_hitl_id(self):
        hid = generate_stable_id("hitl")
        assert hid.startswith("hitl_")

    def test_generates_decision_id(self):
        did = generate_stable_id("decision")
        assert did.startswith("dec_")

    def test_generates_approval_id(self):
        aid = generate_stable_id("approval")
        assert aid.startswith("apr_")

    def test_generates_policy_decision_id(self):
        pid = generate_stable_id("policy_decision")
        assert pid.startswith("pd_")

    def test_node_id_with_suffix(self):
        nid = generate_stable_id("node", suffix="reviewer_001")
        assert nid == "reviewer_001"

    def test_node_id_without_suffix(self):
        nid = generate_stable_id("node")
        assert nid.startswith("node_")

    def test_edge_id_with_suffix(self):
        eid = generate_stable_id("edge", suffix="start→reviewer")
        assert eid == "start→reviewer"

    def test_unknown_kind_raises(self):
        with pytest.raises(ValueError, match="Unknown ID kind"):
            generate_stable_id("unknown_kind")

    def test_ids_are_unique(self):
        ids = {generate_stable_id("message") for _ in range(100)}
        assert len(ids) == 100


class TestGenerateNodeId:
    def test_format(self):
        nid = generate_node_id("my_workflow", "reviewer")
        assert nid == "my_workflow.reviewer"

    def test_with_special_chars(self):
        nid = generate_node_id("wf-001", "agent_01")
        assert nid == "wf-001.agent_01"


class TestGenerateEdgeId:
    def test_format(self):
        eid = generate_edge_id("start", "reviewer")
        assert eid == "start→reviewer"


class TestEnsureStableId:
    def test_returns_existing(self):
        result = ensure_stable_id("existing_id", "message")
        assert result == "existing_id"

    def test_generates_when_none(self):
        result = ensure_stable_id(None, "message")
        assert result.startswith("msg_")

    def test_generates_when_empty(self):
        result = ensure_stable_id("", "message")
        assert result.startswith("msg_")


class TestParseStableId:
    def test_parse_message_id(self):
        kind, ulid = parse_stable_id("msg_01JABC123")
        assert kind == "msg"
        assert ulid == "01JABC123"

    def test_parse_tool_call_id(self):
        kind, ulid = parse_stable_id("tc_01JXYZ789")
        assert kind == "tc"
        assert ulid == "01JXYZ789"

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError, match="Invalid stable ID format"):
            parse_stable_id("noUnderscore")


class TestIsValidStableId:
    def test_valid_message_id(self):
        assert is_valid_stable_id("msg_01JABC") is True

    def test_valid_tool_call_id(self):
        assert is_valid_stable_id("tc_01JXYZ") is True

    def test_invalid_no_underscore(self):
        assert is_valid_stable_id("invalid") is False

    def test_invalid_empty(self):
        assert is_valid_stable_id("") is False

    def test_invalid_unknown_prefix(self):
        assert is_valid_stable_id("unknown_01JABC") is False

    def test_node_prefix_id_valid(self):
        assert is_valid_stable_id("node_01JABC") is True

    def test_workflow_node_id_valid(self):
        assert is_valid_stable_id("wf-001.reviewer") is True

    def test_edge_id_valid(self):
        assert is_valid_stable_id("start→reviewer") is True

    def test_filename_is_not_node_id(self):
        assert is_valid_stable_id("README.md") is False

    def test_node_id_rejects_multiple_or_missing_parts(self):
        assert is_valid_stable_id("a.b.c") is False
        assert is_valid_stable_id(".x") is False
        assert is_valid_stable_id("x.") is False

    def test_edge_id_rejects_missing_parts(self):
        assert is_valid_stable_id("→b") is False
        assert is_valid_stable_id("a→") is False
        assert is_valid_stable_id("→") is False


class TestDegradationManifest:
    def test_empty_manifest(self):
        m = DegradationManifest()
        assert m.is_degraded() is False
        assert m._total_events == 0

    def test_record_event_with_all_ids(self):
        m = DegradationManifest()
        m.record_event(
            {"node_id": "n1", "message_id": "m1", "tool_call_id": "tc1", "evidence_refs": []}
        )
        assert m._total_events == 1
        assert m._missing_node_ids == 0
        assert m._missing_message_ids == 0
        assert m._missing_tool_call_ids == 0
        assert m._missing_evidence_refs == 0

    def test_record_event_missing_all_ids(self):
        m = DegradationManifest()
        m.record_event({})
        assert m._total_events == 1
        assert m._missing_node_ids == 1
        assert m._missing_message_ids == 1
        assert m._missing_tool_call_ids == 1
        assert m._missing_evidence_refs == 1

    def test_degraded_when_majority_missing_node_ids(self):
        m = DegradationManifest()
        m.record_event({})
        m.record_event({})
        m.record_event({"node_id": "n1"})
        assert m.is_degraded() is True

    def test_not_degraded_when_minority_missing(self):
        m = DegradationManifest()
        m.record_event({"node_id": "n1", "message_id": "m1", "tool_call_id": "tc1"})
        m.record_event({"node_id": "n2", "message_id": "m2", "tool_call_id": "tc2"})
        m.record_event({})
        assert m.is_degraded() is False

    def test_get_degradation_summary(self):
        m = DegradationManifest()
        m.record_event({})
        summary = m.get_degradation_summary()
        assert summary["total_events"] == 1
        assert summary["missing_node_ids"] == 1
        assert summary["is_degraded"] is True
        assert summary["cross_linking_available"] is False

    def test_repr(self):
        m = DegradationManifest()
        r = repr(m)
        assert "DegradationManifest" in r
        assert "total=0" in r
