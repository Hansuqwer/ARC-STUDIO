# ARC Studio — Critical Review + Definition-of-Done Elevation Prompt (v2)

> Improved over the v1 "Final Synthesis critical review" prompt. Two changes drive this version:
> (1) every implemented slice must reach the **Definition of Done (Polished Complete)** bar in `AGENTS.md`, and
> (2) every phase currently at **Baseline Complete** gets an explicit **baseline → Polished Complete** elevation plan.

---

## 0. How to read "enterprise-grade / production-ready / complete UI-UX" in this prompt

These words are **not** labels you may write. In this prompt they are a single, precise contract:

> **"Enterprise-grade / complete" = meets all 8 Definition of Done gates in `AGENTS.md` with cited evidence in `docs/phases.md`, AND `scripts/check-banned-claims.sh` passes.**

Therefore:
- Raising the bar raises the **work required**, not the **words allowed**.
- You never write "production-ready", "multi-user", "tenant-isolated", "enterprise-grade", "hardened", or "Polished Complete" until the DoD evidence exists. `scripts/check-banned-claims.sh` (which scans `AGENTS.md` + `README.md` via `release_check.sh`) is authoritative.
- ARC Studio stays a single-user, loopback-only alpha workstation tool. The DoD elevates engineering quality; it does not unlock new product claims.

If any instruction below seems to ask you to claim readiness, resolve it as "produce the evidence and the slices that would earn the status," not "write the status."

---

## 1. Role

You are simultaneously: principal engineer, product strategist, release auditor, adversarial reviewer, roadmap editor, implementation-sequencing critic, and **Definition-of-Done elevation lead** for ARC Studio.

You do not add vague ideas. You convert prior research + the cleanup audit into a complete, evidence-backed, roadmap-aligned **issue ledger**, a **Baseline → Polished Complete elevation ledger**, and a corrected, safely-sequenced implementation plan.

---

## 2. Repository & baseline

```
git clone https://github.com/Hansuqwer/arc-theia-studio.git   # or use the existing checkout
cd arc-theia-studio
git status --short                                             # record pre-existing changes; do NOT disturb them
git rev-parse --short HEAD
```

This is a **review + research + mapping** pass. **Do not edit files** unless a final instruction explicitly says to. If asked to execute, implement only the smallest safe slice and follow `AGENTS.md` rule 7 (no commits unless asked).

---

## 3. Read first (canonical sources, then surfaces)

Governance (authoritative, locked): `AGENTS.md` · `docs/roadmap.md` · `docs/phases.md`
Release: `docs/release/checklist.md` (or nearest) · `scripts/release_check.sh` · `scripts/check-banned-claims.sh` · `scripts/check-pr.sh`
Prior work: `docs/research-findings/*` (the category audits, the unified backlog, and the cleanup-refactor audit)
Surfaces:
- `README.md`, `package.json`, `applications/browser/package.json`, `applications/electron/package.json` (if present), `packages/arc-extension/package.json`
- `packages/arc-extension/src/browser/arc-extension-frontend-module.ts`
- `packages/arc-extension/src/node/arc-extension-backend-module.ts`
- `packages/arc-extension/src/common/arc-protocol.ts`
- `packages/arc-extension/src/browser/arc-studio-widget.tsx`, `packages/arc-extension/src/browser/tabs/*`, `packages/arc-extension/src/browser/style/*`
- `python/` (CLI, TUI, providers, security, swarmgraph, mcp, audit), `tests/`, `scripts/`

---

## 4. The Definition of Done contract (quote, then audit against it)

Every slice and every elevation target is judged against the 8 gates in `AGENTS.md → "Definition of Done — Baseline Complete → Polished Complete"`:

1. **UX states** — loading / empty / error / degraded / success on every CLI/TUI/IDE surface; no silent `.catch(() => null)`; producer-truth (no invented data).
2. **Accessibility** — keyboard reachable, visible focus, ARIA roles/labels, color contrast, `NO_COLOR` / high-contrast TUI parity, axe/contract checks.
3. **Parity** — CLI ↔ TUI ↔ IDE consistent; stable, documented JSON.
4. **Tests** — unit + integration; contract/e2e if UI/IDE changed; CLI snapshot if a command changed; protocol test if protocol changed; deterministic + offline.
5. **Performance** — bounded buffers, virtualized lists, no sync FS in hot UI paths, async bridges, debounced inputs; before/after measurement when claimed.
6. **Security** — paid calls gated, secrets redacted, mutations confirmation-gated, deterministic decisions, audit on allow.
7. **Reliability** — timeouts, cancellation, structured error envelopes on long-running/bridged actions.
8. **Docs** — README/`--help`/roadmap/phases updated in place; claims pass `check-banned-claims.sh`.

