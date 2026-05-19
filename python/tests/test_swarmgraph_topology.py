"""Tests for standalone SwarmGraph internal topology/consensus capture.

Verifies that the SwarmGraph adapter emits SWARMGRAPH_TOPOLOGY and
SWARMGRAPH_CONSENSUS events when executing workflows, not just the
LangGraph adoption runner.
"""
from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Any

import pytest


def _make_swarmgraph_cli(tmp_path: Path, output: dict[str, Any]) -> Path:
    """Create a fake SwarmGraph CLI script (Python) that returns given JSON."""
    cli = tmp_path / "swarmgraph"
    cli.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        f"print(json.dumps({json.dumps(output)}))\n"
    )
    cli.chmod(cli.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return cli


def test_swarmgraph_adapter_rejects_explicit_invalid_cli(monkeypatch, tmp_path):
    """Explicit ARC_SWARMGRAPH_CLI errors must not fall back to native mode."""
    from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter

    ws = tmp_path / "ws"
    ws.mkdir()
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(tmp_path / "missing-swarmgraph"))

    import asyncio
    adapter = SwarmGraphAdapter()
    with pytest.raises(FileNotFoundError):
        asyncio.run(adapter.run_workflow("wf-test", {"workspace": str(ws), "prompt": "test"}))


def test_swarmgraph_adapter_native_events_not_duplicated(monkeypatch, tmp_path):
    """Native path emits one topology and one consensus event."""
    from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter

    monkeypatch.delenv("ARC_SWARMGRAPH_CLI", raising=False)
    ws = tmp_path / "ws"
    ws.mkdir()

    import asyncio
    adapter = SwarmGraphAdapter()
    result = asyncio.run(adapter.run_workflow("wf-native", {"workspace": str(ws), "prompt": "test"}))

    topology_events = [e for e in result.events if e.type == "SWARMGRAPH_TOPOLOGY"]
    consensus_events = [e for e in result.events if e.type == "SWARMGRAPH_CONSENSUS"]
    assert len(topology_events) == 1
    assert len(consensus_events) == result.metadata["total_tasks"]
    assert result.started_at <= result.ended_at


def test_swarmgraph_adapter_emits_topology_event(monkeypatch, tmp_path):
    """SwarmGraphAdapter.run_workflow emits SWARMGRAPH_TOPOLOGY with nodes/edges."""
    from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "swarmgraph.yaml").write_text("name: test\n")

    cli = _make_swarmgraph_cli(tmp_path, {
        "swarm_id": "sg-test-1",
        "status": "completed",
        "worker_count": 3,
        "final_output": "Topology test complete",
    })
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "stub")

    import asyncio
    adapter = SwarmGraphAdapter()
    result = asyncio.run(adapter.run_workflow("wf-test", {"workspace": str(ws), "prompt": "test"}))

    topology_events = [e for e in result.events if e.type == "SWARMGRAPH_TOPOLOGY"]
    assert len(topology_events) == 1
    topo = topology_events[0]
    assert topo.data["source"] == "swarmgraph_standalone"
    assert len(topo.data["nodes"]) == 4  # queen + 3 workers
    assert len(topo.data["edges"]) == 3  # queen -> worker-1,2,3
    assert topo.data["worker_count"] == 3


def test_swarmgraph_adapter_emits_consensus_event(monkeypatch, tmp_path):
    """SwarmGraphAdapter.run_workflow emits SWARMGRAPH_CONSENSUS with votes."""
    from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "swarmgraph.yaml").write_text("name: test\n")

    cli = _make_swarmgraph_cli(tmp_path, {
        "swarm_id": "sg-consensus-1",
        "status": "completed",
        "worker_count": 2,
        "final_output": "Consensus reached",
    })
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "stub")

    import asyncio
    adapter = SwarmGraphAdapter()
    result = asyncio.run(adapter.run_workflow("wf-consensus", {"workspace": str(ws)}))

    consensus_events = [e for e in result.events if e.type == "SWARMGRAPH_CONSENSUS"]
    assert len(consensus_events) == 1
    cons = consensus_events[0]
    assert cons.data["source"] == "swarmgraph_standalone"
    assert cons.data["consensus_reached"] is True
    assert cons.data["confidence"] == 1.0
    assert cons.data["strategy"] == "standalone_swarmgraph"
    assert len(cons.data["voters"]) == 2


