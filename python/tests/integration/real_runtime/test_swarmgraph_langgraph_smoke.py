"""Opt-in real-runtime smoke tests for release readiness.

These tests are intentionally skipped in the default offline gate. Enable with
``ARC_REAL_RUNTIME_SMOKE=1`` when validating a release candidate or nightly CI.
"""
from __future__ import annotations

import os

import pytest

from agent_runtime_cockpit.adoption.langgraph_runner import (
    LangGraphAdoptionRunner,
    _setup_swarmgraph_paths,
)
from agent_runtime_cockpit.adoption.protocol import AdoptionStatus


pytestmark = pytest.mark.real_runtime


def _requires_real_runtime_smoke() -> None:
    if os.environ.get("ARC_REAL_RUNTIME_SMOKE") != "1":
        pytest.skip("set ARC_REAL_RUNTIME_SMOKE=1 to run real-runtime smoke tests")


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
