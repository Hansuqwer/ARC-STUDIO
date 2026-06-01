# SwarmGraph Notifications, Push Hooks, DAG Planning, Provider E2E Research

Date: 2026-06-01

## Current Reality

- Existing notification hooks live in `python/packages/swarmgraph-sdk/swarmgraph/notifications.py`.
- Existing durable outbox is append-only JSONL; existing runner drains per-run hook tasks before returning.
- Existing ARC `EventBroker` already supports bounded queues, drop-oldest slow-client policy, ring replay, and aiohttp SSE for active runs.
- Existing SwarmGraph decomposition is deterministic/trivial: copy, step, mesh, tree.
- Live provider-backed SwarmGraph E2E now exists as an opt-in skipped-by-default test; local worktree proof passed only for CrofAI `deepseek-v4-pro-precision` with explicit gates.

## Research Notes

| Source | Link/query | What was learned | Implementation consequence | Confidence | Unresolved questions |
|---|---|---|---|---|---|
| Context7 | `Typer`, `Pydantic`, `FastAPI` resolve calls | Tool failed: `Invalid API key. Please check your API key. API keys should start with 'ctx7sk' prefix.` | Recorded failure; used official docs via webfetch plus repo patterns. | High | Configure Context7 API key before next research-gated pass. |
| Typer docs | https://typer.tiangolo.com/tutorial/testing/ | `CliRunner().invoke(app, [...])` returns exit code/stdout/stderr; tests can assert JSON output. | Added CLI test for `arc swarmgraph plan --strategy dag --json`. | High | None. |
| Pydantic docs | https://docs.pydantic.dev/latest/concepts/models/ | `BaseModel`, `ConfigDict(extra="forbid")`, `model_dump`, `model_dump_json`, validators support strict JSON-stable models. | Added strict/frozen service/DAG models and JSON stability coverage. | High | None. |
| FastAPI WebSockets docs | https://fastapi.tiangolo.com/advanced/websockets/ | WebSocket push needs accepted connections, disconnect cleanup, and single-process in-memory managers are limited. | Implemented server-side broadcaster abstraction only; no frontend/live-product claim. | Medium | Whether to expose a public FastAPI route in a later daemon slice. |
| FastAPI SSE docs | https://fastapi.tiangolo.com/tutorial/server-sent-events/ | SSE uses `text/event-stream`, yielded events, keepalive pings, `Last-Event-ID` resume. | Reused existing `EventBroker` concept; added SDK push hook surface without extra dependency. | High | Route integration remains future work. |
| Starlette docs | https://www.starlette.io/responses/ | `EventSourceResponse` is a third-party/Starlette-compatible SSE response; streaming responses use async iterables. | Avoided adding a dependency; kept SDK broadcaster transport-agnostic. | Medium | None. |
| Python asyncio docs | https://docs.python.org/3/library/asyncio-task.html | Keep strong refs to background tasks; cancellation should be propagated/handled; `create_task` schedules concurrently. | Managed service owns task ref, has idempotent `start()`/`stop()`, cancels/waits on stop. | High | None. |
| Vercel Grep | `async def notify(self, event` | Real projects use async notification callbacks and gather/fanout patterns. | Kept `NotificationHook` protocol and added push hook; no broad runtime coupling. | Medium | Public examples varied in quality. |
| Vercel Grep | `EventSourceResponse` | SSE routes commonly stream model/events with keepalive and disconnect handling. | Server-side push surface emits JSON dicts suitable for future SSE/WebSocket bridge. | Medium | Future route path/auth model. |
| Vercel Grep | `class ConnectionManager` | FastAPI docs/examples use connection managers for WebSockets; in-memory manager is process-local. | Did not claim multi-process production push; tests cover in-memory fanout only. | Medium | Multi-process broker backend later. |
| Vercel Grep | `topological_sort` | DAG systems prefer deterministic/lexicographic topological order for stable planning. | Implemented stable sorted Kahn-style topological order. | High | Whether future provider planner should preserve deterministic canonicalization. |
| Existing ARC code | `EventBroker`, `notifications.py`, `decomposition.py`, `runner.py` | ARC already has active-run SSE and SwarmGraph hooks; missing piece was lifecycle-managed retry service and SwarmGraph-specific push hook surface. | Extended existing SDK modules instead of parallel systems. | High | Public daemon route integration remains separate. |
| Context7 | `Pydantic` resolve call for serialization docs | Tool failed: `Invalid API key. Please check your API key. API keys should start with 'ctx7sk' prefix.` | Recorded failure; used official Pydantic docs via webfetch. | High | Configure Context7 API key before next research-gated pass. |
| Pydantic docs | https://docs.pydantic.dev/latest/concepts/serialization/ | `model_dump_json()` emits JSON directly; field inclusion/exclusion and default v2 subclass serialization help avoid accidental sensitive-field leakage. | Added strict evidence model and JSON writer using Pydantic serialization. | High | None. |
| Python hashlib docs | https://docs.python.org/3/library/hashlib.html | `sha256(...).hexdigest()` provides stable hex digest for text without storing raw content. | Evidence artifact stores prompt/output length + SHA-256 only. | High | Hashes still prove content equivalence if raw content is known externally; acceptable for release evidence. |
| pytest tmp_path docs | https://docs.pytest.org/en/stable/how-to/tmp_path.html | Fetch returned truncated/odd content (`clean — nothing to commit`), but pytest tmp path is the standard per-test artifact dir fixture. | Used `tmp_path` for artifact writer tests. | Medium | Re-fetch when web docs are stable. |
| Vercel Grep | `artifact_path.write_text(json.dumps` | Public Python tools commonly write durable JSON artifacts with explicit path and newline. | Evidence writer writes pretty JSON + trailing newline. | Medium | Examples are pattern guidance only. |
| Vercel Grep | `hashlib.sha256(output.encode` | Public evidence/eval code stores output hashes rather than raw output. | Evidence artifact stores output SHA-256 and byte-independent string length. | Medium | No single canonical schema across projects. |

