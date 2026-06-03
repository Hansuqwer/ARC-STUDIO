"""SwarmGraph IR graph diff - structural and semantic comparison."""

from __future__ import annotations


from ..swarmgraph_ir import graph_hash
from ..swarmgraph_ir.models import IRGraph
from .models import (
    ChangeType,
    DiffSubject,
    DiffSubjectKind,
    FirstDivergence,
    GraphDiff,
    NodeDiff,
    NodeDiffField,
    RunDiffReport,
)

_NODE_SEMANTIC_FIELDS = ["label", "kind", "privileged", "write_path", "trust_annotation"]


def _node_map(nodes):
    return {n.id: n for n in nodes}


def _edge_map(edges):
    return {e.id: e for e in edges}


def _compare_risk(left, right):
    if left is None and right is None:
        return None
    l = left.level if left else "none"
    r = right.level if right else "none"
    return f"{l} -> {r}" if l != r else None


def _compare_gate(left, right):
    if left is None and right is None:
        return None
    if left is None and right is not None:
        return "added"
    if left is not None and right is None:
        return "removed"
    if left.blocking != right.blocking:
        return f"blocking {left.blocking} -> {right.blocking}"
    return None


def _compare_mcp(left, right):
    if left is None and right is None:
        return None
    if left is None and right is not None:
        return "added"
    if left is not None and right is None:
        return "removed"
    parts = []
    if left.approved != right.approved:
        parts.append(f"approved {left.approved} -> {right.approved}")
    if left.blocked != right.blocked:
        parts.append(f"blocked {left.blocked} -> {right.blocked}")
    if left.manifest_hash != right.manifest_hash:
        parts.append("manifest_hash changed")
    return "; ".join(parts) if parts else None


def _compare_tool_delta(left, right):
    if left is None and right is None:
        return None
    ln = left.get("name") if left else None
    rn = right.get("name") if right else None
    return f"{ln} -> {rn}" if ln != rn else None


def _compare_model_call(left, right):
    if left is None and right is None:
        return None
    lp = left.paid if left else False
    rp = right.paid if right else False
    if lp != rp:
        return rp and not lp
    return None


def diff_nodes(left_nodes, right_nodes):
    left_map = _node_map(left_nodes)
    right_map = _node_map(right_nodes)
    added_ids = [nid for nid in right_map if nid not in left_map]
    removed_ids = [nid for nid in left_map if nid not in right_map]
    changed = []
    for nid in set(left_map) & set(right_map):
        left_node = left_map[nid]
        right_node = right_map[nid]
        diff = _diff_single_node(left_node, right_node)
        if diff is not None and diff.change_type != ChangeType.UNCHANGED:
            changed.append(diff)
    return changed, added_ids, removed_ids


def _diff_single_node(left, right):
    changed_fields = []
    risk_delta = _compare_risk(left.risk, right.risk)
    l_data = left.model_dump(mode="json")
    r_data = right.model_dump(mode="json")
    for field in _NODE_SEMANTIC_FIELDS:
        l_val = l_data.get(field)
        r_val = r_data.get(field)
        if l_val != r_val:
            ct = (
                ChangeType.ADDED
                if l_val is None
                else ChangeType.REMOVED
                if r_val is None
                else ChangeType.CHANGED
            )
            changed_fields.append(
                NodeDiffField(field_name=field, left_value=l_val, right_value=r_val, change_type=ct)
            )
    tool_left = left.tool.model_dump(mode="json") if left.tool else None
    tool_right = right.tool.model_dump(mode="json") if right.tool else None
    tool_delta = _compare_tool_delta(tool_left, tool_right)
    mcp_delta = _compare_mcp(left.mcp_tool, right.mcp_tool)
    consensus_left = left.consensus.suggested_protocol if left.consensus else None
    consensus_right = right.consensus.suggested_protocol if right.consensus else None
    consensus_delta = None
    if consensus_left != consensus_right:
        consensus_delta = f"{consensus_left or 'none'} -> {consensus_right or 'none'}"
    hitl_delta = _compare_gate(left.human_gate, right.human_gate)
    paid_call_delta = _compare_model_call(left.model_call, right.model_call)
    audit_left = left.audit_boundary is not None
    audit_right = right.audit_boundary is not None
    audit_delta = None
    if audit_left != audit_right:
        audit_delta = "added" if audit_right else "removed"
    is_changed = bool(
        risk_delta
        or changed_fields
        or tool_delta
        or mcp_delta
        or consensus_delta
        or hitl_delta
        or paid_call_delta is not None
        or audit_delta
    )
    if not is_changed:
        return None
    is_regression = bool(
        hitl_delta == "removed"
        or (consensus_delta and "-> none" in consensus_delta)
        or paid_call_delta is True
    )
    regression_reason = None
    if hitl_delta == "removed":
        regression_reason = "HITL gate removed"
    elif risk_delta and ("-> high" in risk_delta or "-> critical" in risk_delta):
        regression_reason = f"Risk level increased: {risk_delta}"
    elif paid_call_delta is True:
        regression_reason = "Paid call introduced without explicit gate"
    return NodeDiff(
        node_id=left.id,
        change_type=ChangeType.CHANGED,
        changed_fields=changed_fields,
        risk_delta=risk_delta,
        tool_delta=tool_delta,
        mcp_delta=mcp_delta,
        consensus_delta=consensus_delta,
        hitl_delta=hitl_delta,
        paid_call_delta=paid_call_delta,
        audit_delta=audit_delta,
        is_semantic_regression=is_regression,
        regression_reason=regression_reason,
    )


