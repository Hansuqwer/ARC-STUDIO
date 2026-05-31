from __future__ import annotations

import json
import subprocess
import sys

import swarmgraph
from swarmgraph.config import ExecutionMode
from swarmgraph.providers import ProviderRequest
from swarmgraph.runner import SwarmRunResult as SubmoduleSwarmRunResult
from swarmgraph import SwarmGraphConfig, SwarmGraphRunner, SwarmRunResult


def test_swarmgraph_import_facade_exports_core_api() -> None:
    assert swarmgraph.SwarmGraphRunner is SwarmGraphRunner
    assert swarmgraph.SwarmGraphConfig is SwarmGraphConfig
    assert swarmgraph.config.ExecutionMode is ExecutionMode
    assert swarmgraph.ProviderRequest is ProviderRequest
    assert ExecutionMode.fake_offline.value == "fake_offline"
    assert SubmoduleSwarmRunResult is SwarmRunResult


def test_run_result_returns_typed_stable_payload() -> None:
    runner = SwarmGraphRunner(config=SwarmGraphConfig(max_rounds=1))

    result = runner.run_result("Explain consensus")

    assert isinstance(result, SwarmRunResult)
    assert result.status == "completed"
    assert result.total_tasks == 1
    assert result.completed_tasks == 1
    assert result.to_dict()["status"] == "completed"


def test_swarmgraph_facade_does_not_import_arc_provider_registry() -> None:
    code = """
import json
import sys
import swarmgraph
import swarmgraph.providers
blocked = [
    name for name in sys.modules
    if name.startswith('agent_runtime_cockpit.providers')
    or name == 'agent_runtime_cockpit.cli_repl.cancellation'
]
print(json.dumps(blocked))
"""

    completed = subprocess.run(
        [sys.executable, "-c", code],
        check=True,
        capture_output=True,
        text=True,
    )

    assert json.loads(completed.stdout) == []
