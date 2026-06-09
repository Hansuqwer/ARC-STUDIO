# Competitive Feature Backlog — 2026-06-09

**Type:** Research-findings backlog (candidate scope). Not a roadmap; not a commitment.
**Source:** `docs/handover/ARC-Studio-Complete-Deliverable.pdf` (Agentic Auditor, 2026-06-09) —
Section 5 "Twenty Invented Realistic Features" and Section 7 "Native Runtime Architecture
Specification".
**Companion roadmap rows:** `docs/roadmap.md` → NEW INTAKE → "Competitive Feature Backlog
Intake (R83–R102 + R-NATIVE-RUNTIME)".
**Companion phase:** `docs/phases.md` → Phase 273 (intake/registration).

---

## Status of every item in this document

> **All items below are `Not Started`.** None are implemented. There is no code, no test, and
> no evidence in this repository for any of them. They are captured as *candidate scope* from a
> competitive analysis so the ideas are tracked in one place. Each item requires an explicit
> roadmap decision (and the `Finish 1 → 100% before broadening` rule in `AGENTS.md`) before any
> implementation slice begins. The IDs `R83`–`R102` and `R-NATIVE-RUNTIME` are **reserved**, not
> active.
>
> These features do **not** change ARC Studio's posture. ARC Studio remains a single-user,
> loopback-only alpha workstation tool. No item here implies a production-grade, remote, or
> shared-host capability; any that touch compliance (e.g. R97) are aspirational targets, not
> certifications.

This deliberately avoids the failure mode flagged in the deliverable's own critical review,
where unstarted features were presented as a shipped patch. Status follows evidence.

---

## Summary

| ID | Feature | PDF Feature # | Effort (est.) | Status |
|---|---|---|---|---|
| R83 | ARC Predict — local next-edit autocomplete | 1 | M (~3w) | Not Started |
| R84 | ARC Index — local semantic codebase search | 2 | M (~2.5w) | Not Started |
| R85 | ARC Context — automatic context retrieval | 3 | M (~2w) | Not Started |
| R86 | ARC Continuum — session persistence & resume | 4 | M (~3w) | Not Started |
| R87 | ARC Stream — real-time event relay (Python → IDE/TUI) | 12 | M (~2.5w) | Not Started |
| R88 | ARC Git — git-native agent workflow | 7 | M (~2w) | Not Started |
| R89 | ARC Diff — one-click inline patch apply | 8 | M (~2w) | Not Started |
| R90 | ARC Memory — persistent project knowledge | 10 | M (~3w) | Not Started |
| R91 | ARC Hub — local-first assistant/config sharing | 9 | M (~3w) | Not Started |
| R92 | ARC Daemon Tasks — local background task runner | 11 | M (~2.5w) | Not Started |
| R93 | ARC Vision — local browser/desktop automation (HITL-gated) | 5 | L (~4w) | Not Started |
| R94 | ARC Advisor — token cost optimization advisor | 17 | M (~2w) | Not Started |
| R95 | ARC Dashboard — multi-workspace control center | 15 | M (~2w) | Not Started |
| R96 | ARC Voice — local voice-to-command interface | 6 | M (~2w) | Not Started |
| R97 | ARC Policies — sandbox policy template library | 14 | M (~2w) | Not Started |
| R98 | ARC Composer — visual SwarmGraph builder | 16 | L (~5w) | Not Started |
| R99 | ARC Debug — inline debugger & REPL (DAP) | 13 | L (~4w) | Not Started |
| R100 | ARC Notebook — agent workbook (`.arcnb`) | 18 | L (~4w) | Not Started |
| R101 | ARC Time Travel — run replay & diff debugger | 19 | L (~5w) | Not Started |
| R102 | ARC Migrate — cross-adapter migration assistant | 20 | L (~4w) | Not Started |
| R-NATIVE-RUNTIME | Native GPU visualizer (Rust/wgpu/egui) augmenting the Theia IDE | §7 | XL (multi-quarter) | Not Started |

DoD gate legend (from `AGENTS.md`): 1 UX-states · 2 a11y · 3 parity · 4 tests · 5 perf ·
6 security · 7 reliability · 8 docs.

---

## Feature details (all Not Started)

### R83 — ARC Predict (local next-edit autocomplete)
- **Concept:** A local, small-model next-edit predictor surfaced as inline ghost text in the
  IDE and a suggestion panel in the TUI. No cloud round-trip.
