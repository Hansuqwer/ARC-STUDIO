"""Infer MCP manifest drift from run artifacts and local registry.

Never starts MCP servers. Never queries remote registries. Read-only.
Emits warnings when MCP metadata is absent; never errors on missing data.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from pydantic import BaseModel

log = logging.getLogger(__name__)

_MCP_EVENT_TYPES = {
    "mcp.tool.call",
    "mcp.tool.result",
    "mcp.tool.call.result",
    "mcp_tool_call",
    "arc.mcp.tool",
}


class McpToolStatus(BaseModel):
    server_id: str
    tool_name: Optional[str] = None
    manifest_hash_in_run: Optional[str] = None  # from run events
    manifest_hash_pinned: Optional[str] = None  # from ManifestStore
    status: str = "unknown"  # pinned | unpinned | drifted | unknown | blocked | approved


class McpDriftSummary(BaseModel):
    total_mcp_events: int = 0
    servers_seen: list[str] = []
    tool_statuses: list[McpToolStatus] = []
    warnings: list[str] = []

    @property
    def has_drift(self) -> bool:
        return any(t.status == "drifted" for t in self.tool_statuses)


def _collect_mcp_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in events if (e.get("type") or "").lower() in _MCP_EVENT_TYPES]


def infer_mcp_drift(
    events: list[dict[str, Any]],
    *,
    workspace: Optional[str] = None,
) -> McpDriftSummary:
    """Infer MCP manifest drift from run events + local ManifestStore/McpRegistryStore.

    Args:
        events:    List of RunEvent dicts from the trace.
        workspace: Workspace root for ManifestStore (default: cwd).

    Returns:
        McpDriftSummary. Warnings emitted, never exceptions.
    """
    from pathlib import Path

    mcp_events = _collect_mcp_events(events)
    summary = McpDriftSummary(total_mcp_events=len(mcp_events))

    if not mcp_events:
        summary.warnings.append("MCP_METADATA_NOT_FOUND_FOR_RUN")
        return summary

    # Collect unique (server_id, tool_name, manifest_hash) from events
    seen: dict[tuple[str, str], str | None] = {}
    for ev in mcp_events:
        data = ev.get("data") or {}
        sid = data.get("server_id", "") or data.get("mcp_server_id", "")
        tname = data.get("tool_name", "") or data.get("mcp_tool_name", "")
        mhash = data.get("manifest_hash") or data.get("mcp_manifest_hash")
        if sid:
            key = (sid, tname)
            if key not in seen:
                seen[key] = mhash

    summary.servers_seen = list({k[0] for k in seen})

    # Load local manifests + registry
    ws = Path(workspace) if workspace else Path.cwd()
    try:
        from ..mcp.manifests import ManifestStore

        manifests = ManifestStore(workspace=ws)
    except Exception as exc:
        log.warning("ManifestStore unavailable: %s", exc)
        manifests = None

    try:
        from ..mcp.registry import McpRegistryStore

        registry = McpRegistryStore()
    except Exception as exc:
        log.warning("McpRegistryStore unavailable: %s", exc)
        registry = None

    for (sid, tname), run_hash in seen.items():
        pinned_manifest = manifests.load(sid) if manifests else None
        pinned_hash = pinned_manifest.manifest_hash if pinned_manifest else None

        approved = registry.is_tool_approved(sid, tname) if registry and tname else False
        blocked = registry.is_tool_blocked(sid, tname) if registry and tname else False

        if blocked:
            status = "blocked"
        elif run_hash and pinned_hash:
            status = "pinned" if run_hash == pinned_hash else "drifted"
        elif pinned_hash:
            status = "pinned"
        elif run_hash:
            status = "unpinned"
        else:
            status = "unknown"

        if approved and status not in ("drifted", "blocked"):
            status = "approved"

        summary.tool_statuses.append(
            McpToolStatus(
                server_id=sid,
                tool_name=tname or None,
                manifest_hash_in_run=run_hash,
                manifest_hash_pinned=pinned_hash,
                status=status,
            )
        )

    return summary
