"""Cache breakpoint computation.

Lock: ADR-011 (prompt caching), ADR-018 (protocol placement)
Phase: 4 Slice 4

Computes where to place cache breakpoints in a provider request. The
algorithm is provider-agnostic; per-provider wire formats are applied
downstream by the client implementations.

Three breakpoint positions:

1. **System prompt** — cached when large enough to amortize cache writes.
2. **Tool definitions** — cached as a group when large enough.
3. **Messages** — cached at specific message indices when message token
   count is above the threshold. For Anthropic, a marker on ``messages[i]``
   caches all content up to and including that message.

A request can have at most 4 cache breakpoints (Anthropic limit as of
2026-Q1). The algorithm prioritizes by amortization potential:
system > tools > largest messages first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

MAX_BREAKPOINTS = 4
DEFAULT_CONTEXT_CACHE_THRESHOLD = 1024
CacheBreakpointPosition = Literal["system", "tools", "messages"]


@dataclass(frozen=True)
class CacheBreakpoint:
    """A cache-control marker for one position in a provider request.

    For ``position="messages"``, ``index`` is the zero-based index of the
    message receiving the cache-control marker. Anthropic caches everything up
    to and including that message. For ``system`` and ``tools``, ``index`` must
    be 0 because those positions carry one block in the wire format.
    """

    position: CacheBreakpointPosition
    index: int = 0
    estimated_tokens: int = 0
    ttl_seconds: Optional[int] = None

    def __post_init__(self) -> None:
        valid = ("system", "tools", "messages")
        if self.position not in valid:
            raise ValueError(
                f"CacheBreakpoint.position must be one of {valid}, got {self.position!r}"
            )
        if self.index < 0:
            raise ValueError(f"CacheBreakpoint.index must be >= 0, got {self.index}")
        if self.position in ("system", "tools") and self.index != 0:
            raise ValueError(
                f"CacheBreakpoint position={self.position!r} requires index=0, got index={self.index}"
            )


@dataclass(frozen=True)
class MessageTokenInfo:
    """Per-message token count for cache breakpoint computation.

    ``index`` is the position of this message in the provider request's
    messages array. ``tokens`` is the token count of the message content as
    measured or estimated by the caller.
    """

    index: int
    tokens: int

    def __post_init__(self) -> None:
        if self.index < 0:
            raise ValueError(f"MessageTokenInfo.index must be >= 0, got {self.index}")
        if self.tokens < 0:
            raise ValueError(f"MessageTokenInfo.tokens must be >= 0, got {self.tokens}")


@dataclass
class CacheBreakpointInput:
    """Inputs to the breakpoint computation."""

    system_prompt_tokens: int = 0
    tool_definition_tokens: int = 0
    messages: list[MessageTokenInfo] = field(default_factory=list)
    threshold: int = DEFAULT_CONTEXT_CACHE_THRESHOLD


def compute_breakpoints(input_data: CacheBreakpointInput) -> list[CacheBreakpoint]:
    """Compute cache breakpoints for a request.

    Returns at most :data:`MAX_BREAKPOINTS` markers. If more message markers
    qualify than available slots, the largest messages by token count are kept;
    ties are broken by latest index. Kept messages are then re-sorted by index
    for stable provider wire order.
    """
    candidates: list[CacheBreakpoint] = []

    if input_data.system_prompt_tokens >= input_data.threshold:
        candidates.append(
            CacheBreakpoint(
                position="system",
                index=0,
                estimated_tokens=input_data.system_prompt_tokens,
            )
        )

    if input_data.tool_definition_tokens >= input_data.threshold:
        candidates.append(
            CacheBreakpoint(
                position="tools",
                index=0,
                estimated_tokens=input_data.tool_definition_tokens,
            )
        )

    cacheable_messages = [m for m in input_data.messages if m.tokens >= input_data.threshold]
    remaining_slots = MAX_BREAKPOINTS - len(candidates)
    if len(cacheable_messages) > remaining_slots:
        cacheable_messages = sorted(
            cacheable_messages,
            key=lambda message: (message.tokens, message.index),
            reverse=True,
        )[:remaining_slots]
        cacheable_messages.sort(key=lambda message: message.index)

    candidates.extend(
        CacheBreakpoint(position="messages", index=message.index, estimated_tokens=message.tokens)
        for message in cacheable_messages
    )

    assert len(candidates) <= MAX_BREAKPOINTS, (
        f"compute_breakpoints produced {len(candidates)} > MAX_BREAKPOINTS ({MAX_BREAKPOINTS}). This is a bug."
    )
    return candidates


def estimate_cache_savings(breakpoints: list[CacheBreakpoint]) -> float:
    """Estimate total input tokens saved by caching *breakpoints*."""
    return sum(bp.estimated_tokens for bp in breakpoints)
