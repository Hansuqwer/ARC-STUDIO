"""Google ADK adapter capabilities.

Adapter Phase 34: T1 (Detection) + T2 (Export) only.
T3 execution is intentionally not implemented because:
- Google ADK 0.x has active API churn; breaking changes expected before 1.0.
- Agent execution requires live Gemini/Google AI provider calls.
- Runner lifecycle (session services, artifact stores) adds significant
  stateful complexity inappropriate for a local static adapter.
"""

from __future__ import annotations

from ...protocol.capabilities import RuntimeCapabilities


def get_google_adk_capabilities() -> RuntimeCapabilities:
    """Return honest capabilities for the Google ADK adapter."""
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
        requires_network=True,
        requires_shell=False,
        requires_secrets=True,
    )
