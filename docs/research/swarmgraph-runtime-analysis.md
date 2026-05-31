# SwarmGraph Runtime Deep Analysis & Critical Review

**Date:** 2026-05-29
**Analyst:** DeepSeek V4 Pro
**Sources:** Full source read of 15 core files + adapter + CLI + supervisor + ADR-013 + test suite + CrewAI docs + AutoGen docs + Python asyncio docs

---

## Analysis Prompt (reusable)

```
Deeply analyze the SwarmGraph runtime at python/src/agent_runtime_cockpit/swarmgraph/. Read every file in the module (runner.py, config.py, models.py, state.py, graph.py, events.py, consensus.py, consensus_escrow.py, risk_assessment.py, adaptive_consensus.py, fixtures.py, nodes/*.py, __init__.py), the adapter at adapters/swarmgraph.py, the CLI at cli/swarmgraph.py, and the supervisor at orchestration/supervisor.py. Also read docs/adr/ADR-013-swarmgraph-architecture.md and docs/research/swarm-memory-graph.md.

Produce:
1. Architecture diagram (Queen/Worker/Consensus lifecycle, data flow)
2. Model inventory (all Pydantic models, their frozen/mutable status, key fields)
3. Consensus protocol comparison table (inputs, outputs, edge cases, complexity)
4. Risk assessment signal catalog (all keywords, weights, thresholds)
5. Code quality assessment (coupling, test coverage gaps, error handling, concurrency model)
6. Gap analysis vs ADR-013 commitments (fan-out gate, 13 failure modes, 6 consensus strategies, checkpoint resume, worker isolation)
7. Integration surface audit (what connects to what, event flow from runner → adapter → supervisor → store)
8. Improvement recommendations ranked by impact/effort
```

---

## 1. Architecture

### Lifecycle (SwarmGraphRunner.run)

```
prompt
  │
  ▼
queen_prepare_agents()          # Create N workers + 1 queen in SwarmState
  │
  ▼
queen_decompose(prompt)         # Split prompt into N tasks (trivial: copy/step-number)
  │
  ▼
build_swarm_graph(state)        # Build topology: star/chain/mesh/tree
  │
  ▼
  ┌──────────────────────────────────────────────────────┐
  │  FOR round_num in range(max_rounds):                │
  │    │                                                  │
  │    ▼                                                  │
  │  get_pending_tasks()                                  │
  │    │                                                  │
  │    ▼                                                  │
  │  queen_assign(tasks)          # Round-robin to idle agents │
  │    │                                                  │
  │    ▼                                                  │
  │  FOR each task:                                       │
  │    worker_execute(task, mode)  # SYNCHRONOUS, sequential │
  │    emit_worker_event()                                 │
  │    emit_budget_event() (if enabled)                    │
  │    │                                                  │
  │    ▼                                                  │
  │  process_worker_results()     # Map results → task.status │
  │    │                                                  │
  │    ▼                                                  │
  │  IF require_hitl:  require_hitl_approval(task)        │
  │  ELSE:              run_consensus_round_with_results()  │
  │                     emit_consensus_events()            │
  │    │                                                  │
  │    ▼                                                  │
  │  save_checkpoint()                                    │
  └──────────────────────────────────────────────────────┘
  │
  ▼
_build_result()        # Dict with swarm_id, status, rounds, tasks, events
```

### Data Flow

```
SwarmGraphRunner ←→ SwarmState (mutable, in-memory)
                ←→ events: list[SwarmGraphEvent] (appended during run)
                → _build_result() returns dict with event.to_dict()
                → SwarmGraphAdapter wraps in RunRecord with RunEvents
                → JobSupervisor persists via JsonlTraceStore
```

### Event Flow to External Systems

```
SwarmGraphRunner.events
  → SwarmGraphAdapter._map_swarmgraph_event()
    → RunEvent objects (NODE_COMPLETED, SWARMGRAPH_CONSENSUS, etc.)
      → RunRecord.events[]
        → JobSupervisor._emit_event() → EventBroker.publish()
          → SSE streams / JSONL persistence
```

---

## 2. Model Inventory