## Decision Table

| Decision | Chosen approach | Alternatives considered | Reason | Files affected | Confidence |
|---|---|---|---|---|---|
| Managed notifications | Add `ManagedNotificationService` around existing `DurableWebhookNotificationHook` and outbox | Replace outbox, add external queue, run unmanaged task in runner | Smallest extension; explicit lifecycle; no new infra; testable offline | `notifications.py`, `test_notifications_service.py` | High |
| Background lifecycle | Idempotent async `start()`, `stop()`, `flush_once()` with owned task ref | Fire-and-forget retry loop | Python docs warn tasks need strong refs; stop must cancel/wait | `notifications.py` | High |
| Push surface | Add in-memory `SwarmGraphEventBroadcaster` + `PushNotificationHook` | Add public FastAPI/SSE routes now, wire IDE UI now | Existing daemon has SSE; this slice needs hook surface without fake product UI | `notifications.py`, tests | Medium |
| SSE/WebSocket claim | Claim server-side push hook surface only | Claim managed SSE/WebSocket product | No route/frontend wiring added here; overclaim unsafe | Docs/tests | High |
| DAG planner | Deterministic local parser + strict DAG model | Provider-backed planner, broad auto-decomposer | Avoid paid/live/provider calls; stable offline tests | `decomposition.py`, CLI, tests | High |
| DAG order | Stable sorted topological order | Preserve insertion-only, import networkx | Deterministic output without extra dependency | `decomposition.py` | High |
| CLI surface | Add `arc swarmgraph plan --strategy dag` | New top-level `arc plan`, hidden-only API | Existing SwarmGraph CLI group is correct scope and avoids conflicts | `cli/swarmgraph.py`, tests | High |
| Provider E2E | Implement skipped-by-default opt-in live SwarmGraph E2E using ARC ProviderClient bridge | Fake success, default live call, broad provider matrix | Gives honest proof for one provider/model path while preserving offline CI defaults | `test_swarmgraph_provider_e2e.py` | High |
| Provider E2E evidence | Write a redacted JSON artifact after successful opt-in live E2E assertions | Store raw prompt/output, rely on console output only, write artifact before assertions | Durable release/roadmap evidence without leaking provider text or secrets; failed runs do not produce success evidence | `providers/e2e_evidence.py`, `test_swarmgraph_provider_e2e.py`, `test_e2e_evidence.py` | High |

## What Is Real In This Slice

- Managed background notification retry service with lifecycle methods and offline tests.
- Server-side in-memory SwarmGraph push hook/broadcaster with fanout, cleanup, overflow tests.
- Deterministic local DAG planner/decomposer and CLI explanation command.
- Opt-in live provider-backed SwarmGraph E2E test that skips by default and passed locally for CrofAI `deepseek-v4-pro-precision` only when explicit gates were set.
- Redacted provider E2E evidence artifact writer that stores provider/model, gates, event kinds, task/call counts, timestamps, and prompt/output length + SHA-256 only.

## Not Real / Not Claimed

- Production multi-process notification service.
- Public SSE/WebSocket product route for SwarmGraph hooks.
- IDE live push UI for SwarmGraph hook events.
- Provider-backed auto DAG planning.
- Broad provider-backed SwarmGraph E2E coverage beyond CrofAI `deepseek-v4-pro-precision`.
- Raw prompt/model-output capture in evidence artifacts.
