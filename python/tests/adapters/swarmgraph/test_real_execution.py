import asyncio
import pathlib
import textwrap

import pytest

from agent_runtime_cockpit.adapters.swarmgraph.runner import SwarmGraphRunner
from agent_runtime_cockpit.audit.chain import verify
from agent_runtime_cockpit.gating import GatingError


def _ws(tmp_path: pathlib.Path) -> pathlib.Path:
    (tmp_path / "myswarm.py").write_text(textwrap.dedent("""
        import asyncio

        class Graph:
            async def run_with_emit(self, inputs, emit):
                emit("agent.text", agent="queen", text="hi")
                emit("tool.call", tool={"id":"t1","name":"echo","args":inputs,"result":inputs})

        graph = Graph()
    """))
    return tmp_path


def test_stub_runs_without_costs(tmp_path):
    runner = SwarmGraphRunner(_ws(tmp_path))
    run_id = asyncio.run(runner.run("myswarm:graph", {"q": 1}))
    trace = (tmp_path / ".arc" / "traces" / f"{run_id}.jsonl").read_text().splitlines()
    assert any('"RUN_STARTED"' in l for l in trace)
    assert any('"RUN_FINISHED"' in l for l in trace)


def test_local_backend_requires_dual_gate(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "local")
    monkeypatch.delenv("ARC_SWARMGRAPH_ALLOW_COSTS", raising=False)
    runner = SwarmGraphRunner(_ws(tmp_path))
    with pytest.raises(GatingError):
        asyncio.run(runner.run("myswarm:graph", {}))


def test_local_backend_real_execution(tmp_path, monkeypatch):
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "local")
    monkeypatch.setenv("ARC_SWARMGRAPH_ALLOW_COSTS", "true")
    runner = SwarmGraphRunner(_ws(tmp_path))
    run_id = asyncio.run(runner.run("myswarm:graph", {"q": 1}))
    events = (tmp_path / ".arc" / "traces" / f"{run_id}.jsonl").read_text().splitlines()
    assert any('"TOOL_CALL_END"' in l for l in events)
    assert any('"arc.cost_warning"' in l for l in events)


def test_audit_chain_detects_tamper(tmp_path):
    runner = SwarmGraphRunner(_ws(tmp_path))
    run_id = asyncio.run(runner.run("myswarm:graph", {}))
    traces = tmp_path / ".arc" / "traces" / f"{run_id}.jsonl"
    audit = tmp_path / ".arc" / "audit" / f"{run_id}.chain.jsonl"
    ok, _ = verify(audit, traces)
    assert ok
    text = traces.read_text()
    traces.write_text(text.replace("RUN_FINISHED", "RUN_FINISHEX", 1))
    ok, reason = verify(audit, traces)
    assert not ok and "drift" in reason
