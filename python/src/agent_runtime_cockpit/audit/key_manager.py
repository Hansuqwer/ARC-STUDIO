"""HMAC audit key management with keychain storage and env fallback (ADR-005)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Any, Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)

ARC_AUDIT_SERVICE = "arc-studio-audit"
ARC_AUDIT_KEY_ID = "hmac-audit-key-v1"


class AuditSigningError(RuntimeError):
    """Raised when an HMAC audit record cannot be signed."""


class AuditKeyStatus(BaseModel):
    available: bool
    source: str
    degraded: bool = False
    warning: str = ""
    key_id: str = ""


class AuditKeyManager:
    """Manages HMAC-SHA256 audit keys with keychain preference and env fallback."""

    def __init__(self, service: str = ARC_AUDIT_SERVICE, key_id: str = ARC_AUDIT_KEY_ID) -> None:
        self.service = service
        self.key_id = key_id

    def get_key(self) -> tuple[Optional[bytes], AuditKeyStatus]:
        """Retrieve HMAC audit key. Tries keychain first, then env fallback."""
        keychain_key = self._try_keychain()
        if keychain_key is not None:
            return keychain_key, AuditKeyStatus(
                available=True,
                source="keychain",
                key_id=self.key_id,
            )
        env_key = os.environ.get("ARC_AUDIT_HMAC_KEY")
        if env_key:
            return env_key.encode("utf-8"), AuditKeyStatus(
                available=True,
                source="env",
                degraded=True,
                key_id="env-fallback",
                warning="Using env fallback for audit key — keychain preferred for production",
            )
        return None, AuditKeyStatus(
            available=False,
            source="none",
            degraded=True,
            warning="No audit key available. Set ARC_AUDIT_HMAC_KEY or run 'arc audit key init'.",
        )

    def set_key(self, key: str) -> bool:
        """Store HMAC audit key in keychain. Returns True on success."""
        try:
            import keyring  # type: ignore[import-untyped]

            keyring.set_password(self.service, self.key_id, key)
            log.info("Audit key stored in keychain: %s/%s", self.service, self.key_id)
            return True
        except Exception as e:
            log.warning("Failed to store audit key in keychain: %s", e)
            return False

    def delete_key(self) -> bool:
        """Delete HMAC audit key from keychain. Returns True on success."""
        try:
            import keyring  # type: ignore[import-untyped]

            keyring.delete_password(self.service, self.key_id)
            log.info("Audit key deleted from keychain: %s/%s", self.service, self.key_id)
            return True
        except Exception as e:
            log.warning("Failed to delete audit key from keychain: %s", e)
            return False

    def generate_key(self) -> str:
        """Generate a cryptographically random HMAC key (hex-encoded)."""
        return os.urandom(32).hex()

    def _try_keychain(self) -> Optional[bytes]:
        try:
            import keyring  # type: ignore[import-untyped]

            key_str = keyring.get_password(self.service, self.key_id)
            if key_str:
                return key_str.encode("utf-8")
        except Exception as e:
            log.debug("Keychain access failed: %s", e)
        return None


def _canonical_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")


def signed_audit_payload(
    data: dict[str, Any],
    prev_hash: str = "GENESIS",
    *,
    seq: int | None = None,
    timestamp: str = "",
    key_id: str = "",
) -> dict[str, Any]:
    """Build the canonical payload bound by the HMAC record hash."""
    payload: dict[str, Any] = {
        "event": data,
        "prev_hash": prev_hash,
    }
    if seq is None and isinstance(data.get("seq"), int):
        seq = data["seq"]
    if seq is not None:
        payload["seq"] = seq
    if timestamp:
        payload["timestamp"] = timestamp
    if key_id:
        payload["key_id"] = key_id
    return payload


def sign_audit_record(
    data: dict[str, Any],
    key: bytes,
    prev_hash: str = "GENESIS",
    *,
    seq: int | None = None,
    timestamp: str = "",
    key_id: str = "",
) -> tuple[str, str]:
    """Sign audit record data with HMAC-SHA256.

    Returns (record_hash, signature).
    record_hash = SHA-256(canonical_json(payload))
    signature = HMAC-SHA256(key, record_hash)
    """
    payload = signed_audit_payload(
        data,
        prev_hash,
        seq=seq,
        timestamp=timestamp,
        key_id=key_id,
    )
    record_hash = hashlib.sha256(_canonical_json(payload)).hexdigest()
    signature = hmac.new(key, record_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return record_hash, signature


def verify_audit_signature(
    data: dict[str, Any],
    signature: str,
    key: bytes,
    prev_hash: str = "GENESIS",
    *,
    seq: int | None = None,
    timestamp: str = "",
    key_id: str = "",
) -> bool:
    """Verify HMAC-SHA256 signature of audit record. Uses constant-time comparison."""
    _, expected_sig = sign_audit_record(
        data,
        key,
        prev_hash,
        seq=seq,
        timestamp=timestamp,
        key_id=key_id,
    )
    return hmac.compare_digest(expected_sig, signature)


def legacy_sign_audit_record(
    data: dict[str, Any], key: bytes, prev_hash: str = "GENESIS"
) -> tuple[str, str]:
    """Sign using the pre-seq-binding format for persisted legacy chains."""
    payload = _canonical_json(data)
    record_hash = hashlib.sha256(payload + prev_hash.encode("utf-8")).hexdigest()
    signature = hmac.new(key, record_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return record_hash, signature


def verify_legacy_audit_signature(
    data: dict[str, Any], signature: str, key: bytes, prev_hash: str = "GENESIS"
) -> bool:
    _, expected_sig = legacy_sign_audit_record(data, key, prev_hash)
    return hmac.compare_digest(expected_sig, signature)