| Model | File | Frozen? | Key Fields | Lines |
|-------|------|---------|------------|-------|
| `SwarmGraphConfig` | config.py | **Yes** | num_workers, max_rounds, topology, strategy, execution_mode, consensus_protocol, require_hitl, enable_budget, budget_limit_usd, worker_timeout | 74 |
| `AgentSpec` | models.py | **Yes** | id, name, role, model, system_prompt, max_tasks, timeout_seconds | 70 |
| `AgentState` | models.py | **No** | agent_id, status, current_task_id, completed_tasks, error | 82 |
| `AgentVote` | models.py | **Yes** | agent_id, task_id, round, approved, confidence, reasoning | 93 |
| `ApprovalDecision` | models.py | **Yes** | approved, reason, token_id, decided_by | 103 |
| `WorkerResult` | models.py | **Yes** | worker_id, task_id, output, artifacts, error, duration, cost, tokens | 118 |
| `QueenDirective` | models.py | **Yes** | task_id, prompt, assigned_worker_ids, expected_output_count, priority | 129 |
| `SwarmTask` | models.py | **No** | id, prompt, status, assigned_agent, directive, result, votes, approval, priority | 146 |
| `SwarmState` | state.py | **No** | id, config, agents, tasks, spec_map, status, current_round, accumulated_cost, checkpoint_history | 93 |
| `SwarmCheckpoint` | state.py | **Yes** | id, round, config, agents, tasks, status, accumulated_cost | 25 |
| `ConsensusResult` | consensus.py | **Yes** | reached, approved, total_votes, approval_count, rejection_count, required, protocol, details, votes + risk audit fields | 29 |
| `RiskAssessment` | risk_assessment.py | **Yes** | risk, score, matched_signals, rationale | 159 |
| `ProtocolSelection` | risk_assessment.py | **Yes** | risk, protocol, assessment | 169 |
| `AdaptiveRiskAssessment` | adaptive_consensus.py | **Yes** | risk_level, recommended_protocol, worker_count, hitl_required, anti_drift, cost_estimate, rationale, base_assessment | 103 |
| `SwarmGraphEvent` | events.py | **Yes** | id, kind, swarm_id, timestamp, data, round | 36 |
| `ConsensusRoundOutcome` | nodes/consensus.py | **Yes** | task_id, decision, consensus_result | 45 |
| `VoteCommit` | consensus_escrow.py | **Yes** | agent_id, task_id, round, commit_hash, commit_timestamp | 44 |
| `CommitRevealVote` | consensus_escrow.py | **Yes** | vote, nonce, commit_hash, commit_timestamp, reveal_timestamp | 61 |
| `RiskFixture` | risk_assessment.py | **Yes** | id, prompt, expected_risk, expected_protocol | 325 |

**Observations:**
- 16/19 models use `extra="forbid"` and `frozen=True` (good)
- 3 mutable models: `AgentState`, `SwarmTask`, `SwarmState` — design choice for in-place mutation during lifecycle, but makes reasoning about state harder
- No field-level docstrings on fields (only class-level or function-level)
- `WorkerResult.output` capped at 65536 chars, `SwarmTask.prompt` at 32768, `QueenDirective.prompt` at 32768 — reasonable bounds

---

## 3. Consensus Protocol Comparison

| Protocol | Input | Logic | Output | Edge Cases |
|----------|-------|-------|--------|------------|
| **majority** | votes, optional quorum | approved >= floor(N/2)+1 | ConsensusResult | empty votes → rejected, tie → rejected |
| **quorum** | votes, quorum=int (default 2) | total >= quorum AND approved >= quorum | ConsensusResult | total < quorum → rejected |
| **raft** | votes | leader = lowest agent_id lexicographically; leader decides | ConsensusResult | empty votes → rejected, leader always breaks ties |
| **bft** | votes, optional quorum | approved >= ceil(2N/3) | ConsensusResult | empty votes → rejected, uses integer math, no float |
| **bft_escrow** | votes, optional quorum | same as bft + commit-reveal hashing | ConsensusResult with protocol=bft_escrow | nonce generation, hash verification, audit chain optional |
| **selective_debate** | votes, candidates, top_k=2 | round1 → top_k survivors → round2 majority | ConsensusResult | fallback to majority if candidates=None or top_k>=total |
| **confidence_weighted** | votes, threshold=0.5 | sum(confidence*approved)/sum(confidence) >= threshold | ConsensusResult | all-default confidence → fallback to majority |
| **critic_verifier** | votes, verifier_votes, multiplier=2.0 | verifier weighted ratio > 0.5 AND worker majority | ConsensusResult | no verifiers → worker majority only |
| **hitl_signoff** | votes, prompts, operators_required=1 | distinct operators >= required AND approved >= required | ConsensusResult | no prompts → rejected, last-response-wins per operator |
| **gossip** | votes, max_rounds=3 | deterministic simulation: majority opinion spreads each round | ConsensusResult | round 0 check, simulated sway logic, ties → approval |

