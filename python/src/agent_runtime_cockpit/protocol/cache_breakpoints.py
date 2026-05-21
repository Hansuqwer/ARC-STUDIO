"""Cache breakpoint computation.

Lock: ADR-011 (prompt caching), ADR-018 (protocol placement)
Phase: 4 Slice 4

Computes where to place cache breakpoints in a provider request. The
algorithm is provider-agnostic; per-provider wire formats are applied
downstream by the client implementations.

Three breakpoint positions, locked per Phase 4 kickoff:

1. **System prompt** — always cached when non-empty. The system prompt
   rarely changes within a session; caching it amortizes the input cost
   across every call.

2. **Tool definitions** — cached as a group when tools are present. Tool
   schemas are stable within a workflow and often shared across runs.

3. **Attached context** — cached per-attachment when above the token
   threshold. Default threshold is 1024 tokens (Anthropic's recommended
   minimum; below this, cache write overhead exceeds savings).

A request can have at most 4 cache breakpoints (Anthropic limit as of
2026-Q1). The algorithm prioritizes by amortization potential:
system > tools > largest context attachments first.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

# Anthropic's hard limit on cache breakpoints per request.
MAX_BREAKPOINTS = 4

# Default minimum tokens for an attachment to be worth caching.
DEFAULT_CONTEXT_CACHE_THRESHOLD = 1024

CacheBreakpointPosition = str  # "system" | "tools" | "context" | "messages"


@dataclass(frozen=True)
class CacheBreakpoint:
    """A computed cache breakpoint.

    Attributes:
        position: Which section of the request this breakpoint marks.
        index: Position-specific index (which attachment, which message).
        estimated_tokens: Token count this breakpoint will cache. Used for
            amortization-priority sorting when more breakpoints are wanted
            than ``MAX_BREAKPOINTS``.
        ttl_seconds: Optional TTL hint for the provider. Anthropic supports
            5-minute (default) and 1-hour TTLs. ``None`` means use provider
            default.
    """

    position: CacheBreakpointPosition
    index: int = 0
    estimated_tokens: int = 0
    ttl_seconds: Optional[int] = None


@dataclass
class CacheBreakpointInput:
    """Inputs to the breakpoint computation.

    Attributes:
        system_prompt_tokens: Estimated token count of the system prompt.
            Zero means no system prompt; no breakpoint will be placed.
        tool_definition_tokens: Estimated token count of all tool definitions
            combined. Zero means no tools.
        context_attachments: List of ``(attachment_id, estimated_tokens)``
            tuples for attached context files.
        threshold: Minimum tokens for a context attachment to be worth caching.
    """

    system_prompt_tokens: int = 0
    tool_definition_tokens: int = 0
    context_attachments: list[tuple[str, int]] = field(default_factory=list)
    threshold: int = DEFAULT_CONTEXT_CACHE_THRESHOLD


def compute_breakpoints(input_data: CacheBreakpointInput) -> list[CacheBreakpoint]:
    """Compute cache breakpoints for a request.

    Returns a list of at most :data:`MAX_BREAKPOINTS` :class:`CacheBreakpoint`
    instances, ordered by request position (system -> tools -> context). When
    more breakpoints are wanted than :data:`MAX_BREAKPOINTS`, the algorithm
    drops the smallest-token context attachments first.

The output is provider-agnostic. Per-provider clients translate these
    into the provider's cache-control wire format. In the current Anthropic
    client, message-position indexes are informational only and collapse to a
    final-message cache marker; per-index mapping is deferred to Phase 4.1.
    """
    candidates: list[CacheBreakpoint] = []

    # 1. System prompt — always first if non-empty.
    if input_data.system_prompt_tokens > 0:
        candidates.append(
            CacheBreakpoint(
                position="system",
                index=0,
                estimated_tokens=input_data.system_prompt_tokens,
            )
        )

    # 2. Tool definitions — always second if present.
    if input_data.tool_definition_tokens > 0:
        candidates.append(
            CacheBreakpoint(
                position="tools",
                index=0,
                estimated_tokens=input_data.tool_definition_tokens,
            )
        )

    # 3. Context attachments — per-attachment, only above threshold.
    cacheable_context = [
        CacheBreakpoint(
            position="context",
            index=i,
            estimated_tokens=tokens,
        )
        for i, (_, tokens) in enumerate(input_data.context_attachments)
        if tokens >= input_data.threshold
    ]

    # If we're over the limit, drop the smallest context attachments.
    remaining_slots = MAX_BREAKPOINTS - len(candidates)
    if len(cacheable_context) > remaining_slots:
        # Keep the largest by token count, preserving request order.
        cacheable_context_sorted = sorted(
            cacheable_context, key=lambda bp: bp.estimated_tokens, reverse=True
        )
        keep_ids = {id(bp) for bp in cacheable_context_sorted[:remaining_slots]}
        cacheable_context = [bp for bp in cacheable_context if id(bp) in keep_ids]

    candidates.extend(cacheable_context)

    # Sanity check: never exceed the hard limit.
    assert len(candidates) <= MAX_BREAKPOINTS, (
        f"compute_breakpoints produced {len(candidates)} > "
        f"MAX_BREAKPOINTS ({MAX_BREAKPOINTS}). This is a bug."
    )

    return candidates


def estimate_cache_savings(breakpoints: list[CacheBreakpoint]) -> float:
    """Estimate the total input tokens saved by caching *breakpoints*.

    Each cached breakpoint avoids being re-processed on subsequent calls
    within the TTL window. The savings is the sum of estimated_tokens
    across all breakpoints.

    This is a coarse estimate; real savings depend on cache hit rate,
    TTL expiry, and provider-specific breakpoint slot limits.
    """
    return sum(bp.estimated_tokens for bp in breakpoints)
