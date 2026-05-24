import pytest

from agent_runtime_cockpit.protocol.trust_diff import TrustDiff

TD_ID = "td_01JCAFEBABE0987654321"


def test_trust_diff_roundtrip():
    diff = TrustDiff(
        diff_id=TD_ID,
        workspace_path="/tmp/ws",
        before=["read_only"],
        after=["read_only", "network"],
        added_capabilities=["network"],
        reason="profile_switch",
        requires_confirmation=True,
    )
    loaded = TrustDiff.model_validate_json(diff.model_dump_json())
    assert loaded == diff


def test_trust_diff_validation():
    with pytest.raises(ValueError):
        TrustDiff(diff_id="bad", workspace_path="/tmp/ws")
    with pytest.raises(ValueError):
        TrustDiff(diff_id=TD_ID, workspace_path="/tmp/ws", reason="other")
