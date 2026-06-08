"""Protocol parity tests: verify TS and Python run-event type alignment.

These tests ensure that the core TypedRunEvent types in TypeScript (run-events.ts)
and Python (typed_events.py) remain aligned. Battle events are Python-only by design
(Phase 34 ARC Battle Mode).
"""

import re
import json
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

# Python-only event types (ARC Battle Mode - Phase 34, Consensus Eval - Phase 81)
PYTHON_ONLY_EVENT_TYPES = {
    "BATTLE_STARTED",
    "BATTLE_CANDIDATE_READY",
    "BATTLE_VOTE_COMMITTED",
    "BATTLE_VOTE_REVEALED",
    "BATTLE_CONSENSUS_REACHED",
    "BATTLE_HITL_REQUIRED",
    "BATTLE_COMPLETED",
    "CONSENSUS_DIFFERENTIATOR",
    "CONSENSUS_EVAL",
    "CONSENSUS_EVAL_RUN",
}

# Registry events deliberately NOT given a dedicated TS interface in run-events.ts, each with the
# reason it is intentional follow-up debt rather than an omission (B2P-10). The IDE still receives
# them via the generic RawEvent/UnknownEvent path — they are neither invented nor dropped.
INTENTIONALLY_UNTYPED_TS_EVENTS: dict[str, str] = {
    "AGENT_START": "AG-UI streaming lifecycle event; consumed generically by the event stream, modeled in the AG-UI layer, not re-typed in run-events.ts.",
    "AGENT_END": "AG-UI streaming lifecycle event; consumed generically by the event stream, modeled in the AG-UI layer.",
    "TOOL_CALL_ARGS": "AG-UI tool-call streaming delta; rendered generically, not re-typed in run-events.ts.",
    "TOOL_CALL_END": "AG-UI tool-call streaming delta; rendered generically.",
    "TOOL_END": "AG-UI tool streaming delta; rendered generically.",
    "HANDOFF": "AG-UI agent-handoff streaming event; rendered generically.",
    "NODE_UPDATE": "AG-UI node-update streaming delta; rendered generically.",
    "MESSAGE_CHUNK": "Streaming message delta; coalesced into MESSAGE for display, no standalone TS interface.",
    "TEXT_MESSAGE_START": "AG-UI text-message streaming delta; coalesced into MESSAGE for display.",
    "TEXT_MESSAGE_CONTENT": "AG-UI text-message streaming delta; coalesced into MESSAGE for display.",
    "TEXT_MESSAGE_END": "AG-UI text-message streaming delta; coalesced into MESSAGE for display.",
    "TEXT_MESSAGE_CHUNK": "AG-UI text-message streaming delta; coalesced into MESSAGE for display.",
    "STATE_SNAPSHOT": "AG-UI state-snapshot streaming event; consumed generically by the event stream.",
    "CONTRACT_PROPOSED": "Auditability event; rendered from stored RunContract records, not the live typed run-event union.",
    "CONTRACT_ACCEPTED": "Auditability event; rendered from stored RunContract records.",
    "CONTRACT_FULFILLED": "Auditability event; rendered from stored RunContract records.",
    "CONTRACT_VIOLATED": "Auditability event; rendered from stored RunContract records.",
    "RECEIPT_GENERATED": "Auditability event; rendered from stored RunReceipt records.",
    "FAILURE_AUTOPSY_GENERATED": "Auditability event; rendered from stored FailureAutopsy records.",
    "EVIDENCE_REF_CREATED": "Auditability event; rendered from stored EvidenceRef records.",
    "CUSTOM": "Open-ended user/custom event with an arbitrary payload; intentionally untyped.",
}

# Back-compat: the parity assertions below operate on the set of untyped TS event types.
INTENTIONALLY_UNTYPED_TS_EVENT_TYPES = (
    set(INTENTIONALLY_UNTYPED_TS_EVENTS) | PYTHON_ONLY_EVENT_TYPES
)


def _repo_root() -> Path:
    return Path(__file__).parents[3]


def _registry_fixture() -> dict:
    return json.loads(
        (_repo_root() / "protocol" / "fixtures" / "run-event-registry.json").read_text()
    )


def _extract_ts_event_types() -> set[str]:
    """Extract event type literals from run-events.ts interface definitions."""
    ts_file = _repo_root() / "packages" / "arc-protocol-ts" / "src" / "run-events.ts"
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


def _python_registry_event_types() -> set[str]:
    from agent_runtime_cockpit.protocol.events import EVENT_TYPES

    return set(EVENT_TYPES)


def test_python_registry_matches_cross_language_fixture():
    """Fixture is the machine-readable evidence anchor for Python canonical events."""
    from agent_runtime_cockpit.protocol.events import EVENT_TYPES

    registry = _registry_fixture()
    fixture_entries = {entry["type"]: entry for entry in registry["eventTypes"]}

    assert set(fixture_entries) == set(EVENT_TYPES)
    for event_type, typedef in EVENT_TYPES.items():
        entry = fixture_entries[event_type]
        assert entry["version"] == typedef.version
        assert entry["requiredFields"] == sorted(typedef.required_fields)
        assert entry["optionalFields"] == sorted(typedef.optional_fields)


def test_typescript_known_and_intentionally_untyped_events_cover_registry():
    """New canonical events must be typed in TS or acknowledged as follow-up debt."""
    ts_types = _extract_ts_event_types()
    registry_types = {entry["type"] for entry in _registry_fixture()["eventTypes"]}

    assert ts_types | INTENTIONALLY_UNTYPED_TS_EVENT_TYPES == registry_types
    assert ts_types & INTENTIONALLY_UNTYPED_TS_EVENT_TYPES == set()


def test_every_intentionally_untyped_event_has_a_documented_rationale():
    """B2P-10: each TS-untyped registry event must carry an explicit rationale, so the debt is
    intentional and documented rather than a silent omission."""
    for event_type, rationale in INTENTIONALLY_UNTYPED_TS_EVENTS.items():
        assert isinstance(rationale, str) and len(rationale.strip()) >= 20, (
            f"{event_type} needs a documented rationale for being untyped in TS"
        )
    # No drift: every registry event not typed in TS (and not Python-only) must be documented here.
    ts_types = _extract_ts_event_types()
    registry_types = {entry["type"] for entry in _registry_fixture()["eventTypes"]}
    undocumented = (registry_types - ts_types - PYTHON_ONLY_EVENT_TYPES) - set(
        INTENTIONALLY_UNTYPED_TS_EVENTS
    )
    assert undocumented == set(), (
        f"registry events neither typed in TS nor documented as intentional debt: {sorted(undocumented)}"
    )


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
