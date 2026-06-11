# ARC v2 — Owner Decision Checkpoint #1 (post-Sprint 1)

Date: 2026-06-11 · Branch: `arc-v2/sprint-1-protocol-bridge` @ `351744f`

## Evidence summary (one page)

- Fixture decode: 100% of existing fixtures (17 run-event, 3 envelope, 7 error-codes,
  3 runtime-capabilities); semantic re-encode equality; unknown-kind/field tolerance proven.
- Registry coverage: **17/69** kinds fixtured; uncovered list committed (`reports/fixture-coverage.md`).
- Round-trip: Rust ✔, Python (canonical Pydantic) ✔, JSON-Schema leg ✔; TS leg pending CI (jest env).
- RTT baseline: p50 241 µs / p95 377 µs / p99 518 µs (n=200, loopback HTTP, sandbox container).
  ADR-0001 A3 kill criterion: **pass** with ~130× headroom.
- SSE: live-proven (decode, cancellation, idle timeout, structured errors).
- UDS: flag-gated additive listener verified (off ⇒ no socket; on ⇒ 0600 + /health over UDS).
- v1: protocol+web suites 220 passed; no canonical-file edits; no renames/removals.
- Finding F5: global SSE stream carries DaemonNotification (not RunEvent); RunEvents
  are per-run (`/api/runs/{run_id}/events`). Handled additively in the client.

## Recorded verdicts (owner go-ahead, 2026-06-11)

| # | Decision | Verdict |
|---|---|---|
| 1 | Accept Sprint-1 exit; authorize Sprint 2 (`arc-ui` + `arc-shell`) | **APPROVED** |
| 2 | C1: bless `docs/planning/` in `AGENTS.md` (additive exception paragraph) | **APPLIED** — see AGENTS.md "Additive exception"; reversal = delete one paragraph |
| 3 | F5 stream split documented as contract (global = notifications, per-run = RunEvents) | **RATIFIED** (additive doc note; no protocol change) |
| 4 | Q10 fixture authoring priority: TOOL_CALL_*, TEXT_MESSAGE_*/MESSAGE*, STATE_SNAPSHOT, *_DENIED first | **ACCEPTED as recommendation** — daemon-side authoring scheduled before the panels that render them (Sprint 7 prep) |
| 5 | TS round-trip leg re-run in CI before gate 2 closes fully | **OPEN** (tracked) |

Constraints unchanged: native-only; additive protocol; deterministic security;
daemon = producer of truth. Sprint 3+ remains gated (ADR-0002 addendum required
before the framework spike).
