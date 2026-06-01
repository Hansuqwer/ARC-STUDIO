"""SwarmGraph CLI commands (Phase 51 / R24 — Adaptive Consensus Protocol)."""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import swarmgraph_app


@swarmgraph_app.command("eval")
def consensus_eval_cmd(
    protocol: Optional[str] = typer.Option(
        None,
        "--protocol",
        "-p",
        help="Protocol to benchmark (default: all). One of: majority, quorum, raft, bft, bft_escrow",
    ),
    workers: int = typer.Option(4, "--workers", "-w", help="Number of synthetic workers", min=1),
    rounds: int = typer.Option(3, "--rounds", "-r", help="Number of consensus rounds", min=1),
    compare: bool = typer.Option(False, "--compare", help="Output comparison table"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Benchmark consensus protocols with synthetic votes.

    Runs each configured protocol on the same set of deterministic synthetic
    votes and reports quality, cost, latency, disagreement, and escalation metrics.
    No LLM, no network — fully deterministic.

    Use --compare to rank protocols by composite score.

    Examples:
        arc swarmgraph eval
        arc swarmgraph eval --protocol raft
        arc swarmgraph eval --protocol majority --workers 6 --rounds 5
        arc swarmgraph eval --compare --json
        arc swarmgraph eval --protocol bft_escrow --json
    """
    _setup_logging(debug)

    from ..evals.consensus import (
        ConsensusEvalConfig,
        compare_protocols,
        run_consensus_eval,
    )

    config = ConsensusEvalConfig(
        protocols=[protocol] if protocol else [],
        num_workers=workers,
        num_rounds=rounds,
    )

    results = run_consensus_eval(config)

    if compare:
        comparison = compare_protocols(results)
        if json_output:
            _out(ok(comparison.model_dump()), json_output)
        else:
            # Print human-readable table
            from rich.console import Console
            from rich.table import Table

            console = Console()
            console.print("\n[bold]Consensus Protocol Comparison[/bold]")
            console.print(f"Workers: {workers} | Rounds: {rounds}\n")

            table = Table()
            table.add_column("Protocol")
            table.add_column("Quality", justify="right")
            table.add_column("Cost", justify="right")
            table.add_column("Latency", justify="right")
            table.add_column("Disagree", justify="right")
            table.add_column("Composite", justify="right")

            scored = [(r, _composite_score_for_display(r, results)) for r in results]
            scored.sort(key=lambda x: x[1], reverse=True)

            for r, s in scored:
                marker = "★" if r.protocol == comparison.best_protocol else " "
                table.add_row(
                    f"{marker} {r.protocol}",
                    f"{r.quality_score:.3f}",
                    f"{r.cost_score:.0f}",
                    f"{r.latency_ms:.0f}ms",
                    f"{r.disagreement_rate:.3f}",
                    f"{s:.4f}",
                )
            console.print(table)
            console.print(f"\n[bold green]Best protocol:[/bold green] {comparison.best_protocol}")
    else:
        if json_output:
            _out(ok([r.model_dump() for r in results]), json_output)
        else:
            from rich.console import Console
            from rich.table import Table

            console = Console()
            console.print("\n[bold]Consensus Protocol Evaluation Results[/bold]")
            console.print(f"Workers: {workers} | Rounds: {rounds}\n")

            table = Table()
            table.add_column("Protocol")
            table.add_column("Reached", justify="center")
            table.add_column("Votes", justify="right")
            table.add_column("Approval", justify="right")
            table.add_column("Quality", justify="right")
            table.add_column("Cost", justify="right")
            table.add_column("Latency", justify="right")
            table.add_column("Disagree", justify="right")
            table.add_column("Escalate", justify="right")

            for r in results:
                reached_str = "[green]YES[/green]" if r.consensus_reached else "[red]NO[/red]"
                table.add_row(
                    r.protocol,
                    reached_str,
                    str(r.total_votes),
                    str(r.approval_count),
                    f"{r.quality_score:.3f}",
                    f"{r.cost_score:.0f}",
                    f"{r.latency_ms:.0f}ms",
                    f"{r.disagreement_rate:.3f}",
                    f"{r.escalation_rate:.3f}",
                )
            console.print(table)


def _composite_score_for_display(result, all_results) -> float:
    """Local composite score helper for display."""
    max_cost = max(r.cost_score for r in all_results) if all_results else 1
    max_latency = max(r.latency_ms for r in all_results) if all_results else 1
    cost_ratio = result.cost_score / max_cost if max_cost > 0 else 0
    latency_ratio = result.latency_ms / max_latency if max_latency > 0 else 0
    score = (
        result.quality_score * 0.4
        + (1.0 - cost_ratio) * 0.3
        + (1.0 - latency_ratio) * 0.2
        + (1.0 - result.disagreement_rate) * 0.1
    )
    return max(0.0, min(1.0, score))


@swarmgraph_app.command("plan")
def plan_cmd(
    task: str = typer.Option(..., "--task", "-t", help="Task text to decompose"),
    strategy: str = typer.Option("dag", "--strategy", help="Planning strategy. Currently: dag"),
    max_nodes: int | None = typer.Option(None, "--max-nodes", help="Maximum plan nodes"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Explain deterministic SwarmGraph decomposition without provider calls."""
    _setup_logging(debug)
    if strategy != "dag":
        _out(
            err(ArcErrorCode.INVALID_INPUT, "Only --strategy dag is supported"),
            json_output,
        )
        raise typer.Exit(1)

    from ..swarmgraph.decomposition import plan_dag

    try:
        plan = plan_dag(task, max_nodes=max_nodes)
    except ValueError as exc:
        _out(err(ArcErrorCode.INVALID_INPUT, str(exc)), json_output)
        raise typer.Exit(1)

    _out(
        ok(
            {
                "strategy": "dag",
                "planner": "deterministic",
                "provider_backed": False,
                "nodes": [node.model_dump(mode="json") for node in plan.nodes],
                "topological_order": plan.topological_order(),
            }
        ),
        json_output,
    )


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
