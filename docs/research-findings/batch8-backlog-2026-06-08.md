# Batch 8 Backlog — v0.2 Polish-Elevation (Tier 1) + Larger Research-Backed Horizon (Tier 2)

**Date:** 2026-06-08 · **Continues:** Batch 7 (Phases 196–202) + v0.2 polish elevation (Phase 203, 18 Polished / 5 Baseline-gap).
**Posture (unchanged):** single-user, loopback-only alpha; simulator-preview for mobile. No production / concurrent-user / tenant-isolation claims. All release-facing wording must pass `scripts/check-banned-claims.sh`.

This doc has two tiers:
- **Tier 1 — 25 none-posture polish-elevation tasks** (immediately executable; same cadence as Batch 7). Drives the next 25 `Baseline Complete` items → `Polished Complete`.
- **Tier 2 — 25 larger, research-backed Horizon tasks** (the bigger roadmap items). Each is labeled **none-posture** (executable now) or **GATED** (planned; needs auth design / native device / paid-live providers / Linux-KVM host / signing certs / human review). Every GATED item carries a **bounded none-posture slice** that *can* be done now. Tier 2 is a **plan**, not an instruction to execute gated work.

---

## Tier 1 — Next 25 Polished-Elevation tasks (none-posture)

**Source (verify-first):** `docs/roadmap.md` has ~116 `Baseline Complete` rows vs 19 `Polished`. Tier 1 = the next 25 non-gated `Baseline Complete` rows driven to `Polished Complete` against the full DoD. **Exclude** gated rows: `R75`, `R79.1`, `R79.2`, `B2P-06/14/15/16/20/21/22`, `B2P-17`.

**Candidate IDs (derive the exact 25 from the live roadmap at run time):** `R3, R8, R9, R10, R11, R12, R14, R15, R16, R17, R18, R19, R20, R21, R22, R25, R26, R27, R28, R29, R30, R31, R32, R33, R34` — plus the `R-POLISH*`, `R-AUDIT1–25`, and `R-MOBILE-*` Baseline rows, and the 4 closeable Phase-203 gaps where Tier-2 work lands (B2P-03/R-AUDIT26 via L-G1, B2P-09 via L-H1).

### Execution prompt (paste to start Tier 1)

```
Execute Batch 8 Tier 1: drive the next 25 non-gated `Baseline Complete` items -> `Polished Complete`
against the full Definition of Done, one commit per item, pushed each. Record as Phase 204.

Step 0 (verify-first): audit docs/roadmap.md; pick 25 non-gated Baseline-Complete rows not yet
Polished (R-*, R-AUDIT*, R-POLISH*, Phase N). Write them to the TODO before executing.

Per task: verify-first (read real code/tests; correct stale notes) -> smallest change or cite
existing passing tests -> run tests as a SEPARATE step and confirm GREEN before committing (husky
gates ruff only, NOT pytest) -> flip the roadmap row to Polished Complete + append a Phase 204
per-gate evidence entry (mark N/A gates with a reason) -> bash scripts/check-banned-claims.sh ->
git pull --ff-only -> git add <explicit files> -> commit -> push.

DoD gates: 1 UX-states, 2 a11y, 3 parity, 4 tests, 5 perf, 6 security, 7 reliability, 8 docs.
Labels follow evidence: if any applicable gate can't be honestly evidenced, KEEP the item Baseline
and record the gap + closure path -- do not flip it.

Hard constraints: no GATED work (auth/native/paid-live/Linux-KVM/external-signing); posture
unchanged; additive-only; don't mutate frozen security primitives (EnforcementContext) as a polish
bolt-on; security stays deterministic (no LLM).

Operational: arc-extension needs the FULL suite for coverage (`pnpm --filter arc-extension test`,
~961 passed/3 skipped); browser tests are source-assertion contract tests except the jest-axe +
interaction tests; Python tests can't import swarmgraph.{decomposition,adaptive_consensus} (TID251 ->
use inspect.getsource); grep current files before editing docs (snapshots go stale).

Finalize: full Python + arc-extension sweep, banned-claims clean, main clean + local==origin, summary
(X Polished / Y kept-Baseline-with-gap + each gap's closure path).

Approved. Execute.
```

---

