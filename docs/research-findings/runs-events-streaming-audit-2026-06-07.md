# ARC Studio Runs / Events / Streaming Architecture Audit — 2026-06-07

> **Scope:** Run lifecycle, trace parser, event schema, active streams, SSE/WebSocket transport, run timeline UI, event stream UI, receipts, failure autopsy, cancellation, live-run product path  
> **Source:** Synthesized from prior sessions + direct reads of RunLifecycleService, TraceParser, ArcEventStreamWidget, ArcRunTimelineWidget

---

## 1. Runs / Events Architecture Map

```
┌──────────────────────────────────────────────────────────────────────┐
│                   RUNS / EVENTS ARCHITECTURE                          │
├──────────────────────────────────────────────────────────────────────┤
│  PYTHON DAEMON (127.0.0.1:7777)                                       │
│                                                                       │
│  EventBroker (in-process pub/sub)                                     │
│  ├── RingBuffer(1000) per run_id — drop-oldest on full                │
│  ├── mark_active(run_id) / mark_inactive(run_id) / end_run(run_id)   │
│  ├── GET /api/runs/{run_id}/events?mode=live   → SSE stream           │
│  │     reconnect via Last-Event-ID header                             │
│  └── GET /api/runs/{run_id}/events?mode=replay → stored JSONL        │
│                                                                       │
│  Event producers → EventBroker:                                       │
│  ✅ SwarmGraph runtime (fake_offline): SWARMGRAPH_TOPOLOGY/CONSENSUS/COST │
│  ✅ Sandbox decisions: SHELL_DENIED, NETWORK_DENIED, PAID_CALL_DENIED │
│  ✅ HITL: HITL_PROMPT, HITL_RESPONSE, HITL_TIMEOUT                   │
│  ✅ Run lifecycle: RUN_STARTED, RUN_COMPLETED, RUN_FAILED, RUN_CANCELLED │
│  ✅ Tool calls: TOOL_CALL, TOOL_CALL_RESULT, TOOL_CALL_ERROR          │
│  ✅ Messages: MESSAGE, TEXT_MESSAGE_START/CONTENT/END                 │
│  ❌ SwarmGraph SDK events (topology/consensus/hitl) — NOT bridged     │
│  ❌ SWARMGRAPH_COST measured=True from real provider (caller-supplied) │
│                                                                       │
│  JsonlTraceStore: ~/.arc/traces/{run_id}.jsonl                        │
│  ├── Traces written by Python runtime on run completion               │
│  └── Read by: arc runs replay, arc runs trace, IDE readTrace()        │
│                                                                       │
│  Receipts/Autopsy/Contract:                                           │
│  ├── ~/.arc/traces/{run_id}.receipt.json (RunReceipt)                 │
│  ├── ~/.arc/traces/{run_id}.autopsy.json (FailureAutopsy)             │
│  └── ~/.arc/traces/{run_id}.contract.json (RunContract)               │
├──────────────────────────────────────────────────────────────────────┤
│  NODE BACKEND (Theia)                                                 │
│                                                                       │
│  RunLifecycleService:                                                 │
│  ├── executeWorkflow() → WorkflowExecutor (async, non-blocking)       │
│  ├── startRun() → execFileSync('arc', [...], {timeout:120000})        │
│  │   ⚠️ BLOCKING 120s on main thread — freezes IDE backend           │
│  ├── preflightRun() → execFileSync('arc run --dry-run', {timeout:10000}) │
│  ├── cancelWorkflow() → WorkflowExecutor.cancelWorkflow()             │
│  ├── streamActiveTrace(mode=live|replay) → AsyncIterable<chunk>       │
│  │   ⚠️ AsyncIterable NOT JSON-RPC serializable via Theia proxy      │
│  │   ✅ readActiveTraceStream() buffers all chunks → JSON-RPC safe   │
│  │   ✅ cancelActiveTraceStream() per runId cancelToken              │
│  ├── Live mode: fetch() to Python daemon /api/runs/{id}/events        │
│  │   ✅ 5-retry exponential backoff (2s base, 30s max, +jitter)      │
│  │   ✅ lastEventId header for resume                                 │
│  │   ✅ timeout 30s-300s clamped                                      │
│  └── Replay mode: execFileSync('arc runs replay', {timeout:30000})   │
│                                                                       │
│  TraceParser:                                                         │
│  ├── parseJsonlContent(): 3 formats (single obj, per-event JSONL,    │
│  │   ARC trace with events[])                                         │
│  ├── streamTrace(): ReadStream with line buffer                       │
│  │   ⚠️ No buffer size limit — large traces can OOM                  │
│  └── normalizeStatus(): completed/success/ok→completed, failed→failed │
├──────────────────────────────────────────────────────────────────────┤
│  IDE BROWSER                                                          │
│                                                                       │
│  ArcEventStreamWidget (accessible, has contribution)                 │
│  ├── 220px trace list sidebar                                        │
│  ├── VirtualizedEventList (bounded ✅)                               │
│  ├── 7 StreamMode states                                             │
│  ├── Event type chip filters                                         │
│  ├── 5-retry reconnect loop (own copy of retry logic)               │
│  ├── PolicyBypassBanner on POLICY_BYPASS_WARNING events             │
│  └── activeStreamToken to cancel stale streams                      │
│                                                                       │
│  ArcRunTimelineWidget (⚠️ DEAD CODE — no contribution file)         │
│  ├── Timeline view with event icons                                  │
│  ├── No VirtualizedEventList (raw array)                             │
│  └── No reconnect logic                                              │
│                                                                       │
│  RunsTab (in ArcStudioWidget):                                       │
│  ├── getTraces() → run list                                          │
│  ├── getRunReceipt() / getRunAutopsy() / getRunContract() → .catch(() => null) │
│  └── diffRuns() → compare two runs                                   │
│                                                                       │
│  SwarmGraphInsightTab:                                               │
│  ├── readTrace() for stored traces                                   │
│  └── streamActiveTrace() for live mode                              │
│                                                                       │
│  ChatTab:                                                            │
│  ├── startRun() — fire-and-forget (BLOCKING ⚠️)                     │
│  └── Transcript: local React state (ephemeral, not persisted)       │
└──────────────────────────────────────────────────────────────────────┘
```