A gate "passes" only with a cited artifact (file:line, test name, command output). "Looks done" is not evidence.

---

## 5. External research (use before finalizing; log honestly)

- **Context7** — fetch current docs for: Eclipse Theia extension APIs, widgets, commands/keybindings, JSON-RPC; React testing; Typer/Click; Textual/Rich; MCP SDK; provider SDKs (only when that surface is discussed).
- **Vercel Grep / code search** — comparable OSS idioms for: Theia extension structure, command registries, ReactWidget patterns, MCP workbench UX, provider settings UI, run/event timelines, audit/evidence dashboards, safe CLI-bridge patterns, nested-CLI alias patterns.
- **Web fetch / official docs** — where current facts matter (Theia, MCP, Typer/Click, Textual, React, packaging/signing, security standards).
- **Fallback rule** — if a tool is unavailable, **say so explicitly**, fall back to repo grep/ripgrep + official web docs, and **never pretend** the tool was used.

---

## 6. Sub-agents (up to 12 parallel)

Keep the v1 critics and **add the elevation critic**:

1. Governance / Roadmap Critic — locked-doc rules, status vocabulary, forbidden claims, every-issue-maps rule.
2. Evidence Critic — verify each claim vs repo/tests/docs/Context7/Grep/web; flag unsupported assumptions.
3. Scope Critic — split broad/mixed/risky slices into one-pass-safe slices.
4. Dependency / Sequencing Critic — prerequisites, blockers, circular deps, order constraints.
5. Security / Policy Critic — paid-call gates, secret exposure, sandbox/microVM overclaims, policy bypass, nondeterministic security, CLI-bridge risk.
6. CLI / TUI / IDE Parity Critic — parity gaps, duplicate commands, nested-depth, alias safety.
7. Theia / IDE Architecture Critic — widget/command/keybinding/JSON-RPC/backend alignment vs current Theia docs.
8. Runtime / SwarmGraph Critic — gates, deterministic DAG planner, consensus, evals, notifications, cost events, evidence artifacts; no broad provider-backed claims.
9. Producer / Data Truth Critic — exact producer for every card/metric/timeline/badge; degraded state if absent/gated/stub.
10. Test / Verification Critic — acceptance criteria + exact tests for every issue.
11. Release / Packaging / Docs Critic — install, browser/electron, signing, README, checklist, claim wording.
12. **Polish / Definition-of-Done Elevation Critic (NEW)** — for **each phase at `Baseline Complete`**, audit it against the 8 DoD gates, mark each gate pass/fail with evidence, and emit the elevation slices needed to reach `Polished Complete`. Then a Prioritization pass re-ranks everything by risk-adjusted value within roadmap/phase order.

Each sub-agent reports: what it reviewed · external docs/tools used (incl. fallbacks) · strong points · weak points · unsupported assumptions · overclaims · missing categories · risky suggestions · required corrections · roadmap mapping · phase mapping · priority changes.

---

## 7. Critical review rules

1. **No "top-N" cap** on the issue ledger or the elevation ledger. Produce the complete set.
2. Every issue has: ID · title · category · severity (blocker/high/medium/low) · current claim/gap · repo evidence · external evidence (if any) · affected files · roadmap mapping · phase mapping · required correction · acceptance criteria · tests required · docs-update? (y/n) · safe-to-implement-now? (y/n) · recommended slice.
3. **No floating issues.** Anything not represented in `docs/roadmap.md`/`docs/phases.md` gets a proposed new R-ID and a proposed new phase/chunk, in the repo's exact status vocabulary (Not Started / In Progress / Baseline Complete / Polished Complete / Complete / Blocked / Deferred) and acceptance-ledger format. **Do not create competing roadmap/status docs** — propose in-place insertions only.
4. Reject vague phrases (production-ready, enterprise-grade, fully wired, complete, secure, isolated, provider-backed, production-grade) unless backed by exact evidence per §0/§4.
5. Treat every slice as unsafe until proven small, testable, sequenced, producer-backed, roadmap-aligned, and compatible with public CLI/protocol/IDE surfaces.
6. **Flag and refuse** any suggestion that would: delete public CLI commands; break protocol compatibility; remove legacy widgets unsafely; invent UI data; expose secrets; make provider calls without explicit gates; claim broad provider-backed SwarmGraph; claim production-grade sandbox/microVM; create competing docs; skip tests; rewrite unrelated code; or use an LLM for security allow/deny.
7. Prefer fewer, safer, better-sequenced slices — but **drop nothing**; lower-priority issues stay in the ledger.

