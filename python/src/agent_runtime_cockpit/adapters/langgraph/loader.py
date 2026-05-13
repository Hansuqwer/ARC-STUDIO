"""Load a real LangGraph from a workspace via langgraph.json."""
from __future__ import annotations

import json
import pathlib
from typing import Any

from agent_runtime_cockpit.workspace.entrypoint import resolve_python_entrypoint


class LangGraphLoadError(RuntimeError):
    pass


def load_graph(workspace: pathlib.Path, graph_id: str | None = None) -> Any:
    cfg_path = workspace / "langgraph.json"
    if not cfg_path.exists():
        raise LangGraphLoadError("langgraph.json not found in workspace")
    cfg = json.loads(cfg_path.read_text())
    graphs = cfg.get("graphs") or {}
    if not graphs:
        raise LangGraphLoadError("langgraph.json has no `graphs` map")
    if graph_id is None:
        graph_id = next(iter(graphs))
    if graph_id not in graphs:
        raise LangGraphLoadError(f"graph id {graph_id!r} not in langgraph.json")
    return resolve_python_entrypoint(workspace, graphs[graph_id])
