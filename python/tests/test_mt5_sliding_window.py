"""MT-5 deterministic core: sliding-window history compaction tests."""

from __future__ import annotations

from agent_runtime_cockpit.cli_repl.session import (
    ChatSession,
    CompactionReceipt,
    sliding_window_compact,
)


def _session(turns: list[tuple[str, str]], system: str | None = "system prompt") -> ChatSession:
    s = ChatSession()
    if system is not None:
        s.add_message("system", system)
    for role, content in turns:
        s.add_message(role, content)
    return s


def _turns(n: int) -> list[tuple[str, str]]:
    """n alternating user/assistant turns."""
    out = []
    for i in range(n):
        role = "user" if i % 2 == 0 else "assistant"
        out.append((role, f"turn-{i}-content"))
    return out


# ── No-op cases ───────────────────────────────────────────────────────────────


def test_noop_when_at_or_below_window():
    s = _session(_turns(5))
    r = sliding_window_compact(s, keep_last_turns=20)
    assert r.cleared_count == 0
    assert r.kept_count == 5


def test_noop_when_exactly_window_plus_one():
    """keep_last_turns + 1 (anchor) → nothing to elide."""
    s = _session(_turns(21), system=None)
    r = sliding_window_compact(s, keep_last_turns=20)
    assert r.cleared_count == 0


# ── Elision behaviour ─────────────────────────────────────────────────────────


def test_elides_middle_turns():
    s = _session(_turns(30), system=None)
    r = sliding_window_compact(s, keep_last_turns=20)
    # 30 turns, keep first(1) + last(20) = 21 kept, 9 elided
    assert r.cleared_count == 9
    assert r.kept_count == 21


def test_first_turn_kept_verbatim():
    s = _session(_turns(30), system=None)
    sliding_window_compact(s, keep_last_turns=20)
    turns = [m for m in s.history if m.get("role") in ("user", "assistant")]
    assert turns[0]["content"] == "turn-0-content"


def test_last_turns_kept_verbatim():
    s = _session(_turns(30), system=None)
    sliding_window_compact(s, keep_last_turns=20)
    turns = [m for m in s.history if m.get("role") in ("user", "assistant")]
    assert turns[-1]["content"] == "turn-29-content"
    assert turns[-20]["content"] == "turn-10-content"  # first kept in window


def test_middle_turns_replaced_with_stub():
    s = _session(_turns(30), system=None)
    sliding_window_compact(s, keep_last_turns=20)
    turns = [m for m in s.history if m.get("role") in ("user", "assistant")]
    # turns[1..9] elided
    assert "[Earlier turn elided" in turns[1]["content"]
    assert "[Earlier turn elided" in turns[9]["content"]


# ── System messages untouched ─────────────────────────────────────────────────


def test_system_messages_untouched():
    s = _session(_turns(30), system="IMPORTANT INSTRUCTIONS")
    sliding_window_compact(s, keep_last_turns=20)
    system_msgs = [m for m in s.history if m.get("role") == "system"]
    assert system_msgs[0]["content"] == "IMPORTANT INSTRUCTIONS"


# ── Tool messages untouched (MT-1 owns those) ────────────────────────────────


def test_tool_messages_untouched():
    s = ChatSession()
    s.add_message("system", "sys")
    for i in range(30):
        s.add_message("user", f"u{i}")
        s.add_message("tool", f"tool-output-{i}")
    sliding_window_compact(s, keep_last_turns=20)
    tool_msgs = [m for m in s.history if m.get("role") == "tool"]
    # No tool message should be elided by the sliding window
    assert all("[Earlier turn elided" not in m["content"] for m in tool_msgs)


# ── Receipt + idempotence ─────────────────────────────────────────────────────


def test_receipt_type_and_hash():
    s = _session(_turns(30), system=None)
    r = sliding_window_compact(s, keep_last_turns=20)
    assert isinstance(r, CompactionReceipt)
    assert len(r.sha256) == 64


def test_idempotent_second_run_is_noop():
    s = _session(_turns(30), system=None)
    sliding_window_compact(s, keep_last_turns=20)
    r2 = sliding_window_compact(s, keep_last_turns=20)
    # Already-elided stubs are skipped → nothing new cleared
    assert r2.cleared_count == 0


def test_cleared_chars_counts_original_content():
    s = _session([("user", "x" * 100)] + _turns(25), system=None)
    r = sliding_window_compact(s, keep_last_turns=20)
    # turn-0 ("x"*100) is the anchor (kept); the 100-char turn at index 0 is NOT elided.
    # Elided turns are turn-1.. with "turn-N-content" content.
    assert r.cleared_chars > 0
    assert r.cleared_count >= 1
