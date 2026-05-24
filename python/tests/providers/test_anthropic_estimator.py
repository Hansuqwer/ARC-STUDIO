"""Tests for the production tokenizer-based estimators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import pytest

from agent_runtime_cockpit.providers.anthropic_estimator import (
    AnthropicCountTokensEstimator,
    EstimateFallback,
    TiktokenApproximateEstimator,
    build_estimate_fn,
    select_estimator,
)

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


@dataclass
class _CountTokensStub:
    input_tokens: int


class _ClientStub:
    def __init__(self, returned_tokens: int):
        self.returned_tokens = returned_tokens
        self.calls: list[dict] = []
        self.messages = self

    def count_tokens(self, *, model: str, messages: list[dict]):
        self.calls.append({"model": model, "messages": messages})
        return _CountTokensStub(input_tokens=self.returned_tokens)


@dataclass
class _ResponseStub:
    model: str = "claude-sonnet-4-6"
    original_messages: Optional[list[dict]] = None
    content: Optional[str] = None
    content_chars: Optional[int] = None


# ---------------------------------------------------------------------------
# EstimateFallback protocol
# ---------------------------------------------------------------------------


def test_estimate_fallback_is_runtime_checkable():
    """EstimateFallback is a Protocol, usable with isinstance checks."""
    estimator = TiktokenApproximateEstimator()
    assert isinstance(estimator, EstimateFallback)


# ---------------------------------------------------------------------------
# AnthropicCountTokensEstimator
# ---------------------------------------------------------------------------


class TestAnthropicCountTokensEstimator:
    def test_uses_client_count_tokens(self):
        client = _ClientStub(returned_tokens=1234)
        estimator = AnthropicCountTokensEstimator(client=client)
        response = _ResponseStub(
            original_messages=[{"role": "user", "content": "hello"}],
        )
        input_tokens, output_tokens = estimator.estimate_tokens(response)

        assert input_tokens == 1234
        assert output_tokens == int(1234 * 0.32)  # default ratio
        assert client.calls[0]["model"] == "claude-sonnet-4-6"

    def test_missing_original_messages_raises(self):
        client = _ClientStub(returned_tokens=100)
        estimator = AnthropicCountTokensEstimator(client=client)
        response = _ResponseStub(original_messages=None)
        with pytest.raises(ValueError, match="original_messages"):
            estimator.estimate_tokens(response)

    def test_method_name_is_audit_ready(self):
        estimator = AnthropicCountTokensEstimator(client=_ClientStub(100))
        assert estimator.method_name == "anthropic-count-tokens"
        assert "anthropic" in estimator.method_name.lower()
        assert "count" in estimator.method_name.lower()

    def test_configurable_output_ratio(self):
        client = _ClientStub(returned_tokens=1000)
        estimator = AnthropicCountTokensEstimator(
            client=client,
            output_to_input_ratio=0.5,
        )
        response = _ResponseStub(
            original_messages=[{"role": "user", "content": "x"}],
        )
        _, output_tokens = estimator.estimate_tokens(response)
        assert output_tokens == 500


# ---------------------------------------------------------------------------
# TiktokenApproximateEstimator
# ---------------------------------------------------------------------------


class TestTiktokenApproximateEstimator:
    def test_counts_text_from_original_messages(self):
        estimator = TiktokenApproximateEstimator()
        response = _ResponseStub(
            original_messages=[
                {"role": "user", "content": "The quick brown fox jumps over"},
            ],
        )
        input_tokens, output_tokens = estimator.estimate_tokens(response)
        assert input_tokens >= 6  # raw count is ~7; with 1.15 bias >= 8
        assert output_tokens == int(input_tokens * 0.3)

    def test_counts_text_from_content_string(self):
        estimator = TiktokenApproximateEstimator()
        response = _ResponseStub(content="hello world this is a test")
        input_tokens, _ = estimator.estimate_tokens(response)
        assert input_tokens > 0

    def test_counts_text_from_content_chars_hint(self):
        estimator = TiktokenApproximateEstimator()
        response = _ResponseStub(content_chars=400)
        input_tokens, _ = estimator.estimate_tokens(response)
        # 400 'x' chars produce a measurable token count in cl100k
        assert input_tokens > 0

    def test_no_text_source_raises(self):
        estimator = TiktokenApproximateEstimator()
        response = _ResponseStub()  # nothing populated
        with pytest.raises(ValueError, match="Cannot extract text"):
            estimator.estimate_tokens(response)

    def test_handles_multi_part_content(self):
        estimator = TiktokenApproximateEstimator()
        response = _ResponseStub(
            original_messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Look at this:"},
                        {"type": "tool_use", "name": "search"},
                        {"type": "text", "text": "what do you think?"},
                    ],
                },
            ],
        )
        input_tokens, _ = estimator.estimate_tokens(response)
        assert input_tokens > 0

    def test_method_name_contains_approximate(self):
        """Audit invariant: estimated records produced by tiktoken must
        carry 'approximate' in the method name so auditors don't confuse
        them with measured or count_tokens-derived numbers.
        """
        estimator = TiktokenApproximateEstimator()
        assert "approximate" in estimator.method_name.lower()

    def test_bias_correction_applied(self):
        """Verify the bias_correction multiplier scales the raw count."""
        low = TiktokenApproximateEstimator(bias_correction=1.0)
        high = TiktokenApproximateEstimator(bias_correction=1.5)
        response = _ResponseStub(
            original_messages=[
                {"role": "user", "content": "The quick brown fox" * 20},
            ],
        )
        low_count, _ = low.estimate_tokens(response)
        high_count, _ = high.estimate_tokens(response)
        ratio = high_count / low_count
        assert 1.4 <= ratio <= 1.6


# ---------------------------------------------------------------------------
# select_estimator
# ---------------------------------------------------------------------------


class TestSelectEstimator:
    def test_prefers_sdk_when_client_available(self):
        client = _ClientStub(returned_tokens=100)
        estimator = select_estimator(prefer_sdk=True, sdk_client=client)
        assert isinstance(estimator, AnthropicCountTokensEstimator)

    def test_falls_back_to_tiktoken_when_no_client(self):
        estimator = select_estimator(prefer_sdk=True, sdk_client=None)
        assert isinstance(estimator, TiktokenApproximateEstimator)

    def test_explicit_no_sdk_returns_tiktoken_even_with_client(self):
        """Preflight callers pass prefer_sdk=False to avoid the
        count_tokens chicken-and-egg.
        """
        client = _ClientStub(returned_tokens=100)
        estimator = select_estimator(prefer_sdk=False, sdk_client=client)
        assert isinstance(estimator, TiktokenApproximateEstimator)


# ---------------------------------------------------------------------------
# build_estimate_fn
# ---------------------------------------------------------------------------


class TestBuildEstimateFn:
    def test_returns_callable_that_returns_token_counts(self):
        estimator = TiktokenApproximateEstimator()
        messages = [
            {
                "role": "user",
                "content": "hello world this is a longer text to produce enough tokens",
            }
        ]
        fn = build_estimate_fn(estimator, messages, model="claude-sonnet-4-6")
        input_tokens, output_tokens = fn()
        assert input_tokens > 0
        assert output_tokens > 0

    def test_works_with_anthropic_sdk_estimator(self):
        client = _ClientStub(returned_tokens=500)
        estimator = AnthropicCountTokensEstimator(client=client)
        messages = [{"role": "user", "content": "test"}]
        fn = build_estimate_fn(estimator, messages, model="claude-sonnet-4-6")
        input_tokens, output_tokens = fn()
        assert input_tokens == 500
        assert output_tokens == 160  # 500 * 0.32

    def test_sdk_estimator_uses_messages_count_tokens_with_model(self):
        calls = []

        class _StubMessages:
            def count_tokens(self, *, model, messages):
                calls.append({"model": model, "messages": messages})
                return _CountTokensStub(input_tokens=1234)

        class _StubClient:
            messages = _StubMessages()

        estimator = AnthropicCountTokensEstimator(_StubClient())
        fn = build_estimate_fn(
            estimator,
            request_messages=[{"role": "user", "content": "hi"}],
            model="claude-sonnet-4-6",
        )
        input_tokens, output_tokens = fn()

        assert calls == [
            {
                "model": "claude-sonnet-4-6",
                "messages": [{"role": "user", "content": "hi"}],
            }
        ]
        assert input_tokens == 1234
        assert output_tokens >= 1

    def test_sdk_estimator_rejects_missing_model(self):
        estimator = AnthropicCountTokensEstimator(_ClientStub(100))
        fn = build_estimate_fn(estimator, request_messages=[], model=None)
        with pytest.raises(ValueError, match="requires request.model"):
            fn()
