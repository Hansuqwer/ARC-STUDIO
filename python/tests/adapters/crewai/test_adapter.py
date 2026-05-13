import pathlib

from agent_runtime_cockpit.adapters.crewai.detect import is_crewai_workspace
from agent_runtime_cockpit.adapters.crewai.mapping import _map
from agent_runtime_cockpit.ag_ui import MappingContext


def test_detect_workspace(tmp_path: pathlib.Path):
    (tmp_path / "crew.py").write_text("from crewai import Crew\n")
    assert is_crewai_workspace(tmp_path)


def test_detect_negative(tmp_path: pathlib.Path):
    (tmp_path / "main.py").write_text("print('hi')\n")
    assert not is_crewai_workspace(tmp_path)


def test_mapping_crew_lifecycle():
    ctx = MappingContext(thread_id="th", run_id="r1", runtime="crewai")
    assert _map({"kind": "crew.start"}, ctx)[0]["type"] == "RUN_STARTED"
    assert _map({"kind": "crew.finish"}, ctx)[0]["type"] == "RUN_FINISHED"
    res = _map({"kind": "tool.call",
                "tool": {"id": "t1", "name": "search", "args": {"q": "x"}}}, ctx)
    assert [e["type"] for e in res] == ["TOOL_CALL_START", "TOOL_CALL_ARGS", "TOOL_CALL_END"]
    chunk = _map({"kind": "llm.chunk", "delta": "Hi"}, ctx)[0]
    assert chunk["type"] == "TEXT_MESSAGE_CHUNK" and chunk["delta"] == "Hi"
