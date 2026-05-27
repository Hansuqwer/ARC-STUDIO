"""Phase 59 Swarm Memory Graph research prototype tests."""

from __future__ import annotations

import json
import os
from pathlib import Path

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._app import app
from agent_runtime_cockpit.memory_graph.models import MemoryGraphSnapshot, MemoryNode
from agent_runtime_cockpit.memory_graph.store import MemoryGraphStore, extract_memories_from_runs
from agent_runtime_cockpit.memory_graph.store import evaluate_memory_graph


def test_memory_models_serialize() -> None:
    snapshot = MemoryGraphSnapshot(
        nodes=[MemoryNode(id="mem-1", type="concept", text="sandbox", confidence=0.5)]
    )
    restored = MemoryGraphSnapshot.model_validate_json(snapshot.model_dump_json())
    assert restored.privacy_mode == "local_workspace_only"
    assert restored.tenant_isolation == "not_claimed"
    assert restored.nodes[0].text == "sandbox"


def test_extract_memories_from_traces(tmp_path: Path) -> None:
    traces = tmp_path / ".arc" / "traces"
    traces.mkdir(parents=True)
    (traces / "r1.jsonl").write_text(
        json.dumps(
            {
                "event_type": "run_completed",
                "message": "Decision chosen: sandbox policy baseline complete",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    snapshot = extract_memories_from_runs(traces)
    assert any(node.type == "decision" for node in snapshot.nodes)
    assert any(node.text == "sandbox" for node in snapshot.nodes)


def test_store_merge_increments_frequency(tmp_path: Path) -> None:
    store = MemoryGraphStore(tmp_path / "graph.json")
    snapshot = MemoryGraphSnapshot(
        nodes=[MemoryNode(id="mem-sandbox", type="concept", text="sandbox", confidence=0.5)]
    )
    store.merge(snapshot)
    merged = store.merge(snapshot)
    node = next(node for node in merged.nodes if node.id == "mem-sandbox")
    assert node.frequency == 2


def test_store_query_filters_and_sorts(tmp_path: Path) -> None:
    store = MemoryGraphStore(tmp_path / "graph.json")
    store.save(
        MemoryGraphSnapshot(
            nodes=[
                MemoryNode(id="a", type="concept", text="sandbox", confidence=0.4, frequency=1),
                MemoryNode(
                    id="b", type="concept", text="sandbox policy", confidence=0.8, frequency=3
                ),
            ]
        )
    )
    nodes = store.query("sandbox")
    assert [node.id for node in nodes] == ["b", "a"]


def test_cli_memory_extract_and_query_json(tmp_path: Path) -> None:
    old = Path.cwd()
    os.chdir(tmp_path)
    try:
        traces = tmp_path / ".arc" / "traces"
        traces.mkdir(parents=True)
        (traces / "r1.jsonl").write_text(
            json.dumps({"message": "Risk blocked destructive command in sandbox"}) + "\n",
            encoding="utf-8",
        )
        runner = CliRunner()
        extract = runner.invoke(app, ["memory", "extract", "--json"])
        assert extract.exit_code == 0, extract.stderr
        data = json.loads(extract.stdout)
        assert data["ok"] is True
        assert data["data"]["privacy_mode"] == "local_workspace_only"

        query = runner.invoke(app, ["memory", "query", "sandbox", "--json"])
        assert query.exit_code == 0, query.stderr
        payload = json.loads(query.stdout)["data"]
        assert payload["count"] >= 1
    finally:
        os.chdir(old)


def test_cli_memory_show_empty_json(tmp_path: Path) -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["memory", "show", "--workspace", str(tmp_path), "--json"])
    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)["data"]
    assert payload["nodes"] == []
    assert payload["tenant_isolation"] == "not_claimed"


def test_extraction_redacts_secret_values(tmp_path: Path) -> None:
    traces = tmp_path / ".arc" / "traces"
    traces.mkdir(parents=True)
    (traces / "r-secret.jsonl").write_text(
        json.dumps(
            {"api_key": "sk-secret123456789012345678901234567890", "message": "sandbox risk"}
        )
        + "\n",
        encoding="utf-8",
    )
    snapshot = extract_memories_from_runs(traces)
    raw = snapshot.model_dump_json()
    assert "sk-secret" not in raw
    assert snapshot.redaction_applied is True


def test_store_forget_run_removes_source_only_nodes(tmp_path: Path) -> None:
    store = MemoryGraphStore(tmp_path / "graph.json")
    store.save(
        MemoryGraphSnapshot(
            nodes=[
                MemoryNode(
                    id="a",
                    type="concept",
                    text="sandbox",
                    confidence=0.5,
                    source_run_ids=["r1"],
                ),
                MemoryNode(
                    id="b",
                    type="concept",
                    text="policy",
                    confidence=0.5,
                    source_run_ids=["r1", "r2"],
                ),
            ]
        )
    )
    snapshot = store.forget_run("r1")
    assert [node.id for node in snapshot.nodes] == ["b"]
    assert snapshot.nodes[0].source_run_ids == ["r2"]


def test_cli_memory_forget_run_json(tmp_path: Path) -> None:
    old = Path.cwd()
    os.chdir(tmp_path)
    try:
        store = MemoryGraphStore(tmp_path / ".arc" / "memory" / "graph.json")
        store.save(
            MemoryGraphSnapshot(
                nodes=[
                    MemoryNode(
                        id="a",
                        type="concept",
                        text="sandbox",
                        confidence=0.5,
                        source_run_ids=["r1"],
                    )
                ]
            )
        )
        result = CliRunner().invoke(app, ["memory", "forget-run", "r1", "--json"])
        assert result.exit_code == 0, result.stderr
        payload = json.loads(result.stdout)["data"]
        assert payload["nodes_remaining"] == 0
    finally:
        os.chdir(old)


def test_evaluate_memory_graph_requires_evidence() -> None:
    report = evaluate_memory_graph(MemoryGraphSnapshot())
    assert report.decision == "insufficient_evidence"
    assert "no measured quality or cost delta supplied" in report.reasons


def test_evaluate_memory_graph_proceed_threshold() -> None:
    snapshot = MemoryGraphSnapshot(
        nodes=[
            MemoryNode(
                id=f"node-{i}",
                type="concept",
                text=f"memory-{i}",
                confidence=0.5,
                source_run_ids=[f"r{i}"],
            )
            for i in range(10)
        ]
    )
    report = evaluate_memory_graph(snapshot, quality_delta=0.12)
    assert report.decision == "proceed"
    assert report.sample_run_count == 10


def test_cli_memory_evaluate_json(tmp_path: Path) -> None:
    store = MemoryGraphStore(tmp_path / ".arc" / "memory" / "graph.json")
    store.save(
        MemoryGraphSnapshot(
            nodes=[
                MemoryNode(
                    id="a",
                    type="concept",
                    text="sandbox",
                    confidence=0.5,
                    source_run_ids=["r1"],
                )
            ]
        )
    )
    result = CliRunner().invoke(
        app,
        ["memory", "evaluate", "--workspace", str(tmp_path), "--quality-delta", "0.01", "--json"],
    )
    assert result.exit_code == 0, result.stderr
    payload = json.loads(result.stdout)["data"]
    assert payload["decision"] == "no_go"
    assert payload["sample_run_count"] == 1
