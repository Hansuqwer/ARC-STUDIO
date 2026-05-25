"""Haystack adapter capabilities.

Phase 31: T1 (Detection) + T2 (Export) available.
T3 (Runner) is gated scaffold only.
"""

from __future__ import annotations

from ...protocol.capabilities import RuntimeCapabilities


def get_haystack_capabilities() -> RuntimeCapabilities:
    """Return capabilities for Haystack adapter.

    T1 (Detection): AST-based detection of Pipelines, Components, YAML pipelines.
    T2 (Export): AST-based export of Pipeline DAGs to WorkflowInfo.
    T3 (Runner): Gated scaffold only; requires ARC_HAYSTACK_RUNNER_ENABLED=1.
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
        can_emit_contract=False,
        can_emit_receipt=False,
        can_emit_autopsy=False,
        can_emit_evidence=False,
        has_stable_ids=False,
    )
