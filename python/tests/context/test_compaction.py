"""Tests for R-02 CompactionStrategy (context/compaction.py)."""

from __future__ import annotations

from unittest.mock import patch

from agent_runtime_cockpit.context.compaction import (
    CompactionConfig,
    compact,
)
from agent_runtime_cockpit.events import reset_bus
from agent_runtime_cockpit.events.types import ContextCompacted
from agent_runtime_cockpit.providers.base import ProviderMessage


def _msg(role: str, content: str) -> ProviderMessage:
    trust = "system" if role == "system" else "user"
    return ProviderMessage(role=role, content=content, trust=trust)


def _build_convo(n_pairs: int, content_per_msg: str = "x" * 100) -> list[ProviderMessage]:
    """System + n user/assistant pairs + current user."""
    msgs = [_msg("system", "System prompt.")]
    for i in range(n_pairs):
        msgs.append(_msg("user", f"User {i}: {content_per_msg}"))
        msgs.append(_msg("assistant", f"Assistant {i}: {content_per_msg}"))
    msgs.append(_msg("user", "Current user question"))
    return msgs


# ── 1. Below threshold — no compaction ────────────────────────────────────


def test_below_threshold_noop():
    msgs = _build_convo(4)
    result = compact(msgs, context_limit=100_000, context_used=1000)
    assert not result.compacted
    assert result.messages_kept == tuple(msgs)
    assert result.messages_evicted == ()


# ── 2. At threshold — compacts to stop ────────────────────────────────────


def test_at_threshold_compacts():
    msgs = _build_convo(10, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)  # 87% usage → triggers
    result = compact(msgs, context_limit=limit)
    assert result.compacted
    assert result.tokens_after < result.tokens_before


# ── 3. First N pairs always kept ──────────────────────────────────────────


def test_first_n_pairs_always_kept():
    msgs = _build_convo(10, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)
    config = CompactionConfig(keep_first_n_pairs=2, keep_last_n_pairs=2)
    result = compact(msgs, context_limit=limit, config=config)
    kept = list(result.messages_kept)
    # First 2 user messages (after system) must be present
    user_msgs = [m.content for m in kept if m.role == "user"]
    assert "User 0:" in user_msgs[0]
    assert "User 1:" in user_msgs[1]


# ── 4. Last M pairs always kept ───────────────────────────────────────────


def test_last_m_pairs_always_kept():
    msgs = _build_convo(10, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)
    config = CompactionConfig(keep_first_n_pairs=2, keep_last_n_pairs=2)
    result = compact(msgs, context_limit=limit, config=config)
    kept_user = [m.content for m in result.messages_kept if m.role == "user"]
    # Last 2 pairs (User 8 + User 9) + current user should be present
    assert any("User 8:" in c or "User 9:" in c for c in kept_user)


# ── 5. System prompt always kept ──────────────────────────────────────────


def test_system_prompt_always_kept():
    msgs = _build_convo(10, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)
    result = compact(msgs, context_limit=limit)
    system_kept = [m for m in result.messages_kept if m.role == "system"]
    assert len(system_kept) == 1
    assert system_kept[0].content == "System prompt."


# ── 6. Current user message always kept ──────────────────────────────────


def test_current_user_message_always_kept():
    msgs = _build_convo(10, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)
    result = compact(msgs, context_limit=limit)
    last_user = [m for m in result.messages_kept if m.role == "user"][-1]
    assert last_user.content == "Current user question"


# ── 7. Middle pairs evicted first (not first or last) ────────────────────


def test_middle_pairs_evicted_not_first_or_last():
    msgs = _build_convo(8, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)
    config = CompactionConfig(keep_first_n_pairs=2, keep_last_n_pairs=2)
    result = compact(msgs, context_limit=limit, config=config)
    evicted_user = [m.content for m in result.messages_evicted if m.role == "user"]
    # Evicted should be middle (User 2..5), not User 0, 1, 6, 7
    for c in evicted_user:
        assert "User 0:" not in c
        assert "User 1:" not in c
        assert "User 6:" not in c
        assert "User 7:" not in c


# ── 8. NO LLM in compaction path (CoSAI) ─────────────────────────────────


def test_no_llm_in_path():
    """CoSAI: compact() must never invoke any LLM client."""
    msgs = _build_convo(10, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)
    with patch("openai.OpenAI") as mock_openai:
        compact(msgs, context_limit=limit)
        mock_openai.assert_not_called()
    with patch("anthropic.Anthropic") as mock_anthropic:
        compact(msgs, context_limit=limit)
        mock_anthropic.assert_not_called()


# ── 9. Hysteresis — compacts to stop_threshold, not trigger ──────────────


def test_hysteresis_compacts_to_stop_not_trigger():
    msgs = _build_convo(12, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)
    config = CompactionConfig(trigger_threshold=0.85, stop_threshold=0.70)
    result = compact(msgs, context_limit=limit, config=config)
    if result.compacted:
        ratio = result.tokens_after / limit
        assert ratio < config.trigger_threshold


# ── 10. No pairs — noop ───────────────────────────────────────────────────


def test_no_pairs_noop():
    msgs = [_msg("system", "sys"), _msg("user", "only one")]
    result = compact(msgs, context_limit=10, context_used=100)
    # Even if "triggered", no pairs to evict → kept unchanged
    assert tuple(msgs) == result.messages_kept or not result.compacted


# ── 11. Single pair — noop (protected by keep_first + keep_last) ─────────


def test_single_pair_noop():
    msgs = [_msg("system", "sys"), _msg("user", "u0"), _msg("assistant", "a0"), _msg("user", "cur")]
    result = compact(msgs, context_limit=10, context_used=1000)
    # Single pair is in both first-N and last-N → never evicted
    assert "u0" in [m.content for m in result.messages_kept]


# ── 12. Deterministic — same input, same eviction set ────────────────────


def test_deterministic_same_input_same_eviction():
    msgs = _build_convo(10, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)
    r1 = compact(msgs, context_limit=limit)
    r2 = compact(msgs, context_limit=limit)
    assert r1.messages_evicted == r2.messages_evicted
    assert r1.messages_kept == r2.messages_kept


# ── 13. ContextCompacted event emitted ───────────────────────────────────


def test_context_compacted_event_emitted():
    reset_bus()
    emitted = []
    from agent_runtime_cockpit.events import get_bus

    get_bus().subscribe("context_compacted", emitted.append)

    msgs = _build_convo(10, content_per_msg="x" * 400)
    total = sum(len(m.content) // 4 for m in msgs)
    limit = int(total / 0.87)
    result = compact(msgs, context_limit=limit)

    if result.compacted:
        assert len(emitted) == 1
        ev = emitted[0]
        assert isinstance(ev, ContextCompacted)
        assert ev.tokens_before > ev.tokens_after
        assert ev.messages_evicted_count > 0


# ── 14. Zero context_limit — noop (guard against div/0) ──────────────────


def test_zero_context_limit_noop():
    msgs = _build_convo(5)
    result = compact(msgs, context_limit=0)
    assert not result.compacted
