"""IR adapter importers.

Each importer maps a runtime's already-exported ``WorkflowInfo`` into an IRGraph.
We re-use ARC's existing adapters' ``export_workflow()`` output rather than
re-parsing frameworks.

The framework-specific importers (langgraph/crewai/...) are thin wrappers around
the native importer for the MVP; they exist so per-runtime quirks can be added
later without changing the public surface.
"""

from __future__ import annotations

from typing import Callable

from ...protocol.schemas import WorkflowInfo
from ..models import IRGraph
from .native import from_ir_dict, from_workflow_info


def _make_importer(adapter_id: str) -> Callable[..., IRGraph]:
    def _importer(workflow: WorkflowInfo, *, workspace: str | None = None) -> IRGraph:
        return from_workflow_info(workflow, adapter_id=adapter_id, workspace=workspace)

    _importer.__name__ = f"import_{adapter_id}"
    return _importer


# Registry: runtime name -> importer callable.
ADAPTER_IMPORTERS: dict[str, Callable[..., IRGraph]] = {
    "native": _make_importer("native"),
    "swarmgraph": _make_importer("swarmgraph"),
    "langgraph": _make_importer("langgraph"),
    "crewai": _make_importer("crewai"),
    "openai_agents": _make_importer("openai_agents"),
    "ag2": _make_importer("ag2"),
    "autogen": _make_importer("ag2"),
    "llamaindex": _make_importer("llamaindex"),
}


def get_importer(runtime: str) -> Callable[..., IRGraph]:
    """Return the importer for ``runtime`` (falls back to native)."""
    return ADAPTER_IMPORTERS.get(runtime, ADAPTER_IMPORTERS["native"])


__all__ = ["ADAPTER_IMPORTERS", "get_importer", "from_workflow_info", "from_ir_dict"]
