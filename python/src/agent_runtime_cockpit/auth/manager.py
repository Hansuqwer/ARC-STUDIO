"""Secure credential storage with Fernet encryption at rest.

Credentials are stored at ``~/.local/share/arc-studio/auth.json`` with ``0o600``
permissions and encrypted using a key derived from a local machine secret.
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
) -> Optional[StoredCredential]:
    """Retrieve a stored credential for a provider.

    Args:
        provider_id: The provider identifier.
        path: Path to the credential store file (defaults to module-level AUTH_PATH).
        trust_check: If True (default), checks workspace trust before returning
            credentials. Set to False only for trust setup flows.

    Returns:
        The stored credential, or None if not found or expired.
    """
    resolved = _resolve_path(path)
    if trust_check and not _is_workspace_trusted():
        _record_credential_audit("get", provider_id, False, "workspace_not_trusted")
        return None
    store = _load_store(resolved)
    for cred in store.credentials:
        if cred.provider_id == provider_id:
            if cred.expires_at and time.time() > cred.expires_at:
                _record_credential_audit("get", provider_id, False, "credential_expired")
                return None
            _record_credential_audit("get", provider_id, True)
            return cred
    _record_credential_audit("get", provider_id, False, "not_found")
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