- **Competitive target:** Cursor Tab.
- **Dependencies:** local model runtime (ONNX/llama.cpp); none on other backlog items.
- **DoD focus:** 1, 3, 4, 5 (latency budget), 6 (local-only, no egress), 7 (graceful fallback if
  model absent), 8.

### R84 — ARC Index (local semantic codebase search)
- **Concept:** A local vector index of the workspace (quantized embeddings) enabling
  natural-language code search via CLI/TUI/IDE. Local embeddings only.
- **Competitive target:** Cursor codebase index.
- **Dependencies:** prerequisite for R85.
- **DoD focus:** 1, 2, 3, 4, 5 (index latency on large repos), 6 (local-only), 7 (stale-index
  degraded state), 8.

### R85 — ARC Context (automatic context retrieval)
- **Concept:** Assemble the most relevant files/symbols/recent edits before each model call,
  with a transparent, user-inspectable context budget.
- **Competitive target:** Windsurf Cascade auto-context.
- **Dependencies:** R84 (index).
- **DoD focus:** 1, 3, 4, 5, 6, 7, 8.

### R86 — ARC Continuum (session persistence & resume)
- **Concept:** Serialize full session state (history, open files, run context, budget) to a
  local store and restore it on restart.
- **Competitive target:** Claude Code / Codex session resume.
- **Dependencies:** none; encryption reuses existing `auth/manager.py` key.
- **DoD focus:** 1, 2, 3, 4 (resume-without-drift), 5, 6 (encrypted at rest), 7, 8.

### R87 — ARC Stream (real-time event relay, Python → IDE/TUI)
- **Concept:** A WebSocket/SSE relay that pushes run events from the local daemon to the IDE and
  TUI as they happen, replacing manual refresh/polling. Loopback-only.
- **Competitive target:** real-time run views in IDE-native tools.
- **Dependencies:** foundational for richer R99/R101 surfaces; reuses existing bounded event
  buffer (`MAX_LIVE_EVENTS`).
- **DoD focus:** 1, 3, 4, 5 (relay latency), 6 (loopback-only, no remote listener), 7
  (auto-reconnect), 8.

### R88 — ARC Git (git-native agent workflow)
- **Concept:** Optional mode where agent actions create micro-commits with generated messages,
  auto-branch per session, and auto-revert on failure.
- **Competitive target:** Aider git-native workflow.
- **Dependencies:** composes with R89.
- **DoD focus:** 1, 3, 4, 5, 6 (confirmation-gated mutations), 7, 8.

### R89 — ARC Diff (one-click inline patch apply)
- **Concept:** Render agent edits as inline diff blocks with accept/reject in the IDE and
  `y/n/q` hunks in the TUI; server-side apply with conflict detection.
- **Competitive target:** Continue.dev one-click apply / Cursor inline diff.
- **Dependencies:** optional integration with R88.
- **DoD focus:** 1, 2, 3, 4, 5, 6, 7, 8.

### R90 — ARC Memory (persistent project knowledge)
- **Concept:** An auto-updating local project knowledge base (architecture notes, conventions,
  recurring errors) with user-confirmed updates after each session.
- **Competitive target:** Windsurf Memories / Claude Code project memory file.
- **Dependencies:** benefits from R84.
- **DoD focus:** 1, 2, 3, 4, 5, 6, 7, 8.

### R91 — ARC Hub (local-first assistant/config sharing)
- **Concept:** A local-first catalog for sharing provider presets, sandbox policy templates,
  agent swarms, eval suites, and themes via git/Gist/local dirs. No central server.
- **Competitive target:** Continue.dev Hub.
- **Dependencies:** pairs with R97 (policy templates).
- **DoD focus:** 1, 2, 3, 4, 5, 6 (signature/checksum verification on install), 7, 8.

### R92 — ARC Daemon Tasks (local background task runner)
- **Concept:** A local scheduler that runs sandboxed, budget-capped agent tasks in the local
  daemon while the user is away. No cloud execution — everything stays on the machine.
- **Competitive target:** background/scheduled agents (kept strictly local here).
- **Dependencies:** benefits from R87 for progress surfacing.
- **DoD focus:** 1, 3, 4, 5, 6 (sandboxed + budget-capped + audited), 7, 8.

