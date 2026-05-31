from __future__ import annotations

from typing import Protocol

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
                metadata={"step": i, "total_steps": num_workers, "isolated": True},
            )
            tasks.append(task)
        return tasks


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