---

## 8. Required output (do not cap lists 3, 4, 5, 6, 8a)

1. **Executive verdict** — one of: ACCEPTABLE / ACCEPTABLE WITH CORRECTIONS / NEEDS MAJOR REVISION / UNSAFE TO RUN, with reasons.
2. **External research log** — Context7 docs fetched · Grep queries · web docs · unavailable tools + fallbacks · which docs changed the verdict.
3. **Complete issue ledger** — full table per §7.2. Uncapped.
4. **Unsupported assumptions ledger** — assumption · where it appears · missing evidence · how to verify · roadmap/phase mapping · safer wording.
5. **Overclaims ledger** — overclaim · why unsupported · forbidden wording · allowed replacement · roadmap/phase mapping · docs correction.
6. **Producer-truth ledger** — proposed UI/data feature · claimed data · actual producer · status (baseline/gated/conditional/stub/absent/deferred) · required degraded state · roadmap/phase mapping · tests.
7. **Corrected roadmap insertion plan** — proposed R-ID · title · status · evidence · notes · why it belongs (propose only; do not edit).
8. **Corrected phase insertion plan** — proposed phase/chunk · roadmap mapping · status · acceptance · verification · risks · dependencies · why it belongs (repo acceptance-ledger format; propose only).
8a. **Baseline → Polished Complete elevation ledger (NEW, uncapped)** — one row per `Baseline Complete` phase:
    - phase id/title · roadmap mapping
    - DoD gate scorecard: gates 1–8 each marked pass (with cited evidence) / fail (with the specific deficiency)
    - elevation slices required to close every failing gate (small + sequenced)
    - tests required per slice · safe-to-implement-now (y/n) · dependencies
    - resulting status only after evidence (must remain `Baseline Complete` until all 8 gates pass)
9. **Corrected priority backlog** — all issues grouped P0/P1/P2/P3/Deferred, each with issue IDs · roadmap/phase mapping · dependencies · tests.
10. **Corrected next implementation order** — numbered steps: objective · issue IDs · roadmap/phase mapping · files likely touched · non-goals · required tests · rollback notes.
11. **Top 3 next implementation prompts** (the only place "top 3" is allowed) — each with: repo setup · files to inspect · sub-agents (≤12) · exact scope · issue IDs · roadmap/phase mapping · non-goals · steps · acceptance criteria mapped to the 8 DoD gates · verification commands · final-response format.
12. **Rewritten Final Synthesis** — shorter, safer, accurate; references the ledgers; no inflated claims; no fake producers; no unsafe instructions; safely sequenced.
13. **Final recommendation** — is the prior synthesis safe to run? what must be fixed first? which corrected prompt to run first? what not to run yet?

---

## 9. Verification vocabulary (cite exact commands as evidence)

```
cd python && uv run ruff check src tests
cd python && uv run pytest tests/ -q          # or targeted: tests/<area> -q
pnpm --filter arc-extension build
pnpm --filter @arc-studio/browser build
pnpm typecheck && pnpm build
bash scripts/check-banned-claims.sh AGENTS.md README.md docs/roadmap.md docs/phases.md
bash scripts/check-pr.sh
```

Selective rule: Python-only change → ruff + relevant pytest. TS-only → arc-extension build + browser build + typecheck. CLI change → CLI tests + help snapshots. Docs change → banned-claims. Always document tests **not** run and why.

---

## 10. Final answer must include

Safe-to-run verdict · complete (uncapped) issue ledger · **Baseline → Polished elevation ledger** · roadmap insertion plan · phase insertion plan · corrected implementation order · corrected top-3 prompts · external research log · zero inflated claims (every "complete/enterprise" tied to cited DoD evidence or restated as a slice that would earn it).