## Tier 2 — 25 larger research-backed Horizon tasks

Legend: **NP** = none-posture executable · **GATED** = planned, needs the noted gate · **slice** = bounded none-posture portion doable now. DoD gates per item; effort S/M/L/XL.

### Theme A — Sandbox / microVM execution (R75, R76, B2P-21)

| # | Task | Ref | Posture | Research-backed approach + bounded NP slice |
|---|---|---|---|---|
| L-A1 | Firecracker Linux/KVM microVM execution proof on a real host | R76 / B2P-21 | **GATED** (Linux/KVM host) | Boot a microVM (kernel boot-source + rootfs drive) under **jailer** for cgroup/namespace isolation + a strict no-network proof; mirror the passing macOS VZ proof structure. **Slice (NP):** harden the existing gated scaffold — jailer arg construction, rootfs/marker integrity guard, CI-skip structure, `firecracker_doctor()` readiness vs execution separation. 4,6 · L |
| L-A2 | macOS Apple Virtualization.framework runner beyond `pwd` | R75 (ADR-024) | GATED-adjacent (default-off) | Lift the kernel-command-line argv-length ceiling (ADR-024) for a bounded multi-arg command set. **Slice (NP):** a length-bounded argv encoder + proof for a small allowlisted command set, default-off, truth-guarded. 4,6 · L |
| L-A3 | Rootless isolation tier evaluation (gVisor / Lima) as a non-gated default-off backend | R-OPEN-SANDBOX | NP (research/ADR) | ADR comparing gVisor runsc / Lima rootless for a developer-grade isolation tier; deterministic doctor/preflight; no execution claim until proven. 6,8 · M |

### Theme B — MCP remote / HTTP transport + authorization (B2P-06, B2P-15)

| # | Task | Ref | Posture | Research-backed approach + bounded NP slice |
|---|---|---|---|---|
| L-B1 | MCP authorization design ADR | roadmap L634 | **NP** (design + unit) | Per MCP spec **2025-11-25**: act as an **OAuth 2.1 resource server** — serve **Protected Resource Metadata** at `/.well-known/oauth-protected-resource`; on missing/invalid token return **`401` + `WWW-Authenticate: Bearer resource_metadata="…"`**; validate the token **audience (RFC 8707)** so a token issued for another resource is rejected. **Slice (NP):** the ADR + a deterministic, offline token-audience/PRM validator unit (no live server, no network). 6,8 · M |
| L-B2 | MCP Streamable HTTP transport behind the auth gate | roadmap L634 | **GATED** (auth decision first; stdio stays default) | Add Streamable HTTP transport (single endpoint, session id) **behind** L-B1's gate; stdio remains the default. **Slice (NP):** loopback-only listener that enforces the 401/PRM/audience flow and is **default-off**, no remote exposure. 6 · L |
| L-B3 | MCP adapter (Phase 35) T3 live transport + client-session lifecycle | roadmap L1041 | **GATED** (live transport + trust posture) | Real MCP client-session connect/list/call/close against an external server. **Slice (NP):** offline client-session state-machine + lifecycle tests against an in-process fake. 4,6 · M |

### Theme C — Provider-backed SwarmGraph + adapters T3 (B2P-14, B2P-16, B2P-22)

| # | Task | Ref | Posture | Research-backed approach + bounded NP slice |
|---|---|---|---|---|
| L-C1 | Broad provider-backed SwarmGraph adoption | roadmap L1156/L831 | **GATED** (paid/live; forbidden claim until proven) | Extend beyond the one opt-in CrofAI/DeepSeek E2E proof to a multi-provider adoption matrix. **Slice (NP):** an offline/fake adoption-matrix harness + opt-in gate expansion; the broad-adoption claim stays forbidden until proven. 4 · L |
| L-C2 | ADK adapter T3 live execution | roadmap L1016/L1033 | **GATED** (google-adk + paid Gemini) | Live `LlmAgent`/`Runner` execution. **Slice (NP):** detection + offline runner scaffold + capability-matrix parity test. 4 · M |
| L-C3 | Live Battle Arena (provider-backed) | phases Ph34.6 | **GATED** (paid/live) | Provider-backed battle execution + voting. **Slice (NP):** deterministic offline battle + the productization scaffold + a11y/states (the Battle tab already renders offline). 4,6 · L |

