"""Deprecated shim for ARC event envelopes.

The canonical ADR-018 module is ``agent_runtime_cockpit.protocol.event_envelope``.

DEPRECATION: Introduced v0.1.0-alpha (2026-05-11, commit 0ab9b7d)
REMOVAL: v0.3.0 per ADR-022 (one minor + one patch cycle)
"""

from __future__ import annotations

from warnings import warn

from agent_runtime_cockpit.protocol.event_envelope import (
    ARC_PROTOCOL_VERSION,
    ArcEnvelope,
    ArcError,
    ArcMeta,
    err,
    ok,
)

warn(
    "agent_runtime_cockpit.protocol.envelope is deprecated since v0.1.0-alpha; "
    "import agent_runtime_cockpit.protocol.event_envelope instead. "
    "This shim will be removed in v0.3.0.",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ARC_PROTOCOL_VERSION", "ArcEnvelope", "ArcError", "ArcMeta", "ok", "err"]
