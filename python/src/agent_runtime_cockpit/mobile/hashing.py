"""Deterministic hashing for ARC Mobile Runtime models.

Excludes only volatile hash fields before hashing: capability_hash,
manifest_hash, plan_hash, and report_hash. ``schema_version`` is intentionally
included so schema-version changes produce different hashes.

Canonical form: sorted keys and compact separators.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

_VOLATILE = frozenset({"capability_hash", "manifest_hash", "plan_hash", "report_hash"})


def _strip(data: Any) -> Any:
    if isinstance(data, dict):
        return {k: _strip(v) for k, v in data.items() if k not in _VOLATILE}
    if isinstance(data, list):
        return [_strip(i) for i in data]
    return data


def _hash(data: Any) -> str:
    clean = _strip(data)
    canonical = json.dumps(clean, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


def capability_hash(cap: Any) -> str:
    d = cap.model_dump(mode="json") if hasattr(cap, "model_dump") else dict(cap)
    return _hash(d)


def manifest_hash(manifest: Any) -> str:
    d = manifest.model_dump(mode="json") if hasattr(manifest, "model_dump") else dict(manifest)
    return _hash(d)


def plan_hash(plan: Any) -> str:
    d = plan.model_dump(mode="json") if hasattr(plan, "model_dump") else dict(plan)
    return _hash(d)


def report_hash(report: Any) -> str:
    d = report.model_dump(mode="json") if hasattr(report, "model_dump") else dict(report)
    return _hash(d)
