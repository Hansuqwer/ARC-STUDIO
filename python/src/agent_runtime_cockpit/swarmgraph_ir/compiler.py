"""SwarmGraph IR compiler — normalization & analysis only.

The compiler maps an already-exported ``WorkflowInfo`` (or raw JSON) into a typed
IRGraph, infers side effects / capabilities / risk / consensus hints, validates the
graph, and computes a deterministic hash.

It NEVER executes the workflow, calls a tool/model, opens a network connection, or
launches an MCP server. Risk/consensus hints come from the SwarmGraph SDK's pure
analysis helpers (``assess_prompt_risk`` / ``select_consensus_protocol``), which are
imported as the top-level ``swarmgraph`` distribution — the same path the policy
linter uses — so the ``agent_runtime_cockpit.swarmgraph`` MetaPathFinder is never
involved.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from pydantic import BaseModel

from ..protocol.schemas import WorkflowInfo
from .adapters import from_ir_dict, get_importer
from .exporters import to_workflow_info
from .hashing import graph_hash
from .models import (
    IRCapabilityRequirement,
    IRConsensusHint,
    IRGraph,
    IRNode,
    IRRisk,
    IRSideEffect,
    IRValidationReport,
    SideEffectKind,
)
from .validation import validate_graph


class CompileResult(BaseModel):
    ok: bool
    graph: IRGraph
    validation: IRValidationReport
    workflow_info: WorkflowInfo


# ── Inference stages (pure) ──────────────────────────────────────────────────


def _infer_capabilities_and_side_effects(node: IRNode) -> None:
    caps: list[IRCapabilityRequirement] = list(node.capabilities)
    effects: list[IRSideEffect] = list(node.side_effects)

    mcp = node.mcp_tool
    if mcp is not None:
        if mcp.can_write:
            caps.append(IRCapabilityRequirement(capability="fs.write", reason="mcp tool"))
            effects.append(IRSideEffect(kind=SideEffectKind.WRITE, target=mcp.tool_name))
        if mcp.can_network:
            caps.append(IRCapabilityRequirement(capability="net.http", reason="mcp tool"))
            effects.append(IRSideEffect(kind=SideEffectKind.NETWORK, target=mcp.tool_name))
        if mcp.can_read_secrets:
            caps.append(IRCapabilityRequirement(capability="secret.read", reason="mcp tool"))
            effects.append(IRSideEffect(kind=SideEffectKind.SECRET_READ, target=mcp.tool_name))
        if mcp.accesses_outside_workspace:
            caps.append(
                IRCapabilityRequirement(capability="fs.outside_workspace", reason="mcp tool")
            )

    if node.write_path:
        caps.append(IRCapabilityRequirement(capability="fs.write", reason="write_path"))
        effects.append(IRSideEffect(kind=SideEffectKind.WRITE, target=node.write_path))

    if node.budget is not None and node.budget.requires_paid_call:
        caps.append(IRCapabilityRequirement(capability="provider.paid_call"))
        effects.append(
            IRSideEffect(
                kind=SideEffectKind.PAID_CALL,
                paid=True,
                target=node.tool.name if node.tool else None,
            )
        )

    # De-duplicate capabilities by (capability) keeping first.
    seen: set[str] = set()
    deduped: list[IRCapabilityRequirement] = []
    for c in caps:
        if c.capability not in seen:
            seen.add(c.capability)
            deduped.append(c)
    node.capabilities = deduped
    node.side_effects = effects


def _assess_risk(graph: IRGraph, use_sdk_risk: bool) -> None:
    """Populate graph + consensus risk hints using the SDK's pure analysis."""
    description = f"{graph.name} " + " ".join(n.label for n in graph.nodes)

    if not use_sdk_risk:
        return

    try:
        # Top-level distribution import (NOT agent_runtime_cockpit.swarmgraph.*).
        from swarmgraph import assess_prompt_risk, select_consensus_protocol

        assessment = assess_prompt_risk(description)
        level = getattr(assessment, "risk", "low")
        rationale = getattr(assessment, "rationale", None)
        graph.risk = IRRisk(level=level, rationale=rationale, source="sdk")

        suggested: Optional[str] = None
        try:
            selection = select_consensus_protocol(assessment)
            proto = getattr(selection, "protocol", None)
            suggested = getattr(proto, "value", None) if proto is not None else None
        except Exception:
            suggested = None

        graph.consensus = IRConsensusHint(
            protocol=graph.consensus.protocol,
            suggested_protocol=suggested,
            min_workers=graph.consensus.min_workers,
            source="sdk",
        )
    except Exception:
        # SDK unavailable or analysis failed → leave heuristic defaults; fail open
        # for *hints* only (never for safety-relevant validation).
        return


# ── Public compile API ───────────────────────────────────────────────────────


def compile_workflow(
    workflow: WorkflowInfo,
    *,
    workspace: str | None = None,
    adapter_id: str | None = None,
    use_sdk_risk: bool = True,
    enrich_mcp: bool = False,
) -> CompileResult:
    """Compile a WorkflowInfo into an IRGraph + policy-linter input.

    No execution occurs. Returns a CompileResult; ``ok`` is False when validation
    finds a structural error (fail-closed).
    """
    runtime = adapter_id or workflow.runtime or "native"
    importer = get_importer(runtime)
    graph = importer(workflow, workspace=workspace)

    # Optional, local-only MCP enrichment (imported lazily to keep core dep-light).
    if enrich_mcp:
        from .enrich import attach_mcp_risk

        attach_mcp_risk(graph, workspace=workspace)

    for node in graph.nodes:
        _infer_capabilities_and_side_effects(node)

    _assess_risk(graph, use_sdk_risk)

    report = validate_graph(graph)

    # Finalize deterministic hash.
    graph.graph_hash = None
    graph.graph_hash = graph_hash(graph)

    wf = to_workflow_info(graph)

    return CompileResult(
        ok=report.ok,
        graph=graph,
        validation=report,
        workflow_info=wf,
    )


def compile_from_json(
    text: str,
    *,
    runtime: str | None = None,
    workspace: str | None = None,
    use_sdk_risk: bool = True,
    enrich_mcp: bool = False,
) -> CompileResult:
    """Compile from a JSON document that is either an IRGraph or a WorkflowInfo.

    Detection is structural: an IR document has ``ir_version`` + ``provenance``.
    """
    data: dict[str, Any] = json.loads(text)

    if "ir_version" in data and "provenance" in data:
        graph = from_ir_dict(data)
        for node in graph.nodes:
            _infer_capabilities_and_side_effects(node)
        _assess_risk(graph, use_sdk_risk)
        report = validate_graph(graph)
        graph.graph_hash = None
        graph.graph_hash = graph_hash(graph)
        return CompileResult(
            ok=report.ok,
            graph=graph,
            validation=report,
            workflow_info=to_workflow_info(graph),
        )

    workflow = WorkflowInfo.model_validate(data)
    return compile_workflow(
        workflow,
        workspace=workspace,
        adapter_id=runtime,
        use_sdk_risk=use_sdk_risk,
        enrich_mcp=enrich_mcp,
    )
