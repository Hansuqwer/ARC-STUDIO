"""Verify ARC's agent_runtime_cockpit.swarmgraph compatibility bridge.

Source ownership now lives in the standalone swarmgraph-sdk package. ARC
re-exports it. These tests guard that:

1. Top-level symbols are identical objects across both import paths.
2. Submodule imports resolve to the *same* module object (Pydantic class
   identity must be preserved).
"""

from __future__ import annotations


def test_top_level_symbols_are_identical() -> None:
    import agent_runtime_cockpit.swarmgraph as bridge
    import swarmgraph as sdk

    assert bridge.SwarmGraphRunner is sdk.SwarmGraphRunner
    assert bridge.SwarmGraphConfig is sdk.SwarmGraphConfig
    assert bridge.EchoProvider is sdk.EchoProvider


def test_submodule_class_identity_preserved() -> None:
    from agent_runtime_cockpit.swarmgraph.config import SwarmGraphConfig as BridgeConfig
    from agent_runtime_cockpit.swarmgraph.state import SwarmState
    from swarmgraph.config import SwarmGraphConfig as SdkConfig

    assert BridgeConfig is SdkConfig

    # SwarmState.config validation must accept the bridge-imported config.
    cfg = BridgeConfig(execution_mode="fake_offline", allow_paid_calls=False)
    state = SwarmState(config=cfg)
    assert state.config is cfg


def test_nodes_subpackage_resolves_through_bridge() -> None:
    from agent_runtime_cockpit.swarmgraph.nodes.worker import worker_execute
    from swarmgraph.nodes.worker import worker_execute as sdk_worker_execute

    assert worker_execute is sdk_worker_execute
