"""OAuth handler for provider authentication flows.

Supports authorization-code (OAuth web) flows using a local HTTP server
to capture the callback, plus PKCE (Proof Key for Code Exchange) for
improved security. Port is dynamically allocated to avoid conflicts.
"""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import random
import secrets
import socket
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
    redirect_port: int = 0  # 0 = dynamically allocated
    extra_params: dict[str, str] = field(default_factory=dict)
    use_pkce: bool = True


@dataclass
class OAuthTokenResult:
    """Result of a successful OAuth token exchange."""

    access_token: str
    refresh_token: Optional[str] = None
    expires_in: int = 3600
    token_type: str = "Bearer"
    raw: dict[str, Any] = field(default_factory=dict)


class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Minimal HTTP server that captures a single OAuth callback.

    Class-level attributes are set before the server starts:
        auth_code: Captured authorization code from the redirect.
        expected_state: The ``state`` parameter sent in the auth request;
            validated on callback to prevent CSRF.
    """

    auth_code: Optional[str] = None
    expected_state: Optional[str] = None
    _error: Optional[str] = None

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)

        # Validate state parameter (CSRF protection)
        received_state = params.get("state", [None])[0]
        if received_state is None or received_state != OAuthCallbackHandler.expected_state:
            OAuthCallbackHandler._error = "state_mismatch"
            self.send_response(400)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>State mismatch!</h1>")
            self.wfile.write(
                b"<p>CSRF validation failed. Close this tab and retry.</p></body></html>"
            )
            raise KeyboardInterrupt

        if "error" in params:
            OAuthCallbackHandler._error = params["error"][0]
            self.send_response(400)
            self.end_headers()
            self.wfile.write(
                b"<html><body><h1>Authorization denied!</h1>"
                b"<p>%s</p></body></html>" % params["error"][0].encode()
            )
            raise KeyboardInterrupt

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html><body><h1>Authorization complete!</h1>")
            self.wfile.write(b"<p>You may close this tab and return to the CLI.</p></body></html>")
        else:
            OAuthCallbackHandler._error = "missing_code"
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing authorization code.")
        # Signal the server to shut down
        raise KeyboardInterrupt

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        log.debug("OAuth callback: %s", format % args)


def _generate_state() -> str:
    """Generate a cryptographically random state string for CSRF protection."""
    return secrets.token_urlsafe(32)


def _generate_code_verifier() -> str:
    """Generate a PKCE code verifier (43-128 unreserved characters)."""
    return secrets.token_urlsafe(64)[:128]


def _generate_code_challenge(verifier: str) -> str:
    """Generate a PKCE code challenge (S256 method)."""
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def _find_free_port() -> int:
    """Bind to an ephemeral port and return the assigned port number."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _generate_state() -> str:
    return "".join(random.choices(string.ascii_letters + string.digits, k=32))


def start_oauth_flow(config: OAuthConfig) -> OAuthTokenResult:
    """Start an OAuth authorization-code flow with a local callback server.

    Dynamically allocates a local port, optionally uses PKCE for improved
    security, validates the ``state`` parameter on callback (CSRF protection),
    exchanges the authorization code for tokens, and returns the result.
    """
    # Allocate dynamic port and update config so token exchange uses same URI
    if config.redirect_port == 0:
        config.redirect_port = _find_free_port()
    redirect_uri = f"http://127.0.0.1:{config.redirect_port}/callback"

    # Generate PKCE challenge if enabled
    code_verifier = _generate_code_verifier() if config.use_pkce else None
    code_challenge = _generate_code_challenge(code_verifier) if code_verifier else None

    # Generate state for CSRF protection
    state = _generate_state()
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.expected_state = state
    OAuthCallbackHandler._error = None

    # Build authorization URL
    params: dict[str, str] = {
        "client_id": config.client_id,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(config.scopes),
        "state": state,
    }
    if code_challenge:
        params["code_challenge_method"] = "S256"
        params["code_challenge"] = code_challenge
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
        if OAuthCallbackHandler.auth_code is not None or OAuthCallbackHandler._error:
            break

    error = OAuthCallbackHandler._error
    code = OAuthCallbackHandler.auth_code
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.expected_state = None
    OAuthCallbackHandler._error = None
    server.server_close()

    if error:
        raise RuntimeError(f"OAuth authorization denied: {error}")

    if not code:
        raise TimeoutError("OAuth authorization timed out after 300 seconds")

    return _exchange_code_for_token(code, config, code_verifier=code_verifier)


def _exchange_code_for_token(
    code: str,
    config: OAuthConfig,
    code_verifier: Optional[str] = None,
) -> OAuthTokenResult:
    """Exchange an authorization code for an access token.

    If PKCE is enabled (``code_verifier`` provided), the verifier is sent
    with the token request. Client secret is still included for providers
    that require it alongside PKCE.
    """
    import urllib.request

    redirect_uri = f"http://127.0.0.1:{config.redirect_port}/callback"
    payload: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
        "client_id": config.client_id,
        "client_secret": config.client_secret,
    }
    if code_verifier:
        payload["code_verifier"] = code_verifier

    data = urlencode(payload).encode("utf-8")

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


def refresh_oauth_token(config: OAuthConfig, refresh_token: str) -> OAuthTokenResult:
    """Refresh an expired OAuth access token using a refresh token.

    Uses the OAuth provider's token endpoint with ``grant_type=refresh_token``
    to obtain a new access token without user interaction.
    """
    import urllib.request
    import urllib.error

    data = urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
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
        raise RuntimeError(f"OAuth token refresh failed: {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"OAuth token refresh network error: {exc.reason}") from exc

    return OAuthTokenResult(
        access_token=body.get("access_token", ""),
        refresh_token=body.get("refresh_token", refresh_token),
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
