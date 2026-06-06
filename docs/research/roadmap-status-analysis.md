# Roadmap + Phases Status Analysis

**Executed:** 2026-06-06 | Prompt: `docs/prompts/roadmap-status-analysis.md`
**Method:** marker counts + per-item code verification (verify-don't-trust).

---

## §1 — Status summary

| Status | Count | Notes |
|---|---|---|
| **Baseline Complete** | 221 roadmap rows | The overwhelming majority. |
| **Partial** | 2 | R-OPEN-HARDEN, R79. |
| **Research Intake** | 1 | R-TS1 — a planning marker only; R-TS2…R-TS10 are all Baseline Complete. |
| **Deferred mentions** | ~8 roadmap / 67 phases | Mostly historical notes *inside* completed entries, not active backlog. |

Highest phase: **123**. Adapter registry: **20 adapters, all 8/8 conformance**. Full
suite: **5529 passed, 7 xfailed, 0 failed**.

---

## §2 — Partly implemented (the only two genuine Partials)

### R-OPEN-HARDEN — Partial
- **Done:** Phase 123 wired `RateLimitError`/`NetworkError` retry into the
  non-streaming `run_turn` path (`_call_with_retry`); prior slices cover retry
  data structures, poison-pill JSONL, concurrent budget.
- **Open follow-ups:** (a) **streaming-path retry** (see §4 — the activation pick);
  (b) cascading multi-provider failure tests; (c) durability-under-error budget tests.

### R79 — Mobile Runtime SDK — Partial
- **Done:** Slices 110.1–110.5 (adapter, mapping, pack converter, protocol parity).
- **Open follow-up:** Slice 110.6 — optional Theia/TUI surfacing. P2 UI work; harder
  to verify fully offline (snapshot tests). **Keep deferred** unless UI is prioritized.

---

## §3 — Deferred items: Activate vs Keep-deferred

| Item | Decision | Reason |
|---|---|---|
| **Firecracker / Linux microVM** | **Keep deferred** | Owner directive. Needs Linux/KVM host; not offline-testable here. |
| **Streaming-path provider retry** | **ACTIVATE** | Bounded, offline-testable, research-backed correctness boundary (§4). Natural extension of Phase 123. |
| **LM Arena live productization** | Keep deferred | Needs a trust-gated provider contract + live infra. |
| **Google ADK execution (runner)** | Keep deferred | `google_adk/__init__.py` documents a *deliberate* choice: "Runner session/artifact infrastructure inappropriate for a local CLI." Not a gap — a design decision. |
| **MCP SDK execution (runner)** | Keep deferred | MCP is a protocol, not a workflow runner; detect+export is the correct surface. Needs live stdio/HTTP transport to execute. |
| **token-estimator representative benchmark** | Keep deferred | Requires real diverse dogfood traces; synthetic corpus would mean fabricated numbers (forbidden). |
| **R-UX3 polish** (DiffViewer side-by-side, per-command frontmatter, ToolCard rerun) | Keep deferred | UI polish, low leverage, snapshot-test heavy. |

### Stale-note finding
The pydantic_ai roadmap note "registration deferred to when real agent.run_sync()
implementation is complete" is **stale** — Phase 116 implemented `run_sync()` AND
registered the adapter (#17). The note predates Phase 116; not a real deferral.

---

## §4 — Hardening candidate (deep research): streaming-path retry

### The gap
Phase 123 added retry to the non-streaming `complete()` path but explicitly left
the streaming path (`async for chunk in self._provider_client.stream(...)`,
turn_manager.py:111) unretried.

### Research finding (why naive retry is wrong)
Streaming retry has a hard correctness boundary. From industry sources
(idempotency-in-LLM-pipelines, streaming chunk-handling/error-recovery):
- Retrying a stream **after** any chunk has been emitted **duplicates output** the
  consumer already saw — LLM calls are non-idempotent (temperature/sampling), so the
  retried stream is not even the same content.
- Retry is only safe **before the first chunk is yielded** (the connection/first-token
  phase). After that, a failure is terminal for that turn.

### Proposed bounded slice (R-OPEN-HARDEN slice 2)
Wrap the stream so a retryable `ProviderError` raised **before the first chunk** is
retried with the same backoff as `_call_with_retry`; once any chunk is emitted, the
error propagates (no duplicate output). Fully offline-testable with a fake stream
that raises on attempt 1 before yielding, succeeds on attempt 2.

- **Acceptance:** retry only pre-first-chunk; post-first-chunk failure propagates;
  `AuthError` never retried; `ARC_DISABLE_RETRY_SLEEP=1` in tests.
- **Risk:** must guarantee no double-emit — the test must assert chunk count.

---

## §5 — Recommendation

1. **Activate now:** streaming-path retry-before-first-chunk (R-OPEN-HARDEN slice 2).
   Small, research-backed, offline-testable, closes the most concrete remaining gap.
2. **Keep deferred (correct as-is):** Firecracker (owner), LM Arena, Google ADK runner
   (by design), MCP runner (by design), token benchmark (no real traces), R-UX3 polish.
3. **Housekeeping:** correct the stale pydantic_ai "registration deferred" note.