**Critical finding:** All protocols produce the same result on single-worker runs (which is what `fake_offline` always does — 1 vote auto-approved). The diversity only matters with multi-vote scenarios, which require multi-worker execution that doesn't exist yet.

---

## 4. Risk Assessment Signal Catalog

### Signal Groups

| Level | Signals | Weight |
|-------|---------|--------|
| **critical** | "production database", "prod database", "delete production", "drop database", "wipe database", "transfer funds", "send payment", "withdraw funds", "rotate root key", "revoke all access", "disable mfa", "private key", "seed phrase", "escrow release", "irreversible", "cannot be undone" | 100 |
| **high** | "delete user", "delete account", "remove admin", "grant admin", "root access", "sudo", "api key", "secret", "password", "token", "credential", "encrypt", "decrypt", "firewall", "security policy", "payment", "invoice", "refund", "deploy to production", "prod deploy", "schema migration" | 50 |
| **medium** | "update config", "change config", "modify config", "edit file", "write file", "create file", "update code", "change code", "refactor", "migration", "restart service", "install package", "dependency update", "database query", "staging", "feature flag" | 20 |
| **low** | "explain", "summarize", "read", "list", "show", "describe", "what is", "how does", "documentation", "comment", "format" | 5 |

### Protocol Selection Matrix

| Risk Level | Default Protocol | Extended Options |
|------------|-----------------|------------------|
| low | majority | majority, selective_debate |
| medium | raft | confidence_weighted, quorum |
| high | bft | critic_verifier, bft |
| critical | bft_escrow | bft_escrow |

### Adaptive Consensus Context Signals

- Untrusted workspace → floor at high
- High-risk file types (.env, .pem, .key, secrets.yaml) → floor at high
- Medium-risk file types (.sql, .db, Dockerfile, .tf) → floor at medium
- Production/staging runtime → floor at high
- Keyword signals (private key, seed phrase, etc.) → floor at critical

### 100 Labeled Fixtures

25 per risk level in `risk_assessment.py:326-931`. All test that `assess_prompt_risk()` returns the correct level and `select_consensus_protocol()` returns the correct protocol.

---

## 5. Code Quality Assessment

### Strengths

1. **Strong typing**: All models use Pydantic v2 with `extra="forbid"` and most are `frozen=True`
2. **Deterministic by design**: No randomness, no LLM calls, no network in the risk assessment or consensus core
3. **Fail-closed**: Any exception in risk assessment → critical/bft_escrow
4. **Clean module boundaries**: `swarmgraph/` is self-contained with clear public API via `__init__.py`
5. **Comprehensive consensus suite**: 10 protocols with good docstrings and edge-case handling
6. **Event-driven architecture**: 7 event kinds cover the full lifecycle
7. **Checkpoint/restore/fork**: Built into SwarmState, though not yet wired to persistent storage
8. **Security-aware adapter**: Env allowlist, workspace path guard, redactor integration
9. **Dual-path adapter**: Native + CLI subprocess fallback

### Weaknesses

1. **Worker execution is fake-only**: `worker_execute()` only handles `fake_offline`; `gated_local` and `provider_backed` both return errors
2. **No parallel execution**: Workers run sequentially in a single-threaded loop — no `asyncio.gather`, no thread pool, no multiprocessing
3. **Trivial decomposition**: `queen_decompose()` copies the same prompt (star) or appends step numbers (chain) — no semantic splitting
4. **No LLM integration at all**: The entire runtime is a deterministic simulation — no model calls, no provider routing
5. **No inter-agent communication**: Workers don't actually talk to each other or the queen after assignment
6. **Events are memory-only**: Stored on the runner instance, returned in result dict — no streaming or persistence at the SwarmGraph level (adapter handles this externally)
7. **No async support**: The core runner is synchronous; the adapter wraps it with `run_in_executor`
8. **16/19 models frozen but 3 critical ones aren't**: `SwarmState`, `AgentState`, `SwarmTask` are mutable, mutated in-place by multiple nodes
9. **No cancellation signal propagation**: `CancellationToken` is a Protocol but only checked at round boundaries, not inside worker execution
10. **Risk assessment is substring-only**: No code analysis, no path traversal analysis, no semantic understanding

