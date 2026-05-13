"""Dual-gate environment resolver. Single source for all runtimes."""
from __future__ import annotations

import enum
import os


class BackendMode(str, enum.Enum):
    STUB = "stub"
    LOCAL = "local"
    GATEWAY = "gateway"


class GatingError(RuntimeError):
    """Raised when a non-stub backend is requested without cost gating."""


def require_dual_gate(runtime: str) -> tuple[BackendMode, bool]:
    """Resolve (backend, allow_costs). STUB is always allowed.

    Non-stub backends require ``ARC_<RUNTIME>_ALLOW_COSTS=true``.
    """
    key = runtime.upper()
    raw_backend = os.environ.get(f"ARC_{key}_RUN_BACKEND", "stub").strip().lower()
    try:
        backend = BackendMode(raw_backend)
    except ValueError as exc:
        raise GatingError(f"invalid backend for {runtime}: {raw_backend!r}") from exc
    allow_costs = os.environ.get(f"ARC_{key}_ALLOW_COSTS", "").strip().lower() == "true"
    if backend is not BackendMode.STUB and not allow_costs:
        raise GatingError(
            f"{runtime} backend {backend.value!r} requires "
            f"ARC_{key}_ALLOW_COSTS=true (dual-gate)"
        )
    return backend, allow_costs
