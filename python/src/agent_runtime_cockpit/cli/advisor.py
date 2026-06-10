"""CLI commands for ARC Advisor — token cost optimization advisor (R94).

Commands:
  arc advisor analyze     Analyze usage history and generate recommendations.
  arc advisor simulate    Simulate a cost-saving strategy.
  arc advisor pricing     Show known model pricing.

All commands accept --json for machine-readable envelope output.
All analysis is local and deterministic. No provider calls.
"""

from __future__ import annotations

from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import advisor_app


@advisor_app.command("analyze")
def advisor_analyze(
    limit: int = typer.Option(100, "--limit", "-n", help="Max traces to analyze"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Analyze usage history and generate cost-saving recommendations."""
    from ..advisor import CostAdvisor

    ws = _workspace(workspace)
    advisor = CostAdvisor()
    records = advisor.load_usage_from_traces(ws, limit=limit)

    if not records:
        _out(
            ok(
                {
                    "total_runs": 0,
                    "total_cost_usd": 0.0,
                    "recommendations": [],
                    "message": "No usage records found. Run some workflows first.",
                }
            ),
            as_json,
        )
        return

    report = advisor.analyze(records)
    _out(ok(report.to_dict()), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Usage Analysis[/bold]")
        console.print(f"  Total runs: {report.total_runs}")
        console.print(f"  Total cost: ${report.total_cost_usd:.4f}")
        console.print(f"  Total input tokens: {report.total_input_tokens:,}")
        console.print(f"  Total output tokens: {report.total_output_tokens:,}")
        console.print(f"\n[bold]Recommendations ({len(report.recommendations)})[/bold]")
        for i, rec in enumerate(report.recommendations, 1):
            console.print(f"\n  {i}. [cyan]{rec.strategy}[/cyan] ({rec.confidence} confidence)")
            console.print(f"     {rec.description}")
            console.print(
                f"     Estimated savings: ${rec.estimated_savings_usd:.4f} "
                f"({rec.estimated_savings_percent:.1f}%)"
            )


@advisor_app.command("simulate")
def advisor_simulate(
    strategy: str = typer.Argument(
        ..., help="Strategy to simulate: model_switch, context_compression, caching, batching"
    ),
    target_model: Optional[str] = typer.Option(
        None, "--target-model", help="Target model for model_switch strategy"
    ),
    compression_ratio: float = typer.Option(
        0.3, "--compression-ratio", help="Compression ratio for context_compression (0-1)"
    ),
    cache_hit_rate: float = typer.Option(
        0.2, "--cache-hit-rate", help="Cache hit rate for caching strategy (0-1)"
    ),
    batch_efficiency: float = typer.Option(
        0.15, "--batch-efficiency", help="Batch efficiency for batching strategy (0-1)"
    ),
    limit: int = typer.Option(100, "--limit", "-n", help="Max traces to analyze"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Simulate a cost-saving strategy and show projected savings."""
    from ..advisor import CostAdvisor

    ws = _workspace(workspace)
    advisor = CostAdvisor()
    records = advisor.load_usage_from_traces(ws, limit=limit)

    if not records:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                "No usage records found. Run some workflows first.",
            ),
            as_json,
        )
        raise typer.Exit(1)

    params = {}
    if strategy == "model_switch":
        if not target_model:
            _out(
                err(
                    ArcErrorCode.INVALID_INPUT,
                    "model_switch strategy requires --target-model",
                ),
                as_json,
            )
            raise typer.Exit(1)
        params["target_model"] = target_model
    elif strategy == "context_compression":
        params["compression_ratio"] = compression_ratio
    elif strategy == "caching":
        params["cache_hit_rate"] = cache_hit_rate
    elif strategy == "batching":
        params["batch_efficiency"] = batch_efficiency

    result = advisor.simulate(records, strategy, params)

    if "error" in result:
        _out(err(ArcErrorCode.INVALID_INPUT, result["error"]), as_json)
        raise typer.Exit(1)

    _out(ok(result), as_json)

    if not as_json:
        from ._app import console

        console.print(f"\n[bold]Strategy Simulation: {strategy}[/bold]")
        for key, value in result.items():
            if key != "strategy":
                if isinstance(value, float):
                    console.print(f"  {key}: {value:.4f}")
                else:
                    console.print(f"  {key}: {value}")


@advisor_app.command("pricing")
def advisor_pricing(
    as_json: bool = JSON_FLAG,
) -> None:
    """Show known model pricing information."""
    from ..optimizer.local import KNOWN_PRICING

    pricing_list = [
        {
            "model": p.model,
            "input_per_1k": p.input_per_1k,
            "output_per_1k": p.output_per_1k,
        }
        for p in KNOWN_PRICING.values()
    ]

    _out(ok({"count": len(pricing_list), "pricing": pricing_list}), as_json)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Known Model Pricing[/bold]")
        console.print(f"  {'Model':<20} {'Input/1K':<12} {'Output/1K':<12}")
        console.print(f"  {'-' * 20} {'-' * 12} {'-' * 12}")
        for p in pricing_list:
            console.print(
                f"  {p['model']:<20} ${p['input_per_1k']:<11.4f} ${p['output_per_1k']:<11.4f}"
            )


__all__ = ["advisor_app"]
