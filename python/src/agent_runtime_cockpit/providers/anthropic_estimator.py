"""Production estimators for Anthropic cost preflight and degraded paths.

Lock: ADR-011 (cost source tagging), ADR-018 (protocol placement)
Phase: 4 Slice 3.5

Two estimators with different accuracy/dependency tradeoffs:

1. :class:`AnthropicCountTokensEstimator` — uses the Anthropic SDK's
   first-party ``count_tokens()`` method. Most accurate. Requires a
   configured client (network + valid API key). Anthropic does not bill
   ``count_tokens`` calls but they consume rate-limit capacity.

2. :class:`TiktokenApproximateEstimator` — uses tiktoken's ``cl100k_base``
   encoding as a coarse local proxy. Off by ~10-15% for Claude (different
   tokenizer family). Fast, local, no network.

Selection policy (caller's responsibility):
- Preflight (before any provider call): TiktokenApproximate to avoid
  the chicken-and-egg of "call count_tokens to estimate the cost of
  calling count_tokens."
- Degraded path (post-call, usage missing): AnthropicCountTokens if
  the session already has a working client; TiktokenApproximate otherwise.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

# ---------------------------------------------------------------------------
# EstimateFallback protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EstimateFallback(Protocol):
    """Protocol for a token estimator used in the degraded/estimated path.

    Implementations must produce an (input_tokens, output_tokens) estimate
    from a response-like object. The estimate is used to compute a USD cost
    when the provider returned no usage data.
    """

    method_name: str

    def estimate_tokens(self, response: Any) -> tuple[int, int]:
        """Return (input_tokens, output_tokens) for *response*."""
        ...


# ---------------------------------------------------------------------------
# Anthropic SDK estimator
# ---------------------------------------------------------------------------


class _CountTokensClient(Protocol):
    """Minimal shape for the Anthropic SDK's token counter.

    Defined as a Protocol so tests can inject a stub without dragging in
    the real SDK.
    """

    @property
    def messages(self) -> _MessagesClient: ...


class _MessagesClient(Protocol):
    def count_tokens(self, *, model: str, messages: list[dict]) -> _CountTokensResult: ...


class _CountTokensResult(Protocol):
    input_tokens: int


@dataclass
class AnthropicCountTokensEstimator:
    """Estimator backed by ``anthropic.messages.count_tokens``.

    Counts only input tokens — output is unknowable pre-call. Uses a
    fixed-ratio multiplier (default 0.3) to estimate output as a
    fraction of input. The multiplier is configurable per session.

    Requires a *client* implementing the ``count_tokens`` protocol
    (e.g., a real ``anthropic.Anthropic`` instance or a test stub).
    """

    client: _CountTokensClient
    method_name: str = "anthropic-count-tokens"
    output_to_input_ratio: float = 0.32

    def estimate_tokens(self, response: Any) -> tuple[int, int]:
        """Estimate (input_tokens, output_tokens) for *response*.

        Expects the response to have ``.original_messages`` (a list of
        Anthropic-shaped message dicts) and ``.model``. The caller
        (typically ``AnthropicClient.complete()``) must attach these in
        the degraded path.
        """
        original_messages = getattr(response, "original_messages", None)
        if original_messages is None:
            raise ValueError(
                "Response has no .original_messages; AnthropicClient "
                "must attach these in the degraded path. Falling back "
                "to TiktokenApproximate is the caller's responsibility."
            )
        model = getattr(response, "model", None)
        if not model:
            raise ValueError(
                "AnthropicCountTokensEstimator requires request.model to be set; got None or empty"
            )
        result = self.client.messages.count_tokens(model=model, messages=original_messages)
        input_tokens = result.input_tokens
        output_tokens = max(1, int(input_tokens * self.output_to_input_ratio))
        return input_tokens, output_tokens


# ---------------------------------------------------------------------------
# Tiktoken estimator
# ---------------------------------------------------------------------------


@dataclass
class TiktokenApproximateEstimator:
    """Estimator backed by tiktoken.

    Uses ``cl100k_base`` encoding (OpenAI's tokenizer) as a coarse proxy
    for Claude's tokenizer. Empirically ~10-15% lower token count than
    Claude's actual tokenizer on English prose; for code and structured
    text the gap is smaller (~5%).

    The ``method_name`` carries ``"approximate"`` explicitly so audit trails
    cannot confuse this with measured cost data.
    """

    method_name: str = "tiktoken-cl100k-approximate"
    output_to_input_ratio: float = 0.3
    bias_correction: float = 1.15

    _encoding: Any = field(init=False, repr=False, default=None)

    def __post_init__(self):
        try:
            import tiktoken

            self._encoding = tiktoken.get_encoding("cl100k_base")
        except ImportError as exc:
            raise ImportError(
                "TiktokenApproximateEstimator requires the 'tiktoken' package. "
                "Install with: pip install tiktoken"
            ) from exc

    def estimate_tokens(self, response: Any) -> tuple[int, int]:
        """Estimate (input_tokens, output_tokens) for *response*.

        Handles two shapes:

        1. Response with ``.original_messages`` (degraded post-call path)
        2. Response with ``.content`` (str) (preflight estimation)

        Falls back through content_chars if neither is populated.
        """
        text = self._extract_text(response)
        raw_count = len(self._encoding.encode(text))
        corrected = int(raw_count * self.bias_correction)
        output = int(corrected * self.output_to_input_ratio)
        return corrected, output

    def _extract_text(self, response: Any) -> str:
        original_messages = getattr(response, "original_messages", None)
        if original_messages is not None:
            return "\n\n".join(_stringify_message_content(m) for m in original_messages)

        content = getattr(response, "content", None)
        if isinstance(content, str):
            return content

        content_chars = getattr(response, "content_chars", None)
        if content_chars is not None:
            return "x" * content_chars

        raise ValueError(
            "Cannot extract text for token estimation from response. "
            "Provide .original_messages, .content (str), or .content_chars."
        )


def _stringify_message_content(message: dict) -> str:
    """Coerce an Anthropic-shaped message to plain text for tokenization."""
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for block in content:
            if isinstance(block, dict):
                if block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif block.get("type") == "tool_use":
                    parts.append(f"[tool_use: {block.get('name', '')}]")
                elif block.get("type") == "tool_result":
                    parts.append(str(block.get("content", "")))
        return "\n".join(parts)
    return str(content)


# ---------------------------------------------------------------------------
# Selection helper
# ---------------------------------------------------------------------------


def select_estimator(
    *,
    prefer_sdk: bool = True,
    sdk_client: _CountTokensClient | None = None,
) -> EstimateFallback:
    """Construct the best available estimator.

    If *prefer_sdk* is ``True`` and *sdk_client* is provided, returns
    :class:`AnthropicCountTokensEstimator`. Otherwise returns
    :class:`TiktokenApproximateEstimator`.

    Callers in the preflight path should pass ``prefer_sdk=False`` to
    avoid the chicken-and-egg problem of "call count_tokens to estimate
    the cost of calling count_tokens."
    """
    if prefer_sdk and sdk_client is not None:
        return AnthropicCountTokensEstimator(client=sdk_client)
    return TiktokenApproximateEstimator()


# ---------------------------------------------------------------------------
# Convenience: build a token-count function for extract_cost
# ---------------------------------------------------------------------------


def build_estimate_fn(
    estimator: EstimateFallback,
    request_messages: list[dict[str, Any]],
    model: str | None = None,
) -> Callable[[], tuple[int, int]]:
    """Build a closure that the cost-extraction pipeline can call.

    Wraps *estimator* and *request_messages* into a callable that takes
    no arguments and returns ``(input_tokens, output_tokens)``.

    Usage from ``AnthropicClient.complete()``::

        cost = extract_cost(
            response,
            self.capabilities(),
            estimate_fn=build_estimate_fn(estimator, request_kwargs["messages"]),
        )
    """

    def _estimate() -> tuple[int, int]:
        ns = _Namespace(original_messages=request_messages, model=model)
        return estimator.estimate_tokens(ns)

    return _estimate


class _Namespace:
    """Minimal namespace for passing data to estimators."""

    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)