### ADR-013 Gap Analysis

| ADR-013 Commitment | Status | Notes |
|--------------------|--------|-------|
| Orchestrator-worker pattern | ✅ Implemented | Queen/Worker with round lifecycle |
| 6 consensus strategies | ✅ Exceeded | 10 implemented (6 req + 4 bonus) |
| Judge-arbitrated strategy | ❌ Missing | Default "queen synthesis" not implemented |
| Majority strategy | ✅ Implemented | `majority_consensus()` |
| Weighted strategy | ✅ Implemented | `confidence_weighted_consensus()` |
| Debate-N strategy | ✅ Implemented | `selective_debate_consensus()` |
| Proof-of-thought | ❌ Missing | "Phase 4.7" per ADR |
| Symbolic verification | ❌ Missing | "Deterministic verification against tests/schemas" |
| Fan-out gate with parallelizability score | ❌ Missing | Always fans out to all workers |
| Worker context isolation | ❌ Missing | All workers see the full prompt |
| 13 failure mode detectors | ❌ Missing | No failure detection |
| Per-step checkpoint resume | ⚠️ Partial | Checkpoint exists but no auto-resume, no persistent storage |
| Hierarchical up to 3 levels | ❌ Missing | Single-level only |
| Worker roles (prompt-file driven) | ❌ Missing | Hardcoded "Worker N" names |
| MASS topology optimization | ❌ Missing | "Phase 6.5" per ADR |
| Event envelope swarmgraph.* attributes | ❌ Missing | Event data has swarm_id but no queen_id, worker_role, fan_out_score, etc. |

---

## 6. Test Gap Analysis

| Area | Coverage | Gaps |
|------|----------|------|
| Models | Good defaults, validation, frozen | No JSON round-trip tests (model_dump → model_validate) |
| Consensus | All 10 protocols, empty votes, ties | No cross-protocol property tests (e.g., majority should be subset of BFT) |
| State | Checkpoint save/restore, fork | No invalid checkpoint ID, no multi-checkpoint scenario |
| Runner | Happy path, HITL, budget, worker counts 1/3/5 | No parallel execution, no error propagation, no cancellation mid-execution |
| Worker execution | fake_offline produces output, timeout | No gated_local tests, no provider_backed tests, no error simulation |
| Risk assessment | 100 fixtures pass | No crossover tests (mixed signals), no Unicode, no injection attempts |
| Adaptive consensus | Escalation logic tested | Missing: all context combinations (untrusted + prod + .env) |
| Topology | Star, chain with 0-3 workers | No mesh or tree topology tests |
| Events | Worker/consensus/budget events | No error events, no state_transition events, no audit events |
| Adapter | Native + stub CLI, event mapping | No real CLI backend, no workspace trust enforcement |
| Integration | LangGraph + SwarmGraph smoke | No end-to-end with real provider |
| Concurrency | None | No concurrent worker tests, no HITL race conditions |
| Budget | limit=0 exhaustion, negative validation | No partial exhaustion, no mid-round cap |
| HITL | Token matching, approve/reject | No token expiry, no concurrent HITL, no cancellation |
| Serialization | None | No large payload, no JSON round-trip for any model |

**Current test count:** ~57 native + 26 escrow + topology + adapter + risk + consensus differentiators + adaptive consensus = ~130 tests

---

## 7. Research Findings

### From CrewAI Docs

**Key patterns observed:**
- Agent attributes: role, goal, backstory, tools, LLM, memory — far richer than SwarmGraph's AgentSpec
- Task attributes: description, expected_output, context (task dependencies), async_execution, guardrails, callbacks, output_* (Pydantic/JSON)
- Process patterns: sequential (task order), hierarchical (manager LLM delegates)
- Code execution: deprecated built-in, recommends E2B/Modal for sandbox
- YAML-driven config (agents.yaml, tasks.yaml) — CrewBase decorator auto-loads