### R93 — ARC Vision (local browser/desktop automation, HITL-gated)
- **Concept:** Local Playwright browser automation and screenshot capture for visual
  verification, with every mouse/keyboard action human-approved by default.
- **Competitive target:** computer-use / background browser control.
- **Dependencies:** none; large scope.
- **DoD focus:** 1, 2, 3, 4, 5, 6 (every action confirmation-gated; sandboxed), 7, 8.

### R94 — ARC Advisor (token cost optimization advisor)
- **Concept:** A local analyzer over usage history that recommends cost-saving strategies
  (model switch, context compression, caching, batching) with a what-if simulator. Local only.
- **Competitive target:** usage dashboards (with actionable advice).
- **Dependencies:** reads existing budget/wallet data.
- **DoD focus:** 1, 2, 3, 4, 5, 6, 7, 8.

### R95 — ARC Dashboard (multi-workspace control center)
- **Concept:** A top-level view of all local ARC workspaces — status, recent runs, spend,
  health — with one-key switching. For one developer managing several local projects.
- **Competitive target:** workspace/project pickers.
- **Dependencies:** none.
- **DoD focus:** 1, 2, 3, 4, 5, 6, 7, 8.

### R96 — ARC Voice (local voice-to-command interface)
- **Concept:** Local speech-to-text (Whisper-class, on-device) feeding the existing
  chat/command pipeline. Hands-free, no cloud transcription.
- **Competitive target:** voice input in agent CLIs.
- **Dependencies:** none; lower priority.
- **DoD focus:** 1, 2, 3, 4, 5, 6 (local model only), 7, 8.

### R97 — ARC Policies (sandbox policy template library)
- **Concept:** A curated library of sandbox policy templates per use case (data science,
  open-source, regulated-industry profiles) as YAML with tests and docs. Compliance profiles are
  **aspirational targets, not certifications**.
- **Competitive target:** enterprise guardrail template sets.
- **Dependencies:** extends the existing deterministic policy sandbox; pairs with R91.
- **DoD focus:** 1, 2, 3, 4, 5, 6 (deterministic, no LLM allow/deny), 7, 8.

### R98 — ARC Composer (visual SwarmGraph builder)
- **Concept:** A drag-and-drop editor for SwarmGraph swarms that generates SwarmGraph Python
  from a visual graph, with validation (cycle/dead-node detection).
- **Competitive target:** visual agent-graph builders.
- **Dependencies:** SwarmGraph runtime maturity.
- **DoD focus:** 1, 2, 3, 4, 5, 6, 7, 8.

### R99 — ARC Debug (inline debugger & REPL, DAP)
- **Concept:** Step-through debugging of agent runs via pdb/IPython and the Debug Adapter
  Protocol; breakpoints in tool functions, variable inspection.
- **Competitive target:** IDE-native interactive debuggers.
- **Dependencies:** Theia already supports DAP; benefits from R87.
- **DoD focus:** 1, 2, 3, 4, 5, 6, 7, 8.

### R100 — ARC Notebook (agent workbook, `.arcnb`)
- **Concept:** A notebook surface where cells are agent prompts, tool calls, or code; output
  cells show results/logs; saved as `.arcnb` JSON with export to `.ipynb`/`.md`/`.py`.
- **Competitive target:** Jupyter-style workbooks for agents.
- **Dependencies:** isolated-context execution.
- **DoD focus:** 1, 2, 3, 4, 5, 6, 7, 8.

### R101 — ARC Time Travel (run replay & diff debugger)
- **Concept:** Record every state change per step (context, tool calls, model outputs, sandbox
  decisions); replay forward/backward, branch from any step, and compare execution paths.
- **Competitive target:** unique — no direct competitor at this depth.
- **Dependencies:** existing flight-recorder infra; benefits from R87.
- **DoD focus:** 1, 2, 3, 4, 5 (delta-storage bounds), 6, 7, 8.

### R102 — ARC Migrate (cross-adapter migration assistant)
- **Concept:** Convert agent projects between frameworks (e.g. LangGraph ↔ CrewAI, SwarmGraph →
  OpenAI Agents) via AST analysis + templated generation, with equivalence validation.
- **Competitive target:** unique — leverages ARC's multi-adapter surface.
- **Dependencies:** mature adapter coverage.
- **DoD focus:** 1, 2, 3, 4 (equivalence tests), 5, 6, 7, 8.

