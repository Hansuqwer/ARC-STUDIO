"""LangChain adapter capabilities.

Phase 26 T1: Detection only.
Phase 26 T2: Export (planned).
Phase 26 T3: Live streaming (planned).
"""

from __future__ import annotations

from ...protocol.capabilities import RuntimeCapabilities


def get_langchain_capabilities() -> RuntimeCapabilities:
    """Return capabilities for LangChain adapter.

    Phase 26 T1 (Detection): Detection implemented.
    Phase 26 T2 (Export): Workflow export implemented (AST-based).
    Phase 26 T3 (Live streaming): Live streaming implemented via BaseCallbackHandler.
    """
    return RuntimeCapabilities(
        can_inspect=True,  # Can detect LangChain usage
        can_run=True,  # T3: Live streaming via ARCCallbackHandler
        can_trace=True,  # T3: Event tracing via callbacks
        can_replay=False,  # Future: Replay support
        can_export_schema=False,  # Future: Schema export
        can_export_workflow=True,  # T2: Workflow export via AST scan
        can_stream_events=True,  # T3: Live event streaming via callbacks
        can_audit=False,  # Future: Audit support
        can_emit_contract=False,  # Future: Contract emission
        can_emit_receipt=False,  # Future: Receipt emission
        can_emit_autopsy=False,  # Future: Autopsy emission
        can_emit_evidence=False,  # Future: Evidence emission
        has_stable_ids=False,  # Future: Stable ID support
    )