**What SwarmGraph could adopt:**
- Task dependency graph (context/await pattern)
- Guardrails on task output before consensus
- YAML-driven agent/task definitions
- Callbacks per task for monitoring

### From AutoGen (Microsoft) Docs

**Key patterns observed:**
- Message-based agent communication via publish/subscribe to topics
- `RoutedAgent` with `@message_handler` decorators
- `SingleThreadedAgentRuntime` and distributed runtime support
- `AgentId`-based addressing (type + key)
- For agent → runtime → agent, not direct calls
- Strong separation: agent logic vs communication infrastructure

**What SwarmGraph could adopt:**
- Publish/subscribe messaging instead of hardcoded queen→worker→consensus pipeline
- Agent identity + routing (AgentId pattern)
- Pluggable runtime backends (single-threaded, distributed)
- Message handler decorators for cleaner node definition

### From Python asyncio Docs

**Key patterns:**
- `asyncio.create_subprocess_exec()` for safe subprocess (no shell)
- `asyncio.gather()` for parallel subprocess execution
- `asyncio.wait_for(proc.communicate(), timeout=)` for timeout
- `Process.kill()` / `Process.terminate()` for process group signaling

**What SwarmGraph could adopt:**
- `asyncio.gather(*[worker_execute(t) for t in tasks])` for parallel execution
- Process group kill (`os.killpg`) for timeout enforcement
- Streaming stdout/stderr via `StreamReader` instead of buffered `communicate()`

### From Local Codebase Patterns

**Context7/Vercel Grep availability:** This 2026-05-30 continuation pass had no Context7 or Vercel Grep/code-search tool exposed in the runtime. Official docs/web fetch and local source search were used instead; do not treat this note as external Context7/Vercel coverage.

- `ok()`/`err()` envelope pattern for CLI responses
- Redactor for secret stripping (already used in adapter)
- HMAC audit chain for tamper-evident logging
- Workspace trust DB at `~/.arc/trusted-workspaces.json`
- Dual-gate pattern: `require_dual_gate("SWARMGRAPH")`

### 2026-05-30 Phase 106 Continuation Research Refresh

| Source | Link / query | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 | Requested for Python asyncio, Typer, Pydantic, SwarmGraph/provider patterns | No Context7 tool is exposed in this runtime. | Recorded blocker; used official docs and local source instead. | High | Re-run Context7 before security or architecture signoff if tool becomes available. |
| Vercel Grep/code search | Requested for SwarmGraph/provider-worker orchestration patterns | No Vercel Grep/code-search tool is exposed in this runtime. | Recorded blocker; avoided external-pattern claims. | High | Run external code search before broad provider-backed SwarmGraph claims. |
| Python asyncio docs | https://docs.python.org/3/library/asyncio-task.html | `asyncio.create_task` schedules concurrent tasks; cancellation propagates through task cancellation; `wait_for` raises `TimeoutError`; `gather` does not cancel other awaitables on first exception unless the gather itself is cancelled. | Existing Phase 106 runner uses explicit task refs, bounded semaphore, completion-order `asyncio.wait`, and cancellation checks; residual budget preflight should happen before task creation when budget is already exhausted. | High | None for this slice. |
| Pydantic docs | https://docs.pydantic.dev/latest/concepts/models/ | `model_copy(update=...)` is the supported frozen-model update pattern; `model_dump()` is the canonical recursive serialization API; `extra="forbid"` rejects unknown fields. | Existing `SwarmGraphConfig.model_copy(update={...})` remains aligned with Pydantic v2; no model change needed for the budget slice. | High | None for this slice. |
| Typer testing docs | https://typer.tiangolo.com/tutorial/testing/ | CLI tests should invoke a Typer app through `CliRunner.invoke` and assert exit code/output. | No CLI touched in this Phase 106 slice; no Typer tests needed. | High | None for this slice. |
| Local Phase 106 handover/roadmap/source search | `docs/handover/PHASE-106-SWARMGRAPH-HARDENING.md`, `docs/phases.md`, `docs/roadmap.md`, `python/src/agent_runtime_cockpit/swarmgraph/` | Phase 106 was already baseline-complete/live-smoke-proven, but acceptance still called out budget checks before execution. Current runner only failed after at least one worker result when budget was already at the limit. | Added a fail-closed pre-dispatch budget check that emits a budget event and skips worker execution when the budget is already exhausted. | High | Provider-specific token-cost estimation before first paid call remains broader P2 work. |

