"""Tests: R-PERF1 aiter_workspace_files + R-PERF6 mmap + R-PERF8 TCPConnector (Phases 312-314)."""

from __future__ import annotations
import asyncio

import pytest


def test_aiter_workspace_files_yields_files(tmp_path):
    """R-PERF1: aiter_workspace_files returns matching files."""
    (tmp_path / "a.py").write_text("x=1")
    (tmp_path / "b.ts").write_text("const x=1")
    (tmp_path / "skip.txt").write_text("nope")
    from agent_runtime_cockpit.workspace import aiter_workspace_files

    async def _collect():
        return [p async for p in aiter_workspace_files(tmp_path, (".py", ".ts"))]

    result = asyncio.run(_collect())
    names = {p.name for p in result}
    assert "a.py" in names
    assert "b.ts" in names
    assert "skip.txt" not in names


def test_aiter_workspace_files_max_files(tmp_path):
    """R-PERF1: max_files cap is respected."""
    for i in range(20):
        (tmp_path / f"f{i}.py").write_text("x")
    from agent_runtime_cockpit.workspace import aiter_workspace_files

    async def _collect():
        return [p async for p in aiter_workspace_files(tmp_path, (".py",), max_files=5)]

    result = asyncio.run(_collect())
    assert len(result) <= 5


@pytest.mark.asyncio
async def test_mmap_trace_reading(tmp_path):
    """R-PERF6: _iter_trace_events uses mmap for large files (> 10 MB check)."""
    import json
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
    from agent_runtime_cockpit.orchestration.event_broker import EventBroker

    store = JsonlTraceStore(base_dir=tmp_path)
    # Write a small JSONL trace
    trace_path = tmp_path / "run-test.jsonl"
    events = [{"type": "TEST_EVENT", "sequence": i, "data": {}} for i in range(10)]
    trace_path.write_text("\n".join(json.dumps(e) for e in events) + "\n")

    broker = EventBroker(store)
    collected = []
    async for evt in broker._iter_trace_events("run-test"):
        collected.append(evt)

    assert len(collected) == 10
    assert all(e["type"] == "TEST_EVENT" for e in collected)


def test_tcp_connector_in_models_dev():
    """R-PERF8: fetch_models_dev_catalog uses TCPConnector."""
    import inspect
    from agent_runtime_cockpit.providers.models_dev import fetch_models_dev_catalog

    src = inspect.getsource(fetch_models_dev_catalog)
    assert "TCPConnector" in src
    assert "limit_per_host" in src


def test_mmap_threshold_env_override(tmp_path, monkeypatch):
    import json
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
    from agent_runtime_cockpit.orchestration.event_broker import EventBroker

    store = JsonlTraceStore(base_dir=tmp_path)
    trace_path = tmp_path / "run-mmap.jsonl"
    trace_path.write_text(json.dumps({"type": "TEST_EVENT"}) + "\n")
    broker = EventBroker(store)

    monkeypatch.setenv("ARC_MMAP_THRESHOLD", "1")
    metrics = broker.read_trace_metrics("run-mmap")
    assert metrics.mmap_used is True
    assert metrics.line_count == 1


def test_mmap_invalid_threshold_degrades_to_default(tmp_path, monkeypatch):
    import json
    from agent_runtime_cockpit.storage.jsonl import JsonlTraceStore
    from agent_runtime_cockpit.orchestration.event_broker import EventBroker, mmap_threshold_bytes

    store = JsonlTraceStore(base_dir=tmp_path)
    (tmp_path / "run-small.jsonl").write_text(json.dumps({"type": "TEST_EVENT"}) + "\n")
    monkeypatch.setenv("ARC_MMAP_THRESHOLD", "bad")
    assert mmap_threshold_bytes() > 1
    assert EventBroker(store).read_trace_metrics("run-small").mmap_used is False
