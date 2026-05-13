"""
ARC HTTP Daemon

Starts a local aiohttp server on 127.0.0.1:7777.
All endpoints return ARC protocol envelopes (JSON).
Optional bearer token auth via ARC_DAEMON_TOKEN env var.
"""
from __future__ import annotations

import hmac
import logging
import os
import signal
from pathlib import Path

import aiohttp.web as web

from .keys import WORKSPACE_KEY
from .routes import setup_routes

log = logging.getLogger(__name__)

HEALTH_PATH = "/health"
TOKEN_ENV = "ARC_DAEMON_TOKEN"


@web.middleware
async def bearer_token_middleware(
    request: web.Request, handler: web.RequestHandler
) -> web.Response:
    """Optional bearer-token authentication.

    When ARC_DAEMON_TOKEN is set, all requests except /health must
    carry Authorization: Bearer <token>. The comparison is constant-time.
    When the env var is unset, pass-through (local-only default).
    """
    token = os.environ.get(TOKEN_ENV)
    if token is None:
        return await handler(request)

    # /health stays open for liveness probes
    if request.path == HEALTH_PATH:
        return await handler(request)

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return web.json_response(
            {"error": "missing Authorization: Bearer <token> header"},
            status=401,
        )

    provided = auth.removeprefix("Bearer ")
    if not hmac.compare_digest(provided, token):
        return web.json_response(
            {"error": "invalid bearer token"},
            status=401,
        )

    return await handler(request)


async def create_app(workspace: Path | None = None) -> web.Application:
    app = web.Application(middlewares=[bearer_token_middleware])
    ws = workspace or Path.cwd()
    app[WORKSPACE_KEY] = ws
    setup_routes(app)
    return app


def run_server(host: str = "127.0.0.1", port: int = 7777,
               workspace: Path | None = None) -> None:
    import asyncio

    async def _run() -> None:
        app = await create_app(workspace)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()
        log.info("ARC daemon listening on http://%s:%d", host, port)
        print(f"  ARC daemon running at http://{host}:{port}")
        print(f"  Workspace: {workspace or Path.cwd()}")
        print("  Press Ctrl+C to stop.")

        # Wait for SIGINT/SIGTERM
        stop = asyncio.Event()
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, stop.set)
            except NotImplementedError:
                pass  # Windows

        await stop.wait()
        await runner.cleanup()
        log.info("ARC daemon stopped.")

    asyncio.run(_run())