### Transport: SSE only (no WebSocket)

| Transport | Used for | Notes |
|---|---|---|
| SSE (EventSource / fetch stream) | Live run events `/api/runs/{id}/events?mode=live` | Python daemon → Node backend (fetch) → IDE (via ArcService RPC) |
| SSE | IDE notification badges `/api/events/stream` | Session/HITL/quota event counts |
| JSON-RPC (WebSocket) | All ArcService calls between IDE browser ↔ Node backend | Single WebSocket channel `/services/arc` |
| `execFileSync` / `execFile` | CLI bridge for replay, preflight, capabilities | Subprocess spawns |

**No WebSocket at the Python daemon level.** All live event streaming from the daemon is SSE over HTTP.

---

## 2. Producer / Consumer Matrix

### Event producers (Python runtime)

| Producer | Event types | Delivery path | Bounded |
|---|---|---|---|
| SwarmGraph `fake_offline` runner | SWARMGRAPH_TOPOLOGY, SWARMGRAPH_CONSENSUS, SWARMGRAPH_COST, RUN_STARTED, RUN_COMPLETED | EventBroker → SSE | RingBuffer(1000) |
| SwarmGraph SDK internal events | `SwarmGraphEventKind.*` (topology, consensus, hitl, arena_vote) | **NOT bridged to EventBroker** | — |
| Run lifecycle | RUN_STARTED, RUN_COMPLETED, RUN_FAILED, RUN_CANCELLED | EventBroker → SSE | ✅ |
| Tool calls | TOOL_CALL, TOOL_CALL_RESULT, TOOL_CALL_ERROR | EventBroker → SSE | ✅ |
| HITL | HITL_PROMPT, HITL_RESPONSE, HITL_TIMEOUT | EventBroker + HitlSqliteStore | ✅ |
| Sandbox | SHELL_DENIED, NETWORK_DENIED, PAID_CALL_DENIED, POLICY_BYPASS_WARNING | EventBroker + audit chain | ✅ |
| Budget | QUOTA_WARNING, CONTEXT_COMPACTED | EventBroker | ✅ |
| Messages | MESSAGE, TEXT_MESSAGE_* | EventBroker | ✅ |
| Audit | AUDIT_CHAIN_* | Local JSONL (not EventBroker) | N/A |

### Event consumers (IDE side)

