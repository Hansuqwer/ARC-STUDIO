"""Cross-adapter integration. Exercises detection, dual-gating, AG-UI conformance."""

import asyncio
import json
import pathlib

import pytest

from agent_runtime_cockpit.ag_ui import EVENT_SCHEMAS

ADAPTERS = ["swarmgraph", "langgraph", "openai-agents", "crewai", "ag2"]


@pytest.fixture
def fixtures_dir() -> pathlib.Path:
    return pathlib.Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("adapter", ADAPTERS)
def test_golden_traces_validate_against_ag_ui_schema(adapter: str, fixtures_dir: pathlib.Path):
    path = fixtures_dir / f"{adapter}.golden.jsonl"
    if not path.exists():
        pytest.skip(f"no golden fixture for {adapter} yet")
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        evt = json.loads(line)
        assert evt["type"] in EVENT_SCHEMAS, f"{adapter}: unknown event type {evt['type']}"


def test_no_live_provider_when_gates_unset(tmp_path, monkeypatch):
    for r in ("SWARMGRAPH", "LANGGRAPH", "CREWAI", "AG2", "OPENAI_AGENTS"):
        monkeypatch.delenv(f"ARC_{r}_RUN_BACKEND", raising=False)
        monkeypatch.delenv(f"ARC_{r}_ALLOW_COSTS", raising=False)
    from agent_runtime_cockpit.adapters.swarmgraph.runner import SwarmGraphRunner

    run_id = asyncio.run(SwarmGraphRunner(tmp_path).run("noop:obj", {}))
    assert run_id


def test_redaction_invariant_across_adapters(fixtures_dir: pathlib.Path):
    import re

    patterns = [
        re.compile(r"sk-[A-Za-z0-9_-]{16,}"),
        re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    ]
    for adapter in ADAPTERS:
        p = fixtures_dir / f"{adapter}.golden.jsonl"
        if not p.exists():
            continue
        text = p.read_text()
        for pat in patterns:
            assert not pat.search(text), f"{adapter}: secret leaked in fixture"


def test_audit_chain_round_trip(tmp_path):
    from agent_runtime_cockpit.adapters.swarmgraph.runner import SwarmGraphRunner
    from agent_runtime_cockpit.audit.chain import verify

    run_id = asyncio.run(SwarmGraphRunner(tmp_path).run("noop:obj", {}))
    ok, _ = verify(
        tmp_path / ".arc" / "audit" / f"{run_id}.chain.jsonl",
        tmp_path / ".arc" / "traces" / f"{run_id}.jsonl",
    )
    assert ok
