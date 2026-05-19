# ARC Studio — Current SwarmGraph Implementation Audit

**Date:** 2026-05-19
**Analyst:** Agent Re-orientation Phase A

---

## ARC SwarmGraph Files Found

Only **one file** in the entire ARC Python runtime:

```
python/src/agent_runtime_cockpit/adapters/swarmgraph.py (596 lines)
```

Marked `DEPRECATED` at top:
> "Prefer `adapters.swarmgraph.runner.SwarmGraphRunner` for new code."

But **`adapters/swarmgraph/runner.py` does not exist**.

No other SwarmGraph-related files exist anywhere in ARC Python source.

---

## Capability Claims vs Reality

Current adapter in `adapters/swarmgraph.py:119-129`:

| Flag | Claimed | Reality |
|---|---|---|
| `can_inspect` | True | Project detection harness works (heuristic file scan) |
| `can_run` | True | Subprocess-based CLI exec only |
| `can_trace` | False | Correct — no SwarmGraph runtime to trace |
| `can_replay` | False | Correct — no journal/event state |
| `can_export_schema` | True | AST-based heuristic only |
| `can_export_workflow` | True | Heuristic AST scan + fixture fallback |
| `can_stream_events` | False | Correct — no event producer |
| `can_audit` | False | Correct — no audit material written |

---

## What ARC Actually Has

1. **Project detection** — scan for `swarmgraph.yaml`, `swarmgraph.yml`, `swarmgraph.toml`, imports in `.py` files
2. **CLI resolution** — `_resolve_cli()` finds external `arc-swarmgraph-cli` binary
3. **Heuristic workflow scan** — AST-based class/function/import extraction
4. **Subprocess execution** — runs external CLI via subprocess with env filtering
5. **Fixture fallback** — returns sample workflow data if scan fails
6. **Detection signals** — weighted filename/import heuristics (0.1-0.9)
7. **Env filtering** — allowlists system vars + `ARC_SWARMGRAPH_*` prefix

---

## What ARC Does NOT Have

| Feature | Status | Original SwarmGraph Has It? |
|---|---|---|
| Pydantic strict runtime models | ❌ Missing | Yes |
| Queen/worker graph topology | ❌ Missing | Yes |
| Graph execution (build_swarm_graph) | ❌ Missing | Yes |
| Consensus (majority/raft/bft/gossip) | ❌ Missing | Yes |
| HITL approval node | ❌ Missing | Yes |
| Audit chain integration | ❌ Missing | Yes |
| Event streaming | ❌ Missing | Partial |
| Checkpoint/replay | ❌ Missing | Yes |
| State management | ❌ Missing | Yes |
| LLM dispatch (fake/real) | ❌ Missing | Yes |
| Budget/cost events | ❌ Missing | Partial |
| Native runner (SwarmGraphRunner) | ❌ Missing | Referenced but absent |
| Topology event emission | ❌ Missing | Yes |
| Judge node | ❌ Missing | Yes |
| Router node | ❌ Missing | Yes |
| Worker node | ❌ Missing | Yes |
| Queen node | ❌ Missing | Yes |
| Memory management | ❌ Missing | Yes |
| Anti-drift | ❌ Missing | Yes |
| Approval node | ❌ Missing | Yes |
| Scaling logic | ❌ Missing | Yes |

---

## Incorrect Doc Claims

### `docs/LOCKED_REMAINING_ROADMAP.md`
> "Standalone SwarmGraph internal topology/consensus capture | **Done**"

**Verdict: FALSE.** ARC has tests for consuming topology events from external adapters, NOT a standalone SwarmGraph runtime that produces them.

Correct status should be:
- "SwarmGraph ad-hoc event consumption tests | Baseline Complete"
- "Full SwarmGraph-native runtime integration | Not Started"

### Producer Inventory
> "SwarmGraph topology | Baseline Complete for first producer"

**Partially correct** — external `langgraph+swarmgraph` path can emit events. ARC's **own SwarmGraph runtime** cannot.

> "Consensus/vote events | Baseline Complete for first producer"

**Same issue** — external only, not ARC-native SwarmGraph.

### `docs/LOCKED_PHASE_IMPLEMENTATION_PLAN.md`
> "Phase 16 | all 6 Active Work Ledger items implemented"

**"Standalone SwarmGraph internal topology/consensus capture" was marked Done but is Not Started.**

### Deferred Ledger
> "Standalone SwarmGraph internal topology/consensus capture | **Done** — Topology/consensus event consumption tests"

**Misleading.** Test infrastructure exists. SwarmGraph-native runtime does not. Should be:
- "SwarmGraph adapter event consumption tests | Baseline Complete"
- "Full SwarmGraph-native runtime | Not Started"

---

## Summary

ARC currently has:
- A **thin adapter harness** that can detect and invoke external SwarmGraph CLI
- **Tests** that consume topology/consensus events from that adapter
- **No native SwarmGraph runtime** whatsoever

The claim of "Done" for standalone SwarmGraph internal capture was a dangerous overclaim that needs immediate correction.
