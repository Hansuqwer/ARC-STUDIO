"""Prompt optimizer — local rule-based cleanup and token counting (P1b)."""

from __future__ import annotations

from .local import (
    OptimizationResult,
    TokenCount,
    count_tokens,
    diff_prompts,
    estimate_cost,
    optimize_prompt,
)

__all__ = [
    "TokenCount",
    "OptimizationResult",
    "count_tokens",
    "optimize_prompt",
    "estimate_cost",
    "diff_prompts",
]
