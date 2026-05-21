"""Deprecated shim for RuntimeCapability.

RuntimeCapability is canonical under ``agent_runtime_cockpit.protocol`` per
ADR-018. This import path stays for one release cycle.
"""

from __future__ import annotations

from warnings import warn

from agent_runtime_cockpit.protocol.runtime_capability import RuntimeCapability

warn(
    "agent_runtime_cockpit.runtime.capability is deprecated; import "
    "agent_runtime_cockpit.protocol.runtime_capability instead",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["RuntimeCapability"]