---

## 8. Improvement Recommendations

### P0: Critical (unblocks real execution)

| # | Improvement | Files | Effort | Impact |
|---|-------------|-------|--------|--------|
| 1 | **Implement async parallel worker execution** — replace sequential FOR loop with `asyncio.gather()` | runner.py, nodes/worker.py | Medium | High — enables actual multi-agent parallelism |
| 2 | **Implement gated_local worker mode** — wire worker_execute to call LLM provider via adapter pattern | nodes/worker.py, provider layer | Large | High — enables real execution beyond simulation |
| 3 | **Add fan-out gate with parallelizability score** — queen computes score, decides single vs multi-worker | nodes/queen.py, runner.py | Medium | High — ADR-013 requirement, prevents wasteful fan-out |

### P1: High (production readiness)

| # | Improvement | Files | Effort | Impact |
|---|-------------|-------|--------|--------|
| 4 | **Wire persistent event streaming** — emit consensus/topology/worker events through EventBroker during run | runner.py → adapter events pipeline | Medium | High — enables real-time monitoring |
| 5 | **Implement 3 of 13 failure mode detectors** — coordination deadlock, consensus failure, resource exhaustion | New file swarmgraph/detectors.py | Medium | High — ADR-013 requirement |
| 6 | **Add task dependency graph** — tasks can declare `context=[other_tasks]` like CrewAI, await their completion | models.py, runner.py | Medium | Medium — enables complex workflows |
| 7 | **Implement worker context isolation** — workers receive only assigned task, not full prompt | nodes/queen.py, nodes/worker.py | Small | High — ADR-013 security commitment |

### P2: Medium (quality of life)

| # | Improvement | Files | Effort | Impact |
|---|-------------|-------|--------|--------|
| 8 | **Add structured task output** — `output_pydantic` / `output_json` on SwarmTask, validated by Pydantic | models.py, nodes/worker.py | Small | Medium |
| 9 | **Add task guardrails** — validation functions that run before consensus | nodes/consensus.py, models.py | Medium | Medium |
| 10 | **Implement cancellation propagation mid-execution** — check token during worker execution, not just at round boundaries | runner.py, nodes/worker.py | Small | Medium |
| 11 | **Add JSON round-trip tests** — `model_dump()` → `model_validate()` for all 19 models | tests/ | Small | Medium — catches serialization bugs |
| 12 | **Add cross-protocol property tests** — e.g., majority approval implies BFT approval | tests/ | Small | Medium |

### P3: Low (nice to have)

| # | Improvement | Files | Effort | Impact |
|---|-------------|-------|--------|--------|
| 13 | **YAML-driven agent/task definitions** — like CrewAI's agents.yaml/tasks.yaml | config.py, new yaml_loader.py | Medium | Medium |
| 14 | **Semantic prompt decomposition** — queen actually splits prompt into distinct sub-tasks | nodes/queen.py | Large | High |
| 15 | **Publish/subscribe agent communication** — agents communicate via topics instead of direct calls | New event bus integration | Large | High |
| 16 | **MCP tool integration per agent** — each worker gets scoped MCP tools | nodes/worker.py | Medium | Medium |
| 17 | **Cost estimation preflight** — estimate token cost before executing, warn if over budget | runner.py, adaptive_consensus.py | Small | Medium |
| 18 | **Checkpoint auto-resume** — detect crash, restore from last checkpoint, continue | runner.py, state.py | Medium | Medium |

---

## Critical Review of This Analysis

**Date:** 2026-05-29
**Reviewer:** Same analyst, adversarial pass

### What the analysis gets right

