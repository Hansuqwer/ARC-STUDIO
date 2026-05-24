import pytest

from agent_runtime_cockpit.protocol.evidence_refs import EvidenceKind, EvidenceRef

EV_ID = "ev_01JDEADBEEF1234567890"


def test_evidence_ref_defaults_and_roundtrip():
    ref = EvidenceRef(evidence_id=EV_ID, kind="file", target="src/workflow.py")
    assert ref.kind == EvidenceKind.FILE
    assert ref.redacted is False

    loaded = EvidenceRef.model_validate_json(ref.model_dump_json(by_alias=True))
    assert loaded == ref


def test_evidence_ref_range_alias():
    ref = EvidenceRef.model_validate(
        {"evidence_id": EV_ID, "kind": "file", "target": "a.py", "range": [1, 3]}
    )
    assert ref.range_ == (1, 3)
    assert ref.model_dump(by_alias=True)["range"] == (1, 3)


def test_evidence_ref_validates_supported_kinds():
    EvidenceRef(evidence_id=EV_ID, kind="file", target="a.py")
    EvidenceRef(evidence_id=EV_ID, kind="tool_output", target="tool")
    with pytest.raises(ValueError):
        EvidenceRef(evidence_id=EV_ID, kind="frame_receipt", target="x")


def test_evidence_ref_validates_id_target_range():
    with pytest.raises(ValueError):
        EvidenceRef(evidence_id="bad", kind="file", target="a.py")
    with pytest.raises(ValueError):
        EvidenceRef(evidence_id=EV_ID, kind="file", target="")
    with pytest.raises(ValueError):
        EvidenceRef(evidence_id=EV_ID, kind="file", target="a.py", range=(-1, 2))
