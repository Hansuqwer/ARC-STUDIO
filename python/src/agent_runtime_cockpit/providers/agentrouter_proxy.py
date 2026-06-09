"""Local AgentRouter OpenAI-compatible proxy for opencode.

The proxy is intentionally small: it forwards OpenAI-style ``/v1/models`` and
``/v1/chat/completions`` requests to a configured AgentRouter-compatible
upstream while keeping the upstream API key out of opencode config.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin

from aiohttp import ClientError, ClientSession, ClientTimeout, web

DEFAULT_BASE_URL = "https://api.agentrouter.org/v1"
DEFAULT_PORT = 8787
DEFAULT_HOST = "127.0.0.1"
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_BODY_BYTES = 1_048_576


class AgentRouterProxyConfigError(RuntimeError):
    """Raised when required proxy config is missing or invalid."""


@dataclass(frozen=True)
class AgentRouterProxyConfig:
    api_key: str
    base_url: str = DEFAULT_BASE_URL
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    default_model: str | None = None
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    max_body_bytes: int = DEFAULT_MAX_BODY_BYTES

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "AgentRouterProxyConfig":
        source = os.environ if env is None else env
        api_key = source.get("AGENTROUTER_API_KEY", "").strip()
        if not api_key:
            raise AgentRouterProxyConfigError("AGENTROUTER_API_KEY is required")
        port_raw = source.get("ARC_AGENTROUTER_PROXY_PORT", str(DEFAULT_PORT))
        try:
            port = int(port_raw)
        except ValueError as exc:
            raise AgentRouterProxyConfigError(
                "ARC_AGENTROUTER_PROXY_PORT must be an integer"
            ) from exc
        if port <= 0 or port > 65535:
            raise AgentRouterProxyConfigError("ARC_AGENTROUTER_PROXY_PORT must be 1-65535")
        return cls(
            api_key=api_key,
            base_url=source.get("AGENTROUTER_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            port=port,
            default_model=source.get("ARC_AGENTROUTER_DEFAULT_MODEL") or None,
        )


AGENTROUTER_CONFIG_KEY = web.AppKey("agentrouter_config", AgentRouterProxyConfig)


def redacted(text: str, config: AgentRouterProxyConfig) -> str:
    """Redact configured secrets from error text."""
    return text.replace(config.api_key, "[REDACTED]") if config.api_key else text


def create_agentrouter_proxy_app(config: AgentRouterProxyConfig) -> web.Application:
    app = web.Application(client_max_size=config.max_body_bytes)
    app[AGENTROUTER_CONFIG_KEY] = config
    app.router.add_get("/v1/models", _models)
    app.router.add_post("/v1/chat/completions", _chat_completions)
    app.router.add_get("/health", _health)
    return app


async def _health(_request: web.Request) -> web.Response:
    return web.json_response({"ok": True, "provider": "agentrouter", "proxy": "local"})


async def _models(request: web.Request) -> web.StreamResponse:
    return await _forward(request, "GET", "models")


async def _chat_completions(request: web.Request) -> web.StreamResponse:
    config = request.app[AGENTROUTER_CONFIG_KEY]
    body = await _read_json_body(request)
    if config.default_model and not body.get("model"):
        body["model"] = config.default_model
    return await _forward(request, "POST", "chat/completions", body)


async def _read_json_body(request: web.Request) -> dict[str, Any]:
    config = request.app[AGENTROUTER_CONFIG_KEY]
    if request.content_length and request.content_length > config.max_body_bytes:
        raise web.HTTPRequestEntityTooLarge(
            max_size=config.max_body_bytes,
            actual_size=request.content_length,
        )
    try:
        body = await request.json()
    except Exception as exc:  # noqa: BLE001 - convert client parse errors to JSON envelope.
        raise web.HTTPBadRequest(
            text='{"error":{"message":"invalid JSON request body","type":"invalid_request"}}',
            content_type="application/json",
        ) from exc
    if not isinstance(body, dict):
        raise web.HTTPBadRequest(
            text='{"error":{"message":"request body must be a JSON object","type":"invalid_request"}}',
            content_type="application/json",
        )
    return body


async def _forward(
    request: web.Request, method: str, endpoint: str, json_body: dict[str, Any] | None = None
) -> web.StreamResponse:
    config = request.app[AGENTROUTER_CONFIG_KEY]
    url = urljoin(f"{config.base_url}/", endpoint)
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Accept": request.headers.get("Accept", "application/json"),
    }
    if json_body is not None:
        headers["Content-Type"] = "application/json"
    timeout = ClientTimeout(total=config.timeout_seconds, sock_read=config.timeout_seconds)
    try:
        # R-PERF8: TCPConnector with limit_per_host=10 for connection pooling.
        from aiohttp import TCPConnector

        connector = TCPConnector(limit_per_host=10)
        async with ClientSession(timeout=timeout, connector=connector) as session:
            async with session.request(method, url, json=json_body, headers=headers) as response:
                if json_body and json_body.get("stream") is True:
                    return await _stream_upstream(request, response)
                data = await response.read()
                return web.Response(
                    body=data,
                    status=response.status,
                    headers={
                        "Content-Type": response.headers.get("Content-Type", "application/json")
                    },
                )
    except asyncio.TimeoutError:
        return _error_response(504, "upstream timeout")
    except ClientError as exc:
        return _error_response(502, redacted(str(exc), config))


async def _stream_upstream(request: web.Request, response: Any) -> web.StreamResponse:
    proxy_response = web.StreamResponse(
        status=response.status,
        headers={"Content-Type": response.headers.get("Content-Type", "text/event-stream")},
    )
    await proxy_response.prepare(request)
    async for chunk in response.content.iter_chunked(8192):
        await proxy_response.write(chunk)
    await proxy_response.write_eof()
    return proxy_response


def _error_response(status: int, message: str) -> web.Response:
    return web.json_response(
        {"error": {"message": message, "type": "agentrouter_proxy_error"}}, status=status
    )


def proxy_bind_host() -> str:
    """Return the only supported default bind host."""
    return DEFAULT_HOST


def run_agentrouter_proxy(config: AgentRouterProxyConfig) -> None:
    web.run_app(create_agentrouter_proxy_app(config), host=config.host, port=config.port)
