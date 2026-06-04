"""R-02 Deterministic context compaction (Lost-in-the-Middle informed).

Algorithm per docs/research/R-02-compaction-options.md §3b:
- Trigger: context_used / context_limit >= trigger_threshold (default 0.85)
- Preserve: system prompt, first keep_first_n pairs, last keep_last_n pairs,
  current (last) user message.
- Evict: middle pairs, oldest first, until usage < stop_threshold (0.70).
- NEVER calls an LLM. Decision is purely positional + byte-count. (CoSAI)

Emits ContextCompacted event via the process-local EventBus.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from ..events import get_bus
from ..events.types import ContextCompacted
from ..providers.base import ProviderMessage


@dataclass(frozen=True)
class CompactionConfig:
    trigger_threshold: float = 0.85  # compact when used/limit >= this
    stop_threshold: float = 0.70  # stop evicting when used/limit < this
    keep_first_n_pairs: int = 2  # preserve first N user/assistant pairs
    keep_last_n_pairs: int = 4  # preserve last N user/assistant pairs


@dataclass(frozen=True)
class CompactionResult:
    messages_kept: tuple[ProviderMessage, ...]
    messages_evicted: tuple[ProviderMessage, ...]
    tokens_before: int
    tokens_after: int
    compacted: bool  # False when below trigger threshold


def _estimate(messages: Sequence[ProviderMessage]) -> int:
    """Rough token estimate: 4 chars ≈ 1 token."""
    return max(0, sum(len(m.content) // 4 for m in messages))


def _pair_messages(
    messages: Sequence[ProviderMessage],
) -> tuple[
    list[ProviderMessage],
    list[tuple[ProviderMessage, ProviderMessage | None]],
    ProviderMessage | None,
]:
    """Split messages into [system/pinned], [(user, assistant), ...] pairs.

    The final user message (current turn) is always excluded from pairing
    and returned separately so it is never evicted.
    """
    system: list[ProviderMessage] = []
    turns: list[ProviderMessage] = []

    for msg in messages:
        if msg.role == "system":
            system.append(msg)
        else:
            turns.append(msg)

    # Current user message is always the last message; protect it.
    current_user: ProviderMessage | None = None
    if turns and turns[-1].role == "user":
        current_user = turns.pop()

    # Build (user, assistant?) pairs from remaining turns
    pairs: list[tuple[ProviderMessage, ProviderMessage | None]] = []
    i = 0
    while i < len(turns):
        if turns[i].role == "user":
            assistant = (
                turns[i + 1] if i + 1 < len(turns) and turns[i + 1].role == "assistant" else None
            )
            pairs.append((turns[i], assistant))
            i += 2 if assistant else 1
        else:
            # Orphan assistant message — treat as its own pseudo-pair
            pairs.append((turns[i], None))
            i += 1

    return system, pairs, current_user


def compact(
    messages: Sequence[ProviderMessage],
    context_limit: int,
    context_used: int | None = None,
    config: CompactionConfig = CompactionConfig(),
) -> CompactionResult:
    """Deterministic Lost-in-the-Middle eviction. NO LLM IN PATH.

    Args:
        messages: Full message list for this request.
        context_limit: Provider context window size in tokens.
        context_used: Current token usage (estimated if None).
        config: Thresholds and preservation counts.

    Returns:
        CompactionResult. If no compaction needed, .compacted is False and
        messages_kept equals the original sequence.
    """
    all_msgs = list(messages)
    tokens_before = context_used if context_used is not None else _estimate(all_msgs)

    if context_limit <= 0 or tokens_before / context_limit < config.trigger_threshold:
        return CompactionResult(
            messages_kept=tuple(all_msgs),
            messages_evicted=(),
            tokens_before=tokens_before,
            tokens_after=tokens_before,
            compacted=False,
        )

    system_msgs, pairs, current_user = _pair_messages(all_msgs)

    # Always-keep set: first N + last N pairs
    keep_first = set(range(min(config.keep_first_n_pairs, len(pairs))))
    keep_last = set(range(max(0, len(pairs) - config.keep_last_n_pairs), len(pairs)))
    always_keep = keep_first | keep_last

    # Middle pairs are candidates for eviction (oldest-first = lowest index first)
    candidates = [i for i in range(len(pairs)) if i not in always_keep]

    # Reconstruct final message list
    evicted_indices: set[int] = set()
    for i in candidates:
        # Recalculate usage after current eviction set
        current_kept = (
            system_msgs
            + [
                m
                for j, pair in enumerate(pairs)
                if j not in evicted_indices
                for m in pair
                if m is not None
            ]
            + ([current_user] if current_user else [])
        )
        current_used = _estimate(current_kept)
        if current_used / context_limit < config.stop_threshold:
            break
        evicted_indices.add(i)

    evicted_pairs = [pairs[i] for i in sorted(evicted_indices)]
    final_kept: list[ProviderMessage] = list(system_msgs)
    for i, pair in enumerate(pairs):
        if i not in evicted_indices:
            final_kept.extend(m for m in pair if m is not None)
    if current_user:
        final_kept.append(current_user)

    evicted_flat = [m for pair in evicted_pairs for m in pair if m is not None]
    tokens_after = _estimate(final_kept)

    if evicted_flat:
        get_bus().publish(
            ContextCompacted(
                tokens_before=tokens_before,
                tokens_after=tokens_after,
                messages_evicted_count=len(evicted_flat),
                evicted_handles=[],
            )
        )

    return CompactionResult(
        messages_kept=tuple(final_kept),
        messages_evicted=tuple(evicted_flat),
        tokens_before=tokens_before,
        tokens_after=tokens_after,
        compacted=bool(evicted_flat),
    )
