"""Deterministic graph hashing for SwarmGraph IR.

The hash is computed over a *normalized* canonical JSON view so that two logically
identical graphs always produce the same digest, regardless of dict ordering or
volatile fields (timestamps, the hash field itself). Style mirrors
``mcp/manifests.py::_hash_tools`` (sha256 over canonical JSON), but we keep the
full 64-hex digest for graph-level integrity.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# Fields that must never influence the structural hash.
_VOLATILE_KEYS = {"compiled_at", "graph_hash", "imported_at"}


def _strip(obj: Any) -> Any:
    """Recursively drop volatile keys and sort dict keys for determinism."""
    if isinstance(obj, dict):
        return {k: _strip(v) for k, v in sorted(obj.items()) if k not in _VOLATILE_KEYS}
    if isinstance(obj, list):
        return [_strip(x) for x in obj]
    return obj


def canonical_json(graph_dict: dict[str, Any]) -> str:
    """Return canonical (sorted, compact, volatile-free) JSON for a graph dict."""
    return json.dumps(_strip(graph_dict), sort_keys=True, separators=(",", ":"))


def graph_hash(graph: Any) -> str:
    """Compute the deterministic sha256 digest of an IRGraph.

    Accepts an ``IRGraph`` instance (uses ``model_dump(mode="json")``) or a plain
    dict already in JSON-compatible form.
    """
    if hasattr(graph, "model_dump"):
        data = graph.model_dump(mode="json")
    else:
        data = graph
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()
