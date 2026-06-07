# ARC Studio Notifications, DAG Planner & Orchestration UI Audit — 2026-06-07

> **Scope:** Notification lifecycle, managed notification service, push hooks, offline retry, bounded subscribers, deterministic DAG planner, orchestration UI  
> **Source:** Synthesized from prior sessions + direct reads of notification-service.ts, notifications/outbox.py, cli/plan.py, cli/swarmgraph.py

---

## 1. Notification Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│              ARC STUDIO NOTIFICATION ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────────┤
│  PYTHON SIDE                                                         │
│                                                                      │
│  ARC EventBus (in-process, no push to IDE)                          │
│  EventBroker: per-run-id fan-out → SSE /api/runs/{id}/events         │
│  EventPersistenceWriter: .arc/events/event-log.jsonl                │
│                                                                      │
│  Notification outbox (Python / swarmgraph-sdk)                      │
│  ├── notifications/outbox.py: NotificationOutbox (DEAD CODE)         │
│  │   ├── append-only JSONL at caller-specified path                 │
│  │   ├── read_all() reads full file on every call (no seek)         │
│  │   ├── gc() removes non-PENDING entries older than ttl_days       │
│  │   ├── Nothing imports or uses this class anywhere               │
│  │   └── notifications/__init__.py is EMPTY                         │
│  └── swarmgraph/notifications.py: DurableNotificationOutbox (LIVE)  │
│      ├── <workspace>/.arc/swarmgraph/notification-outbox.jsonl      │
│      ├── outstanding(): PENDING + FAILED records                    │
│      ├── ManagedNotificationService: async retry loop               │
│      ├── WebhookNotificationHook + DurableWebhookNotificationHook   │
│      └── EventBrokerNotificationHook (BROKEN — import target        │
│          orchestration.event_broker doesn't exist; gate off default) │
│                                                                      │
│  arc events summary --json                                          │
│  ├── Reads .arc/events/event-log.jsonl                              │
│  ├── Counts: hitl, runFailures, auditAlerts, taskFailures,          │
│  │   evalFailures                                                    │
│  ├── source: "local_event_log_recent" | "cli_fallback"              │
│  ├── protocol: "sse" (hardcoded — no real SSE connection)           │
│  └── degraded: true if unmatched HITL decisions after compaction    │
├─────────────────────────────────────────────────────────────────────┤
│  THEIA NODE SIDE                                                     │
│                                                                      │
│  NotificationBackendService (notification-service.ts)               │
│  ├── getCounts() → spawns 'arc events summary --json'               │
│  │   ├── spawn with shell:false ✅                                   │
│  │   ├── NO env argument (inherits full process.env) ⚠️             │
│  │   ├── 5s timeout, output capped at 64KB                         │
│  │   └── Returns NotificationCounts on success, degraded on fail    │
│  ├── No polling loop — getCounts() called on-demand only           │
│  ├── No push channel — IDE badge never updates without explicit call │
│  └── SSE /api/events/stream exists but NOT subscribed by service    │
├─────────────────────────────────────────────────────────────────────┤
│  IDE SIDE                                                            │
│                                                                      │
│  NotificationBadge component: renders hitl/runFailures/auditAlerts  │
│  CommandCentreTab: shows HITL count, run failures count             │
│  No notification tray, no toast history, no notification panel      │
│  No auto-refresh loop — badge stale until user navigates to tab     │
│                                                                      │
│  PUBLIC SSE/WebSocket PRODUCT ROUTE: DEFERRED                       │
│  R53 notes: "does not claim public SSE/WebSocket product routing"   │
│  Current state: CLI polling (getCounts → spawn) is the only path    │
└─────────────────────────────────────────────────────────────────────┘
```

### Key findings

**Notification lifecycle:**
- Python `notifications/outbox.py` is dead code — no consumer, no import, never used
- The live notification system is in `swarmgraph/notifications.py` (DurableNotificationOutbox, ManagedNotificationService)
- `EventBrokerNotificationHook` is gated off by default AND its import target (`orchestration.event_broker`) doesn't exist in the codebase — bridge is permanently broken
- `protocol: "sse"` is hardcoded in `arc events summary` output — this is a **lie**; the actual transport is CLI polling

**Subscriber lifecycle:**
- `NotificationBackendService` has no subscriber registration mechanism — it is a pure polling class
- No bounded subscriber lists to clean up — each `getCounts()` call is independent
- No overflow possible — it is stateless

**Offline retry:**
- `DurableNotificationOutbox`: webhook delivery with exponential retry in `ManagedNotificationService`
- `NotificationOutbox` (dead code): no retry mechanism — PENDING status is stored but nothing processes it
- No durable offline retry for IDE badge counts (polling simply degrades to zeros)

---

## 2. DAG Planner Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│              ARC STUDIO DAG PLANNER ARCHITECTURE                     │
├─────────────────────────────────────────────────────────────────────┤
│  DETERMINISTIC PLANNER (no provider calls)                          │
│                                                                      │
│  arc swarmgraph plan --strategy dag --json                          │
│  ├── DAGPlan / DAGPlanNode (legacy layer, swarmgraph.decomposition) │
│  ├── TrivialDecomposition with topology (star/mesh/tree/dag)        │
│  ├── metadata["planner"] == "deterministic"                         │
│  ├── metadata["auto_provider"] == False                             │
│  ├── Stable task IDs: "task-001", "task-002", ...                  │
│  ├── parallelizability_score: heuristic (prompt length/complexity)  │
│  └── NO provider calls, NO network, fully offline                   │
│                                                                      │
│  arc plan explain -- <cmd> [-- <cmd> ...]                           │
│  ├── Parses command sequence (-- separator)                         │
│  ├── build_plan(commands, policy) → PlanEnvelope                   │
│  │   ├── Per-step: decide(cmd, policy) → classification             │
│  │   ├── validate_command_paths() → workspace confinement           │
│  │   └── static denial: DESTRUCTIVE/PRIVILEGED always denied       │
│  ├── persist_plan_record() → .arc/plans/{plan_id}.json             │
│  ├── persist_plan_audit_event() → audit trail                      │
│  └── Output: plan_id, steps[], audit_path, plan_path               │
│                                                                      │
│  arc plan approve --plan-id <id> [--token <tok>]                   │
│  ├── load_plan_record() → reads .arc/plans/{plan_id}.json          │
│  ├── approve_plan(plan, token) → stores approval                   │
│  └── Returns: approval_id, approval_token, audit_path              │
│                                                                      │
│  arc plan apply --plan-id <id> --approval-token <tok>              │
│  ├── verify_plan_approval(plan, token) → checks token match        │
│  ├── Per step: decide() → approve_decision_with_token()            │
│  │   → validate_command_paths() → build_execution_provider()       │
│  │   → provider.execute()                                           │
│  ├── Audit events: plan_apply_attempted, plan_apply_failed,        │
│  │   plan_apply_denied, plan_apply_completed                        │
│  └── Exit codes: 0=applied, 2=invalid, 3=denied/failed            │
│                                                                      │
│  SwarmGraph IR Compiler (swarmgraph_ir/)                            │
│  ├── compile_workflow(WorkflowInfo) → IRGraph                       │
│  ├── Fully deterministic + offline (use_sdk_risk=False default)    │
│  ├── SHA-256 content-addressed hashing (volatile keys stripped)    │
│  ├── 8-step pipeline: import→enrich→cap-infer→risk?→validate→hash │
│  ├── validation: no cycle detection (GAP)                          │
│  └── arc ir compile/validate/policy commands                        │
│                                                                      │
│  DagPlannerViz (IDE component)                                      │
│  ├── Phase 1 stub — list-only, no D3/SVG                           │
│  ├── NOT imported by SwarmGraphInsightTab (orphaned)                │
│  └── Parent data source unverified                                  │
└─────────────────────────────────────────────────────────────────────┘
```

### DAG planner properties confirmed

| Property | Status | Evidence |
|---|---|---|
| Deterministic (no LLM) | ✅ | `metadata["planner"] == "deterministic"`, `metadata["auto_provider"] == False` |
| Provider-free | ✅ | No provider calls in any planner path |
| Cycle detection | ❌ **Missing** | IR `validate_graph()` has no DFS/topological sort; cyclic IR passes `ok=True` |
| Dependency errors handled | ⚠️ Partial | `validate_command_paths()` catches path issues; no task-level dependency failure handling |
| Stable task IDs | ✅ | `task-001`, `task-002` format; stable across identical inputs |
| Plan persistence | ✅ | `.arc/plans/{plan_id}.json` via `persist_plan_record()` |
| Plan audit trail | ✅ | `persist_plan_audit_event()` on every explain/approve/apply/deny |
| Public SSE route | ❌ **Deferred** | R53: "does not claim public SSE/WebSocket product routing, provider-backed auto planning" |
| IDE live UI | ❌ **Deferred** | DagPlannerViz is Phase 1 stub; not in SwarmGraphInsightTab |

---

## 3. CLI / IDE Gap Matrix

### Notifications

| Feature | CLI | IDE | Gap |
|---|---|---|---|
| HITL count | ✅ `arc events summary` | ✅ badge (stale) | No auto-refresh |
| Run failures count | ✅ | ✅ badge (stale) | No auto-refresh |
| Audit alerts count | ✅ | ✅ badge (stale) | No auto-refresh |
| Notification history | ❌ | ❌ | Full gap |
| Push notifications | ❌ (deferred) | ❌ | Full gap — SSE /api/events/stream not subscribed |
| Notification tray | ❌ | ❌ | Full gap |
| Webhook delivery status | ✅ `arc events webhook-list` | ❌ | Full gap |
| Dead letter log | ✅ internal | ❌ | Full gap |

### DAG / Plan

| Feature | CLI | IDE | Gap |
|---|---|---|---|
| Plan explain | ✅ `arc plan explain` | ✅ EditPlansTab (partial) | EditPlansTab covers edit plans; no general plan-explain panel |
| Plan approve | ✅ `arc plan approve` | ✅ EditPlansTab approve button | Good parity |
| Plan apply | ✅ `arc plan apply` | ✅ EditPlansTab apply button | Good parity |
| DAG plan (SwarmGraph) | ✅ `arc swarmgraph plan` | ❌ DagPlannerViz stub | **Full gap** — DagPlannerViz is Phase 1 list stub, not used by any tab |
| IR compile/validate | ✅ `arc ir compile/validate` | ❌ | **Full gap** |
| Plan audit trail | ✅ `.arc/plans/*.json` | ❌ | **Full gap** |
| Plan-to-run handoff | ❌ | ❌ | Full gap — no "Run this plan" button in any IDE surface |

---

## 4. Reliability Risk Review

### Notifications

| Risk | Severity | Detail |
|---|---|---|
| `protocol: "sse"` is a lie | **Medium** | `arc events summary` hardcodes `protocol: "sse"` in output but the actual transport is CLI polling |
| `EventBrokerNotificationHook` permanently broken | **Medium** | Import target `orchestration.event_broker` doesn't exist; gate is off by default; SwarmGraph SDK events never reach IDE |
| No auto-refresh polling | **Medium** | Badge counts stale until user navigates; no `setInterval` in NotificationBackendService |
| `NotificationOutbox` is dead code | **Low** | Python class with no consumers; safe to delete |
| HITL count semantically imprecise | **Low** | Compaction can drop `hitl_decided` events, producing `unmatched_hitl_decisions`; degraded=true but count may be wrong |
| NotificationBackendService no env allowlist | **High** | `spawn('arc', args)` with no `env` argument — inherits full `process.env` including all API keys |

### DAG Planner

| Risk | Severity | Detail |
|---|---|---|
| IR `validate_graph()` has no cycle detection | **Medium** | A cyclic IR graph passes `ok=True`; downstream policy linting may produce incorrect results |
| `plan apply` is synchronous blocking | **Medium** | `asyncio.run(provider.execute(...))` in a sync CLI command; each step runs sequentially |
| Plan approval token stored in plain JSON | **Low** | `.arc/plans/approvals/{plan_id}.json` — alpha, single-user, acceptable |
| DAG planner `parallelizability_score` uncalibrated | **Low** | Simple prompt-length heuristic; useful for UI display, not deterministic task splitting |

---

## 5. Test Gaps

### Notifications

| Gap | Severity | Detail |
|---|---|---|
| `NotificationBackendService` no env allowlist | **High** | No test verifying spawn doesn't leak API keys to child process |
| `protocol: "sse"` hardcoded lie | **Medium** | No test verifying output is labeled accurately |
| No auto-refresh test | **Low** | No polling loop to test |
| `NotificationOutbox` (dead code) | **None** | Safe to delete; no tests needed |
| `DurableNotificationOutbox` outstanding() dedup | **Low** | Last-write-wins; no test for concurrent writes |

### Existing test coverage

| Test | Covers |
|---|---|
| `tests/node/services/notification-service.test.ts` | getCounts() parsing, degraded fallback, spawn shell:false |
| `tests/evals/test_consensus_earlystop.py` | Early-stop logic |
| `tests/swarmgraph/test_notifications_service.py` | DurableWebhookNotificationHook, ManagedNotificationService, EventBrokerNotificationHook (confirms it's broken) |
| `tests/tui/test_status_bar_quota_warning.py` | QuotaWarning display |

### DAG Planner

| Gap | Severity | Detail |
|---|---|---|
| IR cycle detection absent | **High** | `validate_graph()` with cyclic input should return `ok=False`; currently `ok=True` |
| `arc plan explain` no test for multi-command sequence | **Medium** | `--` separator parsing tested; multi-command plan_id stability untested |
| `arc plan apply` stop-on-first-failure not tested | **Low** | Sequential execution with early exit on non-zero code |
| `DagPlannerViz` live data source | **Low** | Component is stub; source wiring entirely untested |

---

## 6. Improved Implementation Prompt

**Target:** Fix the three most impactful gaps: `NotificationBackendService` env allowlist, badge auto-refresh, and IR cycle detection.

```
# Notifications/Planner Next Slice: Env Fix + Auto-Refresh + Cycle Detection

## Context

ARC Studio v0.8-r-ux2. Three gaps:

1. NotificationBackendService spawns 'arc events summary --json' with no
   env argument, passing full process.env to the child process including
   all API keys (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.). All other
   CLI-bridge services use buildArcCliEnv().

2. NotificationBackendService has no polling loop. getCounts() is called
   only when triggered externally (e.g., on widget mount). Badge counts
   are stale between explicit triggers. The IDE has no auto-refresh for
   HITL notifications.

3. IR validate_graph() in swarmgraph_ir/validation.py has no cycle
   detection. A cyclic graph (A→B→C→A) passes validation with ok=True.
   This allows malformed workflows to reach the policy linter and
   downstream execution paths without being rejected.

## Scope

### 1. Fix NotificationBackendService env allowlist

File: packages/arc-extension/src/node/services/notification-service.ts

```typescript
import { buildArcCliEnv } from './arc-cli-utils';

async #execCli(args: string[]): Promise<string> {
    return new Promise<string>((resolve, reject) => {
        // ADD env: buildArcCliEnv()  ← fixes the missing env allowlist
        const child = spawn('arc', args, {
            shell: false,
            env: buildArcCliEnv(),  // ← ADD THIS
        });
        // ... rest unchanged ...
    });
}
```

Tests: packages/arc-extension/src/node/services/__tests__/notification-service.test.ts (add):
- `test_spawn_uses_env_allowlist` — mock spawn; assert `options.env` does not
  contain `OPENAI_API_KEY`; assert it contains `PATH`.

### 2. Add auto-refresh polling to NotificationBackendService

File: packages/arc-extension/src/node/services/notification-service.ts

```typescript
import { injectable, postConstruct, preDestroy } from '@theia/core/shared/inversify';

@injectable()
export class NotificationBackendService {
    private _counts: NotificationCounts = { hitl: 0, runFailures: 0, auditAlerts: 0 };
    private _pollInterval: ReturnType<typeof setInterval> | undefined;
    private readonly POLL_INTERVAL_MS = 30_000;  // 30 seconds

    @postConstruct()
    protected init(): void {
        this._pollInterval = setInterval(async () => {
            this._counts = await this.getCounts();
        }, this.POLL_INTERVAL_MS);
    }

    @preDestroy()
    protected dispose(): void {
        if (this._pollInterval) {
            clearInterval(this._pollInterval);
            this._pollInterval = undefined;
        }
    }

    get currentCounts(): NotificationCounts {
        return this._counts;
    }

    async getCounts(): Promise<NotificationCounts> {
        // ... existing implementation ...
    }
}
```

Also add to arc-protocol.ts:
```typescript
subscribeToNotifications?(callback: (counts: NotificationCounts) => void): () => void;
```

Note: public SSE/WebSocket push remains deferred per R53.
This 30s poll is purely a quality-of-life improvement; it uses the same
CLI path that already works.

### 3. Add cycle detection to IR validate_graph()

File: python/src/agent_runtime_cockpit/swarmgraph_ir/validation.py

```python
def _detect_cycles(nodes: list, edges: list) -> list[str]:
    """DFS cycle detection. Returns list of error strings for any cycle found."""
    from collections import defaultdict
    
    adj: dict[str, list[str]] = defaultdict(list)
    for edge in edges:
        adj[edge.from_node].append(edge.to_node)
    
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {n.id: WHITE for n in nodes}
    path: list[str] = []
    errors: list[str] = []
    
    def dfs(node_id: str) -> bool:
        color[node_id] = GRAY
        path.append(node_id)
        for neighbor in adj.get(node_id, []):
            if color.get(neighbor) == GRAY:
                cycle_start = path.index(neighbor)
                cycle = "→".join(path[cycle_start:] + [neighbor])
                errors.append(f"cycle detected: {cycle}")
                path.pop()
                return True
            if color.get(neighbor) == WHITE:
                if dfs(neighbor):
                    path.pop()
                    return True
        color[node_id] = BLACK
        path.pop()
        return False
    
    for node in nodes:
        if color[node.id] == WHITE:
            dfs(node.id)
    
    return errors

def validate_graph(graph: IRGraph) -> IRValidationReport:
    errors: list[str] = []
    warnings: list[str] = []
    
    # ... existing checks ...
    
    # ADD cycle detection:
    cycle_errors = _detect_cycles(graph.nodes, graph.edges)
    errors.extend(cycle_errors)
    
    return IRValidationReport(
        ok=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        node_count=len(graph.nodes),
        edge_count=len(graph.edges),
    )
```

Tests: python/tests/swarmgraph_ir/test_validation.py (add):
```python
def test_validate_graph_rejects_direct_cycle():
    # A → B → A
    nodes = [IRNode(id="A", ...), IRNode(id="B", ...)]
    edges = [IREdge(from_node="A", to_node="B"), IREdge(from_node="B", to_node="A")]
    report = validate_graph(IRGraph(nodes=nodes, edges=edges, ...))
    assert not report.ok
    assert any("cycle" in e for e in report.errors)

def test_validate_graph_rejects_self_loop():
    # A → A
    nodes = [IRNode(id="A", ...)]
    edges = [IREdge(from_node="A", to_node="A")]
    report = validate_graph(IRGraph(nodes=nodes, edges=edges, ...))
    assert not report.ok

def test_validate_graph_accepts_diamond_dag():
    # A → B, A → C, B → D, C → D (no cycle)
    report = validate_graph(...)
    assert report.ok
```

### 4. Remove NotificationOutbox dead code

File: python/src/agent_runtime_cockpit/notifications/outbox.py — DELETE
File: python/src/agent_runtime_cockpit/notifications/__init__.py — DELETE (already empty)

This removes dead code that has no consumers, no tests, and is superseded
by `swarmgraph/notifications.py::DurableNotificationOutbox`.

Update imports in any file that references `notifications.outbox` (none found).

## Do NOT do in this slice

- Public SSE/WebSocket push product route (explicitly deferred, R53)
- EventBrokerNotificationHook fix (separate event bridge slice)
- DagPlannerViz D3 visualization (separate DAG viz slice)
- Plan-to-run handoff UI (separate orchestration slice)
- Notification tray (separate UI slice)

## Verification

```bash
cd python && uv run pytest tests/swarmgraph_ir/test_validation.py -q
pnpm --filter arc-extension test
```
```

---

## Appendix: Phase 110 status for notifications/planner

Per `docs/phases.md` and `docs/roadmap.md` (R53 — Phase 110 — Baseline Complete):

> "This phase does not claim public SSE/WebSocket product routing, provider-backed auto planning, or broad provider-backed SwarmGraph adoption."

**What was shipped in Phase 110:**
- `DurableNotificationOutbox` + `ManagedNotificationService` + `WebhookNotificationHook` + `DurableWebhookNotificationHook` — webhook delivery with retry, JSONL outbox, event filtering
- `EventBrokerNotificationHook` — defined but permanently broken (import target missing, gate off)
- Deterministic DAG planner: `DAGPlan`, `TrivialDecomposition`, `parallelizability_score`, `arc swarmgraph plan` CLI
- Narrow live E2E proven for CrofAI/DeepSeek V4 Pro Precision opt-in

**What remains deferred:**
- Public SSE/WebSocket product routing for SwarmGraph live events
- Provider-backed auto planning
- IDE live DAG visualization
- EventBrokerNotificationHook functional wiring
