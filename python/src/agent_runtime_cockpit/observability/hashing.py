"""Deterministic export hashing for ArcTraceExport.

Excludes volatile fields (created_at, export_hash) before hashing.
Canonical: sorted keys, compact separators, stable span ordering by span_id.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


_VOLATILE = frozenset({"created_at", "export_hash", "export_id"})


def _strip_volatile(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _strip_volatile(v) for k, v in data.items() if k not in _VOLATILE}
    if isinstance(data, list):
        return [_strip_volatile(i) for i in data]
    return data


def export_hash(export_dict: dict[str, Any]) -> str:
    """Compute a deterministic SHA-256 hash of an ArcTraceExport dict.

    Strips volatile fields, sorts spans by span_id for stability,
    then serializes to canonical JSON.
    """
    clean = _strip_volatile(export_dict)
    # Stable span ordering
    if "spans" in clean and isinstance(clean["spans"], list):
        clean["spans"] = sorted(clean["spans"], key=lambda s: s.get("span_id", ""))
    canonical = json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]
