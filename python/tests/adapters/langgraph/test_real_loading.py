import asyncio
import importlib.machinery
import importlib.util
import json
import pathlib
import textwrap

import pytest

from agent_runtime_cockpit.adapters.langgraph.loader import (
    LangGraphLoadError, load_graph,
)
from agent_runtime_cockpit.adapters.langgraph.runner import LangGraphRunner
from agent_runtime_cockpit.adapters.langgraph import LangGraphAdapter


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


def test_capability_report_runnable_when_langgraph_and_export_available(tmp_path, monkeypatch):
    (tmp_path / "graph_export.py").write_text(textwrap.dedent("""
        class FakeGraph:
            def invoke(self, inputs):
                return inputs

        graph = FakeGraph()
    """))
    monkeypatch.setenv("ARC_LANGGRAPH_EXPORT", "graph_export:graph")
    original_find_spec = importlib.util.find_spec

    def fake_find_spec(name):
        if name == "langgraph":
            return importlib.machinery.ModuleSpec("langgraph", loader=None)
        return original_find_spec(name)

    monkeypatch.setattr(importlib.util, "find_spec", fake_find_spec)

    report = LangGraphAdapter().capability_report(tmp_path)

    assert report.can_run is True
    assert report.availability == "runnable"
