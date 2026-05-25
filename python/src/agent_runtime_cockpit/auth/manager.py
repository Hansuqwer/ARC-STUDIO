"""Secure credential storage with Fernet encryption at rest.

Credentials are stored at ``~/.local/share/arc-studio/auth.json`` with ``0o600``
permissions and encrypted using a key derived from a local machine secret.
Environment variable fallback remains the default; stored credentials are
checked only when no env var is present.
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


AUTH_DIR = Path.home() / ".local" / "share" / "arc-studio"
AUTH_PATH = AUTH_DIR / "auth.json"
KEY_PATH = AUTH_DIR / ".auth-key"


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


def save_credential(credential: StoredCredential, path: Path = AUTH_PATH) -> None:
    """Persist a credential to the encrypted store."""
    store = _load_store(path)
    store.credentials = [c for c in store.credentials if c.provider_id != credential.provider_id]
    store.credentials.append(credential)
    _save_store(store, path)


def get_credential(provider_id: str, path: Path = AUTH_PATH) -> Optional[StoredCredential]:
    """Retrieve a stored credential for a provider."""
    store = _load_store(path)
    for cred in store.credentials:
        if cred.provider_id == provider_id:
            if cred.expires_at and time.time() > cred.expires_at:
                return None
            return cred
    return None


def get_decrypted_api_key(provider_id: str, path: Path = AUTH_PATH) -> Optional[str]:
    """Return the decrypted API key for a provider, or None."""
    cred = get_credential(provider_id, path)
    if cred is None:
        return None
    return decrypt_credential(cred)


def remove_credential(provider_id: str, path: Path = AUTH_PATH) -> bool:
    """Remove all stored credentials for a provider. Returns True if any removed."""
    store = _load_store(path)
    before = len(store.credentials)
    store.credentials = [c for c in store.credentials if c.provider_id != provider_id]
    _save_store(store, path)
    return len(store.credentials) < before


def list_credentials(path: Path = AUTH_PATH) -> list[dict[str, object]]:
    """List stored credentials without exposing secrets."""
    store = _load_store(path)
    return [
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
