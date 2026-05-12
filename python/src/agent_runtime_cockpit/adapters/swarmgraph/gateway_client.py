"""Thin SSE client for the ARC SwarmGraph gateway."""
from __future__ import annotations

import json
import os
from typing import Any, AsyncIterator

import httpx


class GatewayClient:
    def __init__(self, base_url: str, token: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self._headers = {"Accept": "text/event-stream"}
        if token:
            self._headers["Authorization"] = f"Bearer {token}"
        self._client: httpx.AsyncClient | None = None

    @classmethod
    def from_env(cls) -> "GatewayClient":
        base = os.environ["ARC_SWARMGRAPH_GATEWAY_URL"]
        token = os.environ.get("ARC_SWARMGRAPH_GATEWAY_TOKEN")
        return cls(base, token)

    async def __aenter__(self) -> "GatewayClient":
        self._client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, read=None))
        return self

    async def __aexit__(self, *exc: Any) -> None:
        if self._client:
            await self._client.aclose()

    async def run_stream(self, entrypoint: str, inputs: dict[str, Any]) -> AsyncIterator[dict[str, Any]]:
        assert self._client, "use as async context manager"
        async with self._client.stream(
            "POST",
            f"{self.base_url}/run",
            headers=self._headers,
            json={"entrypoint": entrypoint, "inputs": inputs},
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line or not line.startswith("data:"):
                    continue
                payload = line[5:].strip()
                if payload == "[DONE]":
                    return
                yield json.loads(payload)
