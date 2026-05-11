"""
ARC HTTP Daemon

Starts a local aiohttp server on localhost:7777.
All endpoints return ARC protocol envelopes (JSON).
"""
from __future__ import annotations

import logging
import signal
from pathlib import Path

import aiohttp.web as web

from .routes import setup_routes

log = logging.getLogger(__name__)


async def create_app(workspace: Path | None = None) -> web.Application:
    app = web.Application()
    app["workspace"] = workspace or Path.cwd()
    setup_routes(app)
    return app


def run_server(host: str = "localhost", port: int = 7777,
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