| Consumer | Source | Live capable | Virtualized | Bounded |
|---|---|---|---|---|
| ArcEventStreamWidget | readTrace() + streamActiveTrace() | ✅ (live mode) | ✅ VirtualizedEventList | ✅ (virtualized) |
| ArcRunTimelineWidget | readTrace() + streamActiveTrace() | ✅ (basic) | ❌ raw array | ❌ |
| SwarmGraphInsightTab | readTrace() + streamActiveTrace() | ✅ | N/A | N/A |
| RunsTab | getTraces() | ❌ replay only | ❌ | 100-row cap |
| AssuranceTab | HITL: listPendingHitlPrompts() + 10s poll | ❌ | ❌ | ❌ |
| NotificationBadge | getCounts() → CLI poll | ❌ poll | N/A | N/A |

---

## 3. Live vs Replay Truth Table

| Surface | Data source | Is it live? | Is it honest about it? |
|---|---|---|---|
| ArcEventStreamWidget — replay-trace mode | `readTrace()` → stored JSONL | ❌ replay | ✅ "Replay trace mode" label |
| ArcEventStreamWidget — live mode | SSE proxy to Python daemon | ✅ live | ✅ "Live stream active" label |
| ArcRunTimelineWidget — replay mode | `readTrace()` → stored JSONL | ❌ replay | ✅ |
| ArcRunTimelineWidget — live mode | SSE proxy | ✅ | ✅ basic status |
| SwarmGraphInsightTab — stored trace | `readTrace()` → JSONL | ❌ replay | ✅ anti-hallucination invariant tested |
| SwarmGraphInsightTab — live frame | `streamActiveTrace()` | ✅ | ✅ "Live insight" label |
| RunsTab | `getTraces()` + `getRunReceipt()` | ❌ replay only | ✅ "replay-only label enforcement" in contract test |
| ChatTab transcript | Local React state | ❌ local only | ⚠️ no "not persisted" warning |
| AssuranceTab HITL | `listPendingHitlPrompts()` 10s poll | ⚠️ eventually consistent | ✅ shows "last refreshed" timestamp |
| CommandCentreTab run list | `getRunReceipt()` calls | ❌ stored only | ✅ "read-only" labels |
| NotificationBadge counts | `arc events summary --json` CLI | ❌ local/recent | ✅ `source: "local_event_log_recent"` in response |

**Summary:** UI surfaces are generally honest about live vs stored distinction. The main gap is ChatTab transcript being local React state with no warning that it will be lost on page refresh.

### Buffer bounds

| Surface | Buffer bounded? | Details |
|---|---|---|
| EventBroker (Python) | ✅ RingBuffer(1000) | Drop-oldest on full |
| VirtualizedEventList (IDE) | ✅ | Uses virtual list, renders only visible rows |
| ArcEventStreamWidget.liveEvents | ⚠️ unbounded array | Accumulates all live events in memory: `[...this.liveEvents, event]` |
| ArcRunTimelineWidget.liveEvents | ❌ unbounded | Same pattern |
| TraceParser.streamTrace() | ⚠️ | ReadStream buffer, no max-line or max-byte guard |
| readActiveTraceStream() | ⚠️ | Buffers ALL chunks from stream — no cap |
| ReplayResult.events[] | ⚠️ | All events from `arc runs replay` loaded into memory |

---

## 4. UI Gap Analysis

### Run start / active run panel

**Critical gap:** There is no active run panel anywhere in the IDE. When a user clicks "Start Run" in ChatTab:
1. `startRun()` calls `execFileSync('arc run ...', {timeout: 120000})` — **blocks the Node backend thread for up to 2 minutes**
2. No progress indicator, no cancel button, no streaming output is shown
3. The run completes in the CLI subprocess; the result appears only after `execFileSync` returns
4. ChatTab transcript shows a "Run completed" message but it is local state (lost on reload)
5. No link from ChatTab to RunsTab for the specific run that just completed

This is the biggest product gap in the IDE: the primary workflow action (running an agent) has no live feedback UI.

### Run list / detail (RunsTab)

| Gap | Detail |
|---|---|
| No streaming in RunsTab | Shows completed runs only; no indication a run is currently active |
| Receipts are `.catch(() => null)` | `getRunReceipt`, `getRunAutopsy`, `getRunContract` silently fail; RunReceiptCard never shown if CLI fails |
| `diffRuns` backed by CLI | `arc runs diff` subprocess; no streaming diff |
| No run cancellation button | `cancelWorkflow()` exists but no UI surface calls it |
| 100-row hard cap in `arc runs search` | TUI; IDE has no cap but loads all from `getTraces()` |

