# AGENTS.md — ARC Studio Agent Charter

🔒 **LOCKED CHARTER.** This is the single source of governance for agents working on ARC Studio.

## Single sources of truth

There is exactly **one** of each. Do not create competing or replacement copies.

| Concern | Canonical file |
|---|---|
| Roadmap | `docs/roadmap.md` |
| Phase list / execution plan | `docs/phases.md` |
| Agent charter | `AGENTS.md` (this file) |

Both `docs/roadmap.md` and `docs/phases.md` are CI-protected (`scripts/release_check.sh`). Update them **in place**. Never add a new roadmap/phase/status markdown — everything else is archived under `docs/archive/`.

## Working discipline

1. **Finish 1 → 100% before broadening.** Complete the active phase end to end — with tests and evidence — before starting any new phase, feature, or roadmap item. No new top-level scope while the active phase is incomplete.
2. **Single source.** All roadmap/phase/status updates go into the two canonical docs above.
3. **Evidence over claims.** State what was actually run/verified. Do not claim tests pass unless they were run.
4. **Additive protocol only.** Do not remove or rename existing events, CLI commands, or public API surfaces unless explicitly proposing a breaking change for a future major.
5. **Deterministic security.** Sandbox, trust, policy, budget, audit, and capability decisions are deterministic. No LLM-based security judgement.
6. **Immutable `EnforcementContext`.** Route new runtime state through immutable copies / `ContextVar`, never by mutating the frozen context.
7. **No commits unless asked.** Leave changes in the working tree for review unless the owner explicitly requests a commit.
8. **Baseline is not the finish line.** `Baseline Complete` is a checkpoint, not a destination. Every phase is driven to `Polished Complete` against the Definition of Done below before it is considered done. Do not open new scope to avoid finishing the elevation of an in-flight phase (this is rule 1 applied to polish, not just baseline).

## Definition of Done — Baseline Complete → Polished Complete

The quality bar for ARC Studio is an **enterprise-quality engineering bar expressed as measurable gates** — not an adjective. `Baseline Complete` means the happy path works and has tests. `Polished Complete` means the surface is coherent, accessible, safe, fast enough, parity-complete, and documented. A phase reaches `Polished Complete` only when **every gate below has cited evidence** recorded in `docs/phases.md`.

**Status ladder — labels follow evidence, never the reverse:**

| Status | Meaning | Required evidence |
|---|---|---|
| In Progress | Actively being built | — |
| Baseline Complete | Happy path works; core tests exist; evidence anchored | tests run + commit/worktree anchor |
| Polished Complete | Meets the full Definition of Done | every DoD gate has cited evidence |

**Definition of Done gates (each needs cited evidence before the status changes):**

1. **UX states.** Every user-visible surface (CLI output, TUI view, IDE tab/widget) has explicit loading, empty, error, degraded, and success states. No silent `.catch(() => null)`. No invented data — every card, metric, timeline, and badge names its real producer or renders a degraded state (producer-truth).
2. **Accessibility.** Keyboard-reachable, visible focus, ARIA roles/labels on IDE widgets, sufficient color contrast, and `NO_COLOR` / high-contrast TUI parity. Run available axe / contract checks.
3. **Parity.** CLI ↔ TUI ↔ IDE behavior is consistent; JSON output is stable and documented; equivalent actions produce equivalent results across surfaces.
4. **Tests.** Unit + integration; contract/e2e if a UI/IDE surface changed; CLI snapshot if a command changed; protocol test if the protocol changed. Deterministic, offline, no provider calls unless explicitly gated.
5. **Performance.** Bounded in-memory buffers, virtualized long lists, no sync filesystem I/O in hot UI paths, async backend bridges, debounced inputs. Measure before/after whenever a performance claim is made.
6. **Security.** Paid calls explicitly gated; secrets redacted in logs/UI/audit; destructive or mutating actions confirmation-gated; security decisions deterministic (no LLM allow/deny); audit appended on allow.
7. **Reliability.** Timeouts, cancellation, and structured error envelopes on every long-running or backend-bridged action.
8. **Docs.** README, `--help`, `docs/roadmap.md`, and `docs/phases.md` updated in place; all claims pass `bash scripts/check-banned-claims.sh`.

### Do Not Overclaim

Raising the quality bar raises the **work required**, not the **words allowed**. Status always follows evidence:

- Do not label a phase "Polished Complete", "complete", "hardened", "enterprise-grade", or "Production ready" until every DoD gate has cited evidence and `scripts/check-banned-claims.sh` passes.
- `scripts/check-banned-claims.sh` is authoritative for release-facing wording. "Production ready", "multi-user", "tenant-isolated", broad provider-backed SwarmGraph adoption, and production-grade sandbox/microVM execution stay forbidden until proven by tests and evidence.
- ARC Studio stays a single-user, loopback-only alpha workstation tool until proven otherwise. The Definition of Done elevates engineering quality; it does not change the product's safety posture or unlock new product claims.

## Active track (2026-06-08)

The 2026-06-05 P0 hardening sprint (six five-way-audit items: SQLite budget-lock,
TUI shell-escape fail-closed, orphan FastAPI quarantine, POST-only `/api/runs/start`,
enforcement-surface refresh, profile schema version) is **complete**.

The DoD elevation track (R-POLISH1–18 / Phases 159–176 + Phases 177–252) is **complete**
for the v0.8-r-ux4 internal release. All 25 phases of the Phases 228–252 elevation sprint
landed with cited per-gate DoD evidence:

- **R-POLISH1–28 elevation** (Phases 228–231): All 28 R-POLISH items → Polished Complete
  with per-gate DoD evidence. Security P0 batch, honest states, TUI streaming, MCP security,
  paid-call gate, CLI mutation gate, bounded buffers, protocol parity, refactors.
- **Mobile SDK elevation** (Phases 232–233): R-MOBILE-AUDIT/TS, B5-P9-10/P12a,
  P11-12b/P12-20 → Polished Complete.
- **Roadmap elevations** (Phases 234–249): R-CR-BACKLOG, R11-R77 (cost/packaging/native
  runtime/trust/trace/HITL/memory/adapters/hardening), R39-R65 era batches, R-CLEAN1,
  R-OPEN items → Polished Complete.
- **Infrastructure** (Phases 250–251): B2P-17 terminal-gated honest no-op. Shared
  `map_provider_error` extracted. `arc mobile gate check` alias added.
- **Release gate** (Phase 252): 6003 Python + 969 TS tests, ruff clean, banned-claims clean.
  Version bumped to v0.8-r-ux4.

See `docs/phases.md` (Phases 159–252) and `docs/roadmap.md` for full evidence records.

## Sandbox / microVM truth constraints (still in force)

- **No microVM execution claims** beyond what is proven. macOS direct VZ is a gated public CLI proof passed once for guest-available `pwd` (default-off, not production-grade). Linux/Firecracker is preflight/baseline only, host-unproven (Linux/KVM only). Windows is out of scope.
- **Container is a gated fallback only** — disabled unless `ARC_ENABLE_CONTAINER_SANDBOX=1`.
- **Do not remove** existing alpha/mock/fallback labeling.
- Allowed wording: "production-ready foundation", "microVM preflight/doctor support", "container fallback (gated)". Forbidden until proven: "production-grade microVM execution", "production-ready sandbox", broad "VZ command runner".

## Verification commands

```bash
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q
pnpm typecheck && pnpm build
```

Document failures honestly; do not hide them.
