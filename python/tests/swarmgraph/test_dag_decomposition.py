import json

import pytest
from typer.testing import CliRunner

from agent_runtime_cockpit.cli import app
from agent_runtime_cockpit.swarmgraph.config import SwarmGraphConfig
from agent_runtime_cockpit.swarmgraph.decomposition import (
    DAGDecomposition,
    DAGPlan,
    DAGPlanNode,
    plan_dag,
)


def test_dag_parser_creates_stable_nodes_from_numbered_prompt():
    plan = plan_dag("1. Research. 2. Implement. 3. Test.")

    assert [node.id for node in plan.nodes] == ["task-001", "task-002", "task-003"]
    assert plan.nodes[1].depends_on == ["task-001"]
    assert plan.topological_order() == ["task-001", "task-002", "task-003"]


def test_dag_validator_rejects_missing_dependencies():
    with pytest.raises(ValueError, match="missing dependencies"):
        DAGPlan(nodes=[DAGPlanNode(id="a", prompt="A", depends_on=["missing"])])


def test_dag_validator_rejects_cycles():
    with pytest.raises(ValueError, match="cycle"):
        DAGPlan(
            nodes=[
                DAGPlanNode(id="a", prompt="A", depends_on=["b"]),
                DAGPlanNode(id="b", prompt="B", depends_on=["a"]),
            ]
        )


def test_dag_decomposer_creates_swarm_tasks_with_dependencies():
    tasks = DAGDecomposition().decompose(
        "Research then Implement then Test",
        num_workers=3,
        config=SwarmGraphConfig(),
    )

    assert [task.id for task in tasks] == ["task-001", "task-002", "task-003"]
    assert tasks[1].dependency_task_ids == ["task-001"]
    assert tasks[2].metadata["planner"] == "deterministic"
    assert tasks[2].metadata["auto_provider"] is False


def test_swarmgraph_plan_cli_json_envelope(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        app,
        ["swarmgraph", "plan", "--strategy", "dag", "--task", "1. Research. 2. Test.", "--json"],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["ok"] is True
    assert payload["data"]["provider_backed"] is False
    assert payload["data"]["topological_order"] == ["task-001", "task-002"]
