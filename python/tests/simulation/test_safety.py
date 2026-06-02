"""Safety regression tests for the Action Simulator.

Verifies that the simulation package contains zero execution/network primitives.
These tests are structural (grep-based) and must never be removed.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_SIM_SRC = Path(__file__).parent.parent.parent / "src" / "agent_runtime_cockpit" / "simulation"

_FORBIDDEN = [
    r"\bsubprocess\b",
    r"\bsocket\b",
    r"\baiohttp\b",
    r"\brequests\b",
    r"\bhttpx\b",
    r"\bos\.system\b",
    r"\bPopen\b",
    r"\burlopen\b",
    r"\bos\.popen\b",
    r"\beval\(",  # eval() call — not the word "eval" which appears in variable names
    r"\bexec\(",  # exec() call — not keyword in "execute"
]


def _source_files() -> list[Path]:
    return list(_SIM_SRC.glob("**/*.py"))


@pytest.mark.parametrize("pattern", _FORBIDDEN)
def test_no_forbidden_primitive(pattern):
    """No simulation source file may import or reference execution primitives."""
    compiled = re.compile(pattern)
    violations = []
    for f in _source_files():
        for i, line in enumerate(f.read_text().splitlines(), 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if compiled.search(line):
                violations.append(f"{f.name}:{i}: {line.rstrip()}")
    assert not violations, f"Forbidden pattern '{pattern}' found:\n" + "\n".join(violations)


def test_would_execute_always_false():
    """SimulatedToolCall.would_execute must default to False and never be set True."""
    from agent_runtime_cockpit.simulation.models import SimulatedToolCall

    tc = SimulatedToolCall(id="tc-1", node_id="n1", tool_name="x")
    assert tc.would_execute is False


def test_simulator_has_no_network_imports():
    """simulator.py must not import any network library."""
    simulator_src = (_SIM_SRC / "simulator.py").read_text()
    for lib in ("requests", "httpx", "aiohttp", "urllib", "socket"):
        assert lib not in simulator_src, f"Network import '{lib}' found in simulator.py"


def test_simulation_report_is_pure_data():
    """SimulationReport must be a Pydantic model with no custom executable methods."""
    from agent_runtime_cockpit.simulation.models import SimulationReport
    import inspect

    # Pydantic v2 adds these — all safe
    pydantic_ok = {
        "model_dump",
        "model_dump_json",
        "model_validate",
        "model_validate_json",
        "model_copy",
        "model_rebuild",
        "model_post_init",
        "model_construct",
        "copy",
        "dict",
        "json",  # Pydantic v1 compat shims
    }
    custom_methods = [
        name
        for name, _ in inspect.getmembers(SimulationReport, predicate=inspect.isfunction)
        if not name.startswith("_") and name not in pydantic_ok
    ]
    assert custom_methods == [], f"Unexpected methods on SimulationReport: {custom_methods}"
