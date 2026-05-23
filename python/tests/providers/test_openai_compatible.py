"""Tests for OpenAI-compatible provider client."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from agent_runtime_cockpit.cli_repl.cancellation import CancellationReason, CancellationToken
from agent_runtime_cockpit.providers.base import (
    AuthError,
    CancelledError,
    ProviderFeature,
    ProviderMessage,
    ProviderRequest,
    RateLimitError,
)
from agent_runtime_cockpit.providers.openai_compatible import (
    VENDOR_CONFIGS,
    OpenAICompatibleClient,
)


class TestVendorConfiguration:
    """Test vendor configuration and validation."""

    def test_all_vendors_have_required_fields(self):
        """All vendor configs must have required fields."""
        required_fields = {
            "base_url",
            "default_model",
            "supported_models",
            "features",
            "cost_rates",
        }
        for vendor, config in VENDOR_CONFIGS.items():
            assert set(config.keys()) == required_fields, f"Vendor {vendor} missing fields"

    def test_vendor_cost_rates_cover_supported_models(self):
        """Cost rates must cover all supported models."""
        for vendor, config in VENDOR_CONFIGS.items():
            supported = set(config["supported_models"])
            rated = set(config["cost_rates"].keys())
            assert supported == rated, f"Vendor {vendor} cost rates don't match models"

    def test_unknown_vendor_raises(self):
        """Unknown vendor should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown vendor"):
            OpenAICompatibleClient(vendor="unknown")  # type: ignore

    def test_openai_vendor_default(self):
        """OpenAI should be the default vendor."""
        client = OpenAICompatibleClient()
        caps = client.capabilities()
        assert caps.provider_id == "openai-openai"
        assert "OpenAI" in caps.provider_name

    def test_together_vendor_configuration(self):
        """Together vendor should have correct configuration."""
        client = OpenAICompatibleClient(vendor="together")
        caps = client.capabilities()
        assert caps.provider_id == "openai-together"
        assert "Together" in caps.provider_name
        assert "meta-llama" in caps.default_model

    def test_groq_vendor_configuration(self):
        """Groq vendor should have correct configuration."""
        client = OpenAICompatibleClient(vendor="groq")
        caps = client.capabilities()
        assert caps.provider_id == "openai-groq"
        assert "Groq" in caps.provider_name

    def test_llamacpp_vendor_has_zero_cost(self):
        """Local llama.cpp should have zero cost."""
        client = OpenAICompatibleClient(vendor="llamacpp")
        caps = client.capabilities()
        rates = caps.cost_rates["local-model"]
        assert rates.input_per_million == 0.0
        assert rates.output_per_million == 0.0


class TestCapabilities:
    """Test capabilities() method."""

    def test_capabilities_include_streaming_for_all_vendors(self):
        """All vendors should support streaming."""
        for vendor in VENDOR_CONFIGS:
            client = OpenAICompatibleClient(vendor=vendor)  # type: ignore
            caps = client.capabilities()
            assert ProviderFeature.STREAMING in caps.features

    def test_capabilities_tool_use_varies_by_vendor(self):
        """Tool use support varies by vendor."""
        # OpenAI, Together, Groq, Fireworks support tools
        for vendor in ["openai", "together", "groq", "fireworks"]:
            client = OpenAICompatibleClient(vendor=vendor)  # type: ignore
            caps = client.capabilities()
            assert ProviderFeature.TOOL_USE in caps.features

        # DeepInfra and llama.cpp don't support tools
        for vendor in ["deepinfra", "llamacpp"]:
            client = OpenAICompatibleClient(vendor=vendor)  # type: ignore
            caps = client.capabilities()
            assert ProviderFeature.TOOL_USE not in caps.features

    def test_capabilities_vision_only_openai(self):
        """Only OpenAI supports vision."""
        client = OpenAICompatibleClient(vendor="openai")
        caps = client.capabilities()
        assert ProviderFeature.VISION in caps.features

        # Other vendors don't support vision
        for vendor in ["together", "groq", "deepinfra", "fireworks", "llamacpp"]:
            client = OpenAICompatibleClient(vendor=vendor)  # type: ignore
            caps = client.capabilities()
            assert ProviderFeature.VISION not in caps.features

    def test_custom_base_url_override(self):
        """Custom base_url should override vendor default."""
        custom_url = "https://custom.example.com/v1"
        client = OpenAICompatibleClient(vendor="openai", base_url=custom_url)
        assert client._base_url == custom_url


