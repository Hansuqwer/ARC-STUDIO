# 06 — Event Stream and SSE

## Existing Implementation

**EventBroker:** `python/src/agent_runtime_cockpit/orchestration/event_broker.py` (196 lines) [EXISTS]
- `publish(run_id, event)` → broadcasts to all subscribers
- `subscribe(run_id)` → returns `asyncio.Queue`
- `stream_live(run_id, last_event_id)` → async iterator for SSE
- `sse_handler(request)` → `aiohttp.web.StreamResponse`
- Heartbeat interval: 15s, Queue max: 1000, drop-oldest on overflow

**Event registry:** `python/src/agent_runtime_cockpit/protocol/events.py` (184 lines) [EXISTS]
- 27 registered event types: `RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`, `RUN_CANCELLED`, `STEP_*`, `AGENT_*`, `TOOL_CALL_*`, `NODE_*`, `MESSAGE_*`, `TEXT_MESSAGE_*`, `STATE_SNAPSHOT`, `HITL_*`, `HANDOFF`, `RAW`, `CUSTOM`

**SSE endpoint:** `python/src/agent_runtime_cockpit/web/routes.py:352-381` — `GET /api/runs/{run_id}/events`

**Schema:** `python/src/agent_runtime_cockpit/protocol/schemas.py:109-115` — `RunEvent` with `schema_version`, `type`, `timestamp`, `run_id`, `sequence`, `data`

## What To Add

### New Event Types for Cockpit Primitives

Add to `events.py`:
- `CONTRACT_PROPOSED` — RunContract proposed
- `CONTRACT_ACCEPTED` — RunContract accepted by user
- `CONTRACT_FULFILLED` — RunContract fulfilled on completion
- `CONTRACT_VIOLATED` — RunContract violated
- `RECEIPT_GENERATED` — RunReceipt generated
- `FAILURE_AUTOPSY_GENERATED` — FailureAutopsy generated
- `EVIDENCE_REF_CREATED` — EvidenceRef attached to event

### SSE Protocol (existing, unchanged)

```
GET /api/runs/{run_id}/events

data: {"schema_version":1,"type":"RUN_STARTED","timestamp":"...","run_id":"...","sequence":0,"data":{"contractId":"..."}}

data: {"schema_version":1,"type":"CONTRACT_PROPOSED","timestamp":"...","run_id":"...","sequence":1,"data":{"contract":{...}}}

data: {"schema_version":1,"type":"RUN_COMPLETED","timestamp":"...","run_id":"...","sequence":5,"data":{"receiptId":"...","autopsy":null,"evidenceRefs":[]}}

data: {"type":"STREAM_END"}
```

### Live Event Flow

```
1. User submits run request
2. Supervisor creates RunRecord (PENDING), RunContract (PROPOSED)
3. Supervisor publishes RUN_STARTED + CONTRACT_PROPOSED
4. SSE streams to frontend
5. Frontend shows RunContractCard
6. User accepts contract → POST /api/runs/contract/{id}/accept
7. Supervisor publishes CONTRACT_ACCEPTED → run starts (RUNNING)
8. Events stream live during execution
9. On completion: RUN_COMPLETED + RECEIPT_GENERATED
10. On failure: RUN_FAILED + FAILURE_AUTOPSY_GENERATED
```

## Frontend Integration

**Existing trace parser:** `packages/arc-extension/src/node/services/trace-parser.ts` (325 lines)

**What to extend:**
- `TraceParser.parseTrace()` should handle new event types
- New `ArcService` methods:
  - `streamEvents(runId: string): AsyncIterable<SSEEvent>` — live SSE subscription
  - `acceptContract(contractId: string): Promise<void>`
  - `getReceipt(runId: string): Promise<RunReceipt>`
  - `getAutopsy(runId: string): Promise<FailureAutopsy>`

## Test Locations

| Test | File |
|------|------|
| EventBroker unit | `python/tests/test_event_broker.py` |
| SSE endpoint | `python/tests/web/` |
| Event registry | `python/tests/test_events.py` |

## Likely Failure Modes

1. **Heartbeat timeout disconnect** — client-side reconnection with `Last-Event-ID`
2. **Queue overflow** — slow clients drop oldest events; `QUEUE_MAX_SIZE = 1000`
3. **SSE after run complete** — `stream_live()` falls back to `replay()` from JSONL
4. **Contract not accepted** — run should NOT start until accepted; timeout policy

## Do Not Implement Yet

- Replay scrubber — v0.1 out-of-scope
- Event JSON viewer in default UI — v0.1 out-of-scope
- `PHASE_HANDOFF` event type — reserved v0.2 (naming collision with existing `HANDOFF`) [RESERVED]
