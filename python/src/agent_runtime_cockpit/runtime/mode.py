"""Canonical runtime-mode enum for ARC Studio.

Lock: docs/adr/ADR-011-full-parity-framing.md
Phase: 3 (Runtime Semantics Unification)

The three values are exact. Do not rename, do not add. New modes require an
ADR amendment to ADR-011.

`from_legacy()` exists to migrate Phase 0/1/2 on-disk artifacts and any
external integration code that still uses the pre-unification strings. It is
deliberately noisy (DeprecationWarning) so legacy paths show up in tests and
CI rather than silently working forever.
"""

from __future__ import annotations

import warnings
from enum import StrEnum
from typing import Final


class RuntimeMode(StrEnum):
    """Canonical runtime mode.

    - FAKE          : deterministic stub responses, zero external calls,
                      no gating required. Cost source: 'estimated', value 0.0.
    - GATED_LOCAL   : local model execution behind a gate. The enum value
                      is intentionally 'gated_local' (snake_case) to preserve
                      compatibility with existing on-disk session files
                      written before Phase 3. Do not change.
    - PROVIDER_BACKED : external provider calls. Requires
                      allow_paid_calls=True plus provider-specific gates.
    """

    FAKE = "fake"
    GATED_LOCAL = "gated_local"
    PROVIDER_BACKED = "provider_backed"

    @classmethod
    def from_legacy(cls, value: str | "RuntimeMode") -> "RuntimeMode":
        """Coerce a legacy mode string to the canonical enum.

        Accepts:
          - canonical strings: 'fake', 'gated_local', 'provider_backed'
          - legacy strings:    'offline', 'local', 'gated', 'live'
          - already-RuntimeMode instances (pass-through, no warning)

        Raises ValueError on unknown values. Emits DeprecationWarning when
        a legacy string is supplied, naming the caller so the offending
        code site can be located.

        Mapping rationale (locked by ADR-011, Phase 0 inventory
        docs/archive/phase-0-inventory/runtime-matrix.md):
          offline -> FAKE             (pre-unification term for stub mode)
          local   -> GATED_LOCAL      (pre-unification term for local model)
          gated   -> GATED_LOCAL      (CLI shorthand)
          live    -> PROVIDER_BACKED  (pre-unification term for paid calls)
        """
        if isinstance(value, RuntimeMode):
            return value

        if not isinstance(value, str):
            raise TypeError(
                f"RuntimeMode.from_legacy expected str or RuntimeMode, "
                f"got {type(value).__name__}"
            )

        normalized = value.strip().lower()

        # Canonical values: no warning, direct construction.
        if normalized in _CANONICAL_VALUES:
            return cls(normalized)

        # Legacy values: warn and map.
        if normalized in _LEGACY_MAP:
            canonical = _LEGACY_MAP[normalized]
            warnings.warn(
                f"Legacy runtime mode {value!r} is deprecated; "
                f"use {canonical.value!r} instead. "
                f"This shim will be removed in Phase 6.",
                DeprecationWarning,
                stacklevel=2,
            )
            return canonical

        raise ValueError(
            f"Unknown runtime mode: {value!r}. "
            f"Valid values: {sorted(_CANONICAL_VALUES)} "
            f"(legacy aliases: {sorted(_LEGACY_MAP)})"
        )

    @classmethod
    def is_paid(cls, mode: "RuntimeMode") -> bool:
        """True if the mode requires allow_paid_calls=True to execute.

        Used by capability validation and the /run gate.
        """
        return mode is cls.PROVIDER_BACKED

    @classmethod
    def requires_gate(cls, mode: "RuntimeMode") -> bool:
        """True if the mode requires an explicit gate to execute.

        FAKE is the only mode that runs without a gate.
        """
        return mode is not cls.FAKE


_CANONICAL_VALUES: Final[frozenset[str]] = frozenset(m.value for m in RuntimeMode)

_LEGACY_MAP: Final[dict[str, RuntimeMode]] = {
    "offline": RuntimeMode.FAKE,
    "local": RuntimeMode.GATED_LOCAL,
    "gated": RuntimeMode.GATED_LOCAL,
    "live": RuntimeMode.PROVIDER_BACKED,
}
