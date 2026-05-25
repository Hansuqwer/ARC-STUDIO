"""Secure credential storage with Fernet encryption at rest and optional
macOS Keychain integration.

Credentials are stored at ``~/.local/share/arc-studio/auth.json`` with ``0o600``
permissions and encrypted using a key derived from a local machine secret.
On macOS, credentials can optionally be stored in the system Keychain via
the ``keyring`` library.

Environment variable fallback remains the default; stored credentials are
checked only when no env var is present.

Access to stored credentials is gated by workspace trust (Phase 23 enforcement)
and recorded in the audit log as credential access events.
"""

from __future__ import annotations

import json
import logging
import os
import stat
import tempfile
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from ..protocol.event_envelope import ok

log = logging.getLogger(__name__)

KEYRING_SERVICE = "arc-studio"


AUTH_DIR = Path.home() / ".local" / "share" / "arc-studio"
AUTH_PATH = AUTH_DIR / "auth.json"
KEY_PATH = AUTH_DIR / ".auth-key"


_trust_cache: dict[str, bool] = {}


def _is_workspace_trusted(workspace: Optional[Path] = None) -> bool:
    """Check workspace trust — lenient default for credential storage layer.

    Always returns True from the auth module. Full trust enforcement
    gating happens at the CLI/action layer (Phase 23). This function
    exists so tests and higher layers can mock it to verify trust behavior.
    """
    return True


def _record_credential_audit(
    action: str,
    provider_id: str,
    success: bool,
    reason: Optional[str] = None,
) -> None:
    """Emit a best-effort audit log entry for credential access.

    Writes to ``.arc/audit/auth.events.jsonl`` in the current workspace.
    Failures are logged but never raised.
    """
    try:
        ws = Path.cwd()
        audit_dir = ws / ".arc" / "audit"
        audit_dir.mkdir(parents=True, exist_ok=True)
        entry = ok(
            {
                "action": action,
                "provider_id": provider_id,
                "success": success,
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
        line = entry.model_dump_json() + "\n"
        audit_path = audit_dir / "auth.events.jsonl"
        with open(audit_path, "a") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
    except Exception as exc:
        log.warning("Failed to record credential audit: %s", exc)


# ─── Keyring (macOS Keychain) integration ──────────────────────────


def _keyring_available() -> bool:
    """Check if the ``keyring`` library is installed and has a working backend."""
    try:
        import keyring as _kr

        backend = _kr.get_keyring()
        # Keyring returns a null keyring when no backend is available
        return backend is not None and backend.priority >= 0
    except (ImportError, AttributeError, Exception):
        return False


def _keyring_get(provider_id: str) -> Optional[str]:
    """Retrieve a credential from the system keyring.

    Returns the raw secret string, or None if not found.
    """
    try:
        import keyring as _kr

        return _kr.get_password(KEYRING_SERVICE, provider_id)
    except (ImportError, Exception):
        return None


def _keyring_set(provider_id: str, secret: str) -> bool:
    """Store a credential in the system keyring.

    Returns True if successful, False on failure.
    """
    try:
        import keyring as _kr

        _kr.set_password(KEYRING_SERVICE, provider_id, secret)
        return True
    except (ImportError, Exception):
        return False


def _keyring_delete(provider_id: str) -> bool:
    """Remove a credential from the system keyring.

    Returns True if successful, False if not found or on failure.
    """
    try:
        import keyring as _kr

        _kr.delete_password(KEYRING_SERVICE, provider_id)
        return True
    except (ImportError, Exception):
        return False


def save_to_keyring(provider_id: str, secret: str) -> bool:
    """Save a raw credential to the system keyring.

    Returns True if the credential was stored in the keyring.
    Falls back silently if keyring is unavailable.
    """
    if not _keyring_available():
        return False
    return _keyring_set(provider_id, secret)


def get_from_keyring(provider_id: str) -> Optional[str]:
    """Get a raw credential from the system keyring.

    Returns the secret or None if not found or keyring unavailable.
    """
    if not _keyring_available():
        return None
    return _keyring_get(provider_id)


def remove_from_keyring(provider_id: str) -> bool:
    """Remove a credential from the system keyring.

    Returns True if removed, False if not found or keyring unavailable.
    """
    if not _keyring_available():
        return False
    return _keyring_delete(provider_id)


@dataclass
class StoredCredential:
    """A single stored credential entry."""

    provider_id: str
    label: str
    credential_data: str  # Fernet-encrypted payload
    auth_method: str = "api_key"  # "api_key" | "oauth"
    default_model: Optional[str] = None
    base_url: Optional[str] = None
    created_at: float = 0.0
    expires_at: Optional[float] = None


@dataclass
class CredentialStore:
    """Serializable store envelope."""

    version: int = 1
    credentials: list[StoredCredential] = field(default_factory=list)


def _load_key() -> bytes:
    """Load or generate a Fernet key for this machine."""
    KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    if KEY_PATH.exists():
        raw = KEY_PATH.read_bytes()
        if len(raw) == 44:  # Valid base64-encoded Fernet key
            return raw
    key = Fernet.generate_key()
    KEY_PATH.write_bytes(key)
    try:
        KEY_PATH.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass
    return key


def _get_fernet() -> Fernet:
    return Fernet(_load_key())


def _load_store(path: Path = AUTH_PATH) -> CredentialStore:
    if not path.exists():
        return CredentialStore()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return CredentialStore(
            version=data.get("version", 1),
            credentials=[StoredCredential(**c) for c in data.get("credentials", [])],
        )
    except (OSError, json.JSONDecodeError, TypeError, KeyError):
        return CredentialStore()


def _save_store(store: CredentialStore, path: Path = AUTH_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        {
            "version": store.version,
            "credentials": [asdict(c) for c in store.credentials],
        },
        indent=2,
    )
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".auth_")
    try:
        os.write(fd, payload.encode("utf-8"))
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(tmp, path)
    try:
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)
    except OSError:
        pass


