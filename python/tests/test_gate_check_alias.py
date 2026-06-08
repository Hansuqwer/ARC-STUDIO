"""Phase 248 cleanup: gate check == gate evaluate JSON-equivalence test.

Slice 53 from the cleanup backlog: 'arc mobile gate check' flat alias
for 'arc mobile gate evaluate' with JSON-equivalence verification.
"""

from __future__ import annotations

import json

from typer.testing import CliRunner

from agent_runtime_cockpit.cli._subapps import mobile_app

runner = CliRunner()


def test_gate_check_and_evaluate_produce_equivalent_output():
    """'arc mobile gate check' and 'arc mobile gate evaluate' must return the same structure."""
    cap_id = "app.memory.retrieve.mock"

    r_check = runner.invoke(mobile_app, ["gate", "check", cap_id, "--json"])
    r_evaluate = runner.invoke(mobile_app, ["gate", "evaluate", cap_id, "--json"])

    assert r_check.exit_code == 0
    assert r_evaluate.exit_code == 0

    d_check = json.loads(r_check.output)
    d_evaluate = json.loads(r_evaluate.output)

    # Structural equivalence: same keys in data
    assert set(d_check["data"].keys()) == set(d_evaluate["data"].keys()), (
        "gate check and gate evaluate must return the same data keys"
    )
    assert d_check["data"]["capability_id"] == d_evaluate["data"]["capability_id"]
    assert d_check["data"]["route"] == d_evaluate["data"]["route"]
    assert d_check["data"]["eligible"] == d_evaluate["data"]["eligible"]
