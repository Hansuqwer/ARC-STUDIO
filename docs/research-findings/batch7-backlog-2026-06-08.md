# Batch 7 — Baseline → Polished Execution Backlog (30 tasks · 2026-06-08)

Autonomous execution prompt. These 30 tasks elevate ARC Studio toward the **Polished** engineering bar
(the 8 DoD gates in `AGENTS.md`). Every task is **none-posture** (pure engineering, reachable now) and
sized for **one commit**. Derived from `docs/research-findings/baseline-to-polished-backlog-2026-06-08.md`
(#1 backlog + #2 scorecard) and the canonical `docs/roadmap.md` B2P rows.

## Operating cadence (per task)
1. **Verify-first.** Read the real code before editing; treat doc claims as ~50% reliable.
2. **Smallest safe additive change.** Never remove/rename public surfaces; strengthen tests, don't weaken.
3. **Tests green before push:** `cd python && uv run ruff check src tests && uv run pytest <targeted> -q` ·
   `pnpm --filter arc-extension build` + `pnpm --filter arc-extension test` (or `@arc-studio/protocol test`) as relevant.
4. **One commit per task**, explicit files only (never `git add -A`; never stage `arena/`, `opencode/`, vendor).
5. **Record** status in `docs/roadmap.md` + `docs/phases.md` in the same commit; run `bash scripts/check-banned-claims.sh`.
6. **Push** `git pull --ff-only origin main` → commit → `git push origin main`.

## Hard boundaries (do NOT cross)
- **No GATED work.** Excluded by design (need a human posture decision): MCP HTTP transport (auth), real native
  device access (R79.1/R79.2), ADK/MCP-adapter T3 (paid/live), broad provider-backed SwarmGraph adoption,
  Firecracker-on-Linux, live Battle Arena, Reviewed-Memory evidence pack.
- **Posture unchanged.** Single-user, loopback-only alpha. No `Production ready`/`multi-user`/`tenant-isolated`/
  `HMAC audit` wording; `scripts/check-banned-claims.sh` is authoritative. Polished = engineering bar, not a product claim.
- **Deterministic security; offline tests.** No paid/live provider calls unless an existing explicit gate is set.

---

## Track A — Quick wins (S)

**T1 · R-AUDIT28 — Remove orphaned IDE dead code.** Delete `packages/arc-extension/src/browser/arena/arena-frontend-module.ts`
+ `arc-run-timeline-widget.tsx` after confirming no contribution/import refs. *Tests:* contract test asserts no import; full arc-extension suite. *DoD 8.*

**T2 · B2P-10 — Type the intentionally-untyped run events.** Type the remaining registry events in TS + Python, or document each as intentional with a parity test. *Tests:* protocol parity (Py↔TS). *DoD 4.*

**T3 · B2P-01 — TUI `/statusline` slot reordering.** Config key for slot order; render from config; default preserves current order. *Tests:* TUI snapshot/unit. *DoD 1,3.*

**T4 · R79.5 — Mobile-package dependency vuln scanning.** Add `npm audit`/Dart `pub` audit gates for the mobile JS/Dart trees to `scripts/release_check.sh` (+ a mobile CI lane), guarded by toolchain presence. *Tests:* gate dry-run. *DoD 6,8.*

## Track B — IDE coherence (M)

**T5 · R-AUDIT29 — TestBenchTab Run button.** Add a sandbox-policy-gated Run action → `execArcCliAsync('testbench run --policy local-safe …')`; loading/empty/error/success states; confirm gate. *Tests:* jest + contract. *DoD 1,3,6,7.*

**T6 · R-AUDIT27 — IDE status rail.** Persistent top-rail widget (mode/trust/model/daemon) from existing services; degraded states; ARIA. *Tests:* jest-axe + contract. *DoD 1,2,3.*

**T7 · B2P-03a — Real-component jest-axe (harness + 2 tabs).** Run axe against real rendered tabs (not mocks) for 2 high-traffic tabs; browser-contrast note. *Tests:* jest-axe. *DoD 2,4.*

**T8 · B2P-03b — Real-component jest-axe (remaining tabs).** Extend the real-render axe coverage to the remaining tabs. *Tests:* jest-axe. *DoD 2,4.*

**T9 · B2P-02a — Typed-event migration (core consumers).** Migrate the highest-traffic IDE consumers off legacy `TraceEvent` to the `KnownRunEvent` typed union. *Tests:* contract/parity. *DoD 3,4.*

**T10 · B2P-02b — Typed-event migration (remaining + retire alias usage).** Finish remaining consumers; keep legacy export for back-compat but stop new usage. *Tests:* contract. *DoD 3,4.*

## Track C — MCP coherence (decomposed from B2P-04/05/07)

**T11 · B2P-05 — SwarmGraph MCP tool wrappers.** Expose SwarmGraph ops as MCP tools through the risk gate. *Tests:* mcp unit + risk-gate. *DoD 3,4,6.*

**T12 · B2P-04a — IDE MCP client: backend service.** Loopback stdio invoke routed through the risk gate; structured envelopes; timeout. *Tests:* node service unit. *DoD 6,7.*

**T13 · B2P-04b — IDE MCP client: McpWorkbenchTab invoke UI.** Tool-invoke UI + decision/result render with full UX states. *Tests:* jest + contract. *DoD 1,3.*

**T14 · B2P-04c — IDE MCP client: tests + cancellation.** Contract/e2e coverage + cancellation/timeout paths. *Tests:* contract/e2e. *DoD 4,7.*

**T15 · B2P-07 — MCP task notifications + real exec.** SSE for task state (replace polling); wire task exec to real run/trace/audit (replace placeholder ops); daemon API integration. *Tests:* mcp task unit. *DoD 1,4,7.*

## Track D — Security / budget / runtime (decomposed from B2P-08/09/19)

**T16 · B2P-08 — Runtime-wide high/critical confirmation.** Enforce mandatory confirmation + audit at every high/critical adaptive decision entrypoint (today only surfaced). *Tests:* security/runtime unit. *DoD 6.*

**T17 · B2P-09a — Budget enforcement at the adapter effect hook.** Wire `BudgetEnforcer` (`budget/schema.py`) into the shared adapter effect boundary. *Tests:* budget unit. *DoD 5,6.*

**T18 · B2P-09b — Budget enforcement: per-adapter coverage + interrupts.** Cover each adapter's effect boundary; exhaustion-interrupt tests. *Tests:* per-adapter. *DoD 5,7.*

**T19 · B2P-19 — Keyed audit material across every run path.** Ensure every adapter run path writes + verifies keyed audit material; add the missing ones. *Tests:* audit per-path. *DoD 4,6.*

## Track E — CLI / eval / memory / locking (decomposed from B2P-11/12/13)

**T20 · B2P-11a — Eval artifact schema.** Repeatable, versioned eval artifact paths (`--batch` already exists). *Tests:* eval unit + snapshot. *DoD 3,4,8.*

**T21 · B2P-11b — Eval Inspect-AI-compatible export.** Export eval results to an Inspect-AI-compatible directory/log shape. *Tests:* export snapshot. *DoD 3,4.*

**T22 · B2P-11c — Eval two-run report comparison.** Compare two runs on the same dataset; CLI + JSON. *Tests:* compare unit. *DoD 1,4.*

**T23 · B2P-12 — Memory runtime wiring.** Invoke memory extract/query during runs with redaction-before-extraction (store/query exist CLI-only; not wired into `runtime_router`/adapters). *Tests:* runtime+memory. *DoD 3,4.*

**T24 · B2P-13a — Advisory lock primitive.** Build the advisory file/workspace lock (prereq for the IDE write bridge). *Tests:* lock unit (contended/stale). *DoD 6,7.*

**T25 · B2P-13b — IDE write bridge (Phase 42) on the lock.** IDE write operations behind the advisory lock; confirm gate; structured errors. *Tests:* node + contract. *DoD 6,7.*

## Track F — Mobile (none-posture)

**T26 · R79.4 — Mobile package supply-chain provenance.** SBOM attestation + signed provenance (SLSA/sigstore) for the mobile packages in CI. *Tests:* CI gate dry-run. *DoD 6,8.*

**T27 · R79.3 — Device posture / MDM hook interface.** Deterministic posture/MDM hook interface (simulator-preview, fixtures only; real enforcement stays GATED). *Tests:* mobile unit. *DoD 4,6.*

## Track G — Release / parity (decomposed from B2P-17/18)

**T28 · B2P-18 — Doctor/daemon parity remainder.** Resolve the fate-labeled orphan routes (`ui-deferred` → add UI, or finalize `daemon-only-deprecated`). *Tests:* doctor/route parity. *DoD 3,8.*

**T29 · B2P-17a — Electron app shell + daemon lifecycle.** Daemon-bundled Electron shell + lifecycle (build green); browser stays canonical. *Tests:* build + smoke. *DoD 4,8.*

**T30 · B2P-17b — Electron signing + CI artifact.** Signing + auto-update config + CI artifact build. *Tests:* signing-preflight + build. *DoD 4,8.*

---

## Batch acceptance
All 30 committed to `main`, one per task, with tests green and `check-banned-claims` clean; each recorded in
`docs/roadmap.md` (flip B2P/R-AUDIT row → Baseline Complete) + `docs/phases.md` (new phase entry). Posture
unchanged: single-user loopback alpha; no GATED work; no product-readiness wording. On completion, record a
Batch 7 phase + roadmap entry and run the full suite sweep.

**Suggested grouping for autonomy:** run Track A → B → C → D → E → F → G in order; within a track, tasks are
mostly independent except T12→T13→T14 (MCP client), T17→T18 (budget), T20→T21→T22 (eval), T24→T25 (lock→bridge),
T29→T30 (Electron). Stop and ask a human only if a task turns out to need a posture decision (then it's GATED, skip it).
