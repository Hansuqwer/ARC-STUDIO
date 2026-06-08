"""Tests for ContextPackEntry line_number field and LocalRepoProvider population."""

from __future__ import annotations


def test_context_pack_entry_has_line_number_field():
    from agent_runtime_cockpit.protocol.schemas import ContextPackEntry, SourceType

    entry = ContextPackEntry(
        id="test-1",
        task="find",
        source="foo.py",
        source_type=SourceType.LOCAL_REPO,
        content="# line 5\nsome code here",
        line_number=5,
    )
    assert entry.line_number == 5


def test_context_pack_entry_line_number_optional():
    from agent_runtime_cockpit.protocol.schemas import ContextPackEntry, SourceType

    entry = ContextPackEntry(
        id="test-2",
        task="find",
        source="foo.py",
        source_type=SourceType.LOCAL_REPO,
        content="code",
    )
    assert entry.line_number is None


def test_local_repo_provider_populates_line_number(tmp_path):
    """LocalRepoProvider must populate line_number in returned entries."""
    from agent_runtime_cockpit.context.providers.local_repo import LocalRepoProvider

    # Create a workspace file with a clear keyword on a known line
    workspace = tmp_path / "ws"
    workspace.mkdir()
    src = workspace / "example.py"
    lines = ["# header\n"] * 10 + ["def find_target():\n", "    pass\n"]
    src.write_text("".join(lines))

    provider = LocalRepoProvider()
    results = provider.retrieve("find_target", workspace=workspace)

    assert results, "LocalRepoProvider should find the keyword"
    entry = results[0]
    assert entry.line_number is not None, "line_number should be set"
    assert entry.line_number >= 1, "line_number must be 1-based"
