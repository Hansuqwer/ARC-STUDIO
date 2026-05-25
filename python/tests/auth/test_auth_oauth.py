"""Tests for OAuth flow (Phase 36.2). No live network calls."""

from __future__ import annotations

import json
import urllib.error

from agent_runtime_cockpit.auth.oauth import (
    OAuthConfig,
    OAuthTokenResult,
    _exchange_code_for_token,
    refresh_oauth_token,
    start_oauth_flow,
)


def test_oauth_config_defaults():
    """OAuthConfig sets reasonable defaults."""
    config = OAuthConfig(
        provider_id="openai",
        client_id="test-client",
        client_secret="test-secret",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com",
    )
    assert config.provider_id == "openai"
    assert config.redirect_port == 8080
    assert "openai" in config.scopes


def test_oauth_token_result_defaults():
    """OAuthTokenResult sets reasonable defaults."""
    result = OAuthTokenResult(access_token="tok-test-123")
    assert result.access_token == "tok-test-123"
    assert result.refresh_token is None
    assert result.expires_in == 3600
    assert result.token_type == "Bearer"


def test_exchange_code_for_token_success(monkeypatch):
    """Code exchange returns token when token endpoint succeeds."""
    responses = []

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "access_token": "tok-exchanged-456",
                    "refresh_token": "rtok-789",
                    "expires_in": 7200,
                    "token_type": "Bearer",
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout=30):
        responses.append(("urlopen", req.full_url, timeout))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
    )
    result = _exchange_code_for_token("auth-code-123", config)

    assert result.access_token == "tok-exchanged-456"
    assert result.refresh_token == "rtok-789"
    assert result.expires_in == 7200
    assert result.token_type == "Bearer"
    assert result.raw["access_token"] == "tok-exchanged-456"
    assert len(responses) == 1
    assert "token.example.com" in responses[0][1]


def test_exchange_code_for_token_http_error(monkeypatch):
    """Code exchange raises RuntimeError on HTTP error."""
    import io

    def fail_urlopen(req, timeout=30):
        raise urllib.error.HTTPError(
            url=req.full_url,
            code=400,
            msg="Bad Request",
            hdrs={},
            fp=io.BytesIO(),
        )

    monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
    )
    try:
        _exchange_code_for_token("bad-code", config)
        assert False, "Should have raised"
    except RuntimeError as exc:
        assert "OAuth token exchange failed" in str(exc)


def test_exchange_code_for_token_network_error(monkeypatch):
    """Code exchange raises RuntimeError on network error."""

    def fail_urlopen(req, timeout=30):
        raise urllib.error.URLError(reason="Connection refused")

    monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
    )
    try:
        _exchange_code_for_token("code", config)
        assert False, "Should have raised"
    except RuntimeError as exc:
        assert "OAuth token exchange network error" in str(exc)


def test_refresh_oauth_token_success(monkeypatch):
    """Token refresh returns new access token with preserved or new refresh token."""
    responses = []

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "access_token": "tok-refreshed-999",
                    "refresh_token": "rtok-refreshed-888",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout=30):
        responses.append(("refresh", req.full_url, timeout))
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
    )
    result = refresh_oauth_token(config, "rtok-old-123")

    assert result.access_token == "tok-refreshed-999"
    assert result.refresh_token == "rtok-refreshed-888"
    assert len(responses) == 1


def test_refresh_oauth_token_preserves_refresh_token(monkeypatch):
    """If server does not return a new refresh token, the old one is preserved."""

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "access_token": "tok-refreshed-777",
                }
            ).encode("utf-8")

    def fake_urlopen(req, timeout=30):
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
    )
    result = refresh_oauth_token(config, "rtok-old-456")
    assert result.access_token == "tok-refreshed-777"
    # Preserved old refresh token when server doesn't return new one
    assert result.refresh_token == "rtok-old-456"


def test_refresh_oauth_token_http_error(monkeypatch):
    """Token refresh raises RuntimeError on HTTP error."""
    import io

    def fail_urlopen(req, timeout=30):
        raise urllib.error.HTTPError(
            url=req.full_url,
            code=401,
            msg="Unauthorized",
            hdrs={},
            fp=io.BytesIO(),
        )

    monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
    )
    try:
        refresh_oauth_token(config, "rtok-invalid")
        assert False, "Should have raised"
    except RuntimeError as exc:
        assert "OAuth token refresh failed" in str(exc)


def test_refresh_oauth_token_network_error(monkeypatch):
    """Token refresh raises RuntimeError on network error."""

    def fail_urlopen(req, timeout=30):
        raise urllib.error.URLError(reason="Timeout")

    monkeypatch.setattr("urllib.request.urlopen", fail_urlopen)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
    )
    try:
        refresh_oauth_token(config, "rtok-old")
        assert False, "Should have raised"
    except RuntimeError as exc:
        assert "OAuth token refresh network error" in str(exc)


def test_store_oauth_credential_encrypts_token(monkeypatch, tmp_path):
    """store_oauth_credential encrypts the token and saves it."""
    import agent_runtime_cockpit.auth.oauth as oauth_mod
    import agent_runtime_cockpit.auth.manager as mgr

    auth_path = tmp_path / "auth.json"

    # Monkeypatch manager paths
    monkeypatch.setattr(mgr, "AUTH_PATH", auth_path)

    token = OAuthTokenResult(
        access_token="tok-live-123",
        refresh_token="rtok-456",
        expires_in=3600,
        token_type="Bearer",
    )
    cred = oauth_mod.store_oauth_credential("openai", token, label="my-oauth")
    assert cred.provider_id == "openai"
    assert cred.label == "my-oauth"
    assert cred.auth_method == "oauth"
    assert cred.credential_data != token.access_token  # should be encrypted


def test_start_oauth_flow_timeout(monkeypatch):
    """start_oauth_flow raises TimeoutError when no callback arrives."""
    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
    )

    # Monkeypatch the server to never receive a callback
    class TimeoutServer:
        def __init__(self, addr, handler):
            self.timeout = 0.1

        def handle_request(self):
            raise TimeoutError("OAuth authorization timed out after 300 seconds")

        def server_close(self):
            pass

    monkeypatch.setattr("agent_runtime_cockpit.auth.oauth.HTTPServer", TimeoutServer)

    try:
        start_oauth_flow(config)
        assert False, "Should have raised TimeoutError"
    except TimeoutError:
        pass
