from __future__ import annotations

from agent_runtime_cockpit.swarmgraph.config import SwarmGraphConfig, SwarmTopology
from agent_runtime_cockpit.swarmgraph.nodes.queen import queen_decompose, queen_prepare_agents
from agent_runtime_cockpit.swarmgraph.nodes.worker import worker_execute
from agent_runtime_cockpit.swarmgraph.state import SwarmState


def test_star_workers_get_isolated_prompts() -> None:
    cfg = SwarmGraphConfig(num_workers=3, topology=SwarmTopology.star)
    state = SwarmState(config=cfg)
    queen_prepare_agents(state, 3)

    tasks = queen_decompose(state, "analyze this data")

    prompts = [task.prompt for task in tasks]
    assert len(set(prompts)) == 3
    assert "worker 1 of 3" in prompts[0].lower()
    assert "worker 2 of 3" in prompts[1].lower()
    assert all(task.metadata.get("isolated") for task in tasks)
    assert all(task.metadata.get("context") == task.prompt for task in tasks)


def test_worker_output_does_not_include_sibling_prompt_marker() -> None:
    tasks = queen_decompose(SwarmState(config=SwarmGraphConfig(num_workers=2)), "SAFE_MARKER")
    task = tasks[0]
    sibling = tasks[1]
    sibling.prompt = f"{sibling.prompt}\nSIBLING_SECRET"

    result = worker_execute(task)

    assert task.prompt[:80] in result.output
    assert sibling.prompt not in result.output
    assert "SIBLING_SECRET" not in result.output
