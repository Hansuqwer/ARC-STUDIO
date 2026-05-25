"""Adversarial property-based tests for command classification.

Uses Hypothesis to generate random command-line arguments and verify that:
- classify_command always returns a valid CommandClassification
- Known read-only commands are never classified as destructive/network/privileged
- Always-destructive commands (rm, dd, mkfs, truncate, shred) are always destructive
- Always-network commands (curl, wget, ping) are always network
"""

from hypothesis import assume, given, strategies as st
from hypothesis.strategies import sampled_from

from agent_runtime_cockpit.security.sandbox import CommandClassification, classify_command

SAFE_READONLY = {"ls", "pwd", "cat", "head", "tail", "tree", "wc"}
ALWAYS_NETWORK = {"curl", "wget", "ping"}
ALWAYS_DESTRUCTIVE = {"rm", "dd", "mkfs", "truncate", "shred"}


@given(
    exe=sampled_from(sorted(SAFE_READONLY)),
    args=st.lists(st.text(max_size=8), max_size=5),
)
def test_readonly_command_never_destructive_or_network(exe: str, args: list[str]):
    """Known read-only commands must never be classified as destructive or network."""
    command = [exe, *args]
    classification = classify_command(command)
    assume(classification != CommandClassification.UNKNOWN)
    assert classification not in (
        CommandClassification.DESTRUCTIVE,
        CommandClassification.NETWORK,
        CommandClassification.PRIVILEGED,
    ), f"{command} -> {classification}"


@given(
    exe=sampled_from(sorted(ALWAYS_NETWORK)),
    args=st.lists(st.text(max_size=8), max_size=3),
)
def test_network_command_always_network(exe: str, args: list[str]):
    """curl, wget, ping are always network regardless of arguments."""
    command = [exe, *args]
    assert classify_command(command) == CommandClassification.NETWORK, f"{command}"


@given(
    exe=sampled_from(sorted(ALWAYS_DESTRUCTIVE)),
    args=st.lists(st.text(max_size=8), max_size=3),
)
def test_destructive_command_always_destructive(exe: str, args: list[str]):
    """rm, dd, mkfs, truncate, shred are always destructive."""
    command = [exe, *args]
    assert classify_command(command) == CommandClassification.DESTRUCTIVE, f"{command}"


@given(st.lists(st.text(max_size=16), max_size=8))
def test_classify_command_never_raises(args: list[str]):
    """classify_command should never raise for any valid list input."""
    assume(len(args) > 0)
    result = classify_command(args)
    assert isinstance(result, CommandClassification)


@given(
    exe=sampled_from(sorted({"python", "python3"})),
    codes=st.lists(
        st.text(
            alphabet="abcdefghijklmnopqrstuvwxyz(){}[]=+-*/%&|!<>,.;:'\" \n\t",
            max_size=40,
        ),
        min_size=1,
        max_size=3,
    ),
)
def test_python_code_never_raises(exe: str, codes: list[str]):
    """Python -c invocations should never raise."""
    args = ["-c", *codes]
    command = [exe, *args]
    result = classify_command(command)
    assert isinstance(result, CommandClassification)


@given(
    exe=sampled_from(sorted({"npm", "pnpm", "pip", "uv", "brew"})),
    args=st.lists(st.text(max_size=12), max_size=4),
)
def test_package_manager_commands_stable(exe: str, args: list[str]):
    """Package manager commands should not raise and return a known category."""
    command = [exe, *args]
    result = classify_command(command)
    assert isinstance(result, CommandClassification)
