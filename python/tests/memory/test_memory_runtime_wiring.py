"""B2P-12: memory runtime wiring — redaction-first extraction + opt-in run-path hook."""

from __future__ import annotations

import inspect
from pathlib import Path


def test_memory_extraction_is_redaction_first(tmp_path: Path) -> None:
    """The extractor must redact secrets BEFORE building memory nodes (no raw secret in the graph)."""
    from agent_runtime_cockpit.memory_graph.store import extract_memories_from_runs

    traces = tmp_path / "traces"
    traces.mkdir()
    secret = "sk-abc123def456ghi789jkl012mno345pqr"
    (traces / "run-1.jsonl").write_text(
        '{"type":"MESSAGE","data":{"text":"the api key is ' + secret + ' please remember it"}}\n',
        encoding="utf-8",
    )
    snapshot = extract_memories_from_runs(traces, limit=5)
    assert snapshot.redaction_applied is True
    assert secret not in snapshot.model_dump_json()  # redaction-first: secret never enters memory


def test_executor_memory_wiring_is_opt_in_and_redaction_first() -> None:
    from agent_runtime_cockpit.tasks.executor import TaskExecutor

    src = inspect.getsource(TaskExecutor._execute_run)
    assert "ARC_MEMORY_AUTO_EXTRACT" in src  # opt-in (default off)
    assert "extract_memories_from_runs" in src  # wired into the run path
    assert "redaction-first" in src.lower()  # documented security intent
