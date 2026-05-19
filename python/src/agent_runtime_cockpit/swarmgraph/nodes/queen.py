from __future__ import annotations

import uuid
from datetime import datetime, timezone

from ..config import SwarmTopology
from ..models import (
    AgentRole,
    AgentSpec,
    AgentState,
    AgentStatus,
    QueenDirective,
    SwarmTask,
    TaskPriority,
    TaskStatus,
)
from ..state import SwarmState


def queen_decompose(
    state: SwarmState,
    prompt: str,
) -> list[SwarmTask]:
    tasks: list[SwarmTask] = []
    num_workers = state.config.num_workers

    if state.config.topology == SwarmTopology.star:
        for i in range(num_workers):
            task = SwarmTask(
                prompt=prompt,
                priority=TaskPriority.medium,
                metadata={"worker_index": i, "total_workers": num_workers},
            )
            tasks.append(task)
    elif state.config.topology == SwarmTopology.chain:
        for i in range(num_workers):
            task = SwarmTask(
                prompt=f"{prompt} (step {i + 1}/{num_workers})",
                priority=TaskPriority.medium,
                parent_task_id=tasks[-1].id if tasks else None,
                metadata={"step": i, "total_steps": num_workers},
            )
            tasks.append(task)
    else:
        task = SwarmTask(
            prompt=prompt,
            priority=TaskPriority.medium,
            metadata={"topology": state.config.topology.value},
        )
        tasks.append(task)
    return tasks


def queen_assign(
    state: SwarmState,
    tasks: list[SwarmTask],
) -> dict[str, str]:
    assignment: dict[str, str] = {}
    idle_agents = state.get_idle_agents()

    if not idle_agents:
        return assignment

    for i, task in enumerate(tasks):
        agent_id = idle_agents[i % len(idle_agents)][0]
        assignment[task.id] = agent_id
        if agent_id in state.agents:
            state.agents[agent_id].status = AgentStatus.running
            state.agents[agent_id].current_task_id = task.id
        task.status = TaskStatus.assigned
        task.assigned_agent_id = agent_id
        directive = QueenDirective(
            task_id=task.id,
            prompt=task.prompt,
            assigned_worker_ids=[agent_id],
            priority=task.priority,
        )
        task.directive = directive
    return assignment


def queen_prepare_agents(
    state: SwarmState,
    num_workers: int | None = None,
) -> None:
    n = num_workers or state.config.num_workers
    for i in range(n):
        agent_id = f"worker-{i + 1}"
        spec = AgentSpec(
            id=agent_id,
            name=f"Worker {i + 1}",
            role=AgentRole.worker,
            model=state.config.execution_mode.value,
        )
        state.spec_map[agent_id] = spec
        state.agents[agent_id] = AgentState(agent_id=agent_id)

    queen_spec = AgentSpec(
        id="queen-1",
        name="Queen",
        role=AgentRole.queen,
        model=state.config.execution_mode.value,
    )
    state.spec_map["queen-1"] = queen_spec
    state.agents["queen-1"] = AgentState(agent_id="queen-1")