class TestComplete:
    """Test complete() method."""

    @pytest.mark.asyncio
    async def test_complete_returns_response(self):
        """complete() should return ProviderResponse."""
        mock_response = Mock()
        mock_response.model = "gpt-4o-mini"
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Hello, world!"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAICompatibleClient(sdk_factory=lambda: mock_client)
        request = ProviderRequest(
            model="gpt-4o-mini",
            messages=[ProviderMessage(role="user", content="Hello")],
            max_tokens=100,
        )

        response = await client.complete(request, cancellation_token=CancellationToken())

        assert response.call_id == request.call_id
        assert response.model == "gpt-4o-mini"
        assert response.content == "Hello, world!"
        assert response.finish_reason == "stop"
        assert response.usage.input_tokens == 10
        assert response.usage.output_tokens == 5
        assert not response.degraded

    @pytest.mark.asyncio
    async def test_complete_missing_usage_returns_degraded(self):
        """complete() with missing usage should return degraded response."""
        mock_response = Mock()
        mock_response.model = "gpt-4o-mini"
        mock_response.choices = [Mock()]
        mock_response.choices[0].message = Mock()
        mock_response.choices[0].message.content = "Hello"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage = None

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response

        client = OpenAICompatibleClient(sdk_factory=lambda: mock_client)
        request = ProviderRequest(
            model="gpt-4o-mini",
            messages=[ProviderMessage(role="user", content="Hello")],
            max_tokens=100,
        )

        response = await client.complete(request, cancellation_token=CancellationToken())

        assert response.degraded
        assert response.degraded_reason == "provider usage data unavailable"
        assert response.usage.available is False


class TestStream:
    """Test stream() method."""

    @pytest.mark.asyncio
    async def test_stream_yields_start_delta_stop(self):
        """stream() should yield start, delta, and stop chunks."""
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock()]
        mock_chunk1.choices[0].delta = Mock()
        mock_chunk1.choices[0].delta.content = "Hello"
        mock_chunk1.usage = None

        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock()]
        mock_chunk2.choices[0].delta = Mock()
        mock_chunk2.choices[0].delta.content = " world"
        mock_chunk2.usage = Mock()
        mock_chunk2.usage.prompt_tokens = 10
        mock_chunk2.usage.completion_tokens = 5

        mock_client = Mock()
        mock_client.chat.completions.create.return_value = iter([mock_chunk1, mock_chunk2])

        client = OpenAICompatibleClient(sdk_factory=lambda: mock_client)
        request = ProviderRequest(
            model="gpt-4o-mini",
            messages=[ProviderMessage(role="user", content="Hello")],
            max_tokens=100,
        )

        chunks = []
        async for chunk in client.stream(request, cancellation_token=CancellationToken()):
            chunks.append(chunk)

        assert len(chunks) == 4  # start, delta, delta, stop
        assert chunks[0].chunk_type == "start"
        assert chunks[1].chunk_type == "delta"
        assert chunks[1].delta == "Hello"
        assert chunks[2].chunk_type == "delta"
        assert chunks[2].delta == " world"
        assert chunks[3].chunk_type == "stop"
        assert chunks[3].payload["usage"] is not None


class TestErrorMapping:
    """Test error mapping."""

    @pytest.mark.asyncio
    async def test_rate_limit_error_mapped(self):
        """Rate limit errors should map to RateLimitError."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Rate limit exceeded (429)")

        client = OpenAICompatibleClient(sdk_factory=lambda: mock_client)
        request = ProviderRequest(
            model="gpt-4o-mini",
            messages=[ProviderMessage(role="user", content="Hello")],
            max_tokens=100,
        )

        with pytest.raises(RateLimitError):
            await client.complete(request, cancellation_token=CancellationToken())

    @pytest.mark.asyncio
    async def test_auth_error_mapped(self):
        """Auth errors should map to AuthError."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("Invalid API key (401)")

        client = OpenAICompatibleClient(sdk_factory=lambda: mock_client)
        request = ProviderRequest(
            model="gpt-4o-mini",
            messages=[ProviderMessage(role="user", content="Hello")],
            max_tokens=100,
        )

        with pytest.raises(AuthError):
            await client.complete(request, cancellation_token=CancellationToken())


