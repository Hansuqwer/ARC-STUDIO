"""CLI commands for ARC Notebook — agent workbook `.arcnb` format (R100).

Commands:
  arc notebook new        Create a new notebook.
  arc notebook show       Show notebook contents.
  arc notebook export     Export notebook to .ipynb/.md/.py.
  arc notebook add-cell   Add a cell to a notebook.

All commands accept --json for machine-readable envelope output.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ..protocol.errors import ArcErrorCode
from ..protocol.event_envelope import err, ok
from ._helpers import JSON_FLAG, WORKSPACE_FLAG, _out, _workspace
from ._subapps import notebook_app


@notebook_app.command("new")
def notebook_new(
    output: str = typer.Argument(..., help="Output .arcnb file path"),
    title: str = typer.Option("Untitled Notebook", "--title", "-t", help="Notebook title"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Create a new empty notebook."""
    from ..notebook import create_notebook

    _workspace(workspace)
    nb = create_notebook(title=title)
    output_path = Path(output)
    nb.save(output_path)

    _out(
        ok(
            {
                "path": str(output_path),
                "title": title,
                "cells": 0,
                "message": f"Notebook created: {output_path}",
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[bold]Notebook Created[/bold]")
        console.print(f"  Path: {output_path}")
        console.print(f"  Title: {title}")


@notebook_app.command("show")
def notebook_show(
    notebook_file: str = typer.Argument(..., help="Path to .arcnb file"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Show notebook contents."""
    from ..notebook import load_notebook

    _workspace(workspace)
    nb_path = Path(notebook_file)
    if not nb_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Notebook not found: {notebook_file}"), as_json)
        raise typer.Exit(1)

    nb = load_notebook(nb_path)
    _out(ok(nb.to_dict()), as_json)

    if not as_json:
        from ._app import console

        console.print(f"\n[bold]{nb.metadata.title}[/bold]")
        console.print(f"  Cells: {len(nb.cells)}")
        console.print(f"  Created: {nb.metadata.created_at}")
        console.print(f"  Modified: {nb.metadata.modified_at}")
        for i, cell in enumerate(nb.cells):
            console.print(
                f"\n  [cyan]Cell {i + 1}[/cyan] ({cell.cell_type.value}, {cell.status.value})"
            )
            console.print(f"    {cell.source[:100]}...")


@notebook_app.command("export")
def notebook_export(
    notebook_file: str = typer.Argument(..., help="Path to .arcnb file"),
    output: str = typer.Option(..., "--output", "-o", help="Output file path"),
    format: str = typer.Option(
        "arcnb", "--format", "-f", help="Export format: arcnb, ipynb, md, py"
    ),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Export notebook to .ipynb/.md/.py format."""
    from ..notebook import export_notebook, load_notebook

    _workspace(workspace)
    nb_path = Path(notebook_file)
    if not nb_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Notebook not found: {notebook_file}"), as_json)
        raise typer.Exit(1)

    nb = load_notebook(nb_path)
    output_path = Path(output)

    try:
        export_notebook(nb, output_path, format=format)
        _out(
            ok(
                {
                    "source": str(nb_path),
                    "output": str(output_path),
                    "format": format,
                    "cells": len(nb.cells),
                    "message": f"Exported to {output_path} ({format})",
                }
            ),
            as_json,
        )
    except ValueError as e:
        _out(err(ArcErrorCode.INVALID_INPUT, str(e)), as_json)
        raise typer.Exit(1)

    if not as_json:
        from ._app import console

        console.print("\n[bold]Notebook Exported[/bold]")
        console.print(f"  Source: {nb_path}")
        console.print(f"  Output: {output_path}")
        console.print(f"  Format: {format}")


@notebook_app.command("add-cell")
def notebook_add_cell(
    notebook_file: str = typer.Argument(..., help="Path to .arcnb file"),
    cell_type: str = typer.Option(
        "prompt", "--type", "-t", help="Cell type: prompt, tool_call, code, markdown"
    ),
    source: str = typer.Option(..., "--source", "-s", help="Cell source content"),
    as_json: bool = JSON_FLAG,
    workspace: Optional[str] = WORKSPACE_FLAG,
) -> None:
    """Add a cell to a notebook."""
    from ..notebook import CellType, NotebookCell, load_notebook, save_notebook

    _workspace(workspace)
    nb_path = Path(notebook_file)
    if not nb_path.exists():
        _out(err(ArcErrorCode.INVALID_INPUT, f"Notebook not found: {notebook_file}"), as_json)
        raise typer.Exit(1)

    try:
        ct = CellType(cell_type)
    except ValueError:
        _out(
            err(
                ArcErrorCode.INVALID_INPUT,
                f"Invalid cell type: {cell_type}. Use: prompt, tool_call, code, markdown",
            ),
            as_json,
        )
        raise typer.Exit(1)

    nb = load_notebook(nb_path)
    cell = NotebookCell(cell_type=ct, source=source)
    cell_id = nb.add_cell(cell)
    save_notebook(nb, nb_path)

    _out(
        ok(
            {
                "notebook": str(nb_path),
                "cell_id": cell_id,
                "cell_type": cell_type,
                "total_cells": len(nb.cells),
                "message": f"Cell added: {cell_id}",
            }
        ),
        as_json,
    )

    if not as_json:
        from ._app import console

        console.print("\n[bold]Cell Added[/bold]")
        console.print(f"  ID: {cell_id}")
        console.print(f"  Type: {cell_type}")
        console.print(f"  Total cells: {len(nb.cells)}")


__all__ = ["notebook_app"]