### Theme D — Priority-1 CLI parity (OpenCode / Claude Code; R39, R57, R68–R76)

| # | Task | Ref | Posture | Research-backed approach + bounded NP slice |
|---|---|---|---|---|
| L-D1 | Git-transaction edit safety net | R39/R57 parity | **NP** (local git) | Aider-pattern: each AI edit is an **atomic git checkpoint**; `/undo` undoes **and discards** the last AI change; `/diff` shows changes since the last turn; dirty-state commit with a generated message. Confine to the workspace; **caveat:** untracked files survive `/undo` (document; never auto `git clean -fd`). Deterministic, confirmation-gated, audited. 1,4,6,7 · L |
| L-D2 | Rich IDE diff-apply (review → apply hunks) | R39 parity | **NP** (IDE) | Per-hunk review + apply with explicit loading/empty/error/degraded/success states; confirm-gated writes through the advisory-lock write bridge (B2P-13). 1,3,4,7 · L |
| L-D3 | Repo-map context generation | R68 parity | **NP** | Aider-style repo map (ranked symbol/dependency outline) feeding run-context packing; bounded, deterministic, redaction-aware. 3,4,5 · M |
| L-D4 | Live run-event streaming surface (loopback) | R53 | GATED-adjacent (public SSE/WS route forbidden) | **Slice (NP):** loopback-only `EventSource`/SSE for the IDE over `127.0.0.1`, no auth needed because no remote exposure; server-side push hook already exists. Public SSE/WebSocket product route stays forbidden. 1,5,7 · L |
| L-D5 | Autonomous repair loop (propose → apply → test → revert-on-fail) | R39 parity | **GATED** (provider calls for proposal) | **Slice (NP):** the deterministic repair-loop engine with a **fake** proposer + git **revert-on-fail** (built on L-D1), no provider calls; live proposal stays gated. 4,6,7 · L |
| L-D6 | Priority-1 CLI parity acceptance matrix → executable CI | R68 | **NP** | Turn the R68 research matrix into executable `arc ci` parity checks; stable JSON; documented. 3,4,8 · M |

### Theme E — Native mobile (R79.1, R79.2)

| # | Task | Ref | Posture | Research-backed approach + bounded NP slice |
|---|---|---|---|---|
| L-E1 | Native framework package builds (Expo EAS / RN / Flutter) | R79.1 | **GATED** (native toolchains + signing) | Real device/store builds. **Slice (NP):** build-config + advisory build-plan generation + CI-lane scaffolds (self-skip without toolchains), mirroring the `mobile:deps-audit` pattern. 4,8 · M |
| L-E2 | Native device-capability execution (Phase 11) | R79.2 | **GATED** (device) | **Slice (NP):** extend the fixtures-only capability bridge + a deterministic capability-matrix + fail-closed entry gate (already partial). 4,6 · M |
| L-E3 | Device attestation interface (Play Integrity / App Attest) | R79.3 follow-on | **NP** (fixtures) | Fail-closed, deterministic attestation hook interface (Android Play Integrity / iOS App Attest **shape**) with fixtures only; **real attestation providers stay human-gated** (same hard boundary as device posture). 6,8 · M |

### Theme F — Memory / desktop / evidence (B2P-17, B2P-20, automatic memory injection)

| # | Task | Ref | Posture | Research-backed approach + bounded NP slice |
|---|---|---|---|---|
| L-F1 | Electron signed packaging + notarization | B2P-17 | **GATED** (code-signing certs + Apple ID) | `@electron/notarize` via **`notarytool`** (altool is deprecated) in an `afterSign` hook; `hardenedRuntime: true` + `com.apple.security.cs.allow-jit` entitlement; `APPLE_ID`/`APPLE_TEAM_ID`/app-specific password from secrets. **Slice (NP):** the afterSign hook + entitlements + CI artifact wiring behind the existing `require-electron-signing.mjs` preflight (real sign needs certs). 4,8 · L |
| L-F2 | Reviewed Memory Evidence pack | B2P-20 (Ph67/70) | needs **human review** | Assemble the candidate human-reviewed memory-evidence fixture pack + the review checklist + the gate-unblock wiring. **Slice (NP):** the candidate pack + checklist + a guard test; the gate flips only after a human signs off. 4,8 · M |
| L-F3 | Automatic memory injection into run context | deferred | **NP** (opt-in) | Extend B2P-12's opt-in redaction-first extraction with opt-in **query/injection** at run start (relevance-bounded, redaction-first, default-off); deterministic; best-effort containment. 3,4,6 · M |

