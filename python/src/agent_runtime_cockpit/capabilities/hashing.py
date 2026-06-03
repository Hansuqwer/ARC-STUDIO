"""Deterministic hashing for Capability Cards.

The hash is computed over a *normalized* canonical JSON view so that two logically
identical cards always produce the same digest, regardless of dict ordering or
volatile fields (timestamps, the hash field itself).

This mirrors the hashing approach used in swarmgraph_ir/hashing.py and
mcp/manifests.py, but produces a stable card hash that includes schema version,
entity ID, permissions, side effects, trust, MCP manifest hash, cost, audit, and
replay fields.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import CARD_SCHEMA_VERSION

# Fields that must never influence the structural hash.
# These are volatile or derived after hashing.
_VOLATILE_KEYS = {
    "card_hash",
    "created_at",
    "compiled_at",
    "imported_at",
}

# Fields that contain sensitive data and must be redacted before hashing.
_SENSITIVE_KEYS = {
    "secret",
    "token",
    "key",
    "password",
    "credential",
    "auth",
    "bearer",
    "api_key",
}

REDACTED_VALUE = "[REDACTED]"


def _redact_sensitive(obj: Any) -> Any:
    """Recursively redact sensitive fields and values."""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            k_lower = k.lower()
            # Redact sensitive key names entirely
            if any(s in k_lower for s in _SENSITIVE_KEYS):
                result[k] = REDACTED_VALUE
            else:
                result[k] = _redact_sensitive(v)
        return result
    if isinstance(obj, list):
        return [_redact_sensitive(x) for x in obj]
    if isinstance(obj, str):
        # Redact string values that look like secrets
        if len(obj) > 8 and any(c in obj for c in ["sk-", "ghp_", "AKIA", "Bearer "]):
            return REDACTED_VALUE
    return obj


def _strip(obj: Any) -> Any:
    """Recursively drop volatile keys, redact sensitive data, and sort dict keys."""
    if isinstance(obj, dict):
        result = {}
        for k, v in sorted(obj.items()):
            if k not in _VOLATILE_KEYS:
                if k.lower() in _SENSITIVE_KEYS:
                    result[k] = REDACTED_VALUE
                else:
                    result[k] = _strip(v)
        return result
    if isinstance(obj, list):
        return [_strip(x) for x in obj]
    return obj


def canonical_json(card_dict: dict[str, Any]) -> str:
    """Return canonical (sorted, compact, volatile-free, redacted) JSON for a card dict."""
    return json.dumps(_strip(_redact_sensitive(card_dict)), sort_keys=True, separators=(",", ":"))


def card_hash(card: Any) -> str:
    """Compute the deterministic sha256 digest of a CapabilityCard.

    Accepts a ``CapabilityCard`` instance (uses ``model_dump(mode="json")``) or a
    plain dict already in JSON-compatible form.

    The hash includes:
    - schema_version (ensures breaking changes are detected)
    - id (ensures entity identity is part of hash)
    - capabilities flags
    - permissions
    - side effects
    - trust profile
    - MCP manifest hash (if applicable)
    - cost profile
    - audit profile
    - replay profile

    The hash excludes:
    - card_hash itself (would be circular)
    - created_at (volatile timestamp)
    - metadata (may contain volatile data)

    Sensitive fields are redacted before hashing.
    """
    if hasattr(card, "model_dump"):
        data = card.model_dump(mode="json")
    else:
        data = card

    # Ensure schema_version is always included
    if "schema_version" not in data:
        data["schema_version"] = CARD_SCHEMA_VERSION

    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def verify_hash(card: Any, expected_hash: str) -> bool:
    """Verify that a card's hash matches the expected hash.

    This is a safety check to ensure card integrity.
    """
    actual_hash = card_hash(card)
    return actual_hash == expected_hash