def diff_edges(left_edges, right_edges):
    left_map = _edge_map(left_edges)
    right_map = _edge_map(right_edges)
    added_ids = [eid for eid in right_map if eid not in left_map]
    removed_ids = [eid for eid in left_map if eid not in right_map]
    changed = []
    for eid in set(left_map) & set(right_map):
        left_e = left_map[eid]
        right_e = right_map[eid]
        l_data = left_e.model_dump(mode="json")
        r_data = right_e.model_dump(mode="json")
        meaningful = {"from_node", "to_node", "conditional", "condition", "label"}
        cf = {
            k: (l_data.get(k), r_data.get(k)) for k in meaningful if l_data.get(k) != r_data.get(k)
        }
        if cf:
            changed.append({"edge_id": eid, "changed_fields": cf})
    return added_ids, removed_ids, changed


def build_graph_diff(left, right):
    changed_nodes, nodes_added, nodes_removed = diff_nodes(left.nodes, right.nodes)
    edges_added, edges_removed, edges_changed = diff_edges(left.edges, right.edges)
    return GraphDiff(
        nodes_added=nodes_added,
        nodes_removed=nodes_removed,
        nodes_changed=changed_nodes,
        edges_added=edges_added,
        edges_removed=edges_removed,
        edges_changed=edges_changed,
        node_count_left=len(left.nodes),
        node_count_right=len(right.nodes),
        edge_count_left=len(left.edges),
        edge_count_right=len(right.edges),
        risk_level_left=left.risk.level if left.risk else None,
        risk_level_right=right.risk.level if right.risk else None,
        consensus_left=left.consensus.suggested_protocol if left.consensus else None,
        consensus_right=right.consensus.suggested_protocol if right.consensus else None,
    )


def _divergence_reason(diff):
    reasons = []
    if diff.risk_delta:
        reasons.append(f"Risk: {diff.risk_delta}")
    if diff.hitl_delta:
        reasons.append(f"HITL: {diff.hitl_delta}")
    if diff.consensus_delta:
        reasons.append(f"Consensus: {diff.consensus_delta}")
    if diff.tool_delta:
        reasons.append(f"Tool: {diff.tool_delta}")
    if diff.mcp_delta:
        reasons.append(f"MCP: {diff.mcp_delta}")
    if diff.paid_call_delta is True:
        reasons.append("Paid call introduced")
    if diff.audit_delta:
        reasons.append(f"Audit: {diff.audit_delta}")
    return "; ".join(reasons) if reasons else "Node structure changed"


def find_first_divergence(left, right):
    left_map = {n.id: n for n in left.nodes}
    right_map = {n.id: n for n in right.nodes}
    for node in left.nodes:
        if node.id not in right_map:
            return FirstDivergence(
                kind="node",
                node_id=node.id,
                reason=f"Node '{node.id}' present in left but not in right",
                left_value={"id": node.id, "label": node.label, "kind": node.kind.value},
                right_value=None,
            )
        right_node = right_map[node.id]
        node_diff = _diff_single_node(node, right_node)
        if node_diff is not None and node_diff.change_type == ChangeType.CHANGED:
            return FirstDivergence(
                kind="node",
                node_id=node.id,
                reason=_divergence_reason(node_diff),
                left_value=node.model_dump(mode="json"),
                right_value=right_node.model_dump(mode="json"),
            )
    for node in right.nodes:
        if node.id not in left_map:
            return FirstDivergence(
                kind="node",
                node_id=node.id,
                reason=f"Node '{node.id}' present in right but not in left",
                left_value=None,
                right_value={"id": node.id, "label": node.label, "kind": node.kind.value},
            )
    left_edge_map = {e.id: e for e in left.edges}
    right_edge_map = {e.id: e for e in right.edges}
    for edge in left.edges:
        if edge.id not in right_edge_map:
            return FirstDivergence(
                kind="edge",
                edge_id=edge.id,
                reason=f"Edge '{edge.id}' present in left but not in right",
                left_value=edge.model_dump(mode="json"),
                right_value=None,
            )
    for edge in right.edges:
        if edge.id not in left_edge_map:
            return FirstDivergence(
                kind="edge",
                edge_id=edge.id,
                reason=f"Edge '{edge.id}' present in right but not in left",
                left_value=None,
                right_value=edge.model_dump(mode="json"),
            )
    return None