1. **Architecture diagram is accurate** — confirmed by line-by-line read of `runner.py:39-170`
2. **ADR-013 gap analysis is honest** — 9/16 commitments are genuinely missing, not deferred
3. **Consensus single-vote observation is devastating** — correctly identifies that 10 protocols are academically impressive but functionally identical when `fake_offline` always produces 1 auto-approved vote per task
4. **Test gap analysis is thorough** — cross-referenced with actual test files

### What the analysis overstates or misses

| Issue | Correction |
|-------|-----------|
| "No LLM integration at all" | Phase 20 `TurnManager` + `ProviderClient` exists in the broader runtime — but it's NOT wired into SwarmGraph workers. The analysis is correct that SwarmGraph workers specifically have no provider path. |
| "No async support" | The adapter already uses `run_in_executor` — the analysis should distinguish "runner is sync" from "system is sync". Only the inner loop needs async. |
| "Trivial decomposition" overstated as a defect | For `fake_offline` mode this is appropriate — semantic decomposition requires LLM calls. The real issue is that there's no *interface* for plugging in a better decomposer. |
| Missing analysis of `runtimes/swarmgraph/` vendored code | The analysis only covers `python/src/agent_runtime_cockpit/swarmgraph/` but ignores the `runtimes/swarmgraph/packages/hive-swarm/` vendored runtime which has its own `build_swarm_graph()`, LLM integrations, and factory pattern. This is a potential source of code for the provider-backed worker path. |
| Missing Phase 20 context | Phase 20 already has `TurnManager`, `ToolRegistry`, `ProviderClient` — the "implement gated_local worker mode" recommendation should reference these existing components rather than proposing a new adapter pattern from scratch. |
| Recommendation #15 (pub/sub) is too large | Proposing a full pub/sub architecture is a rewrite, not an improvement. The existing queen→worker→consensus pipeline is fine for the orchestrator-worker pattern; pub/sub would conflict with ADR-013's explicit prohibition of swarm/handoff patterns. |
| Missing cost analysis of recommendations | P0 items are labeled "Medium effort" but implementing async parallel workers with proper cancellation, error handling, and state consistency is closer to "Large" if done properly. |

### What should be added to improvements

| # | Addition | Rationale |
|---|----------|-----------|
| A1 | **Wire Phase 20 ProviderClient into worker_execute gated_local path** | Don't invent new provider integration — reuse existing TurnManager/ProviderClient |
| A2 | **Add `DecompositionStrategy` protocol** | Interface for pluggable decomposition (trivial/heuristic/LLM-backed) without hardcoding |
| A3 | **Add mesh/tree topology execution** | Only star and chain have execution logic; mesh/tree fall through to generic single-task |
| A4 | **Wire event streaming callback into runner** | Runner should accept an optional `on_event: Callable[[SwarmGraphEvent], None]` for live streaming without adapter mediation |
| A5 | **Add `SwarmGraphConfig.max_parallel_workers`** | Config knob for concurrency limit separate from `num_workers` (not all N workers should run simultaneously) |

### Verdict on recommendations priority

The original P0 list is correct in spirit but should be reordered:

1. **P0-actual: Wire ProviderClient into gated_local** (builds on Phase 20 work, enables real execution)
2. **P0-actual: Add async parallel execution with configurable concurrency** (requires ProviderClient to be meaningful)
3. **P1: Fan-out gate** (only valuable once parallel execution exists)
4. **P1: Worker context isolation** (small change, high security value)
5. **P1: Event streaming callback** (enables real-time monitoring without full adapter)
6. **P2: Failure detectors** (meaningful only with real execution that can fail)

---

## 9. Integration Surface Audit

### Internal Dependencies

```
swarmgraph/
  ├── runner.py → config.py, events.py, graph.py, models.py, nodes/*.py, state.py
  ├── consensus.py → config.py, models.py
  ├── consensus_escrow.py → config.py, consensus.py, models.py (+ optional audit.hmac_chain)
  ├── risk_assessment.py → config.py
  ├── adaptive_consensus.py → risk_assessment.py, config.py
  ├── events.py → consensus.py, models.py, state.py
  ├── models.py → (standalone, pydantic only)
  ├── config.py → (standalone, pydantic only)
  ├── state.py → config.py, models.py
  ├── graph.py → config.py, models.py, state.py
  ├── fixtures.py → config.py, runner.py
  └── nodes/
      ├── queen.py → state.py, models.py, config.py
      ├── worker.py → config.py, models.py
      ├── consensus.py → config.py, consensus.py, consensus_escrow.py, models.py, risk_assessment.py
      └── approval.py → models.py
```

