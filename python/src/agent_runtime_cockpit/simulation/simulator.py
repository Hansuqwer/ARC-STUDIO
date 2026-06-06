"""Action Simulator — static/dry-run prediction engine for SwarmGraph IR.

Pure static analysis. No execution, network, model calls, tool calls, or I/O.
Consumes IRGraph; produces SimulationReport.

Pipeline (13 steps):
  1. validate_graph
  2. reachability (BFS from entry points)
  3. per-node side effects
  4. per-node tool calls
  5. MCP registry join (read-only)
  6. policy lint (lint_workflow via to_workflow_info bridge)
  7. gate classification (hitl / trust / paid_call / write / privileged)
  8. node assembly
  9. edge assembly
  10. MCP summary
  11. cost estimate
  12. eval recommendations (optional)
  13. summary + determinism hash
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..swarmgraph_ir.exporters import to_workflow_info
from ..swarmgraph_ir.models import IRGraph, IRNode, IRNodeKind, SideEffectKind
from ..swarmgraph_ir.validation import validate_graph
from .models import (
    EvalRecommendationRef,
    PolicySimulationSummary,
    SimulatedCost,
    SimulatedEdge,
    SimulatedGate,
    SimulatedMcp,
    SimulatedNode,
    SimulatedSideEffect,
    SimulatedToolCall,
    SimulationConfig,
    SimulationReport,
    SimulationSummary,
    SimulationWarning,
)

log = logging.getLogger(__name__)

_OPAQUE_KINDS = {IRNodeKind.UNKNOWN}
_AUDIT_SIDE_EFFECT_KINDS = {SideEffectKind.WRITE, SideEffectKind.EXEC, SideEffectKind.SECRET_READ}

# Rough per-paid-call cost floor (USD) — advisory only, not billing data
_PAID_CALL_COST_FLOOR = 0.0001


# ── Step helpers ──────────────────────────────────────────────────────────────


def _reachable_nodes(graph: IRGraph, assume_all_branches: bool) -> set[str]:
    if assume_all_branches or not graph.entry_points:
        return {n.id for n in graph.nodes}
    reachable: set[str] = set(graph.entry_points)
    queue = list(graph.entry_points)
    adj: dict[str, list[str]] = {}
    for e in graph.edges:
        adj.setdefault(e.from_node, []).append(e.to_node)
    while queue:
        nid = queue.pop()
        for child in adj.get(nid, []):
            if child not in reachable:
                reachable.add(child)
                queue.append(child)
    return reachable


def _side_effects(node: IRNode, node_idx: int) -> list[SimulatedSideEffect]:
    effects = []
    for i, se in enumerate(node.side_effects):
        effects.append(
            SimulatedSideEffect(
                id=f"se-{node.id}-{i}",
                node_id=node.id,
                kind=se.kind.value,
                target=se.target,
                paid=se.paid,
                audit_required=se.kind in _AUDIT_SIDE_EFFECT_KINDS,
            )
        )
    return effects


def _tool_calls(node: IRNode, registry_data: dict[str, dict]) -> list[SimulatedToolCall]:
    calls = []
    i = 0
    if node.mcp_tool is not None:
        ref = node.mcp_tool
        rd = registry_data.get(ref.server_id, {})
        calls.append(
            SimulatedToolCall(
                id=f"tc-{node.id}-{i}",
                node_id=node.id,
                tool_name=ref.tool_name,
                is_mcp=True,
                server_id=ref.server_id,
                approved=ref.tool_name in rd.get("approved_tools", []),
                blocked=ref.tool_name in rd.get("blocked_tools", []),
                risk_level=ref.risk_level,
                would_execute=False,
            )
        )
        i += 1
    if node.tool is not None:
        calls.append(
            SimulatedToolCall(
                id=f"tc-{node.id}-{i}",
                node_id=node.id,
                tool_name=node.tool.name,
                namespace=node.tool.namespace,
                is_mcp=False,
                approved=node.tool.pinned,
                would_execute=False,
            )
        )
    return calls


def _gates(node: IRNode) -> list[SimulatedGate]:
    gates = []
    i = 0
    if node.kind is IRNodeKind.HUMAN_GATE:
        gates.append(
            SimulatedGate(
                id=f"gate-{node.id}-{i}",
                node_id=node.id,
                kind="hitl",
                label=node.label or "Human approval required",
                blocking=node.human_gate.blocking if node.human_gate else True,
            )
        )
        i += 1
    if node.privileged:
        gates.append(
            SimulatedGate(
                id=f"gate-{node.id}-{i}",
                node_id=node.id,
                kind="privileged",
                label=f"{node.label} (privileged)",
            )
        )
        i += 1
    if node.budget and node.budget.requires_paid_call:
        gates.append(
            SimulatedGate(
                id=f"gate-{node.id}-{i}",
                node_id=node.id,
                kind="paid_call",
                label=f"{node.label} (paid call)",
                blocking=not node.budget.paid_call_gate,
            )
        )
        i += 1
    if node.write_path:
        gates.append(
            SimulatedGate(
                id=f"gate-{node.id}-{i}",
                node_id=node.id,
                kind="write",
                label=f"Write: {node.write_path}",
            )
        )
    return gates


def _registry_data(config: SimulationConfig) -> dict[str, dict]:
    """Load MCP registry approval/block records. Read-only. Never queries servers."""
    if not config.include_mcp_registry:
        return {}
    try:
        from ..mcp.registry import McpRegistryStore

        store = McpRegistryStore()
        return {
            r.server_id: {"approved_tools": r.approved_tools, "blocked_tools": r.blocked_tools}
            for r in store.list_servers()
        }
    except Exception as exc:
        log.warning("MCP registry read failed (simulation continues): %s", exc)
        return {}


def _load_eval_recommendations(config: SimulationConfig) -> list[EvalRecommendationRef]:
    if not config.include_eval_recommendations:
        return []
    ws = Path(config.workspace) if config.workspace else Path.cwd()
    rec_dir = ws / ".arc" / "evals" / "recommendations"
    refs: list[EvalRecommendationRef] = []
    if not rec_dir.exists():
        return refs
    for p in sorted(rec_dir.glob("*.json")):
        try:
            data = json.loads(p.read_text())
            for rec in data.get("recommendations", []):
                refs.append(
                    EvalRecommendationRef(
                        source_file=p.name,
                        recommendation_id=rec.get("id", ""),
                        category=rec.get("category", ""),
                        title=rec.get("title", ""),
                        confidence=float(rec.get("confidence", 0.0)),
                        action=rec.get("action", ""),
                    )
                )
        except Exception as exc:
            log.warning("Eval recommendation load failed for %s: %s", p.name, exc)
    return refs


def _determinism_hash(report: SimulationReport) -> str:
    """Stable SHA-256 over the report excluding volatile fields."""
    data = report.model_dump()
    for key in ("generated_at", "determinism_hash"):
        data.pop(key, None)
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()[:16]


# ── Public API ────────────────────────────────────────────────────────────────


def simulate_graph(
    graph: IRGraph,
    config: Optional[SimulationConfig] = None,
) -> SimulationReport:
    """Run the 13-step simulation pipeline against an IRGraph.

    Pure static analysis — no execution, network, or file writes.
    Returns a fully deterministic SimulationReport.
    """
    cfg = config or SimulationConfig()

    # 1. Validate
    val = validate_graph(graph)
    warnings: list[SimulationWarning] = []
    for i, err in enumerate(val.errors):
        warnings.append(SimulationWarning(id=f"warn-{i}", code="validation_error", message=err))
    warn_offset = len(warnings)
    for i, w in enumerate(val.warnings):
        warnings.append(
            SimulationWarning(id=f"warn-{warn_offset + i}", code="validation_warning", message=w)
        )

    # 2. Reachability
    reachable = _reachable_nodes(graph, cfg.assume_all_branches)

    # 3-4. Side effects + tool calls per node (needs registry)
    reg = _registry_data(cfg)
    all_se: list[SimulatedSideEffect] = []
    all_tc: list[SimulatedToolCall] = []
    all_gates: list[SimulatedGate] = []
    sim_nodes: list[SimulatedNode] = []

    for node in graph.nodes:
        is_reachable = node.id in reachable
        se = _side_effects(node, 0) if is_reachable else []
        tc = _tool_calls(node, reg) if is_reachable else []
        gates = _gates(node) if is_reachable else []
        node_warnings: list[str] = []
        if node.kind is IRNodeKind.UNKNOWN and not node.metadata:
            node_warnings.append("opaque node — no structured metadata available")
        if node.mcp_tool and not node.mcp_tool.manifest_hash:
            node_warnings.append(f"MCP tool '{node.mcp_tool.tool_name}' has no manifest pin")

        all_se.extend(se)
        all_tc.extend(tc)
        all_gates.extend(gates)
        sim_nodes.append(
            SimulatedNode(
                node_id=node.id,
                label=node.label,
                kind=node.kind.value,
                reachable=is_reachable,
                risk_level=node.risk.level,
                side_effects=se,
                tool_calls=tc,
                gates=gates,
                is_opaque=(
                    node.kind in _OPAQUE_KINDS
                    and not node.metadata
                    and node.tool is None
                    and node.mcp_tool is None
                ),
                warnings=node_warnings,
            )
        )

    # 5. (MCP registry join already done in step 4 via reg)

    # 6. Policy lint
    policy_summary = PolicySimulationSummary()
    try:
        from ..security.policy_linter import lint_workflow

        wf = to_workflow_info(graph)
        pr = lint_workflow(
            wf,
            workspace_root=Path(cfg.workspace) if cfg.workspace else None,
            risk_level=graph.risk.level,
            suggested_consensus=graph.consensus.suggested_protocol,
        )
        policy_summary = PolicySimulationSummary(
            can_run=pr.can_run,
            risk_level=pr.risk_level,
            suggested_consensus=pr.suggested_consensus,
            error_count=len(pr.errors),
            warning_count=len(pr.warnings),
            issues=[i.model_dump() for i in pr.issues],
        )
    except Exception as exc:
        log.warning("Policy lint failed (simulation continues): %s", exc)
        warn_offset2 = len(warnings)
        warnings.append(
            SimulationWarning(
                id=f"warn-{warn_offset2}",
                code="policy_lint_degraded",
                message=f"Policy lint unavailable: {exc}",
            )
        )

    # 7-8. Edges
    sim_edges = [
        SimulatedEdge(
            edge_id=e.id,
            from_node=e.from_node,
            to_node=e.to_node,
            conditional=e.conditional,
            reachable=e.from_node in reachable and e.to_node in reachable,
        )
        for e in graph.edges
    ]

    # 9. MCP summary
    mcp_nodes = [n for n in graph.nodes if n.mcp_tool is not None and n.id in reachable]
    unique_servers = list({n.mcp_tool.server_id for n in mcp_nodes})  # type: ignore[union-attr]
    unpinned = [n.mcp_tool.server_id for n in mcp_nodes if not n.mcp_tool.manifest_hash]  # type: ignore[union-attr]
    blocked_tools = [tc.tool_name for tc in all_tc if tc.is_mcp and tc.blocked]
    approved_tools = [tc.tool_name for tc in all_tc if tc.is_mcp and tc.approved]
    mcp_summary = SimulatedMcp(
        total_mcp_nodes=len(mcp_nodes),
        unique_servers=unique_servers,
        unpinned_servers=list(set(unpinned)),
        blocked_tools=blocked_tools,
        approved_tools=approved_tools,
    )

    # 10. Cost estimate
    paid_calls = [se for se in all_se if se.paid]
    per_call = (
        cfg.cost_per_paid_call_usd
        if cfg.cost_per_paid_call_usd is not None
        else _PAID_CALL_COST_FLOOR
    )
    cost = SimulatedCost(
        has_paid_calls=bool(paid_calls),
        estimated_paid_call_count=len(paid_calls),
        estimated_cost_floor_usd=round(len(paid_calls) * per_call, 6),
    )

    # 11. Eval recommendations
    eval_refs = _load_eval_recommendations(cfg)

    # 12. Summary
    hitl_gates = [g for g in all_gates if g.kind == "hitl"]
    summary = SimulationSummary(
        total_nodes=len(graph.nodes),
        reachable_nodes=len(reachable),
        opaque_nodes=sum(1 for n in sim_nodes if n.is_opaque),
        total_edges=len(graph.edges),
        side_effect_count=len(all_se),
        tool_call_count=len(all_tc),
        mcp_tool_count=len(mcp_nodes),
        gate_count=len(all_gates),
        hitl_gate_count=len(hitl_gates),
        paid_call_count=len(paid_calls),
        warning_count=len(warnings),
    )

    # 13. Assemble + hash
    report = SimulationReport(
        graph_id=graph.id,
        graph_hash=graph.graph_hash,
        generated_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        config=cfg,
        summary=summary,
        nodes=sim_nodes,
        edges=sim_edges,
        side_effects=all_se,
        tool_calls=all_tc,
        mcp=mcp_summary,
        gates=all_gates,
        policy=policy_summary,
        cost=cost,
        recommendations=eval_refs,
        warnings=warnings,
    )
    report.determinism_hash = _determinism_hash(report)
    return report