### ArcEventStreamWidget gaps

| Gap | Detail |
|---|---|
| `liveEvents` array unbounded | `[...this.liveEvents, event]` grows forever during live stream; VirtualizedEventList bounds the display but not the memory |
| No run ID linkage to RunsTab | Selecting a trace in EventStreamWidget doesn't navigate RunsTab to same run |
| 7 stream states but UI shows only text | Complex states (reconnecting, live-error) shown as plain text, no visual indicator |
| No cancel stream button | User cannot manually stop a live stream; only auto-cancels on trace switch |

### Receipts / Autopsy / Contract

| Gap | Detail |
|---|---|
| All 3 artifact fetches use `.catch(() => null)` | If CLI fails or files missing, no error shown to user; cards silently absent |
| No indication when artifacts are missing vs loading | RunsTab shows placeholder for both states |
| RunReceiptCard shows evidence refs (EvidenceChip) | ✅ wired and clickable; emits `EvidenceSelectionEvent` |
| FailureAutopsyCard shows probable_cause | ✅ shows knows/guesses/retry options |
| No link from failure autopsy to replay | AssuranceTab has replay stepper; RunsTab failure autopsy does not link to it |

### Cancellation

| Surface | Cancellation | Reliability |
|---|---|---|
| `cancelWorkflow()` (WorkflowExecutor) | SIGTERM then SIGKILL to process group | ✅ reliable for subprocess path |
| `cancelActiveTraceStream()` | Sets `cancelToken.cancelled=true`; removes from Map | ✅ but async — in-flight chunk may be yielded before check |
| ArcEventStreamWidget `activeStreamToken` | Increments on trace switch; old stream detects stale token | ✅ per-stream token guards stale streams |
| ArcRunTimelineWidget | No explicit cancellation | ❌ stale streams not cancelled on trace switch |
| `startRun()` blocking `execFileSync` | No cancellation possible | ❌ 120s block cannot be interrupted |
| ChatTab "cancel run" | ❌ no cancel button | — |

---

## 5. Reliability Risk Report

### High severity

| Risk | Detail |
|---|---|
| `startRun()` blocks Node backend main thread for 120s | `execFileSync('arc run ...', {timeout:120000})` — all other IDE backend JSON-RPC calls block while a run is executing |
| `streamTrace()` has no buffer size limit | `ReadStream` with line buffer — a 100 MB trace file will be fully loaded into Node memory |
| `readActiveTraceStream()` buffers entire stream | `for await...` collects all chunks before returning; no cap |
| SwarmGraph SDK events never reach EventBus | Topology/consensus/hitl events from SDK layer are invisible to any live stream consumer |
| `liveEvents` array unbounded in both widgets | Long-running streams accumulate all events in JavaScript heap |

### Medium severity

| Risk | Detail |
|---|---|
| `execFileSync` for `replayRun()` blocks 30s | Replay used in active stream replay mode; blocks during replay |
| `execFileSync` for `listRuntimeCapabilities()` blocks 10s | Called on widget init; blocks IDE startup |
| TraceParser has no per-line size limit | A single very long JSONL line (e.g., a 10 MB base64 tool output) will be parsed in-memory |
| Run ID format inconsistency | Python generates `run-sg-{hex}`, `run-lg-{hex}`, `run-ca-{hex}` etc.; TypeScript `_validate_run_id` regex requires `^run[-_]...` — these may not match older run IDs |
| `cancelToken` map never cleaned up on stream end in finally block | `activeStreamCancels.delete(request.runId)` is in `finally` — but the outer `streamActiveTrace()` creates a new token per call; Map can accumulate stale entries for orphaned streams |

### Low severity

| Risk | Detail |
|---|---|
| ChatTab transcript is ephemeral | Lost on page reload; not persisted to session store; not linked to run trace |
| `streamTrace()` returns `AsyncIterable` — not serializable | Method exists on `ArcService` interface but Theia JSON-RPC proxy cannot serialize it; only `readActiveTraceStream()` (buffered) is usable in practice |
| ArcRunTimelineWidget is dead code | No contribution file; widget unreachable |
| `MESSAGE` event schema mismatch | Registry expects `text` field; typed model expects `message_id+role+content`; `coalesce_chunks()` produces text-only; `MessageEvent.model_validate()` will fail |
| `AssuranceTab` HITL count not persistent | `_age()` returns `""` for ISO string timestamps (real records); age column always empty |
| `liveEvents` uses spread `[...liveEvents, event]` | O(n) array copy on every event; at 10,000 events this becomes a performance problem |

