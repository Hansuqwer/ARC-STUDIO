"""Shared keyed (HMAC) run-audit checkpoint helper (B2P-19).

The canonical way for any adapter run path to write tamper-evident keyed audit material for a
completed run. Key-gated: when no audit key is configured it is a no-op (returns ``None``) — keyed
audit requires an explicit HMAC key (ADR-005). The written chain is verifiable with
``verify_hmac_chain``. This is the shared mechanism run paths adopt; an adapter-wide keyed-audit
claim stays gated until every run path calls it (see roadmap Non-Negotiable Scope Boundaries).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from .hmac_chain import HmacAuditChainWriter
from .key_manager import AuditKeyManager


def write_run_keyed_audit(
    run_id: str,
    *,
    status: str,
    workflow_id: str,
    event_count: int,
    workspace_root: Path,
    runtime: str | None = None,
    key_manager: AuditKeyManager | None = None,
) -> Optional[Path]:
    """Append a keyed (HMAC) audit checkpoint for a completed run.

    Returns the chain path, or ``None`` when no audit key is configured (no-op). Never raises for
    a missing key — callers may invoke it unconditionally at the end of a run path.
    """
    km = key_manager or AuditKeyManager()
    key, _status = km.get_key()
    if key is None:
        return None
    chain_path = Path(workspace_root) / ".arc" / "audit" / f"{run_id}.run.audit.jsonl"
    chain_path.parent.mkdir(parents=True, exist_ok=True)
    writer = HmacAuditChainWriter(chain_path, km)
    writer.append(
        {
            "type": "run_audit_checkpoint",
            "run_id": run_id,
            "status": status,
            "workflow_id": workflow_id,
            "event_count": event_count,
            "runtime": runtime,
        }
    )
    return chain_path
