"""
Tests: Adoption protocol skeleton (P1b).

Tests the Pydantic models, registry, and runner skeleton.
No executable adoption mode is provided — all tests check honest
NOT_IMPLEMENTED / NOT_RUNNABLE status.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from agent_runtime_cockpit.adoption import (
    AdoptionMode,
    AdoptionSpec,
    WorkerTask,
    WorkerProposal,
    Vote,
    ConsensusResult,
    AdoptionStatus,
    AdoptionCapability,
    AdoptionRunner,
    AdoptionRegistry,
)


class TestAdoptionModels:
    """Pydantic models serialize/deserialize correctly."""

    def test_adoption_mode_values(self):
        assert AdoptionMode.LANGGRAPH.value == "langgraph+swarmgraph"
        assert AdoptionMode.AG2.value == "ag2+swarmgraph"
        assert AdoptionMode.OPENAI_AGENTS.value == "openai_agents+swarmgraph"

    def test_adoption_spec_defaults(self):
        spec = AdoptionSpec(mode=AdoptionMode.LANGGRAPH)
        assert spec.max_workers == 3
        assert spec.consensus_threshold == 0.67
        assert spec.runtime_config == {}

    def test_worker_task_serialization(self):
        task = WorkerTask(task_id="t1", worker_id="w1", runtime="langgraph")
        d = task.model_dump()
        assert d["task_id"] == "t1"
        assert d["worker_id"] == "w1"
        assert d["input_data"] == {}

    def test_worker_proposal_defaults(self):
        p = WorkerProposal(task_id="t1", worker_id="w1", output="result")
        assert p.confidence == 1.0
        assert p.metadata == {}

    def test_vote_model(self):
        v = Vote(task_id="t1", voter_id="v1", proposal_id="p1", score=0.9)
        assert v.score == 0.9
        assert v.reason == ""

    def test_consensus_result(self):
        proposal = WorkerProposal(task_id="t1", worker_id="w1", output="ok")
        result = ConsensusResult(
            task_id="t1",
            winning_proposal=proposal,
            consensus_reached=True,
            confidence=0.95,
        )
        assert result.consensus_reached is True
        assert result.confidence == 0.95
        assert len(result.votes) == 0

    def test_adoption_status_enum(self):
        assert AdoptionStatus.NOT_IMPLEMENTED.value == "not_implemented"
        assert AdoptionStatus.NOT_RUNNABLE.value == "not_runnable"
        assert AdoptionStatus.RUNNABLE.value == "runnable"

    def test_adoption_capability(self):
        cap = AdoptionCapability(
            mode=AdoptionMode.LANGGRAPH,
            status=AdoptionStatus.NOT_IMPLEMENTED,
            reason="Not done yet",
        )
        assert cap.mode == AdoptionMode.LANGGRAPH
        assert cap.status == AdoptionStatus.NOT_IMPLEMENTED

    def test_full_serialization_roundtrip(self):
        spec = AdoptionSpec(
            mode=AdoptionMode.CREWAI,
            runtime_config={"key": "val"},
            max_workers=5,
            consensus_threshold=0.8,
        )
        json_str = spec.model_dump_json()
        restored = AdoptionSpec.model_validate_json(json_str)
        assert restored.mode == AdoptionMode.CREWAI
        assert restored.max_workers == 5


class TestAdoptionRegistry:
    """AdoptionRegistry auto-reports NOT_IMPLEMENTED for unregistered modes."""

    def test_unregistered_modes_report_not_implemented(self, tmp_path):
        caps = AdoptionRegistry.list_capabilities(tmp_path)
        for cap in caps:
            assert cap.status == AdoptionStatus.NOT_IMPLEMENTED
            assert "not yet implemented" in cap.reason

    def test_list_contains_all_modes(self, tmp_path):
        caps = AdoptionRegistry.list_capabilities(tmp_path)
        modes = {cap.mode for cap in caps}
        assert modes == set(AdoptionMode)

    def test_parse_runtime_id_standard(self):
        base, mode = AdoptionRegistry.parse_runtime_id("langgraph+swarmgraph")
        assert base == "langgraph"
        assert mode == AdoptionMode.LANGGRAPH

    def test_parse_runtime_id_unknown(self):
        base, mode = AdoptionRegistry.parse_runtime_id("unknown+swarmgraph")
        assert base == "unknown"
        assert mode is None

    def test_parse_runtime_id_standalone(self):
        base, mode = AdoptionRegistry.parse_runtime_id("swarmgraph")
        assert base == "swarmgraph"
        assert mode is None


class TestLangGraphRunner:
    """LangGraphAdoptionRunner reports NOT_RUNNABLE correctly."""

    def test_runner_reports_not_runnable(self, tmp_path):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )
        runner = LangGraphAdoptionRunner()
        cap = runner.check_availability(tmp_path)
        assert cap.status == AdoptionStatus.NOT_RUNNABLE
        assert "not installed" in cap.reason or "scaffold-only" in cap.reason
        assert len(cap.doctor_actions) >= 1

    def test_runner_run_raises_not_implemented(self):
        from agent_runtime_cockpit.adoption.langgraph_runner import (
            LangGraphAdoptionRunner,
        )
        runner = LangGraphAdoptionRunner()
        import asyncio

        async def _run():
            await runner.run(
                AdoptionSpec(mode=AdoptionMode.LANGGRAPH),
                "run-id",
                lambda x: None,
            )

        with pytest.raises(NotImplementedError):
            asyncio.run(_run())