class TestCancellation:
    """Test cancellation handling."""

    @pytest.mark.asyncio
    async def test_cancelled_token_raises_cancelled_error(self):
        """Cancelled token should raise CancelledError."""
        mock_client = Mock()
        client = OpenAICompatibleClient(sdk_factory=lambda: mock_client)
        request = ProviderRequest(
            model="gpt-4o-mini",
            messages=[ProviderMessage(role="user", content="Hello")],
            max_tokens=100,
        )

        token = CancellationToken()
        token.cancel(CancellationReason.USER, "test cancellation")

        with pytest.raises(CancelledError):
            await client.complete(request, cancellation_token=token)

    @pytest.mark.asyncio
    async def test_cancel_adds_to_cancelled_calls(self):
        """cancel() should add call_id to cancelled set."""
        client = OpenAICompatibleClient()
        await client.cancel("test-call-id")
        assert "test-call-id" in client._cancelled_calls


class TestMultiVendorSupport:
    """Test multi-vendor support."""

    def test_all_vendors_instantiate(self):
        """All configured vendors should instantiate successfully."""
        for vendor in VENDOR_CONFIGS:
            client = OpenAICompatibleClient(vendor=vendor)  # type: ignore
            assert client is not None
            caps = client.capabilities()
            assert caps.provider_id == f"openai-{vendor}"

    def test_vendor_specific_models(self):
        """Each vendor should have its own model list."""
        openai_client = OpenAICompatibleClient(vendor="openai")
        openai_caps = openai_client.capabilities()
        assert "gpt-4o" in openai_caps.supported_models

        groq_client = OpenAICompatibleClient(vendor="groq")
        groq_caps = groq_client.capabilities()
        assert "llama-3.3-70b-versatile" in groq_caps.supported_models

    def test_vendor_specific_cost_rates(self):
        """Each vendor should have its own cost rates."""
        openai_client = OpenAICompatibleClient(vendor="openai")
        openai_caps = openai_client.capabilities()
        openai_rate = openai_caps.cost_rates["gpt-4o-mini"]
        assert openai_rate.input_per_million == 0.15

        groq_client = OpenAICompatibleClient(vendor="groq")
        groq_caps = groq_client.capabilities()
        groq_rate = groq_caps.cost_rates["llama-3.3-70b-versatile"]
        assert groq_rate.input_per_million == 0.59


class TestRequestKwargs:
    """Test request kwargs building."""

    def test_request_kwargs_basic(self):
        """_request_kwargs should build basic OpenAI request."""
        client = OpenAICompatibleClient()
        request = ProviderRequest(
            model="gpt-4o-mini",
            messages=[ProviderMessage(role="user", content="Hello")],
            max_tokens=100,
            temperature=0.7,
        )

        kwargs = client._request_kwargs(request, stream=False)

        assert kwargs["model"] == "gpt-4o-mini"
        assert kwargs["max_tokens"] == 100
        assert kwargs["temperature"] == 0.7
        assert kwargs["stream"] is False
        assert len(kwargs["messages"]) == 1
        assert kwargs["messages"][0]["role"] == "user"
        assert kwargs["messages"][0]["content"] == "Hello"

    def test_request_kwargs_with_tools(self):
        """_request_kwargs should include tools when provided."""
        client = OpenAICompatibleClient()
        tools = [{"type": "function", "function": {"name": "test"}}]
        request = ProviderRequest(
            model="gpt-4o-mini",
            messages=[ProviderMessage(role="user", content="Hello")],
            max_tokens=100,
            tools=tools,
        )

        kwargs = client._request_kwargs(request, stream=False)

        assert "tools" in kwargs
        assert kwargs["tools"] == tools

    def test_request_kwargs_with_stop_sequences(self):
        """_request_kwargs should include stop sequences when provided."""
        client = OpenAICompatibleClient()
        request = ProviderRequest(
            model="gpt-4o-mini",
            messages=[ProviderMessage(role="user", content="Hello")],
            max_tokens=100,
            stop_sequences=["STOP", "END"],
        )

        kwargs = client._request_kwargs(request, stream=False)

        assert "stop" in kwargs
        assert kwargs["stop"] == ["STOP", "END"]
