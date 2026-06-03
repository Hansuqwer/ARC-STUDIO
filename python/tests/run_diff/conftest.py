"""Shared fixtures for run_diff tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent.parent / "swarmgraph_ir" / "fixtures"


@pytest.fixture
def native_minimal_ir_path() -> Path:
    return FIXTURES_DIR / "native_minimal.ir.json"


@pytest.fixture
def native_minimal_ir_data() -> dict:
    return json.loads((FIXTURES_DIR / "native_minimal.ir.json").read_text())


@pytest.fixture
def mcp_graph_ir_path() -> Path:
    return FIXTURES_DIR / "mcp_graph.ir.json"


@pytest.fixture
def mcp_graph_ir_data() -> dict:
    return json.loads((FIXTURES_DIR / "mcp_graph.ir.json").read_text())


@pytest.fixture
def langgraph_ir_path() -> Path:
    return FIXTURES_DIR / "langgraph_branch.ir.json"


@pytest.fixture
def modified_ir_data(native_minimal_ir_data) -> dict:
    import copy

    data = copy.deepcopy(native_minimal_ir_data)
    data["id"] = "wf-modified"
    data["nodes"].append(
        {
            "id": "new-node",
            "label": "New Tool",
            "kind": "tool",
            "tool": {"name": "write_file", "namespace": "fs", "pinned": False, "capabilities": []},
            "mcp_tool": None,
            "model_call": None,
            "human_gate": None,
            "consensus": None,
            "risk": {
                "level": "medium",
                "score": 0.5,
                "signals": ["file_write"],
                "rationale": None,
                "source": "heuristic",
            },
            "capabilities": [],
            "side_effects": [{"kind": "write", "target": None, "paid": False, "confidence": 1.0}],
            "budget": None,
            "audit_boundary": None,
            "replay_marker": None,
            "trust_annotation": None,
            "privileged": False,
            "write_path": None,
            "eval_metadata": {},
            "metadata": {},
        }
    )
    return data


@pytest.fixture
def paid_ir_data(native_minimal_ir_data) -> dict:
    import copy

    data = copy.deepcopy(native_minimal_ir_data)
    data["id"] = "wf-paid"
    data["risk"] = {
        "level": "high",
        "score": 0.8,
        "signals": ["paid_call"],
        "rationale": None,
        "source": "heuristic",
    }
    data["nodes"].append(
        {
            "id": "paid-agent",
            "label": "Paid Agent",
            "kind": "model_call",
            "tool": None,
            "mcp_tool": None,
            "model_call": {"provider": "openai", "model": "gpt-4o", "paid": True, "budget": None},
            "human_gate": None,
            "consensus": None,
            "risk": {
                "level": "high",
                "score": 0.8,
                "signals": ["paid_call"],
                "rationale": None,
                "source": "heuristic",
            },
            "capabilities": [],
            "side_effects": [
                {"kind": "paid_call", "target": None, "paid": True, "confidence": 1.0}
            ],
            "budget": None,
            "audit_boundary": None,
            "replay_marker": None,
            "trust_annotation": None,
            "privileged": False,
            "write_path": None,
            "eval_metadata": {},
            "metadata": {},
        }
    )
    return data


@pytest.fixture
def hitl_removed_ir_data(native_minimal_ir_data) -> dict:
    import copy

    data = copy.deepcopy(native_minimal_ir_data)
    data["id"] = "wf-hitl-removed"
    data["risk"] = {
        "level": "high",
        "score": 0.7,
        "signals": ["high_risk"],
        "rationale": None,
        "source": "heuristic",
    }
    data["nodes"].append(
        {
            "id": "write-node",
            "label": "Write File",
            "kind": "tool",
            "tool": {"name": "write_file", "namespace": "fs", "pinned": False, "capabilities": []},
            "mcp_tool": None,
            "model_call": None,
            "human_gate": None,  # No HITL - regression!
            "consensus": None,
            "risk": {
                "level": "high",
                "score": 0.7,
                "signals": ["file_write"],
                "rationale": None,
                "source": "heuristic",
            },
            "capabilities": [],
            "side_effects": [
                {
                    "kind": "write",
                    "target": "workspace://output.txt",
                    "paid": False,
                    "confidence": 1.0,
                }
            ],
            "budget": None,
            "audit_boundary": None,
            "replay_marker": None,
            "trust_annotation": None,
            "privileged": False,
            "write_path": "output.txt",
            "eval_metadata": {},
            "metadata": {},
        }
    )
    return data


@pytest.fixture
def tmp_ir_file(tmp_path, native_minimal_ir_data) -> Path:
    p = tmp_path / "test.ir.json"
    p.write_text(json.dumps(native_minimal_ir_data))
    return p


@pytest.fixture
def tmp_ir_file_b(tmp_path, modified_ir_data) -> Path:
    p = tmp_path / "test-b.ir.json"
    p.write_text(json.dumps(modified_ir_data))
    return p


@pytest.fixture
def tmp_paid_ir_file(tmp_path, paid_ir_data) -> Path:
    p = tmp_path / "test-paid.ir.json"
    p.write_text(json.dumps(paid_ir_data))
    return p


@pytest.fixture
def tmp_hitl_removed_ir_file(tmp_path, hitl_removed_ir_data) -> Path:
    p = tmp_path / "test-hitl-removed.ir.json"
    p.write_text(json.dumps(hitl_removed_ir_data))
    return p
