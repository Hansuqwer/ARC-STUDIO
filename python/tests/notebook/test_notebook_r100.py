"""Tests for ARC Notebook — agent workbook `.arcnb` format (R100, Phase 325)."""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime_cockpit.notebook import (
    ARCNB_SCHEMA_VERSION,
    CellOutput,
    CellStatus,
    CellType,
    Notebook,
    NotebookCell,
    NotebookMetadata,
    create_notebook,
    export_notebook,
    load_notebook,
    save_notebook,
)


class TestNotebookCell:
    def test_create_cell(self) -> None:
        cell = NotebookCell(cell_type=CellType.PROMPT, source="Hello world")
        assert cell.cell_type == CellType.PROMPT
        assert cell.source == "Hello world"
        assert cell.status == CellStatus.IDLE
        assert cell.outputs == []

    def test_cell_to_dict(self) -> None:
        cell = NotebookCell(
            cell_type=CellType.CODE,
            source="print('hello')",
            outputs=[CellOutput(output_type="text", data="hello")],
        )
        d = cell.to_dict()
        assert d["cell_type"] == "code"
        assert d["source"] == "print('hello')"
        assert len(d["outputs"]) == 1
        assert d["outputs"][0]["data"] == "hello"

    def test_cell_from_dict(self) -> None:
        data = {
            "id": "test-id",
            "cell_type": "markdown",
            "source": "# Title",
            "outputs": [],
            "status": "completed",
            "metadata": {},
        }
        cell = NotebookCell.from_dict(data)
        assert cell.id == "test-id"
        assert cell.cell_type == CellType.MARKDOWN
        assert cell.status == CellStatus.COMPLETED


class TestNotebook:
    def test_create_notebook(self) -> None:
        nb = Notebook()
        assert nb.schema_version == ARCNB_SCHEMA_VERSION
        assert nb.cells == []
        assert nb.metadata.title == "Untitled Notebook"

    def test_add_cell(self) -> None:
        nb = Notebook()
        cell = NotebookCell(cell_type=CellType.PROMPT, source="test")
        cell_id = nb.add_cell(cell)
        assert len(nb.cells) == 1
        assert nb.cells[0].id == cell_id

    def test_remove_cell(self) -> None:
        nb = Notebook()
        cell = NotebookCell(cell_type=CellType.PROMPT, source="test")
        cell_id = nb.add_cell(cell)
        assert nb.remove_cell(cell_id) is True
        assert len(nb.cells) == 0
        assert nb.remove_cell("nonexistent") is False

    def test_get_cell(self) -> None:
        nb = Notebook()
        cell = NotebookCell(cell_type=CellType.PROMPT, source="test")
        cell_id = nb.add_cell(cell)
        found = nb.get_cell(cell_id)
        assert found is not None
        assert found.source == "test"
        assert nb.get_cell("nonexistent") is None

    def test_to_dict(self) -> None:
        nb = Notebook(metadata=NotebookMetadata(title="Test"))
        nb.add_cell(NotebookCell(cell_type=CellType.CODE, source="x = 1"))
        d = nb.to_dict()
        assert d["schema_version"] == ARCNB_SCHEMA_VERSION
        assert d["metadata"]["title"] == "Test"
        assert len(d["cells"]) == 1

    def test_from_dict(self) -> None:
        data = {
            "schema_version": 1,
            "metadata": {"title": "Test", "description": "", "author": "", "tags": []},
            "cells": [
                {
                    "id": "c1",
                    "cell_type": "prompt",
                    "source": "hello",
                    "outputs": [],
                    "status": "idle",
                }
            ],
        }
        nb = Notebook.from_dict(data)
        assert nb.metadata.title == "Test"
        assert len(nb.cells) == 1
        assert nb.cells[0].source == "hello"

    def test_save_and_load(self, tmp_path: Path) -> None:
        nb = create_notebook("Test Notebook")
        nb.add_cell(NotebookCell(cell_type=CellType.CODE, source="print('test')"))
        path = tmp_path / "test.arcnb"
        save_notebook(nb, path)
        assert path.exists()

        loaded = load_notebook(path)
        assert loaded.metadata.title == "Test Notebook"
        assert len(loaded.cells) == 1
        assert loaded.cells[0].source == "print('test')"

    def test_export_ipynb(self) -> None:
        nb = create_notebook("Test")
        nb.add_cell(NotebookCell(cell_type=CellType.CODE, source="x = 1"))
        nb.add_cell(NotebookCell(cell_type=CellType.MARKDOWN, source="# Title"))
        ipynb = nb.export_ipynb()
        assert ipynb["nbformat"] == 4
        assert len(ipynb["cells"]) == 2
        assert ipynb["cells"][0]["cell_type"] == "code"
        assert ipynb["cells"][1]["cell_type"] == "markdown"

    def test_export_markdown(self) -> None:
        nb = create_notebook("Test")
        nb.add_cell(NotebookCell(cell_type=CellType.MARKDOWN, source="# Hello"))
        nb.add_cell(NotebookCell(cell_type=CellType.CODE, source="print('hi')"))
        md = nb.export_markdown()
        assert "# Test" in md
        assert "# Hello" in md
        assert "```python" in md
        assert "print('hi')" in md

    def test_export_python(self) -> None:
        nb = create_notebook("Test")
        nb.add_cell(NotebookCell(cell_type=CellType.CODE, source="x = 42"))
        py = nb.export_python()
        assert '"""Test' in py
        assert "x = 42" in py


