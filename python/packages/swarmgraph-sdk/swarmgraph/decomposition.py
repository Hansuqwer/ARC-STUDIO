from __future__ import annotations

import re
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import SwarmGraphConfig, SwarmTopology
from .models import SwarmTask, TaskPriority


class DecompositionStrategy(Protocol):
    def decompose(
        self,
        prompt: str,
        num_workers: int,
        config: SwarmGraphConfig,
    ) -> list[SwarmTask]: ...


class CopyDecomposition:
    def decompose(
        self,
        prompt: str,
        num_workers: int,
        config: SwarmGraphConfig,
    ) -> list[SwarmTask]:
        tasks: list[SwarmTask] = []
        for i in range(num_workers):
            scoped_prompt = (
                f"You are worker {i + 1} of {num_workers}. "
                "Provide your independent analysis. Do not assume knowledge of "
                "other workers' outputs.\n\n"
                f"{prompt}"
            )
            tasks.append(
                SwarmTask(
                    prompt=scoped_prompt,
                    priority=TaskPriority.medium,
                    metadata={
                        "consensus_group": "root",
                        "consensus_prompt": prompt,
                        "worker_index": i,
                        "total_workers": num_workers,
                        "isolated": True,
                        "context": scoped_prompt,
                    },
                )
            )
        return tasks


class StepDecomposition:
    def decompose(
        self,
        prompt: str,
        num_workers: int,
        config: SwarmGraphConfig,
    ) -> list[SwarmTask]:
        tasks: list[SwarmTask] = []
        for i in range(num_workers):
            task = SwarmTask(
                prompt=f"{prompt} (step {i + 1}/{num_workers})",
                priority=TaskPriority.medium,
                parent_task_id=tasks[-1].id if tasks else None,
                dependency_task_ids=[tasks[-1].id] if tasks else [],
                metadata={"step": i, "total_steps": num_workers, "isolated": True},
            )
            tasks.append(task)
        return tasks


class MeshDecomposition:
    """Each worker gets an independent copy of the full prompt (no shared context).

    Mesh topology is similar to star/copy but each worker operates completely
    independently — suitable for diversity sampling and ensemble approaches.
    """

    def decompose(
        self,
        prompt: str,
        num_workers: int,
        config: SwarmGraphConfig,
    ) -> list[SwarmTask]:
        return [
            SwarmTask(
                prompt=prompt,
                priority=TaskPriority.medium,
                metadata={
                    "topology": "mesh",
                    "worker_index": i,
                    "total_workers": num_workers,
                    "isolated": True,
                },
            )
            for i in range(num_workers)
        ]


class TreeDecomposition:
    """Hierarchical decomposition: one root summary task + leaf worker tasks.

    The root task carries the full prompt and runs first (no parent).
    Leaf tasks each receive a scoped slice of the prompt and have the root
    task set as their parent, so they only run after the root completes.
    This allows the root to provide context that leaves can build on.
    """

    def decompose(
        self,
        prompt: str,
        num_workers: int,
        config: SwarmGraphConfig,
    ) -> list[SwarmTask]:
        root = SwarmTask(
            prompt=prompt,
            priority=TaskPriority.high,
            metadata={"topology": "tree", "role": "root", "isolated": False},
        )
        leaves: list[SwarmTask] = []
        num_leaves = max(1, num_workers - 1)
        for i in range(num_leaves):
            leaves.append(
                SwarmTask(
                    prompt=f"{prompt} (subtask {i + 1}/{num_leaves})",
                    priority=TaskPriority.medium,
                    parent_task_id=root.id,
                    dependency_task_ids=[root.id],
                    metadata={
                        "topology": "tree",
                        "role": "leaf",
                        "leaf_index": i,
                        "total_leaves": num_leaves,
                        "isolated": True,
                    },
                )
            )
        return [root, *leaves]


