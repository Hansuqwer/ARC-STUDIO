"""ARC Notebook — agent workbook `.arcnb` format (R100).

A notebook surface where cells are agent prompts, tool calls, or code.
Output cells show results/logs. Saved as `.arcnb` JSON with export to
`.ipynb`/`.md`/`.py`.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional

log = logging.getLogger(__name__)


class NotebookError(Exception):
    """Raised when notebook operations fail (IO, schema mismatch, export error)."""


ARCNB_SCHEMA_VERSION = 1
MAX_CELLS = 500


class CellType(str, Enum):
    PROMPT = "prompt"
    TOOL_CALL = "tool_call"
    CODE = "code"
    MARKDOWN = "markdown"


class CellStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class CellOutput:
    output_type: str  # "text", "error", "result"
    data: str
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class NotebookCell:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    cell_type: CellType = CellType.PROMPT
    source: str = ""
    outputs: list[CellOutput] = field(default_factory=list)
    status: CellStatus = CellStatus.IDLE
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "cell_type": self.cell_type.value,
            "source": self.source,
            "outputs": [
                {
                    "output_type": o.output_type,
                    "data": o.data,
                    "metadata": o.metadata,
                    "timestamp": o.timestamp,
                }
                for o in self.outputs
            ],
            "status": self.status.value,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotebookCell:
        outputs = [
            CellOutput(
                output_type=o.get("output_type", "text"),
                data=o.get("data", ""),
                metadata=o.get("metadata", {}),
                timestamp=o.get("timestamp", ""),
            )
            for o in data.get("outputs", [])
        ]
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            cell_type=CellType(data.get("cell_type", "prompt")),
            source=data.get("source", ""),
            outputs=outputs,
            status=CellStatus(data.get("status", "idle")),
            metadata=data.get("metadata", {}),
        )


@dataclass
class NotebookMetadata:
    title: str = "Untitled Notebook"
    description: str = ""
    author: str = ""
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    modified_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    tags: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class Notebook:
    schema_version: int = ARCNB_SCHEMA_VERSION
    metadata: NotebookMetadata = field(default_factory=NotebookMetadata)
    cells: list[NotebookCell] = field(default_factory=list)

    def add_cell(self, cell: NotebookCell) -> str:
        self.cells.append(cell)
        if len(self.cells) > MAX_CELLS:
            dropped = len(self.cells) - MAX_CELLS
            self.cells = self.cells[-MAX_CELLS:]
            self.metadata.extra["cap_warning"] = (
                f"cells capped at {MAX_CELLS}; dropped {dropped} oldest"
            )
        self.metadata.modified_at = datetime.now(timezone.utc).isoformat()
        return cell.id

    def remove_cell(self, cell_id: str) -> bool:
        for i, cell in enumerate(self.cells):
            if cell.id == cell_id:
                self.cells.pop(i)
                self.metadata.modified_at = datetime.now(timezone.utc).isoformat()
                return True
        return False

    def get_cell(self, cell_id: str) -> Optional[NotebookCell]:
        for cell in self.cells:
            if cell.id == cell_id:
                return cell
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "metadata": {
                "title": self.metadata.title,
                "description": self.metadata.description,
                "author": self.metadata.author,
                "created_at": self.metadata.created_at,
                "modified_at": self.metadata.modified_at,
                "tags": self.metadata.tags,
                "extra": self.metadata.extra,
            },
            "cells": [c.to_dict() for c in self.cells],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Notebook:
        meta_data = data.get("metadata", {})
        metadata = NotebookMetadata(
            title=meta_data.get("title", "Untitled Notebook"),
            description=meta_data.get("description", ""),
            author=meta_data.get("author", ""),
            created_at=meta_data.get("created_at", ""),
            modified_at=meta_data.get("modified_at", ""),
            tags=meta_data.get("tags", []),
            extra=meta_data.get("extra", {}),
        )
        cells = [NotebookCell.from_dict(c) for c in data.get("cells", [])]
        return cls(
            schema_version=data.get("schema_version", ARCNB_SCHEMA_VERSION),
            metadata=metadata,
            cells=cells,
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
            f.write("\n")

    @classmethod
    def load(cls, path: Path) -> Notebook:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def export_ipynb(self) -> dict[str, Any]:
        """Export to Jupyter notebook format (.ipynb v4)."""
        cells = []
        for cell in self.cells:
            if cell.cell_type == CellType.MARKDOWN:
                cells.append(
                    {
                        "cell_type": "markdown",
                        "metadata": {},
                        "source": cell.source.split("\n"),
                    }
                )
            elif cell.cell_type == CellType.CODE:
                outputs = []
                for o in cell.outputs:
                    if o.output_type == "error":
                        outputs.append(
                            {
                                "output_type": "error",
                                "ename": "Error",
                                "evalue": o.data,
                                "traceback": [],
                            }
                        )
                    else:
                        outputs.append(
                            {
                                "output_type": "stream",
                                "name": "stdout",
                                "text": o.data.split("\n"),
                            }
                        )
                cells.append(
                    {
                        "cell_type": "code",
                        "execution_count": None,
                        "metadata": {},
                        "source": cell.source.split("\n"),
                        "outputs": outputs,
                    }
                )
            else:
                cells.append(
                    {
                        "cell_type": "markdown",
                        "metadata": {"arc_cell_type": cell.cell_type.value},
                        "source": [f"**{cell.cell_type.value}:** {cell.source}"],
                    }
                )

        return {
            "nbformat": 4,
            "nbformat_minor": 5,
            "metadata": {
                "kernelspec": {
                    "display_name": "ARC",
                    "language": "python",
                    "name": "arc",
                },
                "language_info": {"name": "python", "version": "3.11"},
                "arc_notebook": self.to_dict()["metadata"],
            },
            "cells": cells,
        }

    def export_markdown(self) -> str:
        """Export to Markdown format."""
        lines = [
            f"# {self.metadata.title}",
            "",
            f"*{self.metadata.description}*" if self.metadata.description else "",
            f"*Author: {self.metadata.author}*" if self.metadata.author else "",
            f"*Created: {self.metadata.created_at}*",
            "",
            "---",
            "",
        ]

        for cell in self.cells:
            if cell.cell_type == CellType.MARKDOWN:
                lines.append(cell.source)
                lines.append("")
            elif cell.cell_type == CellType.CODE:
                lines.append("```python")
                lines.append(cell.source)
                lines.append("```")
                for o in cell.outputs:
                    if o.output_type == "error":
                        lines.append(f"**Error:** {o.data}")
                    else:
                        lines.append("```")
                        lines.append(o.data)
                        lines.append("```")
                lines.append("")
            elif cell.cell_type == CellType.PROMPT:
                lines.append(f"**Prompt:** {cell.source}")
                for o in cell.outputs:
                    lines.append(f"> {o.data}")
                lines.append("")
            elif cell.cell_type == CellType.TOOL_CALL:
                lines.append(f"**Tool Call:** `{cell.source}`")
                for o in cell.outputs:
                    lines.append(f"> {o.data}")
                lines.append("")

        return "\n".join(lines)

    def export_python(self) -> str:
        """Export to Python script format."""
        lines = [
            f'"""{self.metadata.title}',
            "",
            f"{self.metadata.description}" if self.metadata.description else "",
            f"Author: {self.metadata.author}" if self.metadata.author else "",
            f"Created: {self.metadata.created_at}",
            '"""',
            "",
        ]

        for cell in self.cells:
            if cell.cell_type == CellType.CODE:
                lines.append(f"# Cell: {cell.id}")
                lines.append(cell.source)
                lines.append("")
            elif cell.cell_type == CellType.MARKDOWN:
                lines.append(f"# {cell.source}")
                lines.append("")
            elif cell.cell_type == CellType.PROMPT:
                lines.append(f"# Prompt: {cell.source}")
                lines.append("")
            elif cell.cell_type == CellType.TOOL_CALL:
                lines.append(f"# Tool call: {cell.source}")
                lines.append("")

        return "\n".join(lines)


