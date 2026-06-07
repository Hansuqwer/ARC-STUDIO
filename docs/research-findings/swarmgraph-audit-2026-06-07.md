# SwarmGraph Audit — 2026-06-07

> **Scope:** Runtime, CLI, IDE, events, topology, consensus, DAG planning, notifications, evals, provider-backed gates, UI  
> **Agent count:** 12 parallel sub-agents

---

## 1. Architecture Map

```
TUI / CLI                   IDE (Theia)                  HTTP Daemon :7777
arc swarmgraph *            SwarmGraphInsightTab         GET /api/runs/*/events
arc ir compile              (5 inline panels)            SSE per run-id
arc eval                    DagPlannerViz ①              EventBroker fan-out
                            ConsensusEvidenceCard        RingBuffer(1000)
                            HitlApprovalPanel ②
```

**Two disconnected `SwarmGraphRunner` classes** — `adapters/swarmgraph/runner.py` is never called from `SwarmGraphAdapter.run_workflow()`.

**Execution mode matrix:**

| Path | Deterministic | Offline | Provider-backed | Gate |
|---|---|---|---|---|
| `fake_offline` (default) | ✅ | ✅ | ❌ | none |
| `gated_local` | ✅ | ✅ | ❌ | `allow_paid_calls=True` |
| CLI subprocess native | ✅ | ✅ | ❌ | `ARC_SWARMGRAPH_CLI` |
| LOCAL executor | depends | depends | possible | `ARC_SWARMGRAPH_ALLOW_COSTS` |
| GATEWAY backend | ❌ | ❌ | ✅ narrow | dual gate + URL |
| live opt-in smoke | ❌ | ❌ | ✅ narrow | `ARC_SWARMGRAPH_PROVIDER_E2E=1` |
| canonical E2E | ❌ | ❌ | ✅ narrow | dual gate + API key |
| IR compiler | ✅ | ✅ | ❌ | none (always) |

---

## 2. Runtime & CLI Command Inventory

### CLI commands

| Command | What it does | Mode |
|---|---|---|
| `arc swarmgraph plan --strategy dag --json` | DAG plan from prompt | Deterministic, offline |
| `arc swarmgraph eval --compare --json` | Consensus eval comparison | Deterministic, offline |
| `arc ir compile <workflow.json>` | Compile workflow to IR | Deterministic, offline |
| `arc ir inspect <ir.json>` | Summarize IR graph | Deterministic |
| `arc ir validate <ir.json>` | Validate IR, exit 2 on error | Deterministic |
| `arc ir policy <ir.json>` | Run policy linter on IR | Deterministic |

### Orphaned runtime surfaces

- `adapters/swarmgraph/runner.py` — `SwarmGraphRunner` (audit-chain runner): **never called**
- `adapters/swarmgraph/local_executor.py` — in-process user code: **no tests, no sandbox**
- `adapters/swarmgraph/gateway_client.py` — SSE to external gateway: **zero streaming tests**
- `demo_run_workflow()` — public method, `_mock=True`, produces no execution

---

## 3. Event Producer / Consumer Matrix

| Event Type | Producer | IDE Consumer | Audit chain |
|---|---|---|---|
| `SWARMGRAPH_TOPOLOGY` | SDK runner | ✅ `buildSwarmGraphInsight` | ❌ blind |
| `SWARMGRAPH_CONSENSUS` | SDK runner | ✅ (minimal slice only) | ❌ blind |
| `SWARMGRAPH_COST` | SDK runner | ✅ cost panel | ❌ blind |
| `CONSENSUS_DIFFERENTIATOR` | eval harness | ❌ log only | ❌ |
| `SwarmGraphEventKind.consensus` (internal) | consensus node | **never bridged** | ❌ |
| `SwarmGraphEventKind.hitl` (internal) | HITL node | **never bridged** | ❌ |
| `SwarmGraphEventKind.arena_vote` (internal) | arena mode | **never bridged** | ❌ |

### Schema gaps

| Event | Gap |
|---|---|
| `SWARMGRAPH_TOPOLOGY.nodes/edges` | `list[Any]` — no inner schema |
| `SWARMGRAPH_CONSENSUS.votes` | `list[Any]` — no inner schema |
| `MESSAGE` | Registry expects `text`, typed model expects `message_id+role+content` — **live mismatch** |
| Denial events | Typed in `denial_events.py` but not in `KnownRunEvent` union |
| `SWARMGRAPH_*` | Not in `KnownTraceEventType` enum in TypeScript — open-string only |

### Notification routing (broken)

```
SwarmGraph SDK events
    → DurableWebhookNotificationHook   → external HTTP (works, if configured)
    → EventBrokerNotificationHook      → ARC EventBus (BROKEN: module missing, gate off)
    ✗ NotificationOutbox               → dead code
    ✗ ArcEvent log                     → SwarmGraph events never written here
    ✗ IDE badge                        → sees zero SwarmGraph events
```

---

## 4. UI Gap Review

### SwarmGraphInsightTab panels

| Panel | Live data | Status |
|---|---|---|
| Topology visualization | ✅ real events | Node/edge **lists** only (no graph layout) |
| Consensus panel | ✅ real events | Decision + strategy + voters only — no risk, no protocol, no confidence |
| Cost panel | ✅ real events | Works |
| HITL approval | ❌ | `onApprove/onReject` not wired to `arcService.respondHitlPrompt()` |

### Orphaned IDE components

`DagPlannerViz`, `ConsensusEvidenceCard`, and `HitlApprovalPanel` live in `browser/swarmgraph/` but are **not imported** by `SwarmGraphInsightTab`. Dead code from the tab's perspective.

### Other IDE gaps

