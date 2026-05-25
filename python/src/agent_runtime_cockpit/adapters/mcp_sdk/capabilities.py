"""MCP Python SDK adapter capabilities.

Adapter Phase 35: T1 (Detection) + T2 (Export) only.

T3 execution is intentionally not implemented because:
- MCP servers are protocol bridges: executing them requires live transport
  (stdio/HTTP/SSE) and client-side session management.
- Trust posture is the most subtle of all adapters: an MCP server exposes
  tools and resources that may perform privileged operations; running an
  arbitrary MCP server under ARC without user-explicit trust gates would
  violate Phase 23 enforcement principles.
- The MCP Python SDK has active development and API churn (v1.x stable but
  v2 pre-alpha on main), so execution lifecycle management is premature.
"""

from __future__ import annotations

from ...protocol.capabilities import RuntimeCapabilities


def get_mcp_sdk_capabilities() -> RuntimeCapabilities:
    """Return honest capabilities for the MCP Python SDK adapter."""
    return RuntimeCapabilities(
        can_inspect=True,
        can_run=False,
        can_trace=False,
        can_replay=False,
        can_export_schema=False,
        can_export_workflow=True,
        can_stream_events=False,
        can_audit=False,
        can_emit_contract=False,
        can_emit_receipt=False,
        can_emit_autopsy=False,
        can_emit_evidence=False,
        has_stable_ids=False,
        requires_network=False,  # server itself may or may not need network
        requires_shell=False,
        requires_secrets=False,
    )