---

## R-NATIVE-RUNTIME — Native GPU visualizer (candidate track)

- **Concept:** A cross-platform, GPU-accelerated native desktop visualizer (Rust + `wgpu` +
  `egui`) for multi-agent execution: infinite zoomable canvas + event timeline. It would
  **augment** the Eclipse Theia IDE (not replace the Python daemon/CLI/TUI), and is proposed as
  an optional surface, not a default.
- **Status:** `Not Started` in this repository. A separate, exploratory prototype skeleton
  (crate scaffold, WGSL shaders, core data types) exists only in an external arena workspace and
  is **not** part of this repo and **not** promoted. Any adoption requires a dedicated ADR under
  `docs/adr/` because it would affect the Theia investment and the cross-language event contract.
- **DoD focus (if ever started):** all 8 gates, plus a migration/compatibility contract with the
  existing event protocol and an explicit decision record. Performance targets cited in the PDF
  (e.g. high-FPS canvas, high event-ingestion throughput) are **unverified aspirations**.

---

## Notes & cross-references

- Several items map onto known gaps in the repo's own audits (e.g. R87 relates to the
  events/streaming audit; R84/R85 to the workspace-intelligence audit). See
  `docs/research-findings/` siblings for the underlying audits.
- Nothing in this backlog is scheduled. Sequencing, if pursued, would respect the
  `Finish 1 → 100% before broadening` rule: at most one item moves to `In Progress` at a time.


---

## Security Hardening Backlog (R-SEC1–R-SEC4)

Source: PDF Section 6.2 (Threat Model). All `Not Started`. Cross-checked against
`docs/research-findings/security-audit-2026-06-07.md` to avoid duplicating closed work.

| ID | Item | PDF threat | Status | Prior coverage / dedupe |
|---|---|---|---|---|
| R-SEC1 | Subprocess isolation for MCP tool execution (wire through `isolation/selector.py`) | Malicious MCP server/tool | Not Started | Net-new: audit confirms tools run in the same Python process. |
| R-SEC2 | `security/prompt_guard.py` — regex detection of common injection patterns (research-grade, no bulletproof claim) | Prompt injection via provider API | Not Started | Net-new. |
| R-SEC3 | Python dependency SBOM (CycloneDX) + `pnpm-lock.yaml` integrity verification + reproducible-build attestation | Supply chain / dependency compromise | Not Started | Net-new for Python/pnpm; mobile SBOM already exists (R-MOBILE-P12-20). |
| R-SEC4 | `run_id` storage path-traversal residual: character allowlist + `relative_to()` confinement on `base_dir / f"{run_id}.jsonl"` | Workspace path traversal | Not Started | **Residual only.** Workspace paths already use `os.path.realpath()` / `is_path_within_root()`; run-ID guard added in R-POLISH1/CR-006. This closes the remaining storage-layer `run_id` finding still open in the security audit (P0). |

---

## Performance Backlog (R-PERF1–R-PERF9)

Source: PDF Section 9.4 (Recommended Performance Improvements). All `Not Started`. Cross-checked
against `docs/research-findings/accessibility-performance-reliability-audit-2026-06-07.md` and the
roadmap's R17 / R-POLISH rows.

| ID | Item | PDF priority | Status | Prior coverage / dedupe |
|---|---|---|---|---|
| R-PERF1 | Streaming workspace inventory (target < 5s for 100K files) | P0 | Not Started | Net-new. |
| R-PERF2 | Virtualize remaining lists: `TraceViewerSection` / `AssuranceTab` | P0 | Not Started | **Residual only.** The event stream is already virtualized via R17 (`VirtualizedEventList.tsx`, @tanstack/react-virtual) and bounded via R-POLISH9; this covers only the still-plain lists. |
| R-PERF3 | Lazy provider loading (target < 2s startup with 109 providers) | P1 | Not Started | Net-new. |
| R-PERF4 | Async `startRun()` CLI bridge in IDE (eliminate remaining blocking `execFileSync`) | P1 | Not Started | **Residual only.** `config-service`/notification backend already converted async in R-POLISH7/R-POLISH14; residual is `startRun()` (120s block) and `EditPlanBridge` argv-only `execFileSync`. |
| R-PERF5 | SQLite WAL auto-checkpoint tuning (target < 50ms write latency) | P1 | Not Started | Net-new tuning; WAL + busy_timeout already verified (R-AUDIT20). |
| R-PERF6 | Memory-mapped trace reading (target 1 GB trace < 5s) | P2 | Not Started | Net-new; TraceParser 64MB cap exists (R-POLISH11) but no mmap path. |
| R-PERF7 | Incremental workspace index (update < 1s per file change) | P2 | Not Started | Net-new; depends on R84 (ARC Index). |
| R-PERF8 | Provider connection pooling (target 10 concurrent calls/provider) | P2 | Not Started | Net-new. |
| R-PERF9 | WASM trace parser (research; ~10× large-trace speedup) | P3 | Not Started | Net-new; research-grade. |