### External Integration Points

```
SwarmGraphRunner
  → adapters/swarmgraph.py (SwarmGraphAdapter._run_native_workflow)
    → wraps in RunRecord with mapped RunEvents
    → orchestration/supervisor.py (JobSupervisor._execute_run)
      → emits via EventBroker
      → persists via JsonlTraceStore
      → publishes to event bus (RunCompleted/RunFailed)

CLI:
  cli/swarmgraph.py → swarmgraph_app
    → consensus_eval_cmd → evals/consensus.py
    → assess_risk_cmd → adaptive_consensus.assess_risk()

REPL:
  cli_repl/chat_repl.py → uses SwarmGraphRunner directly
  cli_repl/slash_commands.py → instantiate SwarmGraphRunner

IDE:
  packages/arc-extension/src/browser/tabs/swarmgraph-insight-model.ts
    → extracts topology/consensus/cost from trace events
    → rendered in SwarmGraphInsightTab.tsx

AGUI:
  packages/arc-ag-ui/src/mapping/swarmgraph.ts
    → SwarmGraphMapper maps native events to AGUI events
```

---

## 10. SDK Extraction Notes

### Executed first slice

- Added a library-facing `swarmgraph` import facade packaged inside the existing `agent-runtime-cockpit` wheel.
- Added typed `SwarmRunResult` / `SwarmRunTaskResult` wrappers while preserving the existing `dict` return contract for `SwarmGraphRunner.run()` and `run_async()`.
- Added `SwarmGraphRunner.run_result()` and `run_result_async()` for SDK-style typed usage.

### Executed second slice

- Added SDK-owned `swarmgraph.providers` models/protocols: `Provider`, `ProviderRequest`, `ProviderResponse`, `UsageRecord`, `ProviderMessage`, `ProviderCapability`, and `CostRates`.
- Removed ARC provider registry/env coupling from `swarmgraph.nodes.worker`; gated provider execution now requires explicit provider injection.
- Added `SwarmGraphRunner(provider=...)` injection and passes `allow_paid_calls` from `SwarmGraphConfig` into worker execution.
- Enforced paid-call denial by default for `gated_local` provider execution.
- Added a subprocess import guard proving `import swarmgraph` and `import swarmgraph.providers` do not load `agent_runtime_cockpit.providers` or `agent_runtime_cockpit.cli_repl.cancellation`.

### Recommended SDK shape

```python
from swarmgraph import SwarmGraphConfig, SwarmGraphRunner

runner = SwarmGraphRunner(config=SwarmGraphConfig(max_rounds=1))
result = runner.run_result("Explain consensus")
```

### Packaging status

- Current: SDK facade is bundled with ARC's Python package.
- Not yet done: separate `swarmgraph-sdk` distribution, independent release workflow, and independent docs site.
- Provider contract split is now done inside the shared source tree; a separate `swarmgraph-sdk` wheel still requires moving shared source ownership rather than copying code.
- Safe claim: "SwarmGraph SDK import facade / first extraction slice."
- Unsafe claim: "Standalone published SDK" or "production provider-backed SDK."

### Pros

- Existing core is mostly self-contained.
- Deterministic offline mode is CI-safe.
- Consensus, risk, events, decomposition, state, and runner APIs are already useful as library primitives.
- ARC adapter can remain a host integration layer instead of becoming the SDK boundary.

### Cons / blockers

- `gated_local` no longer depends on ARC provider registry/env names, but real provider wiring is injection-only and host-owned.
- `provider_backed` is still not a working SDK-owned execution mode.
- Runner consensus is still limited by current task/vote semantics.
- Durable checkpoint resume remains in-memory only.
- Separate package publication requires dependency pruning and import-path conflict checks.

### Next SDK queue

1. Split `swarmgraph-sdk` into its own wheel by moving shared source ownership to the SDK package and keeping ARC as a bridge/compat consumer.
2. Add a real typed event stream API.
3. Add a durable checkpoint store interface.
4. Implement real multi-worker vote semantics before claiming consensus affects runtime outcomes broadly.
