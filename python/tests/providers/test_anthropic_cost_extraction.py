"""Tests for Anthropic cost extraction from provider responses."""

from __future__ import annotations

from decimal import Decimal

import pytest

from agent_runtime_cockpit.protocol.cost_record import CostRecord
from agent_runtime_cockpit.providers import (
    CostExtractionError,
    CostRates,
    ProviderCapability,
    ProviderFeature,
    ProviderResponse,
    UsageRecord,
    extract_cost,
)


def _capability(model: str = "claude-sonnet-4-6") -> ProviderCapability:
    return ProviderCapability(
        provider_id="anthropic",
        provider_name="Anthropic",
        supported_models=[model],
        default_model=model,
        features=[ProviderFeature.STREAMING],
        max_context_tokens=200_000,
        cost_rates={
            model: CostRates(
                input_per_million=3.0,
                output_per_million=15.0,
                cache_write_per_million=3.75,
                cache_read_per_million=0.30,
            ),
        },
    )


_USAGE = UsageRecord(input_tokens=100, output_tokens=20)
_DEGRADED_USAGE = UsageRecord(available=False, input_tokens=0, output_tokens=0)


def _response(
    model: str = "claude-sonnet-4-6",
    usage: UsageRecord = _USAGE,
    degraded: bool = False,
) -> ProviderResponse:
    return ProviderResponse(
        call_id="test-call",
        model=model,
        content="ok",
        finish_reason="stop",
        usage=usage,
        degraded=degraded,
        degraded_reason="provider usage data unavailable" if degraded else None,
    )


# ---------------------------------------------------------------------------
# Standalone extract_cost
# ---------------------------------------------------------------------------


