"""Opt-in real-runtime smoke tests for release readiness.

These tests are intentionally skipped in the default offline gate. Enable with
``ARC_REAL_RUNTIME_SMOKE=1`` when validating a release candidate or nightly CI.
"""
from __future__ import annotations

import os
import asyncio
import importlib.util

import pytest

from agent_runtime_cockpit.adoption.langgraph_runner import (
    LangGraphAdoptionRunner,
    _setup_swarmgraph_paths,
)
from agent_runtime_cockpit.adoption.protocol import AdoptionStatus
from agent_runtime_cockpit.adoption.protocol import AdoptionMode, AdoptionSpec


pytestmark = pytest.mark.real_runtime


def _requires_real_runtime_smoke() -> None:
    if os.environ.get("ARC_REAL_RUNTIME_SMOKE") != "1":
        pytest.skip("set ARC_REAL_RUNTIME_SMOKE=1 to run real-runtime smoke tests")


def _requires_langgraph_runtime() -> None:
    _requires_real_runtime_smoke()
    if importlib.util.find_spec("langgraph") is None:
        pytest.skip("langgraph package is not installed; skipping optional real-runtime smoke")


def _requires_langgraph_swarmgraph_local_real() -> None:
    _requires_langgraph_runtime()
    if os.environ.get("ARC_LANGGRAPH_SWARMGRAPH_REAL") != "1":
        pytest.skip(
            "set ARC_REAL_RUNTIME_SMOKE=1 and ARC_LANGGRAPH_SWARMGRAPH_REAL=1 "
            "to run local-real langgraph+swarmgraph smoke"
        )


class _LocalRealNoProviderGraph:
    def invoke(self, input_data: dict[str, object]) -> dict[str, object]:
        return {
            "provider_call": False,
            "input_keys": sorted(input_data),
            "swarmgraph_task_seen": "swarmgraph_task" in input_data,
        }


def test_vendored_swarmgraph_imports() -> None:
    _requires_real_runtime_smoke()

    _setup_swarmgraph_paths()

    from swarm.models.config import SwarmConfig
    from swarm.models.state import SwarmState
    from swarm.nodes.consensus import consensus_node
    from swarm.nodes.queen import queen_decompose_node

    assert SwarmConfig is not None
    assert SwarmState is not None
    assert callable(consensus_node)
    assert callable(queen_decompose_node)


def test_langgraph_adoption_runner_availability_reports_real_status(tmp_path) -> None:
    _requires_real_runtime_smoke()

    capability = LangGraphAdoptionRunner().check_availability(tmp_path)

    assert capability.status is AdoptionStatus.RUNNABLE
    assert "LangGraph" in capability.reason
    assert "vendored SwarmGraph" in capability.reason


def test_langgraph_swarmgraph_route_availability_smoke(tmp_path) -> None:
    _requires_langgraph_runtime()

    _setup_swarmgraph_paths()

    capability = LangGraphAdoptionRunner().check_availability(tmp_path)

    assert capability.status is AdoptionStatus.RUNNABLE, (
        f"langgraph+swarmgraph route should be runnable: {capability.reason}"
    )
    assert "LangGraph" in capability.reason
    assert "SwarmGraph" in capability.reason


def test_langgraph_swarmgraph_local_real_requires_second_gate(tmp_path, monkeypatch) -> None:
    _requires_langgraph_runtime()
    monkeypatch.delenv("ARC_LANGGRAPH_SWARMGRAPH_REAL", raising=False)

    events: list[tuple[str, dict[str, object]]] = []

    def emit_event(_run_id: str, event_type: str, payload: dict[str, object]) -> None:
        events.append((event_type, payload))

    spec = AdoptionSpec(
        mode=AdoptionMode.LANGGRAPH,
        runtime_config={
            "runtime_mode": "local-real",
            "graph": _LocalRealNoProviderGraph(),
            "input": {"prompt": "local smoke only"},
        },
        max_workers=1,
    )

    with pytest.raises(PermissionError, match="ARC_LANGGRAPH_SWARMGRAPH_REAL=1"):
        asyncio.run(LangGraphAdoptionRunner().run(spec, "local-real-gated", emit_event))

    assert events == [(
        "RUN_FAILED",
        {
            "error": (
                "LangGraph+SwarmGraph local-real mode requires "
                "ARC_LANGGRAPH_SWARMGRAPH_REAL=1; no provider calls were made."
            ),
            "mode": "langgraph+swarmgraph",
            "runtime_mode": "local-real",
            "real_provider_call": False,
            "provider_backed": False,
        },
    )]


def test_langgraph_swarmgraph_local_real_fixture_runs_without_provider_calls(tmp_path) -> None:
    _requires_langgraph_swarmgraph_local_real()

    events: list[tuple[str, dict[str, object]]] = []

    def emit_event(_run_id: str, event_type: str, payload: dict[str, object]) -> None:
        events.append((event_type, payload))

    spec = AdoptionSpec(
        mode=AdoptionMode.LANGGRAPH,
        runtime_config={
            "runtime_mode": "local-real",
            "graph": _LocalRealNoProviderGraph(),
            "input": {"prompt": "local smoke only"},
            "objective": "verify local langgraph+swarmgraph runner fixture without provider calls",
        },
        max_workers=1,
    )

    result = asyncio.run(LangGraphAdoptionRunner().run(spec, "local-real-smoke", emit_event))

    assert result.consensus_reached is True
    assert result.winning_proposal.metadata["runtime"] == "langgraph"
    assert result.metadata["runtime_mode"] == "local-real"
    assert result.metadata["real_provider_call"] is False
    assert result.metadata["provider_backed"] is False
    assert result.winning_proposal.metadata["real_provider_call"] is False
    assert result.winning_proposal.metadata["provider_backed"] is False
    assert result.winning_proposal.confidence == 1.0
    assert result.winning_proposal.output
    assert any(event_type == "SWARMGRAPH_TOPOLOGY" for event_type, _ in events)
    assert any(event_type == "SWARMGRAPH_CONSENSUS" for event_type, _ in events)
    assert all(payload["runtime_mode"] == "local-real" for _, payload in events)
    assert all(payload["real_provider_call"] is False for _, payload in events)
    assert all(payload["provider_backed"] is False for _, payload in events)
