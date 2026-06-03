"""MCP manifest diff - compare MCP server manifests and drift status."""

from __future__ import annotations

from .models import DiffSubject, DiffSubjectKind, McpManifestDiff, RunDiffReport


def diff_mcp_manifests(left, right):
    from .models import DiffSummary

    left_map = {m.server_id: m for m in left}
    right_map = {m.server_id: m for m in right}
    servers_added = [sid for sid in right_map if sid not in left_map]
    servers_removed = [sid for sid in left_map if sid not in right_map]
    hash_changed = []
    for sid in set(left_map) & set(right_map):
        l_hash = left_map[sid].manifest_hash
        r_hash = right_map[sid].manifest_hash
        if l_hash != r_hash:
            hash_changed.append({"server_id": sid, "left_hash": l_hash, "right_hash": r_hash})
    drifted_servers = [h["server_id"] for h in hash_changed]
    all_tools_left = set()
    all_tools_right = set()
    for m in left:
        all_tools_left.update(m.tool_names)
    for m in right:
        all_tools_right.update(m.tool_names)
    tools_added = sorted(all_tools_right - all_tools_left)
    tools_removed = sorted(all_tools_left - all_tools_right)
    mcp_diff = McpManifestDiff(
        servers_added=servers_added,
        servers_removed=servers_removed,
        hash_changed=hash_changed,
        approved_tools_delta=0,
        blocked_tools_delta=0,
        tools_added=tools_added,
        tools_removed=tools_removed,
        drifted_servers=drifted_servers,
    )
    summary = DiffSummary()
    summary.mcp_drift_changed = bool(drifted_servers)
    summary.compute_total()
    report = RunDiffReport(
        left=DiffSubject(
            kind=DiffSubjectKind.MCP_MANIFEST,
            id="mcp-left",
            metadata={"server_count": len(left), "servers": sorted(left_map.keys())},
        ),
        right=DiffSubject(
            kind=DiffSubjectKind.MCP_MANIFEST,
            id="mcp-right",
            metadata={"server_count": len(right), "servers": sorted(right_map.keys())},
        ),
        mode="mcp_vs_mcp",
        summary=summary,
        mcp_diff=mcp_diff,
        warnings=[f"MCP drift detected: {s}" for s in drifted_servers] if drifted_servers else [],
    )
    return report.with_hash()
