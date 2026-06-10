"""CLI commands for ARC Composer — visual SwarmGraph builder (R98).

Commands:
  arc composer generate   Generate SwarmGraph Python from an IR graph JSON.
  arc composer validate   Validate an IR graph for the composer.

All commands accept --json for machine-readable envelope output.
"""

from __future__ import annotations

import json as json_mod
from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import composer_app


@composer_app.command("generate")
def composer_generate(
    graph_file: str = typer.Argument(..., help="Path to IR graph JSON file"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output Python file path"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Generate SwarmGraph Python code from an IR graph JSON file."""
    from ..composer import generate_swarmgraph_code
    from ..swarmgraph_ir.models import IRGraph

    _workspace(workspace)
    graph_path = Path(graph_file)
    if not graph_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Graph file not found: {graph_file}"), as_json)
        raise typer.Exit(1)

    try:
        with open(graph_path, encoding="utf-8") as f:
            data = json_mod.load(f)
        graph = IRGraph.model_validate(data)
    except Exception as e:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Failed to parse graph: {e}"), as_json)
        raise typer.Exit(1)

    result = generate_swarmgraph_code(graph)

    if not result.ok:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Graph validation failed: {'; '.join(result.errors)}",
                result.to_dict(),
            ),
            as_json,
        )
        raise typer.Exit(1)

    if output:
        output_path = Path(output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(result.code, encoding="utf-8")

    _out(
        ok(
            {
                **result.to_dict(),
                "output_file": output,
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[bold]SwarmGraph Code Generated[/bold]")
        console.print(f"  Graph: {result.graph_id}")
        console.print(f"  Nodes: {result.node_count}")
        console.print(f"  Edges: {result.edge_count}")
        if output:
            console.print(f"  Output: {output}")
        else:
            console.print("\n[dim]--- Generated Code ---[/dim]")
            console.print(result.code)
            console.print("[dim]--- End ---[/dim]")


@composer_app.command("validate")
def composer_validate(
    graph_file: str = typer.Argument(..., help="Path to IR graph JSON file"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Validate an IR graph for the composer (cycle/dead-node detection)."""
    from ..composer import validate_composer_graph
    from ..swarmgraph_ir.models import IRGraph

    _workspace(workspace)
    graph_path = Path(graph_file)
    if not graph_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Graph file not found: {graph_file}"), as_json)
        raise typer.Exit(1)

    try:
        with open(graph_path, encoding="utf-8") as f:
            data = json_mod.load(f)
        graph = IRGraph.model_validate(data)
    except Exception as e:
        _out(err(ArcErrorCode.INVALID_INPUT, f"Failed to parse graph: {e}"), as_json)
        raise typer.Exit(1)

    result = validate_composer_graph(graph)

    if result["ok"]:
        _out(ok(result), as_json)
    else:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Graph validation failed: {'; '.join(result['errors'])}",
                result,
            ),
            as_json,
        )
        raise typer.Exit(1)

    if not as_json:
        from ._app import console

        console.print(f"\n[bold]Composer Validation: {result['graph_id']}[/bold]")
        console.print(f"  Status: {'[green]OK[/green]' if result['ok'] else '[red]FAILED[/red]'}")
        console.print(f"  Nodes: {result['node_count']}")
        console.print(f"  Edges: {result['edge_count']}")
        console.print(f"  Has cycles: {result['has_cycles']}")
        console.print(f"  Has dead nodes: {result['has_dead_nodes']}")
        if result["warnings"]:
            console.print(f"\n  [yellow]Warnings ({len(result['warnings'])})[/yellow]")
            for w in result["warnings"]:
                console.print(f"    - {w}")
        if result["errors"]:
            console.print(f"\n  [red]Errors ({len(result['errors'])})[/red]")
            for e in result["errors"]:
                console.print(f"    - {e}")


__all__ = ["composer_app"]
