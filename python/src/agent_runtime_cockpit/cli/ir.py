"""SwarmGraph IR CLI commands — compile, inspect, validate, policy.

These commands are read-only analysis: they normalize an exported workflow into the
typed SwarmGraph IR and inspect/validate it. They never execute the workflow, call a
tool/model, open a network connection, or launch an MCP server.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import DEBUG_FLAG, JSON_FLAG, _out, _setup_logging
from ._subapps import ir_app


@ir_app.command("compile")
def ir_compile_cmd(
    source: str = typer.Argument(
        ..., help="Path to a workflow export (WorkflowInfo JSON) or an existing IR JSON file."
    ),
    runtime: Optional[str] = typer.Option(
        None, "--runtime", "-r", help="Source runtime (e.g. langgraph, crewai, native)."
    ),
    out: Optional[str] = typer.Option(
        None, "--out", "-o", help="Write the compiled IR JSON to this path."
    ),
    workspace: Optional[str] = typer.Option(
        None, "--workspace", "-w", help="Workspace root for path/trust normalization."
    ),
    enrich_mcp: bool = typer.Option(
        False,
        "--enrich-mcp",
        help="Enrich MCP tool nodes from local manifest/registry (local reads only).",
    ),
    no_sdk_risk: bool = typer.Option(
        False, "--no-sdk-risk", help="Skip SwarmGraph SDK risk/consensus hinting."
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Compile a workflow export into typed SwarmGraph IR (no execution)."""
    _setup_logging(debug)
    from ..swarmgraph_ir import compile_from_json, to_json

    src_path = Path(source)
    if not src_path.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Source file not found: {source}"), json_output)
        raise typer.Exit(1)

    try:
        text = src_path.read_text(encoding="utf-8")
        result = compile_from_json(
            text,
            runtime=runtime,
            workspace=workspace,
            use_sdk_risk=not no_sdk_risk,
            enrich_mcp=enrich_mcp,
        )
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.WORKFLOW_EXPORT_FAILED, f"Compile failed: {exc}"), json_output)
        raise typer.Exit(1) from exc

    ir_json = to_json(result.graph)

    if out:
        out_path = Path(out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(ir_json, encoding="utf-8")

    payload = {
        "ok": result.ok,
        "graph_id": result.graph.id,
        "runtime": result.graph.runtime,
        "graph_hash": result.graph.graph_hash,
        "node_count": result.validation.node_count,
        "edge_count": result.validation.edge_count,
        "risk_level": result.graph.risk.level,
        "suggested_consensus": result.graph.consensus.suggested_protocol,
        "validation_ok": result.validation.ok,
        "errors": result.validation.errors,
        "warnings": result.validation.warnings,
        "out": out,
    }

    if not result.ok:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                "IR validation failed (fail-closed).",
                details=payload,
            ),
            json_output,
        )
        raise typer.Exit(2)

    _out(ok(payload), json_output)


@ir_app.command("inspect")
def ir_inspect_cmd(
    ir_file: str = typer.Argument(..., help="Path to an IR JSON file."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Inspect a compiled IR graph (nodes, kinds, risk, side effects)."""
    _setup_logging(debug)
    from ..swarmgraph_ir import from_json, validate_graph

    path = Path(ir_file)
    if not path.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"IR file not found: {ir_file}"), json_output)
        raise typer.Exit(1)

    try:
        graph = from_json(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid IR JSON: {exc}"), json_output)
        raise typer.Exit(1) from exc

    report = validate_graph(graph)
    kinds: dict[str, int] = {}
    side_effects: dict[str, int] = {}
    for n in graph.nodes:
        kinds[n.kind.value] = kinds.get(n.kind.value, 0) + 1
        for se in n.side_effects:
            side_effects[se.kind.value] = side_effects.get(se.kind.value, 0) + 1

    payload = {
        "graph_id": graph.id,
        "name": graph.name,
        "runtime": graph.runtime,
        "ir_version": graph.ir_version,
        "graph_hash": graph.graph_hash,
        "provenance": graph.provenance.model_dump(),
        "node_count": len(graph.nodes),
        "edge_count": len(graph.edges),
        "entry_points": graph.entry_points,
        "risk_level": graph.risk.level,
        "suggested_consensus": graph.consensus.suggested_protocol,
        "node_kinds": kinds,
        "side_effects": side_effects,
        "validation_ok": report.ok,
        "errors": report.errors,
        "warnings": report.warnings,
    }
    _out(ok(payload), json_output)


@ir_app.command("validate")
def ir_validate_cmd(
    ir_file: str = typer.Argument(..., help="Path to an IR JSON file."),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Validate an IR graph; exit non-zero on structural errors (fail-closed)."""
    _setup_logging(debug)
    from ..swarmgraph_ir import from_json, validate_graph

    path = Path(ir_file)
    if not path.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"IR file not found: {ir_file}"), json_output)
        raise typer.Exit(1)

    try:
        graph = from_json(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INVALID_INPUT, f"Invalid IR JSON: {exc}"), json_output)
        raise typer.Exit(1) from exc

    report = validate_graph(graph)
    payload = report.model_dump()
    if not report.ok:
        _out(err(ArcErrorCode.INVALID_INPUT, "IR validation failed.", details=payload), json_output)
        raise typer.Exit(2)
    _out(ok(payload), json_output)


@ir_app.command("policy")
def ir_policy_cmd(
    ir_file: str = typer.Argument(..., help="Path to an IR JSON file."),
    workspace: Optional[str] = typer.Option(
        None, "--workspace", "-w", help="Workspace root for write-path checks."
    ),
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    """Run the policy linter against an IR graph (no execution)."""
    _setup_logging(debug)
    from ..security.policy_linter import lint_workflow
    from ..swarmgraph_ir import from_json, to_workflow_info

    path = Path(ir_file)
    if not path.is_file():
        _out(err(ArcErrorCode.INVALID_INPUT, f"IR file not found: {ir_file}"), json_output)
        raise typer.Exit(1)

    try:
        graph = from_json(path.read_text(encoding="utf-8"))
        wf = to_workflow_info(graph)
        report = lint_workflow(
            wf,
            workspace_root=Path(workspace) if workspace else None,
            risk_level=graph.risk.level,
            suggested_consensus=graph.consensus.suggested_protocol,
        )
    except Exception as exc:  # noqa: BLE001
        _out(err(ArcErrorCode.INTERNAL_ERROR, f"Policy lint failed: {exc}"), json_output)
        raise typer.Exit(1) from exc

    payload = report.model_dump()
    _out(ok(payload), json_output)
    if not report.can_run:
        raise typer.Exit(2)
