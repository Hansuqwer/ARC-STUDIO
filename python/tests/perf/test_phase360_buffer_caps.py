from __future__ import annotations

from agent_runtime_cockpit.debug import DebugSession, MAX_VARIABLES, Variable
from agent_runtime_cockpit.notebook import MAX_CELLS, Notebook, NotebookCell
from agent_runtime_cockpit.release_intelligence import MAX_COMMITS, parse_git_log
from agent_runtime_cockpit.time_travel import (
    MAX_SNAPSHOTS,
    StateSnapshot,
    StepType,
    TimeTravelSession,
)


def test_time_travel_snapshot_cap():
    session = TimeTravelSession(session_id="s", run_id="r")
    for i in range(MAX_SNAPSHOTS + 1):
        session.add_step(StateSnapshot(step_id=str(i), step_type=StepType.TOOL_CALL))
    assert len(session.steps) == MAX_SNAPSHOTS
    assert "cap_warning" in session.metadata


def test_notebook_cell_cap():
    notebook = Notebook()
    for _ in range(MAX_CELLS + 1):
        notebook.add_cell(NotebookCell())
    assert len(notebook.cells) == MAX_CELLS
    assert "cap_warning" in notebook.metadata.extra


def test_debug_variable_cap():
    session = DebugSession(session_id="s")
    session.variables = [Variable(name=str(i), value="v") for i in range(MAX_VARIABLES + 1)]
    data = session.to_dict()
    assert len(data["variables"]) == MAX_VARIABLES
    assert data["warnings"]


def test_release_intelligence_commit_cap(tmp_path):
    assert parse_git_log(tmp_path, max_count=MAX_COMMITS + 1) == []