def create_notebook(title: str = "Untitled Notebook") -> Notebook:
    """Create a new empty notebook."""
    return Notebook(metadata=NotebookMetadata(title=title))


def load_notebook(path: Path) -> Notebook:
    """Load a notebook from a .arcnb file."""
    return Notebook.load(path)


def save_notebook(notebook: Notebook, path: Path) -> None:
    """Save a notebook to a .arcnb file."""
    notebook.save(path)


def export_notebook(notebook: Notebook, path: Path, format: str = "arcnb") -> None:
    """Export a notebook to the specified format."""
    if format == "arcnb":
        notebook.save(path)
    elif format == "ipynb":
        with open(path, "w", encoding="utf-8") as f:
            json.dump(notebook.export_ipynb(), f, indent=2)
    elif format == "md":
        path.write_text(notebook.export_markdown(), encoding="utf-8")
    elif format == "py":
        path.write_text(notebook.export_python(), encoding="utf-8")
    else:
        raise ValueError(f"Unknown export format: {format}")


__all__ = [
    "NotebookError",
    "ARCNB_SCHEMA_VERSION",
    "MAX_CELLS",
    "CellType",
    "CellStatus",
    "CellOutput",
    "NotebookCell",
    "NotebookMetadata",
    "Notebook",
    "create_notebook",
    "load_notebook",
    "save_notebook",
    "export_notebook",
]
