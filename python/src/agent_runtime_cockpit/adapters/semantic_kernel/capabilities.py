"""Semantic Kernel adapter capabilities.

Adapter Phase 33: T1 (Detection) + T2 (Export) only.
T3 execution is intentionally not implemented because Semantic Kernel versions
and provider wiring vary widely, and agent execution may call external models.
"""

from __future__ import annotations

from ...protocol.capabilities import RuntimeCapabilities


def get_semantic_kernel_capabilities() -> RuntimeCapabilities:
    """Return honest capabilities for the Semantic Kernel adapter."""
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
    )
