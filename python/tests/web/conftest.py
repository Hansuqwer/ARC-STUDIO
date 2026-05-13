"""Web-route test plumbing. Discovers the FastAPI/aiohttp app factory and yields
an httpx.AsyncClient bound to it via ASGI transport — never the network."""
from __future__ import annotations

import importlib
import pathlib
from typing import Any

import pytest


def _resolve_app(workspace: pathlib.Path) -> Any:
    candidates = [
        ("agent_runtime_cockpit.web.server", "create_app"),
        ("agent_runtime_cockpit.web.app", "build_app"),
        ("agent_runtime_cockpit.app", "build_app"),
        ("agent_runtime_cockpit.web.routes", "app"),
    ]
    last_err = None
    for mod_name, attr in candidates:
        try:
            mod = importlib.import_module(mod_name)
        except ImportError as e:
            last_err = e
            continue
        obj = getattr(mod, attr, None)
        if obj is None:
            continue
        # If it's a factory function, call it with workspace
        if callable(obj) and attr in ("build_app", "create_app"):
            return obj(workspace=workspace)
        return obj
    raise pytest.skip.Exception(f"no app entry point found ({last_err})")


@pytest.fixture
def workspace(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / ".arc" / "traces").mkdir(parents=True)
    (tmp_path / ".arc" / "audit").mkdir(parents=True)
    return tmp_path


@pytest.fixture
async def app(workspace):
    app_obj = _resolve_app(workspace)
    # If it's a coroutine, await it
    if hasattr(app_obj, '__await__'):
        app_obj = await app_obj
    return app_obj


@pytest.fixture
async def client(app):
    import httpx
    from aiohttp import web
    
    # Check if it's aiohttp or ASGI
    if isinstance(app, web.Application):
        # aiohttp app - use test client with wrapper
        from aiohttp.test_utils import TestClient, TestServer
        
        class ResponseWrapper:
            """Normalize aiohttp response to httpx-like interface."""
            def __init__(self, aiohttp_response):
                self._resp = aiohttp_response
                self.status_code = aiohttp_response.status
            
            async def json(self):
                return await self._resp.json()
            
            async def text(self):
                return await self._resp.text()
            
            @property
            def content(self):
                return self._resp.content
        
        class ClientWrapper:
            """Normalize aiohttp TestClient to httpx-like interface."""
            def __init__(self, aiohttp_client):
                self._client = aiohttp_client
            
            async def get(self, path, **kwargs):
                resp = await self._client.get(path, **kwargs)
                return ResponseWrapper(resp)
        
        async with TestServer(app) as server:
            async with TestClient(server) as c:
                yield ClientWrapper(c)
    else:
        # ASGI app - use httpx
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as c:
            yield c
