# SwarmGraph Gap Analysis + Implementation Plan

**Date:** 2026-05-19

---

## Gap Table

| Category | Original SwarmGraph | ARC Current | Gap | Priority |
|---|---|---|---|---|
| Pydantic strict models | Full (AgentSpec, SwarmState, Vote, etc.) | None | ❌ Missing | P1 |
| Queen/worker graph | `build_swarm_graph()`, queen.py, worker.py | None | ❌ Missing | P1 |
| Consensus (majority) | `majority_consensus`, `run_consensus` | None | ❌ Missing | P1 |
| LLM dispatch (fake stub) | dispatch.py (stub/mock backends) | None | ❌ Missing | P1 |
| Graph topology events | Emitted during execution | Tests consume events | ❌ No producer | P1 |
| State management | `SwarmState`, `SwarmCheckpoint` | None | ❌ Missing | P1 |
| Event emission hooks | During execution lifecycle | Tests consume events | ❌ No producer | P1 |
| Runner entry point | `SwarmGraphRunner` referenced | Referenced, absent | ❌ Missing | P1 |
| HITL hooks | `approval.py`, single-use tokens | External CLI HITL only | ❌ Missing | P2 |
| Audit chain | `audit.py` (HMAC-SHA256) | External audit CLI | ❌ Missing | P2 |
| Budget/cost events | During execution | BudgetVector exists separately | ⚠️ Partial | P2 |
| Checkpoint/replay | `checkpointing.py`, stores | `arc runs fork` exists | ⚠️ Not wired | P2 |
| Adapter bridge | — | `adapters/swarmgraph.py` | ⚠️ Deprecated, needs rewrite | P2 |
| Consensus (raft/bft/gossip) | Full implementation | None | ❌ Defer | P3 |
| Judge/Evaluation | `judge.py` | None | ❌ Missing | P3 |
| Memory | `SwarmMemory` | None | ❌ Missing | P3 |
| Anti-drift | Embedding similarity | None | ❌ Missing | P3 |
| S3 audit backend | `audit_backends.py` | None | ❌ Not needed | Defer |
| Textual dashboard | TUI | None | ❌ Not needed | Defer |
| Provider gateway | Standalone product | Uses ARC providers | ❌ Not needed | Defer |
| Encrypted vault | Fernet key store | Keychain refs | ❌ Not needed | Defer |
| Semantic cache | SQLite | None | ❌ Not needed | Defer |

---

## Recommended Architecture

New package: `python/src/agent_runtime_cockpit/swarmgraph/`

```
swarmgraph/
  __init__.py          # Public API
  config.py            # SwarmGraphConfig (Pydantic strict)
  models.py            # AgentSpec, AgentState, Vote, Task, etc.
  state.py             # SwarmState, Checkpoint
  graph.py             # Graph construction (queen/worker topology)
  nodes/               # Execution nodes
    __init__.py
    queen.py           # Task decomposition, dispatch
    worker.py          # Task execution
    consensus.py       # Vote aggregation
    approval.py        # HITL gate
  consensus.py         # Consensus logic (majority, quorum)
  runner.py            # SwarmGraphRunner (main entry point)
  events.py            # Event emission (topology, cost, audit)
  audit.py             # Audit chain integration
  budget.py            # Budget enforcement integration
  hitl.py              # HITL prompt integration
  replay.py            # Checkpoint/fork integration
  fixtures.py          # Deterministic fake/offline fixtures
```

---

## Implementation Order

### P1 — SwarmGraph Native Core (NOW)

1. `config.py` — SwarmGraphConfig with all settings
2. `models.py` — All Pydantic strict models
3. `state.py` — SwarmState, SwarmCheckpoint
4. `consensus.py` — majority_consensus, quorum
5. `nodes/queen.py` — Task decomposition logic
6. `nodes/worker.py` — Task execution logic
7. `nodes/consensus.py` — Consensus aggregation node
8. `graph.py` — Graph construction
9. `runner.py` — Main SwarmGraphRunner
10. `events.py` — Event emission
11. Tests for all of the above

### P2 — Adapter Bridge + Default Runtime

1. Rewrite `adapters/swarmgraph.py` → use `swarmgraph.runner.SwarmGraphRunner`
2. Wire budget enforcement
3. Wire audit chain
4. Wire HITL
5. Make SwarmGraph default runtime
6. Update capability flags to honest values

### P3 — CLI Chat REPL

1. `cli/chat_repl.py`
2. `cli/slash_commands.py`
3. `cli/session.py`
4. `packages/arc-studio-cli/`

### P4 — IDE Alignment

1. ChatTab defaults
2. Runtime selector
3. SwarmGraphInsightTab consumes native events

### P5 — Docs Fix

1. Correct overclaims
2. Refresh evidence
3. Verification + commit

---

## Key Design Decisions

1. **No LangGraph dependency** — SwarmGraph-native runtime is pure Python + Pydantic. LangGraph is an optional integration path, not a requirement for the core runtime.
2. **Fake/offline first** — Default mode is deterministic without any provider/LLM calls. Workers produce canned responses.
3. **Provider-backed mode is gated** — Existing ARC provider gates apply.
4. **Audit chain reuses original pattern** — HMAC-SHA256 + hash chain from `swarm-shared`, ported to ARC-native code.
5. **Rich for CLI** — Not Textual. Uses `rich` for formatting.
6. **Default runtime** — SwarmGraph is the default. All other adapters are secondary.

---

## Tests To Add

| File | Content |
|---|---|
| `tests/test_swarmgraph_native_config.py` | Config validation, defaults, serialization |
| `tests/test_swarmgraph_native_models.py` | Model constraints, frozen, strict mode |
| `tests/test_swarmgraph_native_state.py` | State transitions, checkpoints |
| `tests/test_swarmgraph_native_consensus.py` | Majority consensus, quorum, edge cases |
| `tests/test_swarmgraph_native_graph.py` | Graph construction, node wiring |
| `tests/test_swarmgraph_native_runner.py` | Full run lifecycle (fake mode) |
| `tests/test_swarmgraph_native_events.py` | Event emission and topology |
| `tests/test_swarmgraph_native_replay.py` | Checkpoint/fork integrity |
| `tests/test_swarmgraph_native_budget.py` | Budget enforcement in runtime |

---

## Risks and Blockers

- **Risk: Scope creep** — P1 must deliver a *minimum complete* runtime, not the full original surface.
- **Risk: Overclaiming parity** — Must not claim parity with original SwarmGraph until all core features are implemented and tested.
- **Risk: Dead code** — Old `adapters/swarmgraph.py` marked DEPRECATED but no replacement exists. Must bridge carefully.
- **Blocker: No LangGraph dep** — If SwarmGraph must be LangGraph-free, we cannot use LangGraph's `StateGraph`. Pure Python is fine for P1.
- **Risk: UI overclaim** — IDE must not claim SwarmGraph-native graph rendering until the runtime emits real topology events.
