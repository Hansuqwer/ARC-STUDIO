from __future__ import annotations

from agent_runtime_cockpit.swarmgraph.config import SwarmGraphConfig, SwarmTopology
from agent_runtime_cockpit.swarmgraph.decomposition import (
    StepDecomposition,
    TrivialDecomposition,
    parallelizability_score,
)
from agent_runtime_cockpit.swarmgraph.runner import SwarmGraphRunner


class _SingleCustomDecomposition:
    def decompose(self, prompt: str, num_workers: int, config: SwarmGraphConfig):
        from agent_runtime_cockpit.swarmgraph.models import SwarmTask

        return [SwarmTask(prompt=f"custom:{prompt}")]


def test_parallelizability_simple_prompt_scores_low() -> None:
    assert parallelizability_score("Explain consensus") < 0.6


def test_parallelizability_complex_prompt_scores_high() -> None:
    prompt = "Implement feature A, test feature B, then document feature C. Verify errors. Ship."
    assert parallelizability_score(prompt) >= 0.6


def test_trivial_decomposition_star_is_isolated() -> None:
    cfg = SwarmGraphConfig(num_workers=2, topology=SwarmTopology.star)
    tasks = TrivialDecomposition().decompose("analyze", 2, cfg)

    assert len(tasks) == 2
    assert tasks[0].prompt != tasks[1].prompt
    assert all(task.metadata["isolated"] for task in tasks)


def test_step_decomposition_links_parent_tasks() -> None:
    cfg = SwarmGraphConfig(num_workers=2, topology=SwarmTopology.chain)
    tasks = StepDecomposition().decompose("analyze", 2, cfg)

    assert len(tasks) == 2
    assert tasks[1].parent_task_id == tasks[0].id


def test_runner_simple_prompt_uses_single_worker_and_audits() -> None:
    cfg = SwarmGraphConfig(num_workers=4, max_rounds=1)
    runner = SwarmGraphRunner(config=cfg)
    result = runner.run("Explain consensus")

    assert result["total_tasks"] == 1
    audit_events = [event for event in result["events"] if event["kind"] == "audit"]
    assert audit_events[0]["data"]["decision"] == "single"
    assert audit_events[0]["data"]["effective_workers"] == 1


def test_runner_complex_prompt_fans_out_and_audits() -> None:
    cfg = SwarmGraphConfig(num_workers=3, max_rounds=1)
    runner = SwarmGraphRunner(config=cfg)
    result = runner.run(
        "Implement feature A, test feature B, then document feature C. Verify errors. Ship."
    )

    assert result["total_tasks"] == 3
    audit_events = [event for event in result["events"] if event["kind"] == "audit"]
    assert audit_events[0]["data"]["decision"] == "fan_out"
    assert audit_events[0]["data"]["effective_workers"] == 3


def test_runner_accepts_decomposition_strategy_injection() -> None:
    cfg = SwarmGraphConfig(num_workers=3, max_rounds=1, fan_out_threshold=0)
    runner = SwarmGraphRunner(config=cfg, decomposition_strategy=_SingleCustomDecomposition())
    result = runner.run("complex. enough. prompt.")

    assert result["total_tasks"] == 1
    assert result["results"][0]["output"].endswith("custom:complex. enough. prompt.")
