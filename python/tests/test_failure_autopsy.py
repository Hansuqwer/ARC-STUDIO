import pytest

from agent_runtime_cockpit.protocol.evidence_refs import EvidenceRef
from agent_runtime_cockpit.protocol.failure_autopsy import FailureAutopsy, RetryOption


EV_ID = "ev_01JDEADBEEF1234567890"


def test_autopsy_defaults_and_roundtrip():
    autopsy = FailureAutopsy(
        run_id="run_1",
        retry_options=[RetryOption(label="Retry", risk="low")],
        evidence_refs=[EvidenceRef(evidence_id=EV_ID, kind="tool_output", target="tool")],
    )
    assert autopsy.confidence == "unknown"

    loaded = FailureAutopsy.model_validate_json(autopsy.model_dump_json(by_alias=True))
    assert loaded == autopsy


def test_autopsy_preserves_knows_guesses_distinction():
    autopsy = FailureAutopsy(run_id="run_1", knows=["fact"], guesses=["hypothesis"])
    assert autopsy.knows == ["fact"]
    assert autopsy.guesses == ["hypothesis"]


def test_autopsy_validation():
    with pytest.raises(ValueError):
        FailureAutopsy(run_id="run_1", confidence="certain")
    with pytest.raises(ValueError):
        FailureAutopsy(run_id="run_1", error_category="network")
    with pytest.raises(ValueError):
        FailureAutopsy(run_id="run_1", knows=["x"] * 51)
    with pytest.raises(ValueError):
        RetryOption(label="Retry", risk="none")