---

## 6. Improved Implementation Prompt

**Target:** Three slices that unblock the live-run product path without requiring the full SwarmGraph event bridge.

```
# Runs/Events Next Slice: Active Run Panel + Async startRun + Bounded Buffers

## Context

ARC Studio v0.8-r-ux2. Three reliability/product gaps:

1. startRun() uses execFileSync with a 120s timeout — this blocks the
   entire Node.js backend during a run. All IDE JSON-RPC calls (including
   tab refreshes, status bar updates, and HITL notifications) are frozen
   while a run executes. Users have no visible progress and no cancel button.

2. liveEvents arrays in ArcEventStreamWidget and ArcRunTimelineWidget grow
   without bound using [...this.liveEvents, event]. A 10,000-event run
   accumulates 10,000 TraceEvent objects in JavaScript heap before any are
   GC'd. VirtualizedEventList bounds the display but not the memory.

3. ChatTab has no link to the run it just started. After startRun() returns,
   the run ID (from StartRunResponse.runId) is discarded; there is no
   navigation to RunsTab or live stream for the completed run.

## Scope

### Slice A: Convert startRun to non-blocking async (highest priority)

File: packages/arc-extension/src/node/services/run-lifecycle-service.ts

Replace execFileSync with async execFile + streaming progress:

```typescript
import { execFile } from 'child_process';
import { promisify } from 'util';
const execFileAsync = promisify(execFile);

async startRun(request: StartRunRequest): Promise<StartRunResponse> {
    // Build args (same as before)
    const args = ['run', request.workflow || 'crew.py', ...];

    // Use execFileAsync instead of execFileSync
    const { stdout } = await execFileAsync('arc', args, {
        timeout: 120000,
        encoding: 'utf-8',
        windowsHide: true,
        env: buildArcCliEnv(),
    });
    // parse stdout same as before...
}
```

This releases the Node.js event loop during the 120s run. All other IDE
RPC calls (status bar, HITL, notifications) will continue to work normally.

Also convert: listRuntimeCapabilities() (10s), replayRun() (30s),
preflightRun() (10s) — all currently use execFileSync.

Tests: packages/arc-extension/src/node/__tests__/arc-service.integration.test.ts
- Add test that startRun does not block: start a mock slow process,
  assert another RPC call completes before it finishes.

### Slice B: Cap liveEvents buffer in ArcEventStreamWidget

File: packages/arc-extension/src/browser/arc-event-stream-widget.tsx

Add a rolling buffer cap:
```typescript
private readonly MAX_LIVE_EVENTS = 2000;

// In runLiveStream(), replace:
this.liveEvents = [...this.liveEvents, event];

// With:
const next = [...this.liveEvents, event];
this.liveEvents = next.length > this.MAX_LIVE_EVENTS
    ? next.slice(-this.MAX_LIVE_EVENTS)  // keep most recent
    : next;
```

Show a banner when events have been evicted:
```tsx
{this.liveEventsEvicted > 0 && (
    <div style={evictionBannerStyle}>
        {this.liveEventsEvicted} earlier events dropped (buffer cap {this.MAX_LIVE_EVENTS}).
    </div>
)}
```

Track eviction count: `this.liveEventsEvicted += next.length - this.MAX_LIVE_EVENTS`.

Apply same fix to ArcRunTimelineWidget if it's kept.

### Slice C: Post-run navigation from ChatTab to RunsTab

File: packages/arc-extension/src/browser/tabs/ChatTab.tsx

After `startRun()` returns a `StartRunResponse`:
1. Store `response.runId` in local state.
2. Show a "View in Runs" link button that calls `onNavigateToRuns(runId)`.
3. The `onNavigateToRuns` callback already exists in ArcStudioWidget
   and switches the active tab to 'runs' with `initialRunId`.

```tsx
{this.state.lastRunId && (
    <button
        className="arc-studio-chat__run-link"
        onClick={() => this.props.onNavigateToRuns?.(this.state.lastRunId!)}
        aria-label={`View run ${this.state.lastRunId} in Runs tab`}
    >
        View run in Runs tab →
    </button>
)}
```

### Slice D: Fix MESSAGE event schema mismatch

File: python/src/agent_runtime_cockpit/protocol/typed_events.py

The registry defines MESSAGE with `required_fields={"text"}`.
The typed `MessageData` class requires `message_id`, `role`, `content`.
`coalesce_chunks()` produces `{"text": ..., "coalesced": True}` —
this fails `MessageEvent.model_validate()`.

Fix by adding `text: str | None = None` to `MessageData` OR updating
the registry to match the typed model:

```python
class MessageData(BaseModel):
    message_id: str
    role: str
    content: str
    text: str | None = None        # backward compat alias for coalesce path
    source: str | None = None
    coalesced: bool | None = None