class TestExtractCost:
    def test_computes_cost_from_usage(self):
        """100 input @ $3/M + 20 output @ $15/M = $0.00060."""
        cost = extract_cost(_response(), _capability())
        assert cost.provider_id == "anthropic"
        assert cost.model == "claude-sonnet-4-6"
        assert cost.input_tokens == 100
        assert cost.output_tokens == 20
        assert cost.cost_usd == Decimal("0.00060000")
        assert cost.source == "measured"
        assert cost.degraded is False
        assert cost.currency == "USD"

    def test_uses_cache_rates_when_present(self):
        """100 input + 5 cache_creation + 3 cache_read + 20 output."""
        usage = UsageRecord(
            input_tokens=100,
            output_tokens=20,
            cache_creation_input_tokens=5,
            cache_read_input_tokens=3,
        )
        cost = extract_cost(_response(usage=usage), _capability())
        # input: 100 * 3.0 / 1_000_000 = 0.0003
        # output: 20 * 15.0 / 1_000_000 = 0.0003
        # cache_write: 5 * 3.75 / 1_000_000 = 0.00001875
        # cache_read: 3 * 0.30 / 1_000_000 = 0.0000009
        # total: 0.00061965
        assert cost.cost_usd == Decimal("0.00061965")
        assert cost.source == "measured"
        assert cost.degraded is False

    def test_degraded_response_uses_estimated_source(self):
        """When usage is unavailable, source='estimated' and degraded=True."""
        cost = extract_cost(_response(usage=_DEGRADED_USAGE, degraded=True), _capability())
        assert cost.source == "estimated"
        assert cost.degraded is True
        # Estimated cost should be non-zero (uses fallback tokens)
        assert cost.cost_usd > Decimal("0")

    def test_estimated_uses_100_input_32_output_fallback(self):
        """Degraded estimation uses 100 input / 32 output default."""
        cost = extract_cost(_response(usage=_DEGRADED_USAGE, degraded=True), _capability())
        # 100 * 3.0 / 1_000_000 = 0.0003
        # 32 * 15.0 / 1_000_000 = 0.00048
        assert cost.cost_usd == Decimal("0.00078000")
        assert cost.input_tokens == 0  # actual usage, not estimated
        assert cost.output_tokens == 0

    def test_degraded_with_partial_usage_uses_max(self):
        """When degraded but input_tokens is non-zero, use max(actual, 100)."""
        usage = UsageRecord(available=False, input_tokens=200, output_tokens=0)
        cost = extract_cost(_response(usage=usage, degraded=True), _capability())
        # 200 * 3.0 / 1_000_000 = 0.0006
        # 32 * 15.0 / 1_000_000 = 0.00048
        assert cost.cost_usd == Decimal("0.00108000")

    def test_raises_cost_extraction_error_for_unknown_model(self):
        """A model not in cost_rates raises CostExtractionError, not KeyError."""
        with pytest.raises(CostExtractionError, match="not in rate map"):
            extract_cost(_response(model="unknown-model"), _capability())

    def test_unknown_model_error_lists_configured_models(self):
        """Error message must enumerate configured models for operator diagnosis."""
        cap = _capability(model="claude-sonnet-4-6")
        with pytest.raises(CostExtractionError) as excinfo:
            extract_cost(_response(model="claude-opus-4-7"), cap)
        message = str(excinfo.value)
        assert "claude-sonnet-4-6" in message
        assert "claude-opus-4-7" in message
        assert "anthropic" in message

    def test_cost_extraction_error_is_non_retryable(self):
        """CostExtractionError is a configuration bug, not transient."""
        with pytest.raises(CostExtractionError) as excinfo:
            extract_cost(_response(model="unknown-model"), _capability())
        assert excinfo.value.retryable is False

    def test_quantized_cost(self):
        """Cost is quantized to 8 decimal places with ROUND_HALF_EVEN."""
        usage = UsageRecord(input_tokens=1, output_tokens=1)
        cost = extract_cost(_response(usage=usage), _capability())
        # 1 * 3.0 / 1_000_000 = 0.000003
        # 1 * 15.0 / 1_000_000 = 0.000015
        # total: 0.000018
        assert cost.cost_usd == Decimal("0.00001800")

    def test_quantized_method(self):
        """CostRecord.quantized() returns a copy with rounded cost."""
        cost = extract_cost(_response(), _capability())
        quantized = cost.quantized()
        assert quantized.cost_usd == cost.cost_usd
        assert quantized is not cost  # copy, not same instance

    def test_total_tokens_property(self):
        """total_tokens sums all token fields."""
        usage = UsageRecord(
            input_tokens=100,
            output_tokens=20,
            cache_creation_input_tokens=5,
            cache_read_input_tokens=3,
        )
        cost = extract_cost(_response(usage=usage), _capability())
        assert cost.total_tokens == 128

    def test_roundtrip_via_model_dump(self):
        """CostRecord can be serialized to JSON and back."""
        cost = extract_cost(_response(), _capability())
        dumped = cost.model_dump(mode="json")
        restored = CostRecord.model_validate(dumped)
        assert restored.cost_usd == cost.cost_usd
        assert restored.source == cost.source
        assert restored.model_dump(mode="json") == dumped


# ---------------------------------------------------------------------------
# AnthropicClient.extract_cost integration
# ---------------------------------------------------------------------------


class TestAnthropicClientExtractCost:
    def test_client_extract_cost_returns_cost_record(self):
        """AnthropicClient.extract_cost() wraps the standalone function."""
        from agent_runtime_cockpit.providers.anthropic import AnthropicClient

        client = AnthropicClient()
        cost = client.extract_cost(_response())
        assert isinstance(cost, CostRecord)
        assert cost.provider_id == "anthropic"
        assert cost.source == "measured"

    def test_client_extract_cost_degraded(self):
        """Client method handles degraded responses."""
        from agent_runtime_cockpit.providers.anthropic import AnthropicClient

        client = AnthropicClient()
        cost = client.extract_cost(_response(usage=_DEGRADED_USAGE, degraded=True))
        assert cost.degraded is True
        assert cost.source == "estimated"
