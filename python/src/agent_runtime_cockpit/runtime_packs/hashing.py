"""Deterministic hashing for runtime pack manifests.

The hash is computed over a *normalized* canonical JSON view so that two logically
identical manifests always produce the same digest regardless of dict ordering or
volatile fields (timestamps, the hash field itself). Secrets are redacted before
hashing so a manifest hash never depends on a secret value.

This mirrors the approach in ``capabilities/hashing.py`` and ``swarmgraph_ir/
hashing.py``. The stable hash deliberately includes:

* ``schema_version`` (so breaking schema changes are detected),
* ``id`` / ``version`` (entity identity),
* ``permissions`` and ``capabilities`` (the security surface),
* ``entrypoints`` (what the pack claims to expose),
* ``ir`` and ``policy`` declarations.

It excludes ``manifest_hash`` (circular) and volatile provenance timestamps.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .models import RUNTIME_PACK_SCHEMA_VERSION

# Fields that must never influence the structural hash (volatile / derived).
_VOLATILE_KEYS = {
    "manifest_hash",
    "created_at",
    "compiled_at",
    "imported_at",
    "installed_at",
}

# Field *names* whose values are always redacted before hashing.
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
    """Recursively redact sensitive field names and secret-looking string values."""
    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for k, v in obj.items():
            if any(s in k.lower() for s in _SENSITIVE_KEYS):
                result[k] = REDACTED_VALUE
            else:
                result[k] = _redact_sensitive(v)
        return result
    if isinstance(obj, list):
        return [_redact_sensitive(x) for x in obj]
    if isinstance(obj, str):
        if len(obj) > 8 and any(marker in obj for marker in ["sk-", "ghp_", "AKIA", "Bearer "]):
            return REDACTED_VALUE
    return obj


def _strip(obj: Any) -> Any:
    """Recursively drop volatile keys, redact sensitive data, and sort dict keys."""
    if isinstance(obj, dict):
        result: dict[str, Any] = {}
        for k, v in sorted(obj.items()):
            if k in _VOLATILE_KEYS:
                continue
            if k.lower() in _SENSITIVE_KEYS:
                result[k] = REDACTED_VALUE
            else:
                result[k] = _strip(v)
        return result
    if isinstance(obj, list):
        return [_strip(x) for x in obj]
    return obj


def canonical_json(manifest_dict: dict[str, Any]) -> str:
    """Return canonical (sorted, compact, volatile-free, redacted) JSON."""
    return json.dumps(
        _strip(_redact_sensitive(manifest_dict)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def manifest_hash(manifest: Any) -> str:
    """Compute the deterministic sha256 digest of a runtime pack manifest.

    Accepts a ``RuntimePackManifest`` instance (uses ``model_dump(mode="json")``)
    or a plain JSON-compatible dict. ``schema_version`` is always present in the
    hashed view so that schema changes always change the hash.
    """
    if hasattr(manifest, "model_dump"):
        data = manifest.model_dump(mode="json")
    else:
        data = dict(manifest)

    if "schema_version" not in data:
        data["schema_version"] = RUNTIME_PACK_SCHEMA_VERSION

    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def verify_manifest_hash(manifest: Any, expected_hash: str) -> bool:
    """Return True iff the manifest's recomputed hash equals ``expected_hash``."""
    return manifest_hash(manifest) == expected_hash


__all__ = [
    "canonical_json",
    "manifest_hash",
    "verify_manifest_hash",
    "REDACTED_VALUE",
]
