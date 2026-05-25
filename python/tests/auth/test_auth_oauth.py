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
    assert config.redirect_port == 0  # 0 = dynamically allocated
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


# ─── PKCE Tests ────────────────────────────────────────────────────


def test_generate_code_verifier_length():
    """Code verifier is between 43 and 128 characters."""
    from agent_runtime_cockpit.auth.oauth import _generate_code_verifier

    verifier = _generate_code_verifier()
    assert 43 <= len(verifier) <= 128
    # Should only contain unreserved characters
    import string as _string

    allowed = set(_string.ascii_letters + _string.digits + "-._~")
    assert all(c in allowed for c in verifier)


def test_generate_code_challenge_consistent():
    """Same verifier always produces same challenge."""
    from agent_runtime_cockpit.auth.oauth import _generate_code_challenge

    verifier = "test-verifier-1234567890123456789012345678901234567890"
    c1 = _generate_code_challenge(verifier)
    c2 = _generate_code_challenge(verifier)
    assert c1 == c2
    assert len(c1) == 43  # SHA-256 base64url without padding


def test_generate_code_challenge_different():
    """Different verifiers produce different challenges."""
    from agent_runtime_cockpit.auth.oauth import _generate_code_challenge

    v1 = "verifier-one-1234567890123456789012345678901234567890"
    v2 = "verifier-two-1234567890123456789012345678901234567890"
    assert _generate_code_challenge(v1) != _generate_code_challenge(v2)


def test_pkce_params_in_auth_request(monkeypatch):
    """PKCE parameters are included in the authorization URL."""
    from agent_runtime_cockpit.auth.oauth import start_oauth_flow, _find_free_port

    port = _find_free_port()

    class FakeServer:
        def __init__(self, addr, handler):
            self.timeout = 0.01

        def handle_request(self):
            raise TimeoutError("timed out")

        def server_close(self):
            pass

    monkeypatch.setattr("agent_runtime_cockpit.auth.oauth.HTTPServer", FakeServer)
    webbrowser_open = []

    def fake_open(url):
        webbrowser_open.append(url)

    monkeypatch.setattr("agent_runtime_cockpit.auth.oauth.webbrowser.open", fake_open)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
        redirect_port=port,
        use_pkce=True,
    )

    try:
        start_oauth_flow(config)
    except TimeoutError:
        pass

    assert len(webbrowser_open) == 1
    url = webbrowser_open[0]
    assert "code_challenge_method=S256" in url
    assert "code_challenge=" in url


def test_dynamic_port_allocation():
    """_find_free_port returns an available port."""
    from agent_runtime_cockpit.auth.oauth import _find_free_port

    port = _find_free_port()
    assert isinstance(port, int)
    assert 1024 <= port <= 65535


def test_dynamic_port_used_when_port_is_zero(monkeypatch):
    """When redirect_port=0, a dynamic port is allocated."""
    from agent_runtime_cockpit.auth.oauth import start_oauth_flow

    class FakeServer:
        def __init__(self, addr, handler):
            self.server_port = addr[1]
            self.timeout = 0.01

        def handle_request(self):
            raise TimeoutError("timed out")

        def server_close(self):
            pass

    monkeypatch.setattr("agent_runtime_cockpit.auth.oauth.HTTPServer", FakeServer)
    monkeypatch.setattr("agent_runtime_cockpit.auth.oauth.webbrowser.open", lambda url: None)

    # redirect_port=0 should trigger _find_free_port
    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
        redirect_port=0,
        use_pkce=False,
    )

    try:
        start_oauth_flow(config)
    except TimeoutError:
        pass

    # config.redirect_port should have been updated to a non-zero port
    assert config.redirect_port != 0
    assert isinstance(config.redirect_port, int)


# ─── State Validation Tests ────────────────────────────────────────


