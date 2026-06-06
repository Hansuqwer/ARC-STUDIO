"""MT-1: Deterministic tool-result microcompact tests."""

from __future__ import annotations

from agent_runtime_cockpit.cli_repl.session import (
    ChatSession,
    CompactionReceipt,
    microcompact_tool_results,
)


def _session(*tool_contents: str) -> ChatSession:
    s = ChatSession()
    s.add_message("user", "hello")
    s.add_message("assistant", "reply")
    for content in tool_contents:
        s.add_message("tool", content)
    return s


# ── No-op cases ───────────────────────────────────────────────────────────────


def test_noop_when_zero_tool_messages():
    s = _session()
    r = microcompact_tool_results(s)
    assert r.cleared_count == 0
    assert r.kept_count == 0


def test_noop_when_equal_to_keep_last():
    s = _session("t1", "t2", "t3", "t4", "t5")
    r = microcompact_tool_results(s)
    assert r.cleared_count == 0
    assert r.kept_count == 5


def test_noop_when_fewer_than_keep_last():
    s = _session("t1", "t2")
    r = microcompact_tool_results(s)
    assert r.cleared_count == 0
    assert r.kept_count == 2


# ── Compaction behaviour ──────────────────────────────────────────────────────


def test_clears_oldest_tool_messages():
    s = _session("t1", "t2", "t3", "t4", "t5", "t6", "t7")
    r = microcompact_tool_results(s)
    assert r.cleared_count == 2  # 7 - keep_last(5) = 2
    assert r.kept_count == 5


def test_cleared_messages_replaced_with_stub():
    s = _session("long content here", "t2", "t3", "t4", "t5", "t6")
    microcompact_tool_results(s)
    tool_msgs = [m for m in s.history if m.get("role") == "tool"]
    # First message was cleared; should contain the stub
    assert "[Tool output cleared" in tool_msgs[0]["content"]
    # Last 5 are verbatim
    assert tool_msgs[1]["content"] == "t2"


def test_kept_messages_unchanged():
    s = _session("old1", "old2", "kept1", "kept2", "kept3", "kept4", "kept5")
    microcompact_tool_results(s)
    tool_msgs = [m for m in s.history if m.get("role") == "tool"]
    assert tool_msgs[-5:] == [
        {
            "role": "tool",
            "content": f"kept{i}",
            **{k: v for k, v in tool_msgs[-5 + i - 1].items() if k not in ("role", "content")},
        }
        for i in range(1, 6)
    ] or [m["content"] for m in tool_msgs[-5:]] == ["kept1", "kept2", "kept3", "kept4", "kept5"]


def test_kept_messages_verbatim():
    """Simpler form of the above: last 5 contents unchanged."""
    s = _session("old", "k1", "k2", "k3", "k4", "k5")
    microcompact_tool_results(s)
    tool_msgs = [m for m in s.history if m.get("role") == "tool"]
    assert [m["content"] for m in tool_msgs[-5:]] == ["k1", "k2", "k3", "k4", "k5"]


def test_cleared_chars_count():
    s = _session("abc", "de", "f", "g", "h", "i", "j")  # 7 messages → 2 cleared
    r = microcompact_tool_results(s)
    assert r.cleared_count == 2
    assert r.cleared_chars == 3 + 2  # "abc" + "de"


# ── Receipt integrity ─────────────────────────────────────────────────────────


def test_receipt_is_compaction_receipt():
    s = _session("a", "b", "c", "d", "e", "f")
    r = microcompact_tool_results(s)
    assert isinstance(r, CompactionReceipt)


def test_receipt_sha256_is_hex_string():
    s = _session("a", "b", "c", "d", "e", "f")
    r = microcompact_tool_results(s)
    assert len(r.sha256) == 64
    assert all(c in "0123456789abcdef" for c in r.sha256)


def test_receipt_sha256_is_deterministic():
    """Same content → same SHA-256."""
    s1 = _session("x", "y", "z", "w", "v", "u")
    s2 = _session("x", "y", "z", "w", "v", "u")
    r1 = microcompact_tool_results(s1)
    r2 = microcompact_tool_results(s2)
    assert r1.sha256 == r2.sha256


def test_receipt_sha256_different_content_differs():
    s1 = _session("A", "b", "c", "d", "e", "f")
    s2 = _session("B", "b", "c", "d", "e", "f")
    r1 = microcompact_tool_results(s1)
    r2 = microcompact_tool_results(s2)
    assert r1.sha256 != r2.sha256


# ── Custom keep_last ──────────────────────────────────────────────────────────


def test_custom_keep_last():
    s = _session("t1", "t2", "t3", "t4", "t5", "t6", "t7", "t8")
    r = microcompact_tool_results(s, keep_last=3)
    assert r.cleared_count == 5
    assert r.kept_count == 3
    tool_msgs = [m for m in s.history if m.get("role") == "tool"]
    assert [m["content"] for m in tool_msgs[-3:]] == ["t6", "t7", "t8"]


# ── Non-tool messages untouched ───────────────────────────────────────────────


def test_non_tool_messages_untouched():
    s = _session("t1", "t2", "t3", "t4", "t5", "t6")
    user_before = [m for m in s.history if m.get("role") == "user"]
    asst_before = [m for m in s.history if m.get("role") == "assistant"]
    microcompact_tool_results(s)
    assert [m for m in s.history if m.get("role") == "user"] == user_before
    assert [m for m in s.history if m.get("role") == "assistant"] == asst_before


# ── cmd_compact slash command ─────────────────────────────────────────────────


def test_cmd_compact_noop_message():
    from agent_runtime_cockpit.cli_repl.slash_commands import cmd_compact

    s = _session("t1")
    result = cmd_compact("", s)
    assert "Nothing to compact" in result.output


def test_cmd_compact_reports_cleared():
    from agent_runtime_cockpit.cli_repl.slash_commands import cmd_compact

    s = _session("a" * 100, "b" * 100, "c", "d", "e", "f")
    result = cmd_compact("", s)
    assert "Compacted 1" in result.output
    assert "chars removed" in result.output
    assert "sha256:" in result.output
