"""MCP enrichment for SwarmGraph IR — local reads only.

Joins IR MCP-tool nodes against the local ManifestStore (pins + per-tool risk) and
McpRegistryStore (approve/block records). This reads JSON files under the workspace
and ``~/.arc/mcp``; it NEVER launches an MCP server or performs any network call.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from .models import IRGraph

log = logging.getLogger(__name__)


def attach_mcp_risk(graph: IRGraph, *, workspace: Optional[str] = None) -> IRGraph:
    """Fill manifest hash / risk / approval flags on IR MCP-tool nodes (in place)."""
    from ..mcp.manifests import ManifestStore
    from ..mcp.registry import McpRegistryStore

    ws = Path(workspace) if workspace else Path.cwd()
    manifests = ManifestStore(workspace=ws)
    registry = McpRegistryStore()

    for node in graph.nodes:
        ref = node.mcp_tool
        if ref is None:
            continue

        try:
            pinned = manifests.load(ref.server_id)
            if pinned is not None:
                ref.manifest_hash = pinned.manifest_hash
                for tr in pinned.tool_risks:
                    if tr.tool_name == ref.tool_name:
                        ref.can_write = tr.can_write
                        ref.can_network = tr.can_network
                        ref.can_read_secrets = tr.can_read_secrets
                        ref.accesses_outside_workspace = tr.accesses_outside_workspace
                        ref.risk_level = tr.risk_level
                        break

            ref.approved = registry.is_tool_approved(ref.server_id, ref.tool_name)
            ref.blocked = registry.is_tool_blocked(ref.server_id, ref.tool_name)
        except Exception as exc:  # noqa: BLE001
            log.warning(
                "MCP enrichment failed for server=%r tool=%r: %s",
                ref.server_id,
                ref.tool_name,
                exc,
            )

    return graph
