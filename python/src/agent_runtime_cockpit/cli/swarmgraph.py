"""SwarmGraph CLI commands (Phase 51 / R24 — Adaptive Consensus Protocol)."""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import swarmgraph_app


@swarmgraph_app.command("assess-risk")
def assess_risk_cmd(
    task: str = typer.Option(..., "--task", "-t", help="Task text to assess for risk"),
    runtime: Optional[str] = typer.Option(
        None, "--runtime", help="Target runtime hint (e.g. production, staging)"
    ),
    override_protocol: Optional[str] = typer.Option(
        None,
        "--override-protocol",
        help="Override the recommended protocol (e.g. raft, bft, majority). "
        "Emits an AuditOverrideEvent.",
    ),
    workspace_trusted: bool = typer.Option(
        True,
        "--workspace-trusted/--no-workspace-trusted",
        help="Whether the workspace is trusted (default: true)",
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Assess risk level for a task and recommend a consensus protocol.

    Uses deterministic heuristics only — no LLM dependency. Fail-closed:
    any assessment error maps to critical/bft_escrow.

    Examples:
        arc swarmgraph assess-risk --task "list API endpoints"
        arc swarmgraph assess-risk --task "delete production database" --json
        arc swarmgraph assess-risk --task "deploy" --override-protocol raft
    """
    _setup_logging(debug)

    from ..swarmgraph.adaptive_consensus import assess_risk

    assessment = assess_risk(
        task_text=task,
        workspace_trusted=workspace_trusted,
        target_runtime=runtime,
    )

    result = {
        "risk_level": assessment.risk_level,
        "recommended_protocol": assessment.recommended_protocol.value,
        "worker_count": assessment.worker_count,
        "hitl_required": assessment.hitl_required,
        "anti_drift": assessment.anti_drift,
        "cost_estimate_tokens": assessment.cost_estimate_tokens,
        "rationale": assessment.rationale,
    }

    # Handle override
    if override_protocol is not None:
        valid_protocols = {"majority", "raft", "bft", "bft_escrow", "quorum", "gossip"}
        if override_protocol not in valid_protocols:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    f"Invalid protocol: {override_protocol!r}. Valid: {sorted(valid_protocols)}",
                ),
                json_output,
            )
            raise typer.Exit(1)

        original = assessment.recommended_protocol.value

        # Emit AuditOverrideEvent
        from ..events.bus import get_bus
        from ..events.types import AuditOverrideEvent

        event = AuditOverrideEvent(
            override_type="protocol_override",
            original_value=original,
            override_value=override_protocol,
            operator_id="cli",
            reason=f"User override via --override-protocol on task: {task[:200]}",
            context={
                "task_text": task[:200],
                "risk_level": assessment.risk_level,
                "target_runtime": runtime,
            },
        )
        get_bus().publish(event)

        result["recommended_protocol"] = override_protocol
        result["override_applied"] = True
        result["original_protocol"] = original
        result["override_event_id"] = event.event_id

    _out(ok(result), json_output)
