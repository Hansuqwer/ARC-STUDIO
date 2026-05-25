"""Smolagents adapter capabilities."""

from __future__ import annotations

from ...protocol.capabilities import RuntimeCapabilities


def get_smolagents_capabilities() -> RuntimeCapabilities:
    """Return capabilities for Smolagents adapter.

    T1/T2 are static. T3 is gated due to code-execution/provider risk.
    """
    return RuntimeCapabilities(
        can_inspect=True,
        can_run=False,
        can_trace=False,
        can_replay=False,
        can_export_schema=False,
        can_export_workflow=True,
        can_stream_events=False,
        can_audit=False,
        requires_network=True,
        requires_shell=True,
        requires_secrets=True,
    )