```

Test: add to tests/protocol/test_message_event_schema.py (new):
```python
def test_coalesced_message_passes_model_validate():
    data = {"text": "hello", "source": "agent", "coalesced": True}
    event = MessageEvent.model_validate({"type": "MESSAGE", "timestamp": "...",
                                         "run_id": "r", "sequence": 1, "data": data})
    assert event.data.text == "hello"
```

### Slice E: Remove ArcRunTimelineWidget dead code

File: packages/arc-extension/src/browser/arc-run-timeline-widget.tsx — DELETE
File: packages/arc-extension/src/browser/arc-extension-frontend-module.ts

Remove the 3-line factory registration:
```typescript
// DELETE:
bind(ArcRunTimelineWidget).toSelf();
bind(WidgetFactory).toDynamicValue(ctx => ({
    id: 'arc:run-timeline',
    createWidget: () => ctx.container.get(ArcRunTimelineWidget)
})).inSingletonScope();
bindViewContribution(bind, ArcRunsContribution);
bind(FrontendApplicationContribution).toService(ArcRunsContribution);
```

Note: ArcEventStreamWidget (which HAS a contribution file) should be kept.
It provides VirtualizedEventList, 7-state reconnect, PolicyBypassBanner,
and per-type chip filtering — superior to the timeline widget in every way.

## Do NOT do in this slice

- Full SwarmGraph event bridge (separate SwarmGraph slice)
- Run timeline D3 visualization
- Large trace file pagination (separate trace slice)
- `readActiveTraceStream()` streaming cursor (requires protocol change)

## Verification

```bash
cd python && uv run pytest tests/ -q  # all Python tests
pnpm typecheck && pnpm build           # TypeScript + bundle
```

---

## Appendix: Run ID stability across CLI and IDE

| Surface | Run ID format | Stable? |
|---|---|---|
| SwarmGraph CLI subprocess | `run-sg-{8hexchars}` | ✅ UUID-derived |
| LangGraph adapter | `run-lg-{8hexchars}` | ✅ |
| CrewAI adapter | `run-ca-{8hexchars}` | ✅ |
| `arc runs search` (SQLite) | same formats | ✅ |
| TypeScript `validateRunId()` regex | `^run[-_][a-zA-Z0-9]+(?:[-_][a-zA-Z0-9]+)*$` | ✅ matches all formats |
| MCP `_SAFE_ID_RE` | `^run-(sg|lg|ca|openai)-[a-f0-9]+$` | ✅ matches all formats |
| Storage JSONL path | `{workspace}/.arc/traces/{run_id}.jsonl` | ✅ direct map |
| Receipt/Autopsy/Contract | `{workspace}/.arc/traces/{run_id}.{receipt|autopsy|contract}.json` | ✅ |

Run IDs are stable and consistent across CLI and IDE. The TypeScript regex is slightly more permissive than the MCP regex but both accept the same real run ID formats.

## Appendix: Event Schema Issues

| Issue | Severity | Detail |
|---|---|---|
| MESSAGE event schema mismatch | **Medium** | Registry expects `text`; TypeScript typed model expects `message_id+role+content`; `coalesce_chunks()` produces text-only |
| SWARMGRAPH_TOPOLOGY.nodes/edges are `list[Any]` | Low | No inner schema; IDE cannot navigate topology elements |
| SWARMGRAPH_CONSENSUS.votes is `list[Any]` | Low | No inner schema |
| SWARMGRAPH_* not in `KnownTraceEventType` TypeScript enum | Low | Open-string only; no compile-time type safety |
| Denial events (TRUST_DENIED, PAID_CALL_DENIED, etc.) typed but not in `KnownRunEvent` union | Low | Unreachable via `parse_typed_event()`; fall through to UnknownEvent |
| Contract/Receipt events registry-only (no Pydantic models) | Low | CONTRACT_PROPOSED etc. have no typed models |
