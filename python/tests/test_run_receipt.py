import pytest

from agent_runtime_cockpit.protocol.evidence_refs import EvidenceRef
from agent_runtime_cockpit.protocol.run_receipt import FileChange, RunReceipt

RCPT_ID = "rcpt_01JKLMNOPQRSTUVWXYZ1"
EV_ID = "ev_01JDEADBEEF1234567890"


def make_receipt(**overrides):
    data = {
        "receipt_id": RCPT_ID,
        "run_id": "run_1",
        "status": "completed",
        "summary": "ok",
        "cost_usd": 0.01,
    }
    data.update(overrides)
    return RunReceipt(**data)


def test_receipt_defaults_and_roundtrip():
    receipt = make_receipt(
        files_changed=[FileChange(path="a.py", added=1, removed=0)],
        evidence_refs=[EvidenceRef(evidence_id=EV_ID, kind="tool_output", target="tool")],
    )
    assert receipt.duration_ms == 0
    assert receipt.signature is None

    loaded = RunReceipt.model_validate_json(receipt.model_dump_json(by_alias=True))
    assert loaded == receipt


def test_receipt_sign_verify_and_tamper():
    receipt = make_receipt()
    receipt.sign("secret")
    assert receipt.verify("secret") is True
    assert receipt.verify("wrong") is False

    receipt.summary = "tampered"
    assert receipt.verify("secret") is False


def test_receipt_canonical_deterministic():
    assert (
        make_receipt(created_at="2026-05-16T00:00:00Z").canonical_bytes()
        == make_receipt(created_at="2026-05-16T00:00:00Z").canonical_bytes()
    )


def test_receipt_validation():
    with pytest.raises(ValueError):
        make_receipt(receipt_id="bad")
    with pytest.raises(ValueError):
        make_receipt(status="running")
    with pytest.raises(ValueError):
        make_receipt(summary="x" * 2001)