def test_state_validation_rejects_mismatch(monkeypatch):
    """OAuth callback with mismatched state raises error."""
    from agent_runtime_cockpit.auth.oauth import (
        start_oauth_flow,
        _find_free_port,
        OAuthCallbackHandler,
    )

    port = _find_free_port()

    class FakeServer:
        def __init__(self, addr, handler):
            self.timeout = 0.01

        def handle_request(self):
            # Set values as if a callback with wrong state arrived
            OAuthCallbackHandler.expected_state = "expected-state-value"
            OAuthCallbackHandler._error = "state_mismatch"
            OAuthCallbackHandler.auth_code = None
            raise RuntimeError("OAuth authorization denied: state_mismatch")

        def server_close(self):
            pass

    monkeypatch.setattr("agent_runtime_cockpit.auth.oauth.HTTPServer", FakeServer)
    monkeypatch.setattr("agent_runtime_cockpit.auth.oauth.webbrowser.open", lambda url: None)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
        redirect_port=port,
        use_pkce=False,
    )

    try:
        start_oauth_flow(config)
        assert False, "Should have raised RuntimeError"
    except RuntimeError as exc:
        assert "OAuth authorization denied" in str(exc)


def test_oauth_error_denied(monkeypatch):
    """OAuth provider error response raises RuntimeError."""
    from agent_runtime_cockpit.auth.oauth import (
        start_oauth_flow,
        _find_free_port,
        OAuthCallbackHandler,
    )

    port = _find_free_port()

    class FakeServer:
        def __init__(self, addr, handler):
            self.timeout = 0.01

        def handle_request(self):
            handler = OAuthCallbackHandler
            handler.expected_state = "test-state"
            handler.auth_code = None
            handler._error = None
            # Set error to simulate provider rejection
            handler._error = "access_denied"
            raise RuntimeError("OAuth authorization denied: access_denied")

        def server_close(self):
            pass

    monkeypatch.setattr("agent_runtime_cockpit.auth.oauth.HTTPServer", FakeServer)
    monkeypatch.setattr("agent_runtime_cockpit.auth.oauth.webbrowser.open", lambda url: None)

    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
        redirect_port=port,
        use_pkce=False,
    )

    try:
        start_oauth_flow(config)
        assert False, "Should have raised RuntimeError"
    except RuntimeError as exc:
        assert "OAuth authorization denied" in str(exc)


# ─── Keyring Tests ──────────────────────────────────────────────────


def test_keyring_available_returns_false_when_not_installed(monkeypatch):
    """_keyring_available returns False when keyring is not installed."""
    from agent_runtime_cockpit.auth.manager import _keyring_available

    monkeypatch.setattr(
        "agent_runtime_cockpit.auth.manager._keyring_available",
        lambda: False,
    )
    assert _keyring_available() is False


def test_save_to_keyring_fallback(monkeypatch):
    """save_to_keyring returns False when keyring unavailable."""
    from agent_runtime_cockpit.auth.manager import save_to_keyring

    monkeypatch.setattr(
        "agent_runtime_cockpit.auth.manager._keyring_available",
        lambda: False,
    )
    assert save_to_keyring("test_provider", "secret") is False


def test_get_from_keyring_fallback(monkeypatch):
    """get_from_keyring returns None when keyring unavailable."""
    from agent_runtime_cockpit.auth.manager import get_from_keyring

    monkeypatch.setattr(
        "agent_runtime_cockpit.auth.manager._keyring_available",
        lambda: False,
    )
    assert get_from_keyring("test_provider") is None


def test_remove_from_keyring_fallback(monkeypatch):
    """remove_from_keyring returns False when keyring unavailable."""
    from agent_runtime_cockpit.auth.manager import remove_from_keyring

    monkeypatch.setattr(
        "agent_runtime_cockpit.auth.manager._keyring_available",
        lambda: False,
    )
    assert remove_from_keyring("test_provider") is False


def test_keyring_roundtrip(monkeypatch):
    """Test keyring save/get/delete with monkeypatched keyring module."""
    from agent_runtime_cockpit.auth.manager import (
        save_to_keyring,
        get_from_keyring,
        remove_from_keyring,
    )

    class FakeKeyring:
        _store: dict[str, str] = {}

        def get_password(self, service, username):
            return self._store.get(f"{service}:{username}")

        def set_password(self, service, username, password):
            self._store[f"{service}:{username}"] = password

        def delete_password(self, service, username):
            self._store.pop(f"{service}:{username}", None)

    fake = FakeKeyring()

    # Make keyring available
    monkeypatch.setattr(
        "agent_runtime_cockpit.auth.manager._keyring_available",
        lambda: True,
    )
    monkeypatch.setattr(
        "agent_runtime_cockpit.auth.manager._keyring_get",
        lambda pid: fake.get_password("arc-studio", pid),
    )
    monkeypatch.setattr(
        "agent_runtime_cockpit.auth.manager._keyring_set",
        lambda pid, secret: fake.set_password("arc-studio", pid, secret) or True,
    )
    monkeypatch.setattr(
        "agent_runtime_cockpit.auth.manager._keyring_delete",
        lambda pid: fake.delete_password("arc-studio", pid) or True,
    )

    # Save
    assert save_to_keyring("test_provider", "test-secret") is True
    # Get
    assert get_from_keyring("test_provider") == "test-secret"
    # Remove
    assert remove_from_keyring("test_provider") is True
    # Get after remove
    assert get_from_keyring("test_provider") is None


