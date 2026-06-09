# R87 ARC Stream — Real-Time Event Relay Audit

Date: 2026-06-09
Auditor: Agentic Auditor
Repository: Hansuqwer/ARC-STUDIO @ e2526c3
Scope: Python daemon → Node backend → IDE event streaming path. Identify the minimum-touch
change to eliminate polling fallback and guarantee real-time delivery.

---

## 1. Current Architecture (Verified from Source)

```
┌─────────────────────────────────────────────────────────────────────┐
│  Python Daemon (127.0.0.1:7777)                                     │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ EventBroker (orchestration/event_broker.py)                  │   │
│  │  • RingBuffer(1000) per run_id — drop-oldest on full         │   │
│  │  • asyncio.Queue(maxsize=1000) per subscriber                │   │
│  │  • SSE handler: /api/runs/{run_id}/events?mode=live|replay   │   │
│  │  • Heartbeat: 15s (comment lines to keep connection alive)   │   │
│  │  • Terminal events: RUN_COMPLETED, RUN_FAILED, RUN_CANCELLED │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │ SSE (text/event-stream)               │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ Node Backend (Theia extension host)                          │   │
│  │  • ArcService.streamActiveTrace() → fetch() to Python SSE   │   │
│  │  • Reads SSE chunks, buffers into AsyncIterable<chunk>      │   │
│  │  • Proxies to IDE via JSON-RPC (Theia service protocol)     │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              │ JSON-RPC                              │
│                              ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ IDE Browser (ArcEventStreamWidget)                           │   │
│  │  • 7 StreamMode states: replay-trace, live-available, ...   │   │
│  │  • MAX_LIVE_EVENTS = 2000 (frontend memory cap)              │   │
│  │  • 5-retry exponential backoff (2s base, 30s max, +jitter)  │   │
│  │  • activeStreamToken for cancellation                        │   │
│  │  • VirtualizedEventList (bounded DOM rendering)              │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. What Already Works (Do Not Break)

| Component | Status | Evidence |
|---|---|---|
| SSE endpoint | ✅ Functional | `event_broker.py::sse_handler()` serves `text/event-stream` with heartbeat |
| Ring buffer replay | ✅ Functional | `RingBuffer.replay_from(last_event_id)` reconnects missed events |
| Last-Event-ID header | ✅ Functional | Respected in SSE handler for resume |
| Live mode widget | ✅ Functional | `connectLiveStream()` → `runLiveStream()` with retry logic |
| Heartbeat | ✅ Functional | 15s comment: heartbeat keepalive |
| Event types | ✅ 15+ types | RUN_STARTED, RUN_COMPLETED, TOOL_CALL, HITL_PROMPT, etc. |
| Queue backpressure | ✅ Drop-oldest | `asyncio.QueueFull` → `get_nowait()` + `put_nowait()` |

---

## 3. What's Missing — The Polling Fallback

The polling fallback is not in the Python daemon. It is in the IDE's assurance surface.

### 3.1 NotificationBadge — 10-second CLI poll

`AssuranceTab` (and `NotificationBadge` in the status bar) calls `getCounts()` which calls:

```typescript
// packages/arc-extension/src/browser/assurance/notification-badge.ts (inferred)
const counts = await this.arcService.getCounts(); // → execFile('arc status --json')
```

This is a subprocess poll every 10 seconds to check for pending HITL prompts, quota warnings,
and session events. It does **not** use the SSE channel. It spawns a new Python process per poll.

### 3.2 RunsTab — replay-only, no live

`RunsTab` calls `getTraces()` which reads `~/.arc/traces/` directory. It has no real-time event
relay capability. A run must complete before it appears in the runs list.

### 3.3 ArcRunTimelineWidget — dead code, no contribution

The timeline widget exists but is not registered in any `frontend-module.ts`. It cannot be
opened. Even if it were, it has no reconnect logic.

### 3.4 ChatTab — fire-and-forget, no live events

`ChatTab.startRun()` calls `execFileSync('arc run', ...)` which blocks the Node backend for up
to 120 seconds. The run's events are not streamed to the chat transcript. The transcript only
shows the final result.

---

## 4. Gap Summary Table

| Surface | Current | Target | Effort |
|---|---|---|---|
| ArcEventStreamWidget | SSE live + replay ✅ | Already works | — |
| NotificationBadge | 10s CLI poll | Push via SSE `/api/events/stream` | Small |
| RunsTab | Directory scan | Live run registration via SSE | Medium |
| ChatTab | Blocking exec | Non-blocking + live event stream | Medium |
| ArcRunTimelineWidget | Dead code | Revive + SSE live mode | Medium |
| TUI screen | No live events | SSE client in Python (asyncio) | Small |

---

## 5. Minimum-Touch Implementation Plan

### Phase A: Global SSE Stream (1 file, ~80 lines)

Add a global event stream endpoint for system-wide events (HITL, quota, run state changes).

**File to create:** `python/src/agent_runtime_cockpit/stream/websocket.py`
**Stub already written at:** `python/src/agent_runtime_cockpit/stream/websocket.py`

```python
# Global SSE endpoint: /api/events/stream
# Publishes: HITL_PROMPT, HITL_RESPONSE, QUOTA_WARNING, RUN_STARTED, RUN_COMPLETED
# Does NOT publish per-run detailed events (use /api/runs/{id}/events for that)