---

## Process / Release Hygiene Backlog (R-PROC1–R-PROC6)

Source: PDF Section 1 (Process Actions for the Repository) + Section 10 immediate actions.
All `Not Started`. These harden the release/docs pipeline against the exact failure modes the
deliverable's critical review identified (stale, forward-dated, fabricated artifacts).

| ID | Item | Status | Notes |
|---|---|---|---|
| R-PROC1 | Auto-generate release intelligence from CI (export a HEAD-derived summary on merge to main) | Not Started | Replaces hand-maintained static deliverables. |
| R-PROC2 | `docs/RELEASE_SNAPSHOTS/` — dated, locked, auto-generated-from-HEAD markdown | Not Started | Dated snapshots from `git log` + `patches/INDEX.md`. |
| R-PROC3 | Enforce `patches/INDEX.md` freshness in CI (warn/fail if index older than HEAD by > 24h) | Not Started | Net-new CI gate. |
| R-PROC4 | Normalize repo name in docs (`arc-theia-studio` legacy alias → `ARC-STUDIO`) in README + DEVELOPMENT | Not Started | Cosmetic/consistency; additive. |
| R-PROC5 | Extend `scripts/check-banned-claims.sh` to flag forward-dated docs (Generated date newer than source commit) | Not Started | Directly prevents the re-dated-stale-PDF failure mode. |
| R-PROC6 | Retire/archive the `patches/` directory to `docs/archive/patches-2026-06-04/` + warn that `verify.sh` is 788dbc9-only | Not Started | All 27 patches already merged; directory is a historical artifact. |

---

## Approved Mockups

14 UI/UX mockups from the arena deliverable, **approved as design references**, preserved in
`docs/handover/mockups/`. Approval applies to the *design*; the corresponding feature
implementations remain at the status shown (mostly `Not Started`). Mockups are not evidence of
implementation.

| Mockup file | Maps to | Implementation status |
|---|---|---|
| `arc-predict-autocomplete.svg` | R83 ARC Predict | Not Started |
| `arc-continuum-session-resume.svg` | R86 ARC Continuum | Not Started |
| `arc-time-travel-debugger.svg` | R101 ARC Time Travel | Not Started |
| `arc-run-replay-timeline.png` | R101 ARC Time Travel (replay timeline) | Not Started |
| `arc-composer-visual-swarmgraph.svg` | R98 ARC Composer | Not Started |
| `arc-swarmgraph-parallel-agents.png` | R98 ARC Composer / SwarmGraph insight | Not Started |
| `arc-sandbox-policy-editor.png` | R97 ARC Policies | Not Started |
| `arc-tui-dashboard-v2.png` | R95 ARC Dashboard | Not Started |
| `arc-ide-browser-v2.png` | Existing Theia IDE (design refresh reference) | Shipped surface |
| `arc-mcp-workbench.png` | Existing MCP Workbench (Batch 7 / R-AUDIT) | Shipped surface |
| `arc-provider-wallet-picker.png` | Existing provider/wallet (R3 / R8 / R80) | Shipped surface |
| `arc-mobile-runtime-simulator.png` | Existing Mobile Runtime SDK (simulator) | Shipped surface |
| `arc-hitl-approval-gate.png` | Existing HITL + audit UX (R4) | Shipped surface |
| `arc-system-architecture.png` | Overall architecture reference (incl. R-NATIVE-RUNTIME) | Reference only |

> "Shipped surface" means a mockup proposes a visual refresh of an existing feature; it is a
> design reference, not a claim that the refreshed design is implemented.
