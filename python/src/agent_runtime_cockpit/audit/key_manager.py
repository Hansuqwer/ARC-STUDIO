"""HMAC audit key management with keychain storage and env fallback (ADR-005)."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
from typing import Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)

ARC_AUDIT_SERVICE = "arc-studio-audit"
ARC_AUDIT_KEY_ID = "hmac-audit-key-v1"


class AuditKeyStatus(BaseModel):
    available: bool
    source: str
    degraded: bool = False
    warning: str = ""
    key_id: str = ""


class AuditKeyManager:
    """Manages HMAC-SHA256 audit keys with keychain preference and env fallback."""

    def __init__(
        self, service: str = ARC_AUDIT_SERVICE, key_id: str = ARC_AUDIT_KEY_ID
    ) -> None:
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


def sign_audit_record(
    data: dict, key: bytes, prev_hash: str = "GENESIS"
) -> tuple[str, str]:
    """Sign audit record data with HMAC-SHA256.

    Returns (record_hash, signature).
    record_hash = SHA-256(canonical_json(data) + prev_hash)
    signature = HMAC-SHA256(key, record_hash)
    """
    payload = json.dumps(data, sort_keys=True, separators=(",", ":")).encode("utf-8")
    record_hash = hashlib.sha256(payload + prev_hash.encode("utf-8")).hexdigest()
    signature = hmac.new(key, record_hash.encode("utf-8"), hashlib.sha256).hexdigest()
    return record_hash, signature


def verify_audit_signature(
    data: dict, signature: str, key: bytes, prev_hash: str = "GENESIS"
) -> bool:
    """Verify HMAC-SHA256 signature of audit record. Uses constant-time comparison."""
    expected_hash, expected_sig = sign_audit_record(data, key, prev_hash)
    return hmac.compare_digest(expected_sig, signature)