class GlobalEventBroker:
    """Lightweight pub/sub for system-wide events."""
    _subscribers: list[asyncio.Queue] = []

    def publish(self, event: dict) -> None:
        for queue in self._subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass  # drop oldest — system events are low volume

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue
```

**File to change:** `python/src/agent_runtime_cockpit/web/routes.py`
Add: `app.router.add_get("/api/events/stream", global_sse_handler)`

**File to change:** `python/src/agent_runtime_cockpit/orchestration/event_broker.py`
In `publish()`, also call `global_broker.publish(summarized_event)` for terminal event types.

### Phase B: NotificationBadge Push (IDE side, ~40 lines)

**File to change:** `packages/arc-extension/src/browser/assurance/notification-badge.ts`

Replace the 10s poll with an `EventSource` connection to `/api/events/stream`:

```typescript
// Replace the 10s interval with:
const es = new EventSource('/api/events/stream'); // proxied by Node backend
es.addEventListener('HITL_PROMPT', (e) => this.updateBadge(JSON.parse(e.data)));
es.addEventListener('QUOTA_WARNING', (e) => this.updateBadge(JSON.parse(e.data)));
```

### Phase C: TUI SSE Client (~60 lines)

**File to create:** `python/src/agent_runtime_cockpit/tui/stream_client.py`
(Covered by `TuiEventSource` class in the websocket.py stub.)

Wire into `ArcScreen._check_daemon()` — instead of polling `/health` every 5s, use the SSE
connection for both health and events.

---

## 6. Security Constraints

- **Bind address:** `127.0.0.1` only (already enforced in `server.py`).
- **CORS:** Origin restricted to `http://127.0.0.1:3000` (Theia default) + `ARC_CORS_ORIGIN`.
- **Auth:** Bearer token middleware applies to `/api/events/stream` (reuse `bearer_token_middleware`).
- **No multi-tenant:** Global broker is single-user; no user isolation needed.
- **Rate limiting:** SSE connections are long-lived; no burst risk. Queue size 100 is sufficient
  for system events (~1–10/min).

---

## 7. Files to Create / Change

| File | Action | Lines | Test Target |
|---|---|---|---|
| `stream/websocket.py` | Create (stub) | ~120 | `tests/web/test_events_sse.py` |
| `web/routes.py` | Add route | +2 | Existing route tests |
| `orchestration/event_broker.py` | Hook global publish | +5 | `tests/orchestration/test_event_broker.py` |
| `tui/screen.py` | Wire stream client | +10 | `tests/test_tui_core.py` |
| `packages/arc-extension/src/browser/assurance/notification-badge.ts` | Replace poll with SSE | ~40 | Manual test |
| `packages/arc-extension/src/browser/arc-service.ts` | Add proxy method | +5 | Contract test |

---

## 8. Kiro Session Prompt

> Implement Phase A: Add `/api/events/stream` global SSE endpoint using the stub at
> `python/src/agent_runtime_cockpit/stream/websocket.py`. The endpoint must publish terminal
> run events, HITL events, and quota warnings. Reuse the existing `EventBroker` ring buffer
> logic. Add bearer token auth. Do NOT publish per-run detailed events (keep those on
> `/api/runs/{id}/events`). Add `tests/web/test_events_sse.py` with at least 3 tests: connect,
> receive event, reconnect with missed events. All existing tests must pass
> (`pytest tests/orchestration tests/web -q`).
