# ADR-030: Competitive Feature Sequencing (R83–R102 + R-NATIVE-RUNTIME)

**Status:** Proposed
**Date:** 2026-06-09
**Repository:** Hansuqwer/ARC-STUDIO @ e2526c3
**Companions:**
- `docs/research-findings/r87-stream-relay-audit-2026-06-09.md`
- `docs/research-findings/r86-session-persistence-audit-2026-06-09.md`
- `docs/research-findings/r-sec1-mcp-subprocess-isolation-2026-06-09.md`
- `docs/research-findings/r-proc-release-hygiene-plan-2026-06-09.md`
- `docs/roadmap.md` → NEW INTAKE (R83–R102 + R-NATIVE-RUNTIME, all Not Started)
- `docs/phases.md` → Phase 273 (intake/registration)

---

## 1. Context

A competitive analysis (delivered in `docs/handover/ARC-Studio-Complete-Deliverable.pdf`)
identified 20 candidate features (R83–R102) and one native-runtime track (R-NATIVE-RUNTIME).
All are currently **Not Started** in this repository.

AGENTS.md mandates: **Finish 1 → 100% before broadening.** At most one item moves to
`In Progress` at a time.

This ADR locks the dependency graph and sequencing order so that Kiro agents and human
reviewers can verify alignment without re-deriving it from the backlog each time.

---

## 2. Decision

### 2.1 Foundational Prerequisite

**R87 ARC Stream** (real-time event relay) is the single foundational prerequisite for all
features that require live event visibility:

- **R86 ARC Continuum** — Resume needs live reconnection to interrupted runs
- **R99 ARC Debug** — Step-through debugging needs live event stepping
- **R101 ARC Time Travel** — Replay needs live event capture + bidirectional scrub

### 2.2 Index / Context / Memory Chain

**R84 ARC Index** is the prerequisite chain head for workspace-intelligence features:

- **R85 ARC Context** — Auto-context retrieval depends on the vector index
- **R90 ARC Memory** — Persistent project knowledge enriched by index queries

This chain is **independent of R87** and may run in parallel if a second senior engineer is
available (see Mitigation below).

### 2.3 Sequencing Order

```
Phase 1 — Foundation (MUST be done first):
  R87 ARC Stream ──────────────────────────────────────────────────┐
                                                                   │
Phase 2 — After R87 is 100%:                                       │
  ├─> R86 ARC Continuum (depends on R87 for run-resume) ──────────┘
  ├─> R99 ARC Debug (depends on R87 for live stepping)
  └─> R101 ARC Time Travel (depends on R87 + R99)

Parallel chain (independent of R87):
  R84 ARC Index ───────────────────────────────────────────────────┐
    ├─> R85 ARC Context (depends on R84)                           │
    └─> R90 ARC Memory (soft-depends on R84)                       ┘

Independent features (Phase 4, any order after Phase 2):
  R88 ARC Git ──> R89 ARC Diff (composes)
  R91 ARC Hub
  R92 ARC Daemon Tasks (soft-depends on R87 for progress surfacing)
  R93 ARC Vision (large scope, independent)
  R94 ARC Advisor
  R95 ARC Dashboard
  R96 ARC Voice
  R97 ARC Policies
  R98 ARC Composer (depends on SwarmGraph maturity)
  R100 ARC Notebook
  R102 ARC Migrate (depends on adapter maturity)

R-NATIVE-RUNTIME (optional augmentation track):
  - Requires dedicated ADR (ADR-031) if approved
  - Multi-quarter scope; cannot start before Phase 3 completes
  - Performance targets in the spec are unverified aspirations pending a prototype
```

### 2.4 Finish 1 → 100% Enforcement

Only one feature may be `In Progress` at any time. Each feature must clear all 8 DoD gates
before its phase is recorded as `Polished Complete` and the next phase opens.

CI enforced via `scripts/check-banned-claims.sh` (existing) — prose describing a feature as
"shipped" while it is `Not Started` triggers a banned-claim hit.

---

## 3. Consequences

**Positive**
- Kiro agents read one file to know exactly which feature to implement next.
- R87's test suite becomes the event-contract that R86, R99, R101 test against.
- Single-feature focus eliminates cross-branch conflicts on hot paths (event broker, web routes).
- No feature can be misrepresented as shipped when it is `Not Started`.

**Negative**
- 20 features at 2–5 weeks each = 40–100 weeks sequential. Parallel execution (if resourced)
  could cut to 12–18 months.
- If R87 is blocked, all downstream features are blocked.
- R84 (Index) provides immediate user value but must wait for R87 if strictly sequential.

**Mitigation**
- R84/R85/R90 chain **may** run in parallel with R87 if a second senior engineer is available.
  This requires explicit approval and a dedicated branch that does not touch
  `orchestration/event_broker.py`.
- R87 timebox: 2.5 weeks. If R87 exceeds 4 weeks, split into R87a (global SSE endpoint) and
  R87b (TUI client + NotificationBadge push) to unblock IDE-side work sooner.

---

## 4. Dependencies on Existing Infrastructure

| Feature | Reuses Existing | New Code | Risk |
|---|---|---|---|
| R87 | `event_broker.py`, `web/server.py`, `bearer_token_middleware` | `stream/websocket.py` (stub provided) | Low |
| R86 | `auth/manager.py` (Fernet), `budget/storage.py` (WAL), `cli_repl/session.py` | `continuum/store.py` (stub provided) | Low |
| R84 | `storage/indexed_store.py`, `audit/session.py` | Vector index, embedding loader | Medium (new ONNX dep) |
| R88 | `git` CLI, `isolation/subprocess.py` | Auto-commit, auto-branch | Low |
| R99 | MCP server, Theia DAP (already supported) | Breakpoint injection, variable inspector | Medium |
| R101 | `event_broker.py`, `storage/indexed_store.py` | Delta storage, branching engine | Medium |

---

## 5. References

- `docs/research-findings/r87-stream-relay-audit-2026-06-09.md` — R87 implementation plan
- `docs/research-findings/r86-session-persistence-audit-2026-06-09.md` — R86 schema + resume flow
- `docs/research-findings/r-sec1-mcp-subprocess-isolation-2026-06-09.md` — R-SEC1 MCP fix
- `docs/research-findings/r-proc-release-hygiene-plan-2026-06-09.md` — R-PROC3/5/6 scripts
- `docs/research-findings/competitive-feature-backlog-2026-06-09.md` — Full backlog (all 20 features)
- `docs/roadmap.md` — NEW INTAKE (R83–R102 + R-SEC* + R-PERF* + R-PROC*)
- `docs/phases.md` — Phase 273–274 (intake/registration)
- `AGENTS.md` — Finish 1 → 100% before broadening rule
