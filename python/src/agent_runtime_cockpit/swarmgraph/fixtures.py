from __future__ import annotations

from .config import ExecutionMode, SwarmGraphConfig
from .runner import SwarmGraphRunner


def run_deterministic_swarm(
    prompt: str = "test deterministic swarm",
    num_workers: int = 3,
    max_rounds: int = 1,
) -> dict:
    config = SwarmGraphConfig(
        num_workers=num_workers,
        max_rounds=max_rounds,
        execution_mode=ExecutionMode.fake_offline,
        allow_paid_calls=False,
        require_hitl=False,
        enable_audit=False,
        enable_budget=False,
    )
    runner = SwarmGraphRunner(config=config)
    return runner.run(prompt=prompt)


def run_hitl_swarm(
    prompt: str = "test HITL swarm",
) -> tuple:
    config = SwarmGraphConfig(
        num_workers=2,
        max_rounds=1,
        execution_mode=ExecutionMode.fake_offline,
        require_hitl=True,
    )
    runner = SwarmGraphRunner(config=config)
    result = runner.run(prompt=prompt)
    return result, runner


def run_budget_swarm(
    prompt: str = "test budget swarm",
    budget_limit: float = 0.01,
    num_workers: int = 3,
) -> dict:
    config = SwarmGraphConfig(
        num_workers=num_workers,
        max_rounds=3,
        execution_mode=ExecutionMode.fake_offline,
        enable_budget=True,
        budget_limit_usd=budget_limit,
    )
    runner = SwarmGraphRunner(config=config)
    return runner.run(prompt=prompt)
