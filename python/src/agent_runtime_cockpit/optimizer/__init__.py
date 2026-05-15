"""Prompt optimizer — local rule-based cleanup and token counting (P1b)."""
from __future__ import annotations

from .local import (
    TokenCount,
    OptimizationResult,
    count_tokens,
    optimize_prompt,
    estimate_cost,
    diff_prompts,
)

__all__ = [
    "TokenCount",
    "OptimizationResult",
    "count_tokens",
    "optimize_prompt",
    "estimate_cost",
    "diff_prompts",
]