def test_swarmgraph_adapter_topology_with_no_workers(monkeypatch, tmp_path):
    """SwarmGraph topology works with zero workers (at least queen exists)."""
    from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "swarmgraph.yaml").write_text("name: test\n")

    cli = _make_swarmgraph_cli(tmp_path, {
        "swarm_id": "sg-zero",
        "status": "completed",
        "worker_count": 0,
        "final_output": "No workers needed",
    })
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "stub")

    import asyncio
    adapter = SwarmGraphAdapter()
    result = asyncio.run(adapter.run_workflow("wf-zero", {"workspace": str(ws)}))

    topology_events = [e for e in result.events if e.type == "SWARMGRAPH_TOPOLOGY"]
    assert len(topology_events) == 1
    topo = topology_events[0]
    assert len(topo.data["nodes"]) == 1  # just queen
    assert topo.data["worker_count"] == 0


def test_swarmgraph_adapter_failed_run_still_emits_topology(monkeypatch, tmp_path):
    """Even failed runs emit topology/consensus events from available data."""
    from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "swarmgraph.yaml").write_text("name: test\n")

    cli = _make_swarmgraph_cli(tmp_path, {
        "swarm_id": "sg-fail",
        "status": "failed",
        "worker_count": 1,
        "final_output": "",
    })
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "stub")

    import asyncio
    adapter = SwarmGraphAdapter()
    result = asyncio.run(adapter.run_workflow("wf-fail", {"workspace": str(ws)}))

    topology_events = [e for e in result.events if e.type == "SWARMGRAPH_TOPOLOGY"]
    assert len(topology_events) == 1
    consensus_events = [e for e in result.events if e.type == "SWARMGRAPH_CONSENSUS"]
    assert len(consensus_events) == 1
    assert consensus_events[0].data["consensus_reached"] is False
    assert result.status.value == "failed"


def test_swarmgraph_adapter_topology_event_order(monkeypatch, tmp_path):
    """Topology and consensus events appear before RUN_COMPLETED."""
    from agent_runtime_cockpit.adapters.swarmgraph import SwarmGraphAdapter

    ws = tmp_path / "ws"
    ws.mkdir()
    (ws / "swarmgraph.yaml").write_text("name: test\n")

    cli = _make_swarmgraph_cli(tmp_path, {
        "swarm_id": "sg-order",
        "status": "completed",
        "worker_count": 2,
        "final_output": "Order test",
    })
    monkeypatch.setenv("ARC_SWARMGRAPH_CLI", str(cli))
    monkeypatch.setenv("ARC_SWARMGRAPH_RUN_BACKEND", "stub")

    import asyncio
    adapter = SwarmGraphAdapter()
    result = asyncio.run(adapter.run_workflow("wf-order", {"workspace": str(ws)}))

    event_types = [e.type for e in result.events]

    topo_idx = event_types.index("SWARMGRAPH_TOPOLOGY") if "SWARMGRAPH_TOPOLOGY" in event_types else -1
    cons_idx = event_types.index("SWARMGRAPH_CONSENSUS") if "SWARMGRAPH_CONSENSUS" in event_types else -1
    completed_idx = event_types.index("RUN_COMPLETED") if "RUN_COMPLETED" in event_types else -1

    assert topo_idx >= 0, "SWARMGRAPH_TOPOLOGY not found"
    assert cons_idx >= 0, "SWARMGRAPH_CONSENSUS not found"
    assert completed_idx >= 0, "RUN_COMPLETED not found"
    assert topo_idx < completed_idx, "Topology should precede RUN_COMPLETED"
    assert cons_idx < completed_idx, "Consensus should precede RUN_COMPLETED"
