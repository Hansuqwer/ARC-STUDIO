"""Permission audit logging — records profile enforcement decisions to the hash-chain audit log."""
from __future__ import annotations

import datetime as dt
from pathlib import Path

from .chain import AuditChainWriter


def log_permission_decision(
    audit_log_dir: Path,
    runtime: str,
    profile_id: str,
    decision: str,
    reason: str,
    details: dict | None = None,
) -> None:
    """Append a permission decision to the hash-chained audit log.

    Args:
        audit_log_dir: Directory containing the audit chain file.
        runtime: The runtime adapter ID.
        profile_id: The profile ID that was enforced.
        decision: ``allow`` | ``deny`` | ``warn``.
        reason: Human-readable explanation.
        details: Optional extra context (env, backend, etc.).
    """
    audit_log_dir.mkdir(parents=True, exist_ok=True)
    chain_path = audit_log_dir / "permissions.audit.jsonl"

    event = {
        "type": "permission_decision",
        "runtime": runtime,
        "profile_id": profile_id,
        "decision": decision,
        "reason": reason,
        "timestamp": dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    if details:
        event["details"] = details

    with AuditChainWriter(chain_path) as writer:
        writer.append(event)