### Theme G — Layout-capable a11y / DoD-elevation infra (closes B2P-03, R-AUDIT26)

| # | Task | Ref | Posture | Research-backed approach + bounded NP slice |
|---|---|---|---|---|
| L-G1 | Playwright + axe layout-capable a11y harness | B2P-03 + R-AUDIT26 closure | **NP** | `@axe-core/playwright`: `new AxeBuilder({ page }).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze()` against the **rendered** browser IDE — measures **color-contrast** (WCAG 1.4.3) that jsdom can't. Shared test fixture (`makeAxeBuilder`), `include()`/`exclude()` scoping, CI lane. **Closes the two Phase-203 contrast gaps.** 2,4 · L |
| L-G2 | Theme-token contrast audit across the 6 shipped themes | R-UX4 / R-AUDIT21 | **NP** | Deterministically compute WCAG ratios for every `--theia-charts-*` / `--arc-*` semantic token (and the risk-badge palette) on each theme background; fix any AA failures. Complements L-G1 without a browser. 2,4,8 · M |

### Theme H — Adapter budget + cross-cutting (closes B2P-09)

| # | Task | Ref | Posture | Research-backed approach + bounded NP slice |
|---|---|---|---|---|
| L-H1 | Scoped adapter-budget enforcement phase | B2P-09 closure | **NP** (scoped phase) | Extend the run-scoped enforcement context with an **optional** budget enforcer (immutable copy / `ContextVar`, never mutating the frozen `EnforcementContext` in place), read it at one real adapter effect boundary, call `budget_checkpoint`, and add a real-enforcer exhaustion-interrupt test. **Closes the B2P-09 gap.** 5,6,7 · L |
| L-H2 | Provider configuration UX | roadmap L1083 | **NP** | Interactive provider config beyond env vars (TUI/IDE): select provider, enter key, pick model; secrets redacted in logs/UI/audit; deterministic; full UX states. 1,2,6,8 · L |

---

## Research sources

- **MCP authorization** — MCP spec **2025-11-25** `basic/authorization` + security tutorial (via context7 `/websites/modelcontextprotocol_io`): OAuth 2.1 resource server, Protected Resource Metadata (`.well-known/oauth-protected-resource`), `401` + `WWW-Authenticate` `resource_metadata`, RFC 8707 audience validation. (L-B1/B2/B3)
- **Playwright a11y** — Playwright `accessibility-testing-js` docs (via context7 `/microsoft/playwright`): `@axe-core/playwright` `AxeBuilder({page}).withTags([...]).analyze()`, fixture pattern, `include/exclude`. (L-G1)
- **Electron signing/notarization** — `@electron/notarize` + electron.build notarization docs (web): `notarytool` (altool deprecated), `afterSign` hook, `hardenedRuntime` + `com.apple.security.cs.allow-jit`, `APPLE_ID`/`APPLE_TEAM_ID`/app-specific password. (L-F1)
- **CLI agentic parity** — Aider git-integration docs + 2026 CLI-agent write-ups (web): atomic git auto-commits, `/undo` (undo + discard), `/diff`, `/commit`, repo-map context, edit modes; "git as a safety net" (untracked-file `git clean -fd` caveat). (L-D1/D2/D3/D5)
- **microVM** — grounded in the repo's own R75/R76 scaffold + ADR-024 (Firecracker behind KVM/rootfs/jailer gates; macOS VZ argv-length ceiling). (L-A1/A2)

## How to use Tier 2
Tier 2 items are **larger and mostly cross-batch**. Execute only the **NP** items and the **NP slices** under the same cadence as Tier 1. **GATED** items stay as planned scope — they require an explicit human decision and the noted gate (auth design, native device/toolchain, paid-live providers, Linux/KVM host, signing certs, or human review) and must not be claimed complete until proven by tests + evidence. Labels follow evidence; the posture stays single-user loopback alpha throughout.
