"""OAuth handler for provider authentication flows.

Supports authorization-code (OAuth web) flows using a local HTTP server
to capture the callback, plus device-code flow for headless environments.
"""

from __future__ import annotations

import json
import logging
import random
import string
import time
import webbrowser
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any, Optional
from urllib.parse import parse_qs, urlencode, urlparse

from .manager import StoredCredential, save_credential

log = logging.getLogger(__name__)

OAUTH_TIMEOUT = 300  # 5 minutes


@dataclass
class OAuthConfig:
    """Configuration for an OAuth provider flow."""

    provider_id: str
    client_id: str
    client_secret: str
    auth_url: str
    token_url: str
    scopes: list[str] = field(default_factory=lambda: ["openai", "offline_access"])
    redirect_port: int = 8080
    extra_params: dict[str, str] = field(default_factory=dict)


@dataclass
class OAuthTokenResult:
    """Result of a successful OAuth token exchange."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 3600
    token_type: str = "Bearer"
    raw: dict[str, Any] = field(default_factory=dict)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server that captures a single OAuth callback."""

    auth_code: Optional[str] = None
    state: Optional[str] = None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization complete!</h1>")
            self.wfile.write(b"<p>You may close this tab and return to the CLI.</p></body></html>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing authorization code.")
        # Signal the server to shut down
        raise KeyboardInterrupt

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        log.debug("OAuth callback: %s", format % args)


def _generate_state() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=32))


def start_oauth_flow(config: OAuthConfig) -> OAuthTokenResult:
    """Start an OAuth authorization-code flow with a local callback server.

    Opens the user's browser, starts a local HTTP server to capture the
    authorization code, exchanges it for tokens, and returns the result.
    """
    state = _generate_state()
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.state = state

    # Build authorization URL
    params = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": f"http://127.0.0.1:{config.redirect_port}/callback",
        "scope": " ".join(config.scopes),
        "state": state,
    }
    params.update(config.extra_params)
    auth_url = f"{config.auth_url}?{urlencode(params)}"

    # Start local server
    server = HTTPServer(("127.0.0.1", config.redirect_port), OAuthCallbackHandler)
    server.timeout = OAUTH_TIMEOUT

    # Open browser
    webbrowser.open(auth_url)
    log.info("Browser opened to %s", auth_url)

    # Wait for callback
    deadline = time.time() + OAUTH_TIMEOUT
    while time.time() < deadline:
        server.handle_request()
        if OAuthCallbackHandler.auth_code is not None:
            break

    code = OAuthCallbackHandler.auth_code
    OAuthCallbackHandler.auth_code = None
    server.server_close()

    if not code:
        raise TimeoutError("OAuth authorization timed out after 300 seconds")

    return _exchange_code_for_token(code, config)


def _exchange_code_for_token(code: str, config: OAuthConfig) -> OAuthTokenResult:
    """Exchange an authorization code for an access token."""
    import urllib.request

    data = urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": f"http://127.0.0.1:{config.redirect_port}/callback",
            "client_id": config.client_id,
            "client_secret": config.client_secret,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        config.token_url,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"OAuth token exchange failed: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OAuth token exchange network error: {exc.reason}") from exc

    return OAuthTokenResult(
        access_token=body.get("access_token", ""),
        refresh_token=body.get("refresh_token"),
        expires_in=body.get("expires_in", 3600),
        token_type=body.get("token_type", "Bearer"),
        raw=body,
    )


def store_oauth_credential(
    provider_id: str,
    token_result: OAuthTokenResult,
    label: str = "oauth-default",
) -> StoredCredential:
    """Encrypt and store an OAuth token result."""
    import json as _json

    payload = _json.dumps(
        {
            "access_token": token_result.access_token,
            "refresh_token": token_result.refresh_token,
            "expires_in": token_result.expires_in,
            "token_type": token_result.token_type,
        }
    )
    from .manager import encrypt_credential

    cred = encrypt_credential(provider_id, payload)
    cred.label = label
    cred.auth_method = "oauth"
    if token_result.expires_in:
        cred.expires_at = time.time() + token_result.expires_in
    save_credential(cred)
    return cred