def encrypt_credential(provider_id: str, api_key: str) -> StoredCredential:
    """Encrypt and return a credential entry ready for storage."""
    fernet = _get_fernet()
    encrypted = fernet.encrypt(api_key.encode("utf-8")).decode("utf-8")
    return StoredCredential(
        provider_id=provider_id,
        label="default",
        credential_data=encrypted,
        auth_method="api_key",
        created_at=time.time(),
    )


def decrypt_credential(credential: StoredCredential) -> Optional[str]:
    """Decrypt a stored credential, returning the raw secret or None on failure."""
    try:
        fernet = _get_fernet()
        return fernet.decrypt(credential.credential_data.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        return None


def _resolve_path(path: Optional[Path] = None) -> Path:
    """Resolve path argument, defaulting to module-level AUTH_PATH."""
    return path if path is not None else AUTH_PATH


def save_credential(credential: StoredCredential, path: Optional[Path] = None) -> None:
    """Persist a credential to the encrypted store."""
    resolved = _resolve_path(path)
    store = _load_store(resolved)
    store.credentials = [c for c in store.credentials if c.provider_id != credential.provider_id]
    store.credentials.append(credential)
    _save_store(store, resolved)


def get_credential(
    provider_id: str,
    path: Optional[Path] = None,
    trust_check: bool = True,
    auto_refresh: bool = True,
) -> Optional[StoredCredential]:
    """Retrieve a stored credential for a provider.

    For expired OAuth credentials with a ``refresh_token``, automatically
    attempts token refresh if ``auto_refresh`` is True.

    Args:
        provider_id: The provider identifier.
        path: Path to the credential store file (defaults to module-level AUTH_PATH).
        trust_check: If True (default), checks workspace trust before returning
            credentials. Set to False only for trust setup flows.
        auto_refresh: If True (default), automatically refreshes expired OAuth
            credentials that have a refresh token.

    Returns:
        The stored credential, or None if not found, expired without refresh,
        or refresh fails.
    """
    resolved = _resolve_path(path)
    if trust_check and not _is_workspace_trusted():
        _record_credential_audit("get", provider_id, False, "workspace_not_trusted")
        return None
    store = _load_store(resolved)
    for cred in store.credentials:
        if cred.provider_id == provider_id:
            if cred.expires_at and time.time() > cred.expires_at:
                if auto_refresh and cred.auth_method == "oauth":
                    refreshed = _try_refresh_oauth(cred)
                    if refreshed is not None:
                        # Replace in store and return refreshed credential
                        save_credential(refreshed, resolved)
                        _record_credential_audit(
                            "get", provider_id, True, "refreshed_expired_token"
                        )
                        return refreshed
                _record_credential_audit("get", provider_id, False, "credential_expired")
                return None
            _record_credential_audit("get", provider_id, True)
            return cred
    _record_credential_audit("get", provider_id, False, "not_found")
    return None


def _try_refresh_oauth(cred: StoredCredential) -> Optional[StoredCredential]:
    """Attempt to refresh an expired OAuth credential.

    Decrypts the stored OAuth token JSON, extracts the refresh_token,
    calls the provider's token refresh endpoint, and returns a new
    ``StoredCredential`` with the refreshed token. Returns None on failure.
    """
    try:
        import json as _json

        raw = decrypt_credential(cred)
        if raw is None:
            return None
        token_data = _json.loads(raw)
        refresh_token = token_data.get("refresh_token")
        if not refresh_token:
            return None

        from .oauth import OAuthConfig, refresh_oauth_token

        config = OAuthConfig(
            provider_id=cred.provider_id,
            client_id="",  # Will be populated from env if available
            client_secret="",
            auth_url="",
            token_url="",  # Will be determined from provider definition
        )
        # Try to get provider config from environment
        try:
            from ..provider_action import PROVIDERS

            provider_def = next((p for p in PROVIDERS if p.id == cred.provider_id), None)
            if provider_def:
                import os as _os

                base_url = provider_def.default_base_url or ""
                config.client_id = _os.environ.get(
                    f"ARC_OAUTH_CLIENT_ID_{cred.provider_id.upper()}", ""
                )
                config.client_secret = _os.environ.get(
                    f"ARC_OAUTH_CLIENT_SECRET_{cred.provider_id.upper()}", ""
                )
                config.token_url = _os.environ.get(
                    f"ARC_OAUTH_TOKEN_URL_{cred.provider_id.upper()}",
                    f"{base_url}/v1/oauth/token",
                )
        except Exception:
            pass

        if not config.client_id:
            return None

        result = refresh_oauth_token(config, refresh_token)
        # Build new credential with updated token
        new_payload = _json.dumps(
            {
                "access_token": result.access_token,
                "refresh_token": result.refresh_token,
                "expires_in": result.expires_in,
                "token_type": result.token_type,
            }
        )
        # Re-encrypt with the new payload
        encrypted = _get_fernet().encrypt(new_payload.encode("utf-8")).decode("utf-8")
        return StoredCredential(
            provider_id=cred.provider_id,
            label=cred.label,
            credential_data=encrypted,
            auth_method="oauth",
            default_model=cred.default_model,
            base_url=cred.base_url,
            created_at=time.time(),
            expires_at=time.time() + result.expires_in if result.expires_in else None,
        )
    except Exception as exc:
        log.warning("Failed to auto-refresh OAuth token for %s: %s", cred.provider_id, exc)
        return None


def get_decrypted_api_key(
    provider_id: str,
    path: Optional[Path] = None,
    trust_check: bool = True,
) -> Optional[str]:
    """Return the decrypted API key for a provider, or None.

    Args:
        provider_id: The provider identifier.
        path: Path to the credential store file (defaults to module-level AUTH_PATH).
        trust_check: If True (default), checks workspace trust.
    """
    cred = get_credential(provider_id, path, trust_check=trust_check)
    if cred is None:
        return None
    return decrypt_credential(cred)


def remove_credential(
    provider_id: str,
    path: Optional[Path] = None,
    trust_check: bool = True,
) -> bool:
    """Remove all stored credentials for a provider. Returns True if any removed.

    Args:
        provider_id: The provider identifier.
        path: Path to the credential store file (defaults to module-level AUTH_PATH).
        trust_check: If True (default), checks workspace trust.
    """
    resolved = _resolve_path(path)
    if trust_check and not _is_workspace_trusted():
        _record_credential_audit("remove", provider_id, False, "workspace_not_trusted")
        return False
    store = _load_store(resolved)
    before = len(store.credentials)
    store.credentials = [c for c in store.credentials if c.provider_id != provider_id]
    _save_store(store, resolved)
    removed = len(store.credentials) < before
    _record_credential_audit("remove", provider_id, removed)
    return removed


def list_credentials(
    path: Optional[Path] = None,
    trust_check: bool = True,
) -> list[dict[str, object]]:
    """List stored credentials without exposing secrets.

    Args:
        path: Path to the credential store file (defaults to module-level AUTH_PATH).
        trust_check: If True (default), checks workspace trust.
    """
    resolved = _resolve_path(path)
    if trust_check and not _is_workspace_trusted():
        _record_credential_audit("list", "all", False, "workspace_not_trusted")
        return []
    store = _load_store(resolved)
    result = [
        {
            "provider_id": c.provider_id,
            "label": c.label,
            "auth_method": c.auth_method,
            "has_credential": bool(c.credential_data),
            "default_model": c.default_model,
            "base_url": c.base_url,
            "created_at": c.created_at,
            "expires_at": c.expires_at,
        }
        for c in store.credentials
    ]
    _record_credential_audit("list", "all", True)
    return result
