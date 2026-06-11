"""ARC HTTP Daemon.

Starts a local aiohttp server on 127.0.0.1:7777.
All endpoints return ARC protocol envelopes (JSON).
Bearer token auth via ARC_DAEMON_TOKEN env var.
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
ALLOW_UNAUTH_ENV = "ARC_DAEMON_ALLOW_UNAUTHENTICATED"
MUTATING_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})
MUTATING_GET_PATHS = frozenset({"/api/runs/start"})
MAX_REQUEST_BODY_BYTES = 512 * 1024


def _allowed_origins() -> set[str]:
    configured = os.environ.get("ARC_CORS_ORIGIN", "http://127.0.0.1:3000")
    return {origin.strip() for origin in configured.split(",") if origin.strip()}


@web.middleware
async def bearer_token_middleware(
    request: web.Request, handler: web.RequestHandler
) -> web.Response:
    """Bearer-token authentication.

    All requests except /health must carry Authorization: Bearer <token> unless
    ARC_DAEMON_ALLOW_UNAUTHENTICATED=1 is set for tests/local experiments.
    """
    token = os.environ.get(TOKEN_ENV)
    if token is None and os.environ.get(ALLOW_UNAUTH_ENV) == "1":
        return await handler(request)

    # /health stays open for liveness probes
    if request.path == HEALTH_PATH:
        return await handler(request)

    if token is None:
        return web.json_response(
            {"error": f"{TOKEN_ENV} required; set {ALLOW_UNAUTH_ENV}=1 only for local tests"},
            status=401,
        )

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


@web.middleware
async def request_security_middleware(
    request: web.Request, handler: web.RequestHandler
) -> web.StreamResponse:
    if request.method in MUTATING_METHODS or request.path in MUTATING_GET_PATHS:
        length = request.content_length
        if length is not None and length > MAX_REQUEST_BODY_BYTES:
            return web.json_response(
                {"error": "payload exceeds 512 KB limit"},
                status=413,
            )
        origin = request.headers.get("Origin")
        referer = request.headers.get("Referer")
        allowed = _allowed_origins()
        if origin and origin not in allowed:
            return web.json_response({"error": "origin not allowed"}, status=403)
        if not origin and referer and not any(referer.startswith(base) for base in allowed):
            return web.json_response({"error": "referer not allowed"}, status=403)
    return await handler(request)


async def create_app(workspace: Path | None = None) -> web.Application:
    app = web.Application(
        middlewares=[request_security_middleware, bearer_token_middleware],
        client_max_size=MAX_REQUEST_BODY_BYTES,
    )
    ws = workspace or Path.cwd()
    app[WORKSPACE_KEY] = ws
    setup_routes(app)
    return app


def run_server(host: str = "127.0.0.1", port: int = 7777, workspace: Path | None = None) -> None:
    import asyncio

    async def _run() -> None:
        app = await create_app(workspace)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, host, port)
        await site.start()

        # --- ADDITIVE (arc-v2 Sprint 1, ADR-0004): optional UDS listener.   ---
        # Default OFF; enabled only via ARC_ENABLE_UDS=1. HTTP+SSE on loopback
        # stays canonical and untouched. Rollback = delete this block.
        if os.environ.get("ARC_ENABLE_UDS") == "1":
            runtime_dir = Path(
                os.environ.get("ARC_RUNTIME_DIR", str(Path.home() / ".arc"))
            )
            runtime_dir.mkdir(parents=True, exist_ok=True)
            sock_path = runtime_dir / "arc-daemon.sock"
            sock_path.unlink(missing_ok=True)
            uds_site = web.UnixSite(runner, path=str(sock_path))
            await uds_site.start()
            os.chmod(sock_path, 0o600)  # owner-only; permission test in Sprint 12
            log.info("ARC daemon UDS listener at %s (mode 0600)", sock_path)
        # --- end additive UDS block ---

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
