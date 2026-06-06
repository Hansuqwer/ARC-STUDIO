"""MT-3 v1: deterministic response cache (replay-as-cache).

Content-addressed cache of provider responses keyed by a SHA-256 of
(model, messages, temperature, max_tokens, tools). On a cache hit the stored
response is returned without any provider call — 0 new tokens on a deterministic
re-run.

Design constraints:
- **Default-off.** Only active when ``ARC_ENABLE_REPLAY_CACHE=1``.
- **Deterministic only.** Cache is read/written only when ``temperature == 0.0``.
  At temperature > 0 the model is expected to vary, so caching would suppress
  intended randomness — get/put are no-ops there.
- **Fail-open.** Any cache error (corrupt file, permission, parse) falls back to
  a normal provider call. The cache never blocks execution.
- **Zeroed usage on hit.** A cache hit reports 0 input/output tokens (no API
  call was made) and ``metadata["cache_hit"] = True`` so cost tracking and the
  wallet correctly attribute 0 cost to the re-run.

This intentionally does NOT couple to the Flight Recorder (the original MT-3
sketch assumed an ``input_hash`` on ``RunEntry`` that does not exist). A
content-addressed cache is the simpler, more general mechanism for the same
"0 tokens on deterministic re-run" outcome.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any, Optional

from ..providers.base import ProviderRequest, ProviderResponse, UsageRecord


class DeterministicResponseCache:
    """Local content-addressed cache for deterministic provider responses."""

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self._dir = cache_dir or (Path.home() / ".arc" / "response-cache")

    @staticmethod
    def enabled() -> bool:
        return os.environ.get("ARC_ENABLE_REPLAY_CACHE") == "1"

    @staticmethod
    def _key(request: ProviderRequest) -> str:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [[m.role, m.content] for m in request.messages],
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "tools": request.tools,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def get(self, request: ProviderRequest) -> Optional[ProviderResponse]:
        """Return a cached response for a deterministic request, or None."""
        if not self.enabled() or request.temperature != 0.0:
            return None
        try:
            path = self._dir / f"{self._key(request)}.json"
            if not path.exists():
                return None
            cached = ProviderResponse.model_validate_json(path.read_text(encoding="utf-8"))
            # Zero usage on hit (no API call) + tag as a cache hit.
            return cached.model_copy(
                update={
                    "usage": UsageRecord(available=True, input_tokens=0, output_tokens=0),
                    "metadata": {**cached.metadata, "cache_hit": True},
                }
            )
        except Exception:
            return None  # fail-open

    def put(self, request: ProviderRequest, response: ProviderResponse) -> None:
        """Store a response for a deterministic request. No-op on error or non-determinism."""
        if not self.enabled() or request.temperature != 0.0:
            return
        # Never cache degraded / error responses.
        if response.degraded or response.finish_reason in ("error", "cancelled"):
            return
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            (self._dir / f"{self._key(request)}.json").write_text(
                response.model_dump_json(), encoding="utf-8"
            )
        except Exception:
            pass  # fail-open


__all__ = ["DeterministicResponseCache"]
