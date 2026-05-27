"""Property-based tests for sandbox policy ``decide()`` and related functions."""

from pathlib import Path
import tempfile

from hypothesis import assume, given, strategies as st

from agent_runtime_cockpit.security.sandbox import (
    SandboxPolicy,
    CommandClassification,
    classify_command,
    decide,
    cap_output,
    validate_command_paths,
)


@given(st.lists(st.text(max_size=16), max_size=6))
def test_decide_never_raises(command: list[str]):
    """``decide()`` should never raise for any command list."""
    assume(len(command) > 0)
    policy = SandboxPolicy(workspace_root=Path.cwd())
    result = decide(command, policy)
    assert result.allowed in (True, False)
    assert isinstance(result.classification, CommandClassification)
    assert isinstance(result.reason, str)
    assert result.policy == "local-safe"


@given(
    st.text(max_size=200),
    st.integers(min_value=1, max_value=65_536),
)
def test_cap_output_never_raises(text: str, max_bytes: int):
    """``cap_output()`` should never raise."""
    capped, truncated = cap_output(text, max_bytes)
    assert isinstance(capped, str)
    assert isinstance(truncated, bool)
    if len(text.encode("utf-8")) <= max_bytes:
        assert truncated is False
        assert capped == text
    else:
        assert truncated is True
        assert len(capped.encode("utf-8")) <= max_bytes


@given(st.lists(st.text(max_size=32), max_size=8))
def test_classify_command_never_raises(command: list[str]):
    result = classify_command(command)
    assert isinstance(result, CommandClassification)


@given(command=st.lists(st.text(max_size=32), max_size=8))
def test_validate_command_paths_never_crashes(command: list[str]):
    with tempfile.TemporaryDirectory() as tmp:
        policy = SandboxPolicy(workspace_root=Path(tmp))
        try:
            validate_command_paths(command, policy)
        except ValueError as exc:
            assert str(exc)