| Gap | Detail |
|---|---|
| Port mismatch | Live stream placeholder shows `127.0.0.1:8000`; daemon runs on `:7777` |
| No SSE reconnect | `lastEventId` field exists but reconnect not implemented |
| `SWARMGRAPH_*` not enum-typed | Open-string only in TypeScript |
| `safeMetadataSummary` untested | Secret-filtering regex incomplete |
| Zero tests on `SwarmGraphInsightTab` | Largest SwarmGraph UI file |
| Props-only React tests | Component tests call `React.createElement` and check `.props.*` only — never mount/render |

---

## 5. Safety / Claim Review

### Correctly labeled

- All external adapters return `provider_backed=False` in `capability_report()` ✅
- `require_dual_gate()` enforces gates at runtime ✅
- Roadmap boundary: "No broad live/provider-backed SwarmGraph adoption claim" ✅
- `check-banned-claims.sh` enforces release hygiene ✅

### Contradictions (all low severity)

| # | Item | Severity |
|---|---|---|
| C1 | `SwarmGraphRunner` docstring says "Provider-backed runner" but default STUB is offline | Low |
| C2 | README table doesn't note gateway mode opt-in gate | Low |
| C3 | LM Arena README says "live productization deferred" but arena battle system is concretely implemented in tests | Low |

### Security findings

| Issue | Severity |
|---|---|
| `LocalSwarmExecutor` runs arbitrary workspace Python in-process, no isolation | Medium |
| `GatewayClient` sends unauthenticated requests silently when token absent | Low |
| `_run_cli_workflow()` acknowledged missing sandbox gate (`# TODO` on subprocess) | Low |
| `resolve_python_entrypoint()` permanently mutates `sys.path` | Low |
| Consensus results not HMAC-signed — invisible to audit chain | Medium |

---

## 6. Test Gap Review

### Zero-test surfaces

| Surface | Risk |
|---|---|
| `adapters/swarmgraph/local_executor.py` | Arbitrary in-process execution |
| `SwarmGraphInsightTab.tsx` (20 KB) | Largest SwarmGraph UI file |
| `GatewayClient.run_stream()` async generator | Live SSE streaming path |
| `swarmgraph_ir/compiler.py` internal stages | Only tested via CLI integration |
| `swarmgraph_ir/enrich.py` | `enrich_mcp=True` path never exercised |
| `swarmgraph_ir/validation.py` | Only via CLI integration |
| `swarmgraph_ir/provenance.py` | No tests |

### Test quality issues

| Issue | File |
|---|---|
| Code-archaeology test | `test_gateway_backend.py` — `inspect.getsource()` passes even if logic deleted |
| Props-only React tests | `swarmgraph-insight-components.test.tsx` — no mount/render |
| Synthetic metrics | `quality_score` and `cost_score` are hard-coded formulas |
| `latency_ms == duration_ms` | Duplicate field, identical value |
| Orphaned golden fixture | `tests/integration/fixtures/swarmgraph.golden.jsonl` — no test reads it |

---

## 7. Next-Slice Implementation Prompt

**Target:** SwarmGraph SDK event bridge into IDE (unblocks all UI panels without touching provider-backed paths)

### Slice scope

1. **Bridge:** `adapters/swarmgraph/event_bridge.py` (new) — `translate_swarmgraph_event(sg_event, run_id, sequence) -> RunEvent`
   - `topology` → `SWARMGRAPH_TOPOLOGY` (flat, no nested key)
   - `consensus` → `SWARMGRAPH_CONSENSUS` (votes, decision, strategy, voters, confidence, task_id)
   - `worker` → `STEP_COMPLETED`/`STEP_FAILED`
   - `budget` → `QUOTA_WARNING`
   - `hitl` → `HITL_PROMPT`
   - Wire into `SwarmGraphAdapter._run_native_workflow()`

2. **Fix MESSAGE schema mismatch** — registry expects `text`, typed model expects `message_id+role+content`
   - Test: assert `coalesce_chunks()` output passes `MessageEvent.model_validate()`

3. **Add denial events to `KnownRunEvent`** — `TrustDeniedEvent`, `PaidCallDeniedEvent`, `ShellDeniedEvent`, etc.

4. **ConsensusEvidenceCard Phase 2** — add risk level badge, protocol name, per-vote confidence, escrow status

5. **Cycle detection in IR validation** — DFS in `validate_graph()`, fail on cycle with path in error

6. **Fix port mismatch** — `127.0.0.1:8000` → `127.0.0.1:7777` in `SwarmGraphInsightTab.tsx`

7. **Critical test gaps** — `test_local_executor.py`, `test_enrich_mcp.py`, `test_budget_exhaustion.py`; upgrade React component tests to use `@testing-library/react render()`

### Do NOT do in this slice

- Provider-backed broad adoption
- D3 graph visualization
- `HitlApprovalPanel` action wiring
- `EvalArtifactStore` indexing
- Commit-reveal behavioral tests

---

## Key Findings Summary

**Three biggest structural problems:**

1. **SwarmGraph SDK events never reach the IDE.** `EventBrokerNotificationHook` is broken by default (import target `orchestration.event_broker` doesn't exist + gate off). All downstream UI panels are starved of data.

2. **Two `SwarmGraphRunner` classes exist with the same name and zero integration.** `adapters/swarmgraph/runner.py` is never called from the main adapter entry point.

3. **IDE components are orphaned.** `DagPlannerViz`, `ConsensusEvidenceCard`, `HitlApprovalPanel` are not imported by `SwarmGraphInsightTab`. The tab uses inline equivalents and has zero tests itself.

**Recommended next slice priority:**
1. Event bridge (SDK → RunEvent → EventBroker → IDE)
2. MESSAGE schema mismatch fix
3. ConsensusEvidenceCard Phase 2
4. IR cycle detection
5. Budget exhaustion test + local_executor tests
