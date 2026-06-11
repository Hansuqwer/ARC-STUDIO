#!/usr/bin/env python3
"""Tranche-2 run-event fixtures: the 31 kinds left after the Q10 tranche.

Same hard rules as scripts/generate-priority-fixtures.py: every fixture must
pass the canonical registry validator AND the canonical Pydantic model before
being written; never overwrites; purely additive.

Covers: NODE_*, CONTRACT_*, EVIDENCE_REF_CREATED, POLICY_BYPASS_WARNING,
CONSENSUS_*, BATTLE_* (deferred surface, fixtures still wanted for decode
safety), CAPABILITY_CARD_DECISION, MCP_CALL_DECISION, EVAL_POLICY_*,
RAW, CUSTOM, QUOTA_WARNING, CONTEXT_COMPACTED, TOOL_OUTPUT_VIRTUALIZED,
MODEL_CHANGED, PRICING_FEED_REFRESHED, BUDGET_BROKER_SYNC,
OBSERVABILITY_EXPORT_STARTED.

Run from repo root: PYTHONPATH=python/src python3 scripts/generate-tranche2-fixtures.py
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
RUN_ID = "01HV7B3S0K9N3W2Q5J4Y8A6C2P"

FIXTURES: dict[str, dict] = {
    # ── SwarmGraph node lifecycle ─────────────────────────────────────────
    "NODE_STARTED": {"node_id": "node-planner-1"},
    "NODE_UPDATE": {"runtime": "swarmgraph", "status": "running", "node_id": "node-planner-1"},
    "NODE_FAILED": {"node_id": "node-planner-1", "error": "worker timeout after 120s"},
    # ── Contracts ─────────────────────────────────────────────────────────
    "CONTRACT_PROPOSED": {
        "contract": {
            "contract_id": "ct_5f1e02",
            "goal": "Refactor parser without changing public API",
            "acceptance_criteria": ["all existing tests pass", "no public symbol removed"],
        },
        "node_id": "node-planner-1",
    },
    "CONTRACT_ACCEPTED": {"contract_id": "ct_5f1e02"},
    "CONTRACT_FULFILLED": {"contract_id": "ct_5f1e02", "run_id": RUN_ID},
    # ── Evidence / policy ─────────────────────────────────────────────────
    "EVIDENCE_REF_CREATED": {
        "evidence_ref": {
            "ref_id": "ev_88a1",
            "kind": "test-output",
            "uri": "arc-evidence://runs/01HV7B3S0K9N3W2Q5J4Y8A6C2P/ev_88a1",
        }
    },
    "POLICY_BYPASS_WARNING": {
        "policy_id": "paid-call-gate",
        "bypass_reason": "ARC_ALLOW_PAID_CALLS=1 env override active",
        "suggested_remediation": "Unset the override; use profile budget gates instead.",
        "surface": "env",
        "surface_identifier": "ARC_ALLOW_PAID_CALLS",
    },
    # ── Consensus ─────────────────────────────────────────────────────────
    "CONSENSUS_DIFFERENTIATOR": {
        "decision": "candidate_b",
        "protocol": "commit-reveal-majority",
        "votes": [
            {"worker_id": "w1", "candidate": "candidate_b"},
            {"worker_id": "w2", "candidate": "candidate_b"},
            {"worker_id": "w3", "candidate": "candidate_a"},
        ],
    },
    "CONSENSUS_EVAL": {"num_rounds": 3, "num_workers": 5, "protocols": ["majority", "commit-reveal-majority"]},
    "CONSENSUS_EVAL_RUN": {"consensus_reached": True, "protocol": "majority", "total_votes": 5},
    # ── Battle (deferred surface; fixtures for decode safety only) ───────
    "BATTLE_STARTED": {
        "battle_id": "bt_001",
        "consensus_protocol": "commit-reveal-majority",
        "prompt": "Implement the fastest correct JSON escaper",
        "topology": "star",
        "workers": ["w1", "w2", "w3"],
    },
    "BATTLE_CANDIDATE_READY": {"battle_id": "bt_001", "candidate_id": "cand_a", "model_id": "model-x", "worker_id": "w1"},
    "BATTLE_VOTE_COMMITTED": {"battle_id": "bt_001", "commit_hash": "9c1ffadb22", "vote_id": "v_01"},
    "BATTLE_VOTE_REVEALED": {"approved": True, "battle_id": "bt_001", "candidate_id": "cand_a", "vote_id": "v_01"},
    "BATTLE_CONSENSUS_REACHED": {"battle_id": "bt_001", "consensus_reached": True},
    "BATTLE_HITL_REQUIRED": {"battle_id": "bt_001", "candidates": ["cand_a", "cand_b"], "hitl_id": "hitl_bt_001"},
    "BATTLE_COMPLETED": {"battle_id": "bt_001", "status": "completed"},
    # ── Deterministic gate decisions (audit-adjacent panels) ─────────────
    "CAPABILITY_CARD_DECISION": {
        "action": "fs.write:${workspace}/src",
        "decision": "allow",
        "mode": "deterministic",
        "reason": "capability granted for this workspace by user on 2026-06-10",
    },
    "MCP_CALL_DECISION": {
        "decision": "deny",
        "policy": "deny-by-default",
        "reason": "tool not in per-workspace allowlist",
        "risk_level": "high",
        "server_id": "mcp-shell-server",
        "tool_name": "exec_command",
    },
    "EVAL_POLICY_RECOMMENDED": {
        "actions": ["raise paid-call cap to 5 USD", "enable consensus for risky merges"],
        "correlation_id": "corr_7d2",
        "profile_id": "default",
        "recommendations_count": 2,
    },
    "EVAL_POLICY_APPLIED": {
        "correlation_id": "corr_7d2",
        "diff_summary": "+paid_call_cap_usd: 5.0 (was 2.0)",
        "dry_run": False,
        "new_path": ".arc/profiles/default.yaml",
        "profile_id": "default",
        "version": 4,
    },
    # ── Escape hatches ────────────────────────────────────────────────────
    "RAW": {"raw": {"vendor": "langgraph", "payload": {"kind": "checkpoint", "step": 7}}, "source": "adapter"},
    "CUSTOM": {"custom_type": "vendor.langgraph.checkpoint", "data": {"step": 7}},
    # ── Budget / quota / context ──────────────────────────────────────────
    "QUOTA_WARNING": {"current": 8200, "dimension": "tokens_per_run", "limit": 10000, "usage_pct": 82.0},
    "CONTEXT_COMPACTED": {"messages_evicted_count": 14, "tokens_after": 6100, "tokens_before": 11800},
    "TOOL_OUTPUT_VIRTUALIZED": {
        "estimated_tokens_saved": 5400,
        "handle_uri": "arc-handle://runs/01HV7B3S0K9N3W2Q5J4Y8A6C2P/tool-out/3",
        "original_size_bytes": 262144,
        "tool_name": "read_file",
    },
    "MODEL_CHANGED": {"current_model": "model-y", "previous_model": "model-x"},
    "PRICING_FEED_REFRESHED": {
        "feed_hash": "sha256:1f6c…",
        "feed_url": "https://pricing.example.com/feed.json",
        "rows_seen": 128,
        "source": "remote",
    },
    "BUDGET_BROKER_SYNC": {
        "amount_usd": 0.42,
        "fell_back": False,
        "local_approved": True,
        "remote_approved": True,
        "scope": "run",
    },
    "OBSERVABILITY_EXPORT_STARTED": {"destination": "otlp://127.0.0.1:4317", "protocol": "otlp-grpc", "span_count": 311},
}


def main() -> None:
    unknown = [k for k in FIXTURES if k not in EVENT_TYPES]
    if unknown:
        sys.exit(f"kinds not in registry: {unknown}")
    written = 0
    for i, (kind, data) in enumerate(sorted(FIXTURES.items())):
        errors = validate_event_data(kind, data)
        if errors:
            sys.exit(f"REFUSING invalid fixture {kind}: {errors}")
        ev = {
            "schema_version": EVENT_TYPES[kind].version,
            "type": kind,
            "timestamp": f"2026-05-22T10:30:{i % 60:02d}.000Z",
            "run_id": RUN_ID,
            "sequence": 300 + i,
            "data": data,
        }
        RunEvent.model_validate(ev)
        path = RUN_EVENT_DIR / f"{kind.lower().replace('_', '-')}.json"
        if path.exists():
            sys.exit(f"REFUSING to overwrite: {path}")
        path.write_text(json.dumps(ev, indent=2) + "\n")
        written += 1
    print(f"tranche-2 fixtures written: {written}")


if __name__ == "__main__":
    main()
