"""Golden-hash regression (Commit 5).

Locks the deterministic graph hash for the committed fixtures so that any
unintended change to IR shape or hashing is caught.
"""

from __future__ import annotations

import json
from pathlib import Path

from agent_runtime_cockpit.swarmgraph_ir import compile_from_json

FIX = Path(__file__).parent / "fixtures"


def _golden() -> dict[str, str]:
    return json.loads((FIX / "expected_hashes.json").read_text())


def test_fixture_hashes_are_stable() -> None:
    golden = _golden()
    for name, expected in golden.items():
        text = (FIX / f"{name}.workflow.json").read_text()
        res = compile_from_json(text, use_sdk_risk=False)
        assert res.ok, (name, res.validation.errors)
        assert res.graph.graph_hash == expected, f"hash drift for {name}"


def test_ir_fixture_files_match_recompiled_hash() -> None:
    golden = _golden()
    for name, expected in golden.items():
        ir_text = (FIX / f"{name}.ir.json").read_text()
        obj = json.loads(ir_text)
        assert obj["graph_hash"] == expected
