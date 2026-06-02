"""arc ir simulate — static dry-run simulation of a SwarmGraph IR graph.

No execution, network calls, model calls, tool invocations, or file writes
except the optional --out path.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import ir_app


@ir_app.command("simulate")
def ir_simulate_cmd(
    source: str = typer.Argument(..., help="Path to an IR JSON file (or WorkflowInfo JSON)."),
    out: Optional[str] = typer.Option(
        None, "--out", "-o", help="Write SimulationReport JSON here."
    ),
    workspace: Optional[str] = typer.Option(None, "--workspace", "-w"),
    include_eval_recommendations: bool = typer.Option(False, "--include-eval-recommendations"),
    no_mcp_registry: bool = typer.Option(False, "--no-mcp-registry"),
    fail_on_policy_block: bool = typer.Option(False, "--fail-on-policy-block"),
    no_redact: bool = typer.Option(False, "--no-redact"),
    no_assume_all_branches: bool = typer.Option(False, "--no-assume-all-branches"),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Simulate an IR workflow — predict actions without executing anything."""
    _setup_logging(debug)

    from ..simulation import SimulationConfig, simulate_graph
    from ..swarmgraph_ir import compile_from_json
    from ..swarmgraph_ir.exporters import from_json

    src = Path(source)
    if not src.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"File not found: {source}"), json_output)
        raise typer.Exit(1)

    try:
        text = src.read_text(encoding="utf-8")
        # detect IR vs WorkflowInfo
        import json as _json

        data = _json.loads(text)
        if "ir_version" in data and "provenance" in data:
            graph = from_json(text)
        else:
            result = compile_from_json(text, workspace=workspace)
            graph = result.graph
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Failed to load IR: {exc}"), json_output)
        raise typer.Exit(1) from exc

    cfg = SimulationConfig(
        assume_all_branches=not no_assume_all_branches,
        include_mcp_registry=not no_mcp_registry,
        include_eval_recommendations=include_eval_recommendations,
        redact_secrets=not no_redact,
        workspace=workspace,
    )

    try:
        report = simulate_graph(graph, cfg)
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INTERNAL_ERROR, f"Simulation failed: {exc}"), json_output)
        raise typer.Exit(1) from exc

    report_json = report.model_dump_json(indent=2)

    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report_json, encoding="utf-8")

    payload = {
        "graph_id": report.graph_id,
        "determinism_hash": report.determinism_hash,
        "can_run": report.policy.can_run,
        "risk_level": report.policy.risk_level,
        "reachable_nodes": report.summary.reachable_nodes,
        "side_effect_count": report.summary.side_effect_count,
        "gate_count": report.summary.gate_count,
        "hitl_gate_count": report.summary.hitl_gate_count,
        "paid_call_count": report.summary.paid_call_count,
        "warning_count": report.summary.warning_count,
        "out": out,
        "report": _json.loads(report_json),
    }

    _out(ok(payload), json_output)

    if fail_on_policy_block and not report.policy.can_run:
        raise typer.Exit(2)
