"""Deprecated shim for ARC event envelopes.

The canonical ADR-018 module is ``agent_runtime_cockpit.protocol.event_envelope``.
This import path stays for one release cycle.
"""
from __future__ import annotations

from warnings import warn

from agent_runtime_cockpit.protocol.event_envelope import ARC_PROTOCOL_VERSION, ArcEnvelope, ArcError, ArcMeta, err, ok

warn(
    "agent_runtime_cockpit.protocol.envelope is deprecated; import "
    "agent_runtime_cockpit.protocol.event_envelope instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["ARC_PROTOCOL_VERSION", "ArcEnvelope", "ArcError", "ArcMeta", "ok", "err"]
