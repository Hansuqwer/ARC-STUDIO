#!/usr/bin/env python3
"""Generate Q10 priority run-event fixtures (arc-v2 Sprint-7 prep).

Authoring rule (checkpoint #1, decision 4): fixtures are authored *daemon-side* —
every fixture is validated against the canonical registry validator
(`agent_runtime_cockpit.protocol.events.validate_event_data`) and the canonical
Pydantic model (`RunEvent.model_validate`) before it is written. Nothing is
invented free-hand.

Outputs (all additive; existing fixtures are never touched):
  protocol/fixtures/run-event/<kind>.json          per-instance fixtures for the
                                                   uncovered priority kinds
  protocol/fixtures/run-event-seq/<scenario>/NNN-<TYPE>.json
                                                   ordered, gap-free sequences for
                                                   the replay scrubber (blocking
                                                   issue #8; naming per brief §5.6)

Run from repo root:  PYTHONPATH=python/src python3 scripts/generate-priority-fixtures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from agent_runtime_cockpit.protocol.events import (  # noqa: E402
    EVENT_TYPES,
    RunEvent,
    validate_event_data,
)

ROOT = Path(__file__).resolve().parent.parent
RUN_EVENT_DIR = ROOT / "protocol" / "fixtures" / "run-event"
SEQ_DIR = ROOT / "protocol" / "fixtures" / "run-event-seq"

RUN_ID = "01HV7B3S0K9N3W2Q5J4Y8A6C2P"  # same ULID family as existing fixtures
TS_BASE = "2026-05-22T10:{m:02d}:{s:02d}.{ms:03d}Z"


def ts(minute: int, second: int, ms: int = 0) -> str:
    return TS_BASE.format(m=minute, s=second, ms=ms)


def event(kind: str, sequence: int, timestamp: str, data: dict) -> dict:
    """Build + validate one event against the canonical registry/model."""
    errors = validate_event_data(kind, data)
    if errors:
        sys.exit(f"REFUSING to write invalid fixture {kind}: {errors}")
    ev = {
        "schema_version": EVENT_TYPES[kind].version,
        "type": kind,
        "timestamp": timestamp,
        "run_id": RUN_ID,
        "sequence": sequence,
        "data": data,
    }
    RunEvent.model_validate(ev)  # canonical model must accept it
    return ev


# ---------------------------------------------------------------------------
# 1) Per-instance fixtures for uncovered priority kinds (Q10 families
#    + STEP_STARTED and HANDOFF, which sit in the same Runs-timeline path).
# ---------------------------------------------------------------------------

PER_INSTANCE: dict[str, dict] = {
    # --- TOOL_CALL family -------------------------------------------------
    "TOOL_CALL": {
        "tool_call_id": "call_9f2c1a",
        "tool_name": "read_file",
        "node_id": "node-tooluse-1",
    },
    "TOOL_CALL_START": {
        "tool_call_id": "call_9f2c1a",
        "tool_name": "read_file",
        "message_id": "msg_044",
    },
    "TOOL_CALL_ARGS": {
        "tool_call_id": "call_9f2c1a",
        "delta": "{\"path\": \"src/main.rs\"",
    },
    "TOOL_CALL_END": {
        "tool_call_id": "call_9f2c1a",
    },
    "TOOL_CALL_RESULT": {
        "tool_call_id": "call_9f2c1a",
        "result": "fn main() { println!(\"hello\"); }\n",
    },
    "TOOL_CALL_ERROR": {
        "tool_call_id": "call_b7e004",
        "error": "ENOENT: no such file or directory: src/missing.rs",
    },
    "TOOL_END": {
        "tool_name": "read_file",
        "result": "1 file read, 34 bytes",
    },
    # --- MESSAGE / TEXT_MESSAGE family -------------------------------------
    "MESSAGE": {
        "text": "I will read the entrypoint first, then propose the patch.",
        "source": "assistant",
        "message_id": "msg_044",
    },
    "MESSAGE_CHUNK": {
        "text": "…then propose",
        "message_id": "msg_044",
        "source": "assistant",
    },
    "TEXT_MESSAGE_START": {
        "message_id": "msg_045",
        "role": "assistant",
    },
    "TEXT_MESSAGE_CONTENT": {
        "message_id": "msg_045",
        "delta": "Reading src/main.rs to locate the entrypoint",
    },
    "TEXT_MESSAGE_END": {
        "message_id": "msg_045",
    },
    "TEXT_MESSAGE_CHUNK": {
        "delta": "Reading src/",
        "role": "assistant",
        "message_id": "msg_045",
    },
    # --- STATE_SNAPSHOT -----------------------------------------------------
    "STATE_SNAPSHOT": {
        "state": {
            "phase": "tool-use",
            "open_tool_calls": 1,
            "messages": 12,
            "budget_used_usd": 0.0421,
        },
        "node_id": "node-tooluse-1",
        "redacted": False,
    },
    # --- security denial family (deterministic gates; render in Event Stream
    #     + Runs panels; never produced by an LLM) ---------------------------
    "TRUST_DENIED": {
        "action": "run.start",
        "reason": "Workspace not found in external trust database",
        "trust_level": "untrusted",
        "workspace_path": "/home/user/untrusted-project",
        "remediation": "Run 'arc workspace trust' to approve this workspace.",
    },
    "PAID_CALL_DENIED": {
        "action": "provider.chat",
        "profile_id": "default",
        "reason": "allow_paid_calls is false for this profile",
        "provider": "anthropic",
        "model": "claude-sonnet",
        "allow_paid_calls": False,
        "remediation": "Enable paid calls in Settings > Provider budget gates.",
    },
    "SHELL_DENIED": {
        "action": "tool.shell",
        "profile_id": "default",
        "reason": "allow_shell is false for this profile",
        "command": "rm -rf build/",
        "allow_shell": False,
        "remediation": "Grant shell capability for this workspace (deny-by-default).",
    },
    "NETWORK_DENIED": {
        "action": "tool.fetch",
        "profile_id": "default",
        "reason": "allow_network is false for this profile",
        "url": "https://example.com/api",
        "allow_network": False,
        "remediation": "Grant network capability with a host allowlist.",
    },
    "PERMISSION_DENIED": {
        "action": "fs.write",
        "permission_type": "filesystem",
        "reason": "Path is outside the granted scope ${workspace}/docs",
        "context": {"requested_path": "/etc/hosts", "granted_scope": "${workspace}/docs"},
        "remediation": "Request a wider fs.write grant; denials are audited.",
    },
    # --- runs-timeline stragglers in the same panels ------------------------
    "STEP_STARTED": {
        "step_id": "step-3",
        "step_name": "apply-patch",
        "step_type": "mutation",
    },
    "HANDOFF": {
        "from_agent": "planner",
        "to_agent": "editor",
    },
}


def write_per_instance() -> list[str]:
    written = []
    seq = 200  # well clear of existing fixture sequence numbers
    for i, (kind, data) in enumerate(sorted(PER_INSTANCE.items())):
        path = RUN_EVENT_DIR / f"{kind.lower().replace('_', '-')}.json"
        if path.exists():
            sys.exit(f"REFUSING to overwrite existing fixture: {path} (additive rule)")
        ev = event(kind, seq + i, ts(16, i % 60), data)
        path.write_text(json.dumps(ev, indent=2) + "\n")
        written.append(path.name)
    return written


# ---------------------------------------------------------------------------
# 2) Ordered scenario for the replay scrubber: one coherent run, contiguous
#    sequence numbers, naming NNN-<TYPE>.json (brief §5.6).
#    Scenario "tool-use-streaming": run -> agent -> streamed tool call ->
#    streamed assistant message -> state snapshot -> denial -> HITL -> end.
# ---------------------------------------------------------------------------


def scenario_tool_use_streaming() -> list[dict]:
    s = 0
    out = []

    def nxt(kind: str, minute: int, second: int, ms: int, data: dict) -> None:
        nonlocal s
        s += 1
        out.append(event(kind, s, ts(minute, second, ms), data))

    nxt("RUN_STARTED", 20, 0, 0, {"workflow_id": "wf-demo-replay", "runtime": "swarmgraph"})
    nxt("AGENT_START", 20, 0, 250, {"agent_name": "planner", "instructions": "Read entrypoint, propose patch"})
    nxt("TEXT_MESSAGE_START", 20, 1, 0, {"message_id": "msg_100", "role": "assistant"})
    nxt("TEXT_MESSAGE_CONTENT", 20, 1, 120, {"message_id": "msg_100", "delta": "Reading the entrypoint "})
    nxt("TEXT_MESSAGE_CONTENT", 20, 1, 240, {"message_id": "msg_100", "delta": "before proposing changes."})
    nxt("TEXT_MESSAGE_END", 20, 1, 360, {"message_id": "msg_100"})
    nxt("TOOL_CALL_START", 20, 2, 0, {"tool_call_id": "call_seq01", "tool_name": "read_file", "message_id": "msg_100"})
    nxt("TOOL_CALL_ARGS", 20, 2, 80, {"tool_call_id": "call_seq01", "delta": "{\"path\": \"src/"})
    nxt("TOOL_CALL_ARGS", 20, 2, 160, {"tool_call_id": "call_seq01", "delta": "main.rs\"}"})
    nxt("TOOL_CALL_END", 20, 2, 240, {"tool_call_id": "call_seq01"})
    nxt("TOOL_CALL_RESULT", 20, 2, 400, {"tool_call_id": "call_seq01", "result": "fn main() { run() }\n"})
    nxt("STATE_SNAPSHOT", 20, 3, 0, {"state": {"phase": "review", "open_tool_calls": 0, "messages": 2}, "redacted": False})
    nxt("SHELL_DENIED", 20, 4, 0, {
        "action": "tool.shell", "profile_id": "default",
        "reason": "allow_shell is false for this profile",
        "command": "cargo build", "allow_shell": False,
        "remediation": "Grant shell capability for this workspace (deny-by-default).",
    })
    nxt("HITL_PROMPT", 20, 5, 0, {
        "hitl_id": "hitl_seq_001", "step_id": "approval-gate",
        "prompt_text": "Planner requests shell access to run cargo build. Approve?",
        "options": ["approve", "reject"], "timeout_seconds": 120,
    })
    nxt("HITL_RESPONSE", 20, 5, 300, {
        "hitl_id": "hitl_seq_001",
        "decision": "reject",
        "operator_id": "user@example.com",
        "responded_at": ts(20, 5, 300),
    })
    nxt("HANDOFF", 20, 6, 0, {"from_agent": "planner", "to_agent": "editor"})
    nxt("AGENT_END", 20, 7, 0, {"agent_name": "planner", "output": "Patch proposed without build verification (shell denied)."})
    nxt("RUN_COMPLETED", 20, 7, 500, {"duration_ms": 420_500.0, "output": "1 proposal ready for review"})
    return out


def write_scenario(name: str, events: list[dict]) -> int:
    d = SEQ_DIR / name
    d.mkdir(parents=True, exist_ok=True)
    # gap-free check before writing — ordered streams must not have gaps at rest
    seqs = [e["sequence"] for e in events]
    if seqs != list(range(seqs[0], seqs[0] + len(seqs))):
        sys.exit(f"scenario {name}: sequence not contiguous: {seqs}")
    for e in events:
        path = d / f"{e['sequence']:03d}-{e['type']}.json"
        if path.exists():
            sys.exit(f"REFUSING to overwrite: {path}")
        path.write_text(json.dumps(e, indent=2) + "\n")
    return len(events)


def main() -> None:
    hitl_missing = [k for k in PER_INSTANCE if k not in EVENT_TYPES]
    if hitl_missing:
        sys.exit(f"kinds not in registry: {hitl_missing}")
    written = write_per_instance()
    n = write_scenario("tool-use-streaming", scenario_tool_use_streaming())
    print(f"per-instance fixtures written: {len(written)}")
    for w in written:
        print(f"  run-event/{w}")
    print(f"scenario tool-use-streaming: {n} ordered events (gap-free)")


if __name__ == "__main__":
    main()