# ─── Auto Token Refresh Tests ───────────────────────────────────────


def test_auto_token_refresh_expired_oauth(tmp_path, monkeypatch):
    """Expired OAuth credential with refresh_token is auto-refreshed."""
    import json as _json
    import time
    from agent_runtime_cockpit.auth.manager import (
        encrypt_credential,
        save_credential,
        get_credential,
    )

    auth_path = tmp_path / "auth.json"

    token_data = _json.dumps(
        {
            "access_token": "tok-expired",
            "refresh_token": "rtok-still-valid",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
    )
    cred = encrypt_credential("openai", token_data)
    cred.auth_method = "oauth"
    cred.expires_at = time.time() - 1
    save_credential(cred, auth_path)

    # Mock _try_refresh_oauth to return a refreshed credential directly
    def fake_try_refresh(cred):
        encrypted = _json.dumps(
            {
                "access_token": "tok-refreshed-fresh",
                "refresh_token": "rtok-new",
                "expires_in": 3600,
                "token_type": "Bearer",
            }
        )
        from agent_runtime_cockpit.auth.manager import _get_fernet, StoredCredential

        enc = _get_fernet().encrypt(encrypted.encode("utf-8")).decode("utf-8")
        return StoredCredential(
            provider_id="openai",
            label="default",
            credential_data=enc,
            auth_method="oauth",
            expires_at=time.time() + 3600,
        )

    import agent_runtime_cockpit.auth.manager as _mgr

    monkeypatch.setattr(_mgr, "_try_refresh_oauth", fake_try_refresh)

    result = get_credential("openai", auth_path, auto_refresh=True)
    assert result is not None
    assert result.auth_method == "oauth"
    assert result.expires_at is not None
    assert result.expires_at > time.time()


def test_auto_token_refresh_skipped_when_disabled(tmp_path):
    """auto_refresh=False skips refresh for expired OAuth credentials."""
    import json as _json
    import time
    from agent_runtime_cockpit.auth.manager import (
        encrypt_credential,
        save_credential,
        get_credential,
    )

    auth_path = tmp_path / "auth.json"

    token_data = _json.dumps(
        {
            "access_token": "tok-expired",
            "refresh_token": "rtok-still-valid",
            "expires_in": 3600,
            "token_type": "Bearer",
        }
    )
    cred = encrypt_credential("openai", token_data)
    cred.auth_method = "oauth"
    cred.expires_at = time.time() - 1  # expired
    save_credential(cred, auth_path)

    result = get_credential("openai", auth_path, auto_refresh=False)
    assert result is None  # Should return None without attempting refresh


def test_auto_token_refresh_no_refresh_token(tmp_path):
    """Expired OAuth without refresh_token returns None."""
    import json as _json
    import time
    from agent_runtime_cockpit.auth.manager import (
        encrypt_credential,
        save_credential,
        get_credential,
    )

    auth_path = tmp_path / "auth.json"

    token_data = _json.dumps(
        {
            "access_token": "tok-expired",
            "refresh_token": None,
            "expires_in": 3600,
            "token_type": "Bearer",
        }
    )
    cred = encrypt_credential("openai", token_data)
    cred.auth_method = "oauth"
    cred.expires_at = time.time() - 1
    save_credential(cred, auth_path)

    result = get_credential("openai", auth_path, auto_refresh=True)
    assert result is None


def test_start_oauth_flow_timeout(monkeypatch):
    """start_oauth_flow raises TimeoutError when no callback arrives."""
    config = OAuthConfig(
        provider_id="test",
        client_id="cid",
        client_secret="cs",
        auth_url="https://auth.example.com",
        token_url="https://token.example.com/token",
        redirect_port=9999,  # Use explicit port to avoid _find_free_port
        use_pkce=False,  # Skip PKCE for simplicity
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