class TestExportNotebook:
    def test_export_arcnb(self, tmp_path: Path) -> None:
        nb = create_notebook("Test")
        path = tmp_path / "test.arcnb"
        export_notebook(nb, path, format="arcnb")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["metadata"]["title"] == "Test"

    def test_export_ipynb(self, tmp_path: Path) -> None:
        nb = create_notebook("Test")
        path = tmp_path / "test.ipynb"
        export_notebook(nb, path, format="ipynb")
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["nbformat"] == 4

    def test_export_markdown(self, tmp_path: Path) -> None:
        nb = create_notebook("Test")
        path = tmp_path / "test.md"
        export_notebook(nb, path, format="md")
        assert path.exists()
        assert "# Test" in path.read_text()

    def test_export_python(self, tmp_path: Path) -> None:
        nb = create_notebook("Test")
        path = tmp_path / "test.py"
        export_notebook(nb, path, format="py")
        assert path.exists()
        assert '"""Test' in path.read_text()

    def test_export_unknown_format(self, tmp_path: Path) -> None:
        nb = create_notebook("Test")
        path = tmp_path / "test.xyz"
        try:
            export_notebook(nb, path, format="xyz")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown export format" in str(e)


class TestNotebookCLI:
    def test_notebook_help(self) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        result = runner.invoke(app, ["notebook", "--help"])
        assert result.exit_code == 0
        assert "notebook" in result.output.lower()

    def test_notebook_new(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        runner = CliRunner()
        output = tmp_path / "test.arcnb"
        result = runner.invoke(
            app,
            ["notebook", "new", str(output), "--title", "CLI Test", "--json", "-w", str(tmp_path)],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert output.exists()

    def test_notebook_show(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        nb = create_notebook("Show Test")
        nb.add_cell(NotebookCell(cell_type=CellType.CODE, source="x = 1"))
        path = tmp_path / "show.arcnb"
        save_notebook(nb, path)

        runner = CliRunner()
        result = runner.invoke(app, ["notebook", "show", str(path), "--json", "-w", str(tmp_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["metadata"]["title"] == "Show Test"

    def test_notebook_add_cell(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        nb = create_notebook("Add Cell Test")
        path = tmp_path / "add.arcnb"
        save_notebook(nb, path)

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "notebook",
                "add-cell",
                str(path),
                "--type",
                "code",
                "--source",
                "print('hello')",
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert data["data"]["total_cells"] == 1

    def test_notebook_export(self, tmp_path: Path) -> None:
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        nb = create_notebook("Export Test")
        nb.add_cell(NotebookCell(cell_type=CellType.CODE, source="x = 1"))
        src_path = tmp_path / "export.arcnb"
        save_notebook(nb, src_path)

        runner = CliRunner()
        out_path = tmp_path / "export.md"
        result = runner.invoke(
            app,
            [
                "notebook",
                "export",
                str(src_path),
                "--output",
                str(out_path),
                "--format",
                "md",
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["ok"] is True
        assert out_path.exists()


class TestNotebookError:
    """Phase 342 DoD elevation: structured error class + overwrite gate."""

    def test_notebook_error_is_exception(self) -> None:
        from agent_runtime_cockpit.notebook import NotebookError

        assert issubclass(NotebookError, Exception)
        err = NotebookError("test message")
        assert str(err) == "test message"

    def test_notebook_error_in_all(self) -> None:
        import agent_runtime_cockpit.notebook as nb_mod

        assert "NotebookError" in nb_mod.__all__

    def test_cell_type_has_4_values(self) -> None:
        from agent_runtime_cockpit.notebook import CellType

        values = [v.value for v in CellType]
        assert "prompt" in values
        assert "tool_call" in values
        assert "code" in values
        assert "markdown" in values
        assert len(values) == 4

    def test_notebook_export_overwrite_requires_yes(self, tmp_path: Path) -> None:
        """export --output to existing file must require --yes in JSON mode."""
        from typer.testing import CliRunner
        from agent_runtime_cockpit.cli._app import app

        # Create source notebook
        src = tmp_path / "src.arcnb"
        src.write_text(
            '{"schema_version": 1, "metadata": {"title": "t", "created_at": "", "modified_at": ""}, "cells": []}'
        )

        # Create existing output
        out = tmp_path / "out.md"
        out.write_text("# existing\n")

        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "notebook",
                "export",
                str(src),
                "--output",
                str(out),
                "--format",
                "md",
                "--json",
                "-w",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 1
        data = json.loads(result.output)
        assert data["ok"] is False
        assert data["error"]["code"] == "PERMISSION_DENIED"
