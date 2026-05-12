import asyncio
import json
import pathlib
import textwrap

import pytest

from agent_runtime_cockpit.adapters.langgraph.loader import (
    LangGraphLoadError, load_graph,
)
from agent_runtime_cockpit.adapters.langgraph.runner import LangGraphRunner


def _make_workspace(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "mygraph.py").write_text(textwrap.dedent("""
        class FakeGraph:
            async def astream_events(self, inputs, version):
                assert version == "v2"
                yield {"event": "on_chain_start", "name": "langgraph", "run_id": "r"}
                yield {"event": "on_chat_model_stream", "run_id": "m",
                       "data": {"chunk": {"content": "hello"}}}
                yield {"event": "on_chain_end", "name": "langgraph", "run_id": "r"}
        graph = FakeGraph()
    """))
    (tmp_path / "langgraph.json").write_text(json.dumps({
        "graphs": {"default": "mygraph:graph"}
    }))
    return tmp_path


def test_load_missing_config(tmp_path):
    with pytest.raises(LangGraphLoadError):
        load_graph(tmp_path)


def test_load_real_graph(tmp_path):
    ws = _make_workspace(tmp_path)
    g = load_graph(ws)
    assert hasattr(g, "astream_events")


def test_real_streaming_no_mock(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_LANGGRAPH_RUN_BACKEND", "local")
    monkeypatch.setenv("ARC_LANGGRAPH_ALLOW_COSTS", "true")
    ws = _make_workspace(tmp_path)
    run_id = asyncio.run(LangGraphRunner(ws).run("default", {"q": 1}))
    text = (ws / ".arc" / "traces" / f"{run_id}.jsonl").read_text()
    assert "_mock" not in text
    assert "RUN_STARTED" in text or "STEP_STARTED" in text
    assert "TEXT_MESSAGE_CHUNK" in text
    assert "STEP_FINISHED" in text
