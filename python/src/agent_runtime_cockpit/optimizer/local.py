"""Local prompt optimizer — rule-based cleanup and token counting (P1b).

Provides:
  - count_tokens: token counting via tiktoken (fallback to word estimate)
  - optimize_prompt: rule-based whitespace/indentation cleanup
  - estimate_cost: cost estimation from known model pricing
  - diff_prompts: structural comparison of two prompts

No provider calls are made. Works fully offline.
"""
from __future__ import annotations

import difflib
import logging
import re
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, Field

log = logging.getLogger(__name__)


class TokenCount(BaseModel):
    """Token count result for a piece of text."""

    count: int
    encoding: str
    model: str = ""


class OptimizationResult(BaseModel):
    """Result of a prompt optimization."""

    original: str
    optimized: str
    original_tokens: TokenCount
    optimized_tokens: TokenCount
    tokens_saved: int
    changes: list[str] = Field(default_factory=list)


KNOWN_MODEL_ENCODINGS: dict[str, str] = {
    "gpt-4": "cl100k_base",
    "gpt-4o": "o200k_base",
    "gpt-4o-mini": "o200k_base",
    "gpt-3.5-turbo": "cl100k_base",
    "text-embedding-3-small": "cl100k_base",
    "text-embedding-3-large": "cl100k_base",
}


def count_tokens(text: str, model: str = "gpt-4") -> TokenCount:
    """Count tokens in text using tiktoken.

    Falls back to a word-count estimate if tiktoken is not installed
    or if the encoding fails.
    """
    encoding_name = KNOWN_MODEL_ENCODINGS.get(model, "cl100k_base")
    try:
        import tiktoken

        enc = tiktoken.get_encoding(encoding_name)
        tokens = enc.encode(text)
        return TokenCount(count=len(tokens), encoding=encoding_name, model=model)
    except ImportError:
        log.debug("tiktoken not installed — using character-based token estimate")
        estimated = len(text.split())
        return TokenCount(count=estimated, encoding="word-estimate", model=model)
    except Exception as e:
        log.warning("tiktoken encoding failed for %s: %s", encoding_name, e)
        estimated = len(text.split())
        return TokenCount(count=estimated, encoding="word-estimate", model=model)


RULES: list[tuple[str, str, str]] = [
    ("collapse_whitespace", r"\n{3,}", "\n\n"),
    ("strip_trailing_whitespace", r"[ \t]+$", ""),
    ("normalize_indent", r"^[ \t]{8,}", "    "),
    ("remove_trailing_newlines", r"\n+$", "\n"),
]


def optimize_prompt(prompt: str, model: str = "gpt-4") -> OptimizationResult:
    """Apply rule-based optimization to a prompt.

    Rules applied (in order):
      1. Collapse 3+ consecutive newlines to 2.
      2. Strip trailing whitespace from each line.
      3. Normalize over-deep indentation to 4 spaces.
      4. Remove trailing newlines (keep one).

    No provider calls are made.
    """
    original_tokens = count_tokens(prompt, model)
    optimized = prompt
    changes: list[str] = []
    for rule_name, pattern, replacement in RULES:
        new_text = re.sub(pattern, replacement, optimized, flags=re.MULTILINE)
        if new_text != optimized:
            changes.append(rule_name)
            optimized = new_text
    optimized_tokens = count_tokens(optimized, model)
    return OptimizationResult(
        original=prompt,
        optimized=optimized,
        original_tokens=original_tokens,
        optimized_tokens=optimized_tokens,
        tokens_saved=original_tokens.count - optimized_tokens.count,
        changes=changes,
    )


@dataclass
class ModelPricing:
    """Pricing for a model (USD per 1K tokens)."""

    model: str
    input_per_1k: float
    output_per_1k: float


KNOWN_PRICING: dict[str, ModelPricing] = {
    "gpt-4o": ModelPricing("gpt-4o", 0.0025, 0.01),
    "gpt-4o-mini": ModelPricing("gpt-4o-mini", 0.00015, 0.0006),
    "gpt-4": ModelPricing("gpt-4", 0.03, 0.06),
    "gpt-3.5-turbo": ModelPricing("gpt-3.5-turbo", 0.0005, 0.0015),
}


def estimate_cost(token_count: int, model: str) -> Optional[float]:
    """Estimate cost for input tokens given known pricing.

    Returns None if pricing for the given model is unknown.
    """
    pricing = KNOWN_PRICING.get(model)
    if pricing is None:
        return None
    return (token_count / 1000.0) * pricing.input_per_1k


def diff_prompts(
    prompt_a: str,
    prompt_b: str,
    context_lines: int = 3,
) -> str:
    """Return a unified-diff string comparing two prompts.

    Useful for 'arc prompt diff' CLI command.
    """
    lines_a = prompt_a.splitlines(keepends=True)
    lines_b = prompt_b.splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(
            lines_a,
            lines_b,
            fromfile="prompt_a",
            tofile="prompt_b",
            n=context_lines,
        )
    )
