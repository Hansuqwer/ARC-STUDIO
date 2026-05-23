"""Contract test for ProviderClient implementations."""

from __future__ import annotations

from agent_runtime_cockpit.providers.client import (
    ProviderCapabilities,
    ProviderClient,
    ProviderMessage,
)


class _FakeProviderClient:
    name = "fake"

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            streaming=True, tool_use=False, prompt_caching=False, vision=False, json_mode=False
        )

    def complete(self, messages, *, model, max_tokens):
        return ProviderMessage(role="assistant", content="ok")

    def stream(self, messages, *, model, max_tokens):
        yield "ok"

    async def astream(self, messages, *, model, max_tokens):
        yield "ok"

    def stream_tool_calls(self, messages, tools, *, model):
        return iter(())


def test_fake_implements_protocol():
    assert isinstance(_FakeProviderClient(), ProviderClient)


def test_fake_capabilities_round_trip():
    caps = _FakeProviderClient().capabilities()
    assert caps.streaming is True
    assert caps.tool_use is False


def test_registry_empty_by_default():
    from agent_runtime_cockpit.providers.registry import known

    assert known() == []
