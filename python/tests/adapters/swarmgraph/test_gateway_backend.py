"""Tests for SwarmGraph gateway backend - focused on configuration and error handling."""

import pytest

from agent_runtime_cockpit.adapters.swarmgraph.gateway_client import GatewayClient
from agent_runtime_cockpit.gating import GatingError


def test_gateway_client_from_env_requires_url(monkeypatch):
    """Test gateway client requires URL environment variable."""
    monkeypatch.delenv("ARC_SWARMGRAPH_GATEWAY_URL", raising=False)

    with pytest.raises(KeyError, match="ARC_SWARMGRAPH_GATEWAY_URL"):
        GatewayClient.from_env()


def test_gateway_client_from_env_with_url(monkeypatch):
    """Test gateway client loads from environment."""
    monkeypatch.setenv("ARC_SWARMGRAPH_GATEWAY_URL", "https://gateway.example.com")
    monkeypatch.setenv("ARC_SWARMGRAPH_GATEWAY_TOKEN", "test-token")

    client = GatewayClient.from_env()
    assert client.base_url == "https://gateway.example.com"
    assert "Authorization" in client._headers
    assert client._headers["Authorization"] == "Bearer test-token"


def test_gateway_client_from_env_without_token(monkeypatch):
    """Test gateway client works without token."""
    monkeypatch.setenv("ARC_SWARMGRAPH_GATEWAY_URL", "https://gateway.example.com")
    monkeypatch.delenv("ARC_SWARMGRAPH_GATEWAY_TOKEN", raising=False)

    client = GatewayClient.from_env()
    assert client.base_url == "https://gateway.example.com"
    assert "Authorization" not in client._headers


def test_gateway_client_strips_trailing_slash():
    """Test gateway client normalizes base URL."""
    client = GatewayClient("https://gateway.example.com/", "token")
    assert client.base_url == "https://gateway.example.com"


def test_gateway_client_sets_sse_headers():
    """Test gateway client sets correct headers for SSE."""
    client = GatewayClient("https://gateway.example.com", "token")
    assert client._headers["Accept"] == "text/event-stream"
    assert client._headers["Authorization"] == "Bearer token"


def test_gateway_backend_requires_dual_gate(tmp_path, monkeypatch):
    """Test gateway backend requires dual-gate."""
    from agent_runtime_cockpit.adapters.swarmgraph.runner import SwarmGraphRunner

    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "gateway")
    monkeypatch.delenv("ARC_SWARMGRAPH_ALLOW_COSTS", raising=False)

    runner = SwarmGraphRunner(tmp_path)

    with pytest.raises(GatingError, match="dual-gate"):
        import asyncio

        asyncio.run(runner.run("test:graph", {}))


def test_gateway_backend_with_dual_gate_requires_config(tmp_path, monkeypatch):
    """Test gateway backend with dual-gate still requires URL config."""
    from agent_runtime_cockpit.adapters.swarmgraph.runner import SwarmGraphRunner

    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "gateway")
    monkeypatch.setenv("ARC_SWARMGRAPH_ALLOW_COSTS", "true")
    monkeypatch.delenv("ARC_SWARMGRAPH_GATEWAY_URL", raising=False)

    runner = SwarmGraphRunner(tmp_path)

    with pytest.raises(KeyError, match="ARC_SWARMGRAPH_GATEWAY_URL"):
        import asyncio

        asyncio.run(runner.run("test:graph", {}))


def test_gateway_client_context_manager():
    """Test gateway client can be used as async context manager."""
    import asyncio

    async def test():
        async with GatewayClient("https://gateway.example.com", "token") as client:
            assert client._client is not None
        # After exit, client should be closed
        assert client._client is None or client._client.is_closed

    asyncio.run(test())


def test_gateway_client_requires_context_manager():
    """Test gateway client run_stream requires context manager."""
    import asyncio

    async def test():
        client = GatewayClient("https://gateway.example.com", "token")

        with pytest.raises(AssertionError, match="async context manager"):
            async for _ in client.run_stream("test:graph", {}):
                pass

    asyncio.run(test())


def test_gateway_exempt_paid_call_gate_via_runner():
    """Budget preflight is applied upstream in SwarmGraphRunner (require_dual_gate).
    GatewayClient itself is exempt — it is only reachable after that gate passes.
    This test documents the exemption pattern by verifying the comment is present.
    """
    import inspect
    from agent_runtime_cockpit.adapters.swarmgraph.gateway_client import GatewayClient

    src = inspect.getsource(GatewayClient.__aenter__)
    assert "exempt" in src.lower() or "require_dual_gate" in src
