from __future__ import annotations

import asyncio

import pytest
from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from agent_runtime_cockpit.providers.agentrouter_proxy import (
    AgentRouterProxyConfig,
    AgentRouterProxyConfigError,
    POOL_LIMIT_PER_HOST,
    create_agentrouter_proxy_app,
    get_pool_stats,
    proxy_bind_host,
)


async def _client(app: web.Application) -> TestClient:
    client = TestClient(TestServer(app))
    await client.start_server()
    return client


@pytest.mark.asyncio
async def test_missing_agentrouter_key_returns_config_error():
    with pytest.raises(AgentRouterProxyConfigError, match="AGENTROUTER_API_KEY"):
        AgentRouterProxyConfig.from_env({})


@pytest.mark.asyncio
async def test_models_proxies_upstream_models():
    async def models(request: web.Request) -> web.Response:
        assert request.headers["Authorization"] == "Bearer sk-test-secret"
        return web.json_response({"object": "list", "data": [{"id": "agentrouter/test"}]})

    upstream_app = web.Application()
    upstream_app.router.add_get("/v1/models", models)
    upstream = await _client(upstream_app)
    proxy = await _client(
        create_agentrouter_proxy_app(
            AgentRouterProxyConfig(api_key="sk-test-secret", base_url=str(upstream.make_url("/v1")))
        )
    )
    try:
        response = await proxy.get("/v1/models")
        assert response.status == 200
        payload = await response.json()
        assert payload["data"][0]["id"] == "agentrouter/test"
    finally:
        await proxy.close()
        await upstream.close()


@pytest.mark.asyncio
async def test_chat_completions_forwards_body_and_auth():
    seen = {}

    async def chat(request: web.Request) -> web.Response:
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = await request.json()
        return web.json_response({"choices": [{"message": {"content": "ok"}}]})

    upstream_app = web.Application()
    upstream_app.router.add_post("/v1/chat/completions", chat)
    upstream = await _client(upstream_app)
    proxy = await _client(
        create_agentrouter_proxy_app(
            AgentRouterProxyConfig(
                api_key="sk-test-secret",
                base_url=str(upstream.make_url("/v1")),
                default_model="agentrouter/default",
            )
        )
    )
    try:
        response = await proxy.post("/v1/chat/completions", json={"messages": []})
        assert response.status == 200
        assert seen["auth"] == "Bearer sk-test-secret"
        assert seen["body"]["model"] == "agentrouter/default"
    finally:
        await proxy.close()
        await upstream.close()


@pytest.mark.asyncio
async def test_upstream_failure_redacts_secret():
    proxy = await _client(
        create_agentrouter_proxy_app(
            AgentRouterProxyConfig(api_key="sk-test-secret", base_url="http://sk-test-secret.local")
        )
    )
    try:
        response = await proxy.get("/v1/models")
        payload = await response.json()
        assert response.status == 502
        assert "sk-test-secret" not in str(payload)
        assert "[REDACTED]" in str(payload)
    finally:
        await proxy.close()


@pytest.mark.asyncio
async def test_timeout_returns_json_error():
    async def slow(_request: web.Request) -> web.Response:
        await asyncio.sleep(0.2)
        return web.json_response({})

    upstream_app = web.Application()
    upstream_app.router.add_get("/v1/models", slow)
    upstream = await _client(upstream_app)
    proxy = await _client(
        create_agentrouter_proxy_app(
            AgentRouterProxyConfig(
                api_key="sk-test-secret",
                base_url=str(upstream.make_url("/v1")),
                timeout_seconds=0.01,
            )
        )
    )
    try:
        response = await proxy.get("/v1/models")
        payload = await response.json()
        assert response.status == 504
        assert payload["error"]["type"] == "agentrouter_proxy_error"
    finally:
        await proxy.close()
        await upstream.close()


@pytest.mark.asyncio
async def test_request_size_cap_rejects_oversized_body():
    proxy = await _client(
        create_agentrouter_proxy_app(
            AgentRouterProxyConfig(api_key="sk-test-secret", max_body_bytes=16)
        )
    )
    try:
        response = await proxy.post("/v1/chat/completions", data="x" * 128)
        assert response.status == 413
    finally:
        await proxy.close()


def test_proxy_binds_only_to_loopback_by_default():
    assert proxy_bind_host() == "127.0.0.1"


@pytest.mark.asyncio
async def test_pool_stats_schema_and_limit():
    app = create_agentrouter_proxy_app(AgentRouterProxyConfig(api_key="sk-test-secret"))
    proxy = await _client(app)
    try:
        stats = get_pool_stats(app)
        assert stats["limit_per_host"] == POOL_LIMIT_PER_HOST == 10
        assert stats["session_open"] is True
        assert "active_connections" in stats
    finally:
        await proxy.close()


def test_env_config_port_and_base_url():
    config = AgentRouterProxyConfig.from_env(
        {
            "AGENTROUTER_API_KEY": "sk-test-secret",
            "AGENTROUTER_BASE_URL": "https://example.test/v1/",
            "ARC_AGENTROUTER_PROXY_PORT": "8788",
            "ARC_AGENTROUTER_DEFAULT_MODEL": "agentrouter/model",
        }
    )
    assert config.base_url == "https://example.test/v1"
    assert config.port == 8788
    assert config.default_model == "agentrouter/model"
