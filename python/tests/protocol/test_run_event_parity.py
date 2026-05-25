"""Protocol parity tests: verify TS and Python run-event type alignment.

These tests ensure that the core TypedRunEvent types in TypeScript (run-events.ts)
and Python (typed_events.py) remain aligned. Battle events are Python-only by design
(Phase 34 ARC Battle Mode).
"""

import re
from pathlib import Path

import pytest


# Core event types that MUST exist in both TS and Python
CORE_EVENT_TYPES = {
    "RUN_STARTED",
    "RUN_COMPLETED",
    "RUN_FAILED",
    "RUN_CANCELLED",
    "STEP_STARTED",
    "STEP_COMPLETED",
    "STEP_FAILED",
    "TOOL_CALL",
    "TOOL_CALL_START",
    "TOOL_CALL_RESULT",
    "TOOL_CALL_ERROR",
    "HITL_PROMPT",
    "HITL_RESPONSE",
    "HITL_TIMEOUT",
    "SWARMGRAPH_TOPOLOGY",
    "SWARMGRAPH_CONSENSUS",
    "SWARMGRAPH_COST",
    "MESSAGE",
    "NODE_STARTED",
    "NODE_FAILED",
    "POLICY_BYPASS_WARNING",
    "RAW",
}

# Python-only event types (ARC Battle Mode - Phase 34)
PYTHON_ONLY_EVENT_TYPES = {
    "BATTLE_STARTED",
    "BATTLE_CANDIDATE_READY",
    "BATTLE_VOTE_COMMITTED",
    "BATTLE_VOTE_REVEALED",
    "BATTLE_CONSENSUS_REACHED",
    "BATTLE_HITL_REQUIRED",
    "BATTLE_COMPLETED",
}


def _extract_ts_event_types() -> set[str]:
    """Extract event type literals from run-events.ts interface definitions."""
    ts_file = (
        Path(__file__).parent.parent.parent.parent
        / "packages"
        / "arc-protocol-ts"
        / "src"
        / "run-events.ts"
    )
    if not ts_file.exists():
        pytest.skip(f"TS protocol file not found: {ts_file}")

    content = ts_file.read_text()

    # Extract type literals directly from interface definitions (e.g., type: 'RUN_STARTED')
    type_literals = re.findall(r"type:\s*'([A-Z_]+)'", content)

    return set(type_literals)


def _extract_py_event_types() -> set[str]:
    """Extract event type literals from typed_events.py KnownRunEvent union."""
    from agent_runtime_cockpit.protocol.typed_events import KnownRunEvent, UnknownEvent
    from typing import get_args

    known_types = get_args(KnownRunEvent)

    event_types = set()
    for event_cls in known_types:
        if event_cls is UnknownEvent:
            continue

        # Get the type literal from the class
        type_field = event_cls.model_fields.get("type")
        if type_field and hasattr(type_field, "annotation"):
            # Extract Literal value
            annotation = type_field.annotation
            if hasattr(annotation, "__args__"):
                for arg in annotation.__args__:
                    if isinstance(arg, str):
                        event_types.add(arg)

    return event_types


def test_core_event_types_exist_in_python():
    """Verify all core event types exist in Python KnownRunEvent."""
    py_types = _extract_py_event_types()

    missing = CORE_EVENT_TYPES - py_types
    assert not missing, f"Python missing core event types: {missing}"


def test_core_event_types_exist_in_typescript():
    """Verify all core event types exist in TypeScript KnownRunEvent."""
    ts_types = _extract_ts_event_types()

    missing = CORE_EVENT_TYPES - ts_types
    assert not missing, f"TypeScript missing core event types: {missing}"


def test_python_has_battle_events():
    """Verify Python has Battle events (Phase 34 ARC Battle Mode)."""
    py_types = _extract_py_event_types()

    missing = PYTHON_ONLY_EVENT_TYPES - py_types
    assert not missing, f"Python missing Battle events: {missing}"


def test_typescript_does_not_have_battle_events():
    """Verify TypeScript does NOT have Battle events (Python-only for now)."""
    ts_types = _extract_ts_event_types()

    present = PYTHON_ONLY_EVENT_TYPES & ts_types
    assert not present, f"TypeScript should not have Battle events yet: {present}"


def test_parity_summary():
    """Print parity summary for debugging."""
    ts_types = _extract_ts_event_types()
    py_types = _extract_py_event_types()

    core_in_both = CORE_EVENT_TYPES & ts_types & py_types
    ts_only = ts_types - CORE_EVENT_TYPES - PYTHON_ONLY_EVENT_TYPES
    py_only = py_types - CORE_EVENT_TYPES - PYTHON_ONLY_EVENT_TYPES

    print("\n=== Protocol Parity Summary ===")
    print(f"Core events in both: {len(core_in_both)}/{len(CORE_EVENT_TYPES)}")
    print(f"TypeScript-only: {ts_only or 'none'}")
    print(f"Python-only (expected): {PYTHON_ONLY_EVENT_TYPES & py_types}")
    print(f"Python-only (unexpected): {py_only - PYTHON_ONLY_EVENT_TYPES}")

    assert len(core_in_both) == len(CORE_EVENT_TYPES), "Not all core events are aligned"
