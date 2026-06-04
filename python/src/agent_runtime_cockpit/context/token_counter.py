"""Provider-aware token counter.

Public API::

    from agent_runtime_cockpit.context.token_counter import estimate_tokens

    n = estimate_tokens("hello world", provider="anthropic")
    n = estimate_tokens(data_store.entries, provider="openai")

Priority:
  anthropic → AnthropicCountTokensEstimator if client available, else heuristic
  openai    → tiktoken (cl100k_base) if installed, else heuristic
  other     → heuristic: max(1, int(len(text) / 4 * 1.33))

Results are LRU-cached (256 entries) keyed on (content_hash, provider).
Never calls the remote count_tokens API per-keystroke.

context_limit == 0 means unknown — callers must not compute percentages from 0.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from typing import Any

_HEURISTIC_CHARS_PER_TOKEN = 4
_HEURISTIC_BUFFER = 1.33


def _heuristic(text: str) -> int:
    return max(1, int(len(text) / _HEURISTIC_CHARS_PER_TOKEN * _HEURISTIC_BUFFER)) if text else 0


@lru_cache(maxsize=256)
def _cached_estimate(content_hash: str, provider: str | None, length: int) -> int:
    """Inner cached computation — keyed on hash+provider, not raw content."""
    if provider == "anthropic":
        try:
            from ..providers.anthropic_estimator import TiktokenApproximateEstimator

            est = TiktokenApproximateEstimator()
            # Use tiktoken-based approximation; the SDK count_tokens API requires
            # a live client and is too expensive to call per-keystroke.
            return est.estimate_tokens_from_length(length)
        except Exception:
            pass
    if provider == "openai":
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            # We don't have the text here (only hash + length); fall through to heuristic.
            # Callers that need tiktoken accuracy should call estimate_tokens with the text.
            del enc
        except Exception:
            pass
    # Default heuristic
    return max(1, int(length / _HEURISTIC_CHARS_PER_TOKEN * _HEURISTIC_BUFFER)) if length else 0


def estimate_tokens(
    content: str | list[Any],
    *,
    provider: str | None = None,
) -> int:
    """Estimate the token count for *content*.

    Args:
        content: A string or list of TranscriptEntry (or any object with a
                 `.content` str attribute).
        provider: Optional provider name hint ("anthropic", "openai", …).
                  Unknown providers fall back to the heuristic.

    Returns:
        Estimated token count (always ≥ 0).
    """
    if isinstance(content, str):
        text = content
    else:
        # List of transcript entries or dicts
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif hasattr(item, "content"):
                parts.append(str(item.content))
            elif isinstance(item, dict):
                parts.append(str(item.get("content", "")))
        text = " ".join(parts)

    if not text:
        return 0

    length = len(text)
    # Hash only the first 512 chars to keep cache key computation cheap.
    content_hash = hashlib.md5(text[:512].encode(), usedforsecurity=False).hexdigest()
    norm_provider = (provider or "").lower() or None

    if norm_provider == "anthropic":
        try:
            from ..providers.anthropic_estimator import TiktokenApproximateEstimator

            est = TiktokenApproximateEstimator()
            if hasattr(est, "estimate_tokens_from_text"):
                return est.estimate_tokens_from_text(text)
            # Fallback: use length-based estimate from the estimator
            return _cached_estimate(content_hash, norm_provider, length)
        except Exception:
            return _heuristic(text)

    if norm_provider == "openai":
        try:
            import tiktoken

            enc = tiktoken.get_encoding("cl100k_base")
            return len(enc.encode(text))
        except Exception:
            return _heuristic(text)

    return _heuristic(text)


__all__ = ["estimate_tokens"]
