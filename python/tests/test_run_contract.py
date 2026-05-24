import pytest

from agent_runtime_cockpit.protocol.run_contract import ContractStatus, RunContract
from agent_runtime_cockpit.protocol.run_receipt import RunReceipt

CTR_ID = "ctr_01JABCDEFGHIJKLMNOPQ"
RCPT_ID = "rcpt_01JKLMNOPQRSTUVWXYZ1"


def make_contract(**overrides):
    data = {
        "contract_id": CTR_ID,
        "run_id": "run_1",
        "session_id": "ses_1",
        "objective": "do work",
        "runtime": "swarmgraph",
        "mode": "build",
        "cost_ceiling_usd": 1.0,
    }
    data.update(overrides)
    return RunContract(**data)


def make_receipt(**overrides):
    data = {
        "receipt_id": RCPT_ID,
        "run_id": "run_1",
        "status": "completed",
        "summary": "ok",
        "cost_usd": 0.5,
    }
    data.update(overrides)
    return RunReceipt(**data)


def test_contract_default_status_and_roundtrip():
    contract = make_contract()
    assert contract.status == ContractStatus.PROPOSED
    loaded = RunContract.model_validate_json(contract.model_dump_json())
    assert loaded == contract


def test_contract_is_satisfied_by_receipt():
    assert make_contract().is_satisfied_by(make_receipt()) is True
    assert make_contract().is_satisfied_by(make_receipt(cost_usd=2.0)) is False
    assert make_contract().is_satisfied_by(make_receipt(status="failed")) is False
    assert make_contract().is_satisfied_by(make_receipt(run_id="other")) is False


def test_contract_validation():
    with pytest.raises(ValueError):
        make_contract(contract_id="bad")
    with pytest.raises(ValueError):
        make_contract(mode="chat")
    with pytest.raises(ValueError):
        make_contract(cost_ceiling_usd=-1)