class DAGPlanNode(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(..., min_length=1, max_length=128)
    prompt: str = Field(..., min_length=1, max_length=32768)
    depends_on: list[str] = Field(default_factory=list)


class DAGPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    nodes: list[DAGPlanNode] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_dag(self) -> DAGPlan:
        ids = [node.id for node in self.nodes]
        if len(ids) != len(set(ids)):
            raise ValueError("DAG node ids must be unique")
        id_set = set(ids)
        for node in self.nodes:
            missing = [dep for dep in node.depends_on if dep not in id_set]
            if missing:
                raise ValueError(f"DAG node {node.id} has missing dependencies: {missing}")
        self.topological_order()
        return self

    def topological_order(self) -> list[str]:
        remaining = {node.id: set(node.depends_on) for node in self.nodes}
        ordered: list[str] = []
        while remaining:
            ready = sorted(node_id for node_id, deps in remaining.items() if not deps)
            if not ready:
                raise ValueError("DAG contains a cycle")
            for node_id in ready:
                ordered.append(node_id)
                remaining.pop(node_id)
                for deps in remaining.values():
                    deps.discard(node_id)
        return ordered

    def to_tasks(self) -> list[SwarmTask]:
        by_id = {node.id: node for node in self.nodes}
        tasks: dict[str, SwarmTask] = {}
        for node_id in self.topological_order():
            node = by_id[node_id]
            tasks[node.id] = SwarmTask(
                id=node.id,
                prompt=node.prompt,
                priority=TaskPriority.medium,
                parent_task_id=node.depends_on[-1] if node.depends_on else None,
                dependency_task_ids=list(node.depends_on),
                metadata={"topology": "dag", "planner": "deterministic", "auto_provider": False},
            )
        return [tasks[node_id] for node_id in self.topological_order()]


class DAGDecomposition:
    def decompose(
        self,
        prompt: str,
        num_workers: int,
        config: SwarmGraphConfig,
    ) -> list[SwarmTask]:
        return plan_dag(prompt, max_nodes=max(1, num_workers)).to_tasks()


def plan_dag(prompt: str, max_nodes: int | None = None) -> DAGPlan:
    parts = _split_prompt_steps(prompt)
    if max_nodes is not None:
        parts = parts[:max_nodes]
    if not parts:
        parts = [prompt.strip() or "task"]
    nodes = []
    for index, part in enumerate(parts, start=1):
        node_id = f"task-{index:03d}"
        depends_on = [f"task-{index - 1:03d}"] if index > 1 else []
        nodes.append(DAGPlanNode(id=node_id, prompt=part, depends_on=depends_on))
    return DAGPlan(nodes=nodes)


def _split_prompt_steps(prompt: str) -> list[str]:
    text = prompt.strip()
    if not text:
        return []
    numbered = [
        part.strip(" .:-\t") for part in re.split(r"(?:^|\n|\s)\d+[.)]\s+", text) if part.strip()
    ]
    if len(numbered) > 1:
        return numbered
    bullets = [part.strip(" -\t") for part in re.split(r"(?:^|\n)\s*[-*]\s+", text) if part.strip()]
    if len(bullets) > 1:
        return bullets
    then_parts = [
        part.strip(" .")
        for part in re.split(r"\bthen\b", text, flags=re.IGNORECASE)
        if part.strip()
    ]
    if len(then_parts) > 1:
        return then_parts
    sentence_parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
    return sentence_parts if len(sentence_parts) > 1 else [text]


class TrivialDecomposition:
    def decompose(
        self,
        prompt: str,
        num_workers: int,
        config: SwarmGraphConfig,
    ) -> list[SwarmTask]:
        if config.topology == SwarmTopology.star:
            return CopyDecomposition().decompose(prompt, num_workers, config)
        if config.topology == SwarmTopology.chain:
            return StepDecomposition().decompose(prompt, num_workers, config)
        if config.topology == SwarmTopology.mesh:
            return MeshDecomposition().decompose(prompt, num_workers, config)
        if config.topology == SwarmTopology.tree:
            return TreeDecomposition().decompose(prompt, num_workers, config)
        return [
            SwarmTask(
                prompt=prompt,
                priority=TaskPriority.medium,
                metadata={"topology": config.topology.value, "isolated": True},
            )
        ]


def parallelizability_score(prompt: str) -> float:
    words = len(prompt.split())
    if words < 10:
        return 0.1

    sentence_count = prompt.count(".") + prompt.count("!") + prompt.count("?")
    if sentence_count <= 1:
        return 0.3

    lower = prompt.lower()
    connectors = lower.count(" and ") + lower.count(" then ") + prompt.count(",")
    numbered = sum(1 for marker in ("1.", "2.", "3.", "- ") if marker in prompt)
    score = min(1.0, 0.3 + sentence_count * 0.15 + connectors * 0.1 + numbered * 0.1)
    return round(score, 2)