def diff_ir_graphs(left, right):
    from .models import DiffSummary, RiskDiff

    graph_diff = build_graph_diff(left, right)
    first_div = find_first_divergence(left, right)
    summary = DiffSummary()
    summary.nodes_added = len(graph_diff.nodes_added)
    summary.nodes_removed = len(graph_diff.nodes_removed)
    summary.nodes_changed = len(graph_diff.nodes_changed)
    summary.edges_added = len(graph_diff.edges_added)
    summary.edges_removed = len(graph_diff.edges_removed)
    summary.edges_changed = len(graph_diff.edges_changed)
    for node_diff in graph_diff.nodes_changed:
        if node_diff.is_semantic_regression:
            if node_diff.hitl_delta == "removed":
                summary.hitl_removed = True
            if node_diff.risk_delta and (
                "-> high" in node_diff.risk_delta or "-> critical" in node_diff.risk_delta
            ):
                summary.risk_increased = True
            if node_diff.paid_call_delta is True:
                summary.paid_call_delta += 1
    risk_levels = {"low": 0, "medium": 1, "high": 2, "critical": 3}
    l_val = risk_levels.get(graph_diff.risk_level_left, 0)
    r_val = risk_levels.get(graph_diff.risk_level_right, 0)
    if r_val > l_val:
        summary.risk_increased = True
    elif r_val < l_val:
        summary.risk_decreased = True
    if graph_diff.consensus_left != graph_diff.consensus_right:
        summary.consensus_changed = True
    summary.compute_total()
    left_subject = DiffSubject(
        kind=DiffSubjectKind.IR_GRAPH,
        id=left.id,
        hash=graph_hash(left),
        graph_hash=left.graph_hash,
        metadata={
            "name": left.name,
            "runtime": left.runtime,
            "node_count": len(left.nodes),
            "edge_count": len(left.edges),
        },
    )
    right_subject = DiffSubject(
        kind=DiffSubjectKind.IR_GRAPH,
        id=right.id,
        hash=graph_hash(right),
        graph_hash=right.graph_hash,
        metadata={
            "name": right.name,
            "runtime": right.runtime,
            "node_count": len(right.nodes),
            "edge_count": len(right.edges),
        },
    )
    risk_diff = RiskDiff(
        level_left=graph_diff.risk_level_left,
        level_right=graph_diff.risk_level_right,
        level_changed=graph_diff.risk_level_left != graph_diff.risk_level_right,
        score_delta=float(r_val - l_val),
    )
    report = RunDiffReport(
        left=left_subject,
        right=right_subject,
        mode="ir_vs_ir",
        summary=summary,
        first_divergence=first_div,
        graph_diff=graph_diff,
        risk_diff=risk_diff,
        warnings=[],
        mode_metadata={
            "ir_version_left": left.ir_version,
            "ir_version_right": right.ir_version,
            "runtime_left": left.runtime,
            "runtime_right": right.runtime,
        },
    )
    return report.with_hash()


def diff_ir_from_paths(path_a, path_b):
    from .loaders import load_ir_from_path

    result_left = load_ir_from_path(path_a)
    result_right = load_ir_from_path(path_b)
    errors = [e.message for e in result_left.errors] + [e.message for e in result_right.errors]
    warnings = result_left.warnings + result_right.warnings
    if result_left.data is None or result_right.data is None:
        report = RunDiffReport(
            left=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id=path_a, path=path_a),
            right=DiffSubject(kind=DiffSubjectKind.IR_GRAPH, id=path_b, path=path_b),
            mode="ir_vs_ir",
            warnings=warnings,
            errors=errors,
        )
        return report.with_hash(), errors, warnings
    if not isinstance(result_left.data, IRGraph):
        warnings.append("Left: file parsed as raw dict (not IRGraph)")
    if not isinstance(result_right.data, IRGraph):
        warnings.append("Right: file parsed as raw dict (not IRGraph)")
    if isinstance(result_left.data, IRGraph) and isinstance(result_right.data, IRGraph):
        report = diff_ir_graphs(result_left.data, result_right.data)
        report.left.path = path_a
        report.right.path = path_b
    else:
        from .models import DiffSummary

        l_data = result_left.data if isinstance(result_left.data, dict) else {}
        r_data = result_right.data if isinstance(result_right.data, dict) else {}
        summary = DiffSummary()
        summary.nodes_added = max(0, len(r_data.get("nodes", [])) - len(l_data.get("nodes", [])))
        summary.nodes_removed = max(0, len(l_data.get("nodes", [])) - len(r_data.get("nodes", [])))
        summary.compute_total()
        report = RunDiffReport(
            left=DiffSubject(
                kind=DiffSubjectKind.IR_GRAPH,
                id=l_data.get("id", path_a),
                path=path_a,
                hash="unknown",
            ),
            right=DiffSubject(
                kind=DiffSubjectKind.IR_GRAPH,
                id=r_data.get("id", path_b),
                path=path_b,
                hash="unknown",
            ),
            mode="ir_vs_ir",
            summary=summary,
            warnings=warnings + ["Raw dict comparison - limited structural diff"],
        )
    return report.with_hash(), errors, warnings
