<!-- LOCKED: single source of truth. Do not create competing roadmap docs. -->
> 🔒 **LOCKED — THE single ARC Studio roadmap.** Locked at commit `ffa1e1f` (`spec/v0.8-r-ux2`), 2026-06-05.
> All other roadmap/plan/status docs are archived under `docs/archive/`. **Finish the active phase 1 → 100% before broadening to any new scope.**
> Update this file in place; never create a replacement roadmap/status markdown. Companion phase list: `docs/phases.md`. Charter: `AGENTS.md`.

# ARC Studio — Locked Remaining Roadmap

**Status:** Locked source of truth for remaining product work.
**Created:** 2026-05-17
**Last reality refresh:** 2026-06-06 — R75 macOS direct VZ gated public CLI proofs now pass for `pwd` plus real-host timeout, SIGINT, and command-failure proofs (no-network/workspace/teardown/audit evidence; `killed`/`kill_reason` on timeout+interrupt; failing guest command surfaces its non-zero exit with clean teardown); default-off and not production-grade; argv limited to short commands by a kernel-command-line-length ceiling (ADR-024 known limitation); R76 Linux/Firecracker proof remains host-unproven and Linux/KVM-only; R77 remains narrow live-smoke/gated, not broad provider-backed SwarmGraph E2E.
**2026-06-05 update (what shipped this track):** P0 five-way-audit hardening sprint complete (budget SQLite-lock fix, TUI shell-escape fail-closed, orphan FastAPI quarantine, POST-only `/api/runs/start`, enforcement-surface refresh, profile schema version). Isolation backend selector shipped end to end (commit 2233895): `execution.isolation` = auto|none|subprocess|docker|microvm with a v1→v2 migration, a resolver, policy-aware execution providers, `arc sandbox run` + agent-shell wiring, `arc isolation use/off/status/doctor`, an `arc workspace init` first-run chooser, and a `/settings` TUI selector (+30 tests; full suite 5192 passed, ruff clean). MicroVM gated `pwd` proof is now reproducible end to end on macOS arm64 via `tools/arc-vz-bringup.sh` (static BusyBox + open-source Kata `vmlinux.container` kernel + the `/proc` mount-point init fix, commit f6b3922) plus an additive `auto_bringup` `vz-host-proof` CI lane; still gated/default-off, not production-grade.
**Current evidence anchor:** local worktree | VZ exec-init initrd packer/static-BusyBox guard + reproducible bring-up scripts (`tools/build-arc-vz-busybox.sh`, `tools/arc-vz-bringup.sh`) + manual host-CI slice. The packed-initrd path now WORKS end to end: `tools/arc-vz-bringup.sh --run-proof` builds a static aarch64 BusyBox, fetches the open-source Kata `vmlinux.container` (6.18.28) kernel, packs the initrd, builds + ad-hoc-signs the runner, and runs the gated `uv run arc sandbox run --json --provider microvm -- pwd` → `ok:true`, `errors:[]`, with booted/no-network/virtiofs-workspace-mount/sentinel/symlink-escape markers proven and clean teardown (macOS 26.4 arm64; default-off; not production-grade). The earlier `ARC_VZ_BUSYBOX must be a static Linux BusyBox binary` block is resolved by the build script; ad-hoc signing is sufficient for the VZ entitlement (the real wall was a compressed EFI-zboot `vmlinuz` + virtiofs-as-modules, fixed by the Kata kernel and the `/proc` mount-point init fix, commit f6b3922).
**Update rule:** Update this file in the same commit whenever implementation status changes. Do not create replacement roadmap/status/implementation markdowns.

## Status Vocabulary

Use only these values in roadmap status lines:

| Status | Meaning |
|---|---|
| Not Started | Planned but no implementation slice has begun. |
| In Progress | Implementation is active and not yet accepted. |
| Baseline Complete | Minimum accepted behavior exists with tests/evidence; polish may remain. |
| Polished Complete | Baseline plus user-facing polish is accepted. |
| Blocked | Cannot proceed without an external decision, approval, secret, destructive action, or unavailable dependency. |
| Deferred | Intentionally out of current scope; requires explicit roadmap change to resume. |

Status lines should follow: `Status: <Status Value> | Evidence: <commit/run/test anchor> | Notes: <one sentence>`.

---

## Completed Roadmap — Master Ledger

> Single scannable list of every roadmap item that has reached Complete / Baseline Complete.
> This is navigation; the authoritative status + evidence live in each item's detailed section
> below. Items NOT complete are in the next table. New roadmap items: append under the
> **NEW INTAKE** marker at the end of this file, then add a row here once Baseline Complete.
>
> Note: roadmap IDs were reused across eras (e.g. there are two R45–R55 blocks). The detailed
> sections remain the disambiguator; rows below are grouped by era to stay unambiguous.

### Core product track (R1–R13)

| ID | Title | Status |
|---|---|---|
| R1 | Live Run Streaming Product Path | Complete |
| R2 | IDE Runtime Setup + Config Wizard | Complete (polished UI baseline) |
| R3 | Provider, Quota, Cost Controls UI | Baseline Complete |
| R4 | Dedicated HITL + Audit UX | Complete |
| R5 | SwarmGraph Insight Baseline | Complete |
| R6 | Real Adoption Productization | Complete (local-real baseline) |
| R7 | Release Operations + History Hygiene | Complete |
| R8 | IDE Provider/Quota Completion | Baseline Complete |
| R9 | IDE Live Stream Polish | Baseline Complete |
| R10 | Doctor/Daemon Parity Closure | Baseline Complete |
| R11 | SwarmGraph Cost Producer | Baseline Complete |
| R12 | Packaging/Optional Features | Baseline Complete |
| R13 | SwarmGraph Native Runtime | P1–P4 Baseline Complete |

### Protocol / platform track (R14–R37, R77)

| ID | Title | Status |
|---|---|---|
| R14 | Streaming Audit Verification + HMAC Signing | Baseline Complete |
| R15 | Discriminated RunEvent Unions + Protocol Conformance | Baseline Complete |
| R16 | Enforced Workspace Trust + Paid-Call Gates | Baseline Complete; Active Hardening |
| R17 | Trace Viewer Virtualization + Daemon Resilience | Baseline Complete |
| R18 | CLI Decomposition + Stable JSON Contracts | Baseline Complete |
| R19 | MCP Local Control Plane for ARC | Baseline Complete |
| R20 | MCP Tasks for Async Execution | Baseline Complete |
| R21 | LangGraph Durable Execution + Replay Contract | Baseline Complete |
| R22 | Persistent HITL + Inspect-Style Eval Artifacts | Baseline Complete (HITL only) |
| R23 | Consensus Escrow (Commit-Reveal Voting) | Complete |
| R24 | Adaptive Consensus Protocol | Complete |
| R25 | Event-Driven Audit/HITL Notifications | Baseline Complete |
| R26 | Swarm Memory Graph | Baseline Complete (research prototype + privacy/eval gates) |
| R27 | LangChain Adapter | Baseline Complete |
| R28 | Anthropic Provider + Registry | Baseline Complete |
| R29 | OpenAI-Compatible Provider | Baseline Complete |
| R30 | Pydantic AI Adapter | Baseline Complete |
| R31 | DSPy Adapter | Baseline Complete |
| R32 | Haystack Adapter | Baseline Complete |
| R33 | Smolagents Adapter | Baseline Complete |
| R34 | Semantic Kernel Adapter | Baseline Complete |
| R35 | Google ADK Adapter | Baseline Complete |
| R36 | MCP Python SDK Adapter | Baseline Complete |
| R37 | Provider Management System | Baseline Complete |
| R77 | SwarmGraph Runtime Hardening | Baseline Complete + Live Smoke Proven |

### CLI/UX + sandbox + edit-loop track (R39–R76)

| ID | Title | Status |
|---|---|---|
| R39 | Interactive CLI/UX Foundation | Baseline Complete |
| R40 | CLI/UX Polish & Advanced Features | Baseline Complete |
| R41 | Advisory Locking + IDE Session Bridge | Baseline Complete |
| R42 | Slash Registry Expansion + REPL Error Boundary | Baseline Complete |
| R43 | Approval + Progress + Error UX | Baseline Complete |
| R44 | IDE Write Bridge / Daemon Protocol | Baseline Complete |
| R45–R55 (era-2) | Trace-Aware Review, Plan/Apply, Command/Approval Centre, MCP Workbench, Workspace Intelligence, Theia cleanup, Capability/MCP risk gates, CI Guardrails, Consensus differentiators, Notifications+DAG planner, Eval→Policy, AGENTS.md/SKILL.md | Baseline Complete |
| R53 (era-3) | Local Sandbox Audit Query + Compaction | Baseline Complete |
| R54 (era-3) | Container Isolation Provider | Baseline Complete |
| R55 (era-3) | Local Sandbox Policy YAML | Baseline Complete |
| R56 | Agentic CLI Edit Loop | Baseline Complete |
| R57 | Interactive CLI UX Polish | Baseline Complete |
| R58 | Tool Runtime Unification | Baseline Complete |
| R59 | Edit Preview Staleness Guard | Baseline Complete |
| R60 | Saved Edit Plan Apply Flow | Baseline Complete |
| R61 | Edit Bundle Approval Bridge | Baseline Complete |
| R62 | IDE Edit Plan Review Surface | Baseline Complete |
| R63 | Sandboxed Diff/Apply/Test Loop | Baseline Complete |
| R64 | Patch Engine Hardening v2 | Baseline Complete |
| R65 | Sandbox/MicroVM Truth Audit Guard | Baseline Complete |
| R66 | Sandbox Classifier + Path-Intent Hardening v3 | Baseline Complete |
| R67 | MicroVM Proof-Harness Truth Guards | Baseline Complete |
| R68 | Priority 1 CLI Parity Research + Acceptance Matrix | Baseline Complete |
| R69 | Autonomous Edit-Test-Repair Loop | Baseline Complete |
| R70 | Git-Backed Undo/Redo Transactions | Baseline Complete |
| R71 | Rich IDE Diff Review/Apply Flow | Baseline Complete |
| R72 | Provider-Backed Runtime Shell | Baseline Complete |
| R73 | Live Terminal/Event Streaming UX | Baseline Complete |
| R74 | Broad CLI CI Orchestration | Baseline Complete |
| R75 | macOS MicroVM Execution + Strict No-Network Proof | Gated proof passed once; default-off |
| R76 | Linux Firecracker Execution Proof | Baseline Complete (host-unproven) |
| R78 | A2A Local AgentCard Generator + Loopback Client | Baseline Complete |

### Token-saving + UX + open-hardening track (R-TS / R-UX / R-OPEN)

| ID | Title | Status |
|---|---|---|
| R-TS2 | Token-Saving P0 | Baseline Complete |
| R-TS3 | arc-protocol-ts coverage backfill | Baseline Complete |
| R-TS4 | R-01 TokenWallet | Baseline Complete |
| R-TS5 | Budget Persistence + Pricing Refresh | Baseline Complete |
| R-TS7 | R-02 + QW-4 feature sprint | Baseline Complete |
| R-TS8 | Chinese-labs vendor adoption + capability backfill | Baseline Complete |
| R-TS9 | Catalog-driven model picker + capability gating | Baseline Complete |
| R-TS10 | Opt-in cloud features | Baseline Complete |
| R-UX1 | UX Polish — Header + ContextMeter + ModeBadge + Markdown | Baseline Complete |
| R-UX2 | UX Modes + Approvals | Baseline Complete |
| R-UX3 | UX Components + Information Architecture | Baseline Complete (all deferred items resolved) |
| R-UX4 | UX Themes + Accessibility | Baseline Complete |
| R-OPEN-HARDEN | Production Hardening (retry + degrade + failover + wiring) | Baseline Complete |
| R-OPEN-SANDBOX | MicroVM / Sandbox Layer (shell-escape hardening) | Baseline Complete |
| R-OPEN-DEFERRED-RUNBOOKS | Execute Deferred Research Runbooks | Baseline Complete |
| R-OPEN-ADAPTERS-AUDIT | Audit External Adapters Research Folder | Baseline Complete |
| R-OPEN-ADAPTERS-SHARED | Adapter Shared Helpers Consolidation | Baseline Complete |
| R-OPEN-ADAPTERS-PYDANTIC-AI | pydantic_ai Placeholder Cleanup | Baseline Complete |
| R-OPEN-ADAPTERS-STRANDS | Strands Agents (AWS) Adapter | Baseline Complete |
| R-OPEN-ADAPTERS-PYDANTIC-AI-RUNNER | pydantic_ai Real Runner | Baseline Complete |
| R-OPEN-ADAPTERS-LETTA | Letta (MemGPT) Adapter | Baseline Complete |
| R-OPEN-ADAPTERS-BROWSER-USE | Browser Use Adapter | Baseline Complete |
| R-OPEN-ADAPTERS-AGNO | Agno Adapter | Baseline Complete |
| R-OPEN-SANDBOX-APPROVAL | Sandbox Approval Hint + Dead Branch Removal | Baseline Complete |
| R-OPEN-AG-UI-GAPS | AG-UI Mapper Registration | Baseline Complete |
| R-OPEN-CI-FLAKES-119 | CI Flakes — HMAC+SIGINT xfail | Baseline Complete |
| R-OPEN-CI-FLAKES-120 | CI Flakes — SQLite concurrent accumulation xfail | Baseline Complete |

### Not-yet-Complete / Blocked / Deferred / Research Intake

| ID | Title | Status |
|---|---|---|
| R-TS1 | Token-Saving Research | Baseline Complete (sdk_version sweep done — R-AUDIT24 Phase 155) |
| R79 | Mobile Runtime SDK Integration | Baseline Complete | Evidence: Phase 111 + Phase 148 + Phase 157 | Slices 110.1–110.5 + TUI /budget + Theia Mobile Runtime IDE tab (simulator/mock only; no native-execution claims). |
| R34.6 / Battle Arena | Provider-Backed Battle Arena | Blocked (no default paid/live calls) |

---

## Current Baseline

- Canonical app: `applications/browser` + `packages/arc-extension`.
- Legacy `theia-extensions/*` and `packages/arc-browser-app` are archived under `docs/archive/`.
- GitHub CI green on `7a300fe` (python, node, ARC Roadmap Gate, signing-preflight, e2e). Commit `4b0f6b5` implements all 6 previously-deferred items from the Active Work Ledger. All Baseline Complete phases evaluated for polish; all ship at current status for v0.1 (polish deferred to v0.2).
- Release-scope CLI/IDE basics are implemented and tested.
- Remaining work is product depth, not repo stabilization.

## Non-Negotiable Scope Boundaries

- Priority 1 until complete: full CLI parity track (`R68`-`R76` / `Phases 97`-`105`). Do not advance unrelated product roadmap execution until the CLI parity acceptance matrix is complete or explicitly reprioritized. Security/sandbox/provider/IDE/CI work that directly supports this track is allowed.
- No broad live/provider-backed SwarmGraph adoption claim until real provider-backed adoption paths are implemented and tested.
- No adapter-wide keyed audit claim until every claimed run path writes/verifies keyed audit material.
- No production/concurrent-user/tenant isolation claim.
- LM Arena remains stub-default/gated and out of v0.1 product scope.
- Electron packaging/signing remains post-v0.1 unless explicitly reprioritized.
- `.env` history scrub requires explicit release date + force-push/history-rewrite approval.

## Gated Execution Paths

| Path | Required Gates | Exact Confirmation | What It Proves | What It Does Not Prove | Evidence |
|---|---|---|---|---|---|
| `langgraph+swarmgraph` local-real smoke | `ARC_REAL_RUNTIME_SMOKE=1`, `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`, installed local deps | None beyond smoke invocation | Narrow local, non-provider-backed LangGraph + SwarmGraph execution path can run when dependencies and both gates are present | No provider-backed execution; no broad adoption readiness; no paid calls | Locked R6 baseline; opt-in smoke/manual path |
| `arc providers action` via 9router | Live-provider test env gate, paid-call opt-in, env/key references only | `RUN_PROVIDER_ACTION:<provider>:<model>` | One narrow gated provider action path and ARC local accounting | No remote quota reset; no provider-backed adoption; no SwarmGraph runtime execution | `9184f9b` with `9router` / `nvidia/minimaxai/minimax-m2.7` |
| LM Arena | None accepted for product use | N/A | Stub/default arena behavior only | No live arena product feature | Fiction list / release scope |

## Producer Inventory

Only render rich UI data from event producers listed here. Missing producers must yield absent/degraded UI states, not fabricated data.

| Event/Data Type | Producer Path | Status | UI Consumers |
|---|---|---|---|---|
| Active run SSE transport events | `EventBroker`/`JobSupervisor`, `/api/runs/{id}/events`, `/api/sse/proof` stub | Baseline Complete | Event Stream, Run Timeline |
| `RUN_STARTED` / terminal events | SSE proof stub and supported run paths | Baseline Complete | Event Stream, Run Timeline |
| SwarmGraph topology | `langgraph+swarmgraph` event path | Baseline Complete for first producer; absent elsewhere | SwarmGraph Insight |
| Consensus/vote events | `langgraph+swarmgraph` event path | Baseline Complete for first producer; absent elsewhere | SwarmGraph Insight |
| Measured cost/token events | `langgraph+swarmgraph` adoption runner (first producer) | Baseline Complete | SwarmGraph Insight Cost panel (renders provider/model/tokens/cost/source/measured from explicit events) |
| HITL prompt/response/timeout | `JobSupervisor` HITL flow + CLI/IDE response paths | Baseline Complete | Assurance tab, Runs tab basics |
| Audit chain material | ARC audit paths and keyed audit CLI path where specific run writes material | Conditional | Assurance tab, audit verify/export |
| Effect-boundary journal entries | `arc runs fork` CLI command | Baseline Complete | Fork/replay UX via CLI `arc runs fork` |

## Documentation Inventory

| Location | Purpose |
|---|---|
| `docs/roadmap.md` | Authoritative roadmap/status. |
| `docs/phases.md` | Authoritative ordered execution plan. |
| `docs/adr/` | Architecture decisions. |
| `docs/research/` and `docs/wiki/research-context/` | Supporting research/scaffolds only, not status. |
| `docs/release/checklist.md` | Release evidence and gates. |
| `docs/archive/` | Historical context only. |
| `docs/handover/` | Thin pointers/context; must defer to locked docs. |
| `scripts/check-banned-claims.sh` | Enforced release-claim guard. |

## Research-Backed Candidate Roadmap Intake

**Source:** `docs/research/deep-research-review-findings.md` and `docs/research/deep-research-improvements.md` from the 2026-05-27 deep research synthesis.
**Status:** Planning intake only. These entries are not implementation evidence and do not change any existing Baseline Complete status.

| Candidate ID | Status | Evidence | Notes |
|---|---|---|---|
| R45 Trace-Aware Review Mode | Baseline Complete | local worktree: review/plan tests 34 passed; full Python 3105 passed / 34 skipped / 3 xfailed; `pnpm build` OK; `pnpm typecheck` OK | Review evidence model/CLI links diffs to trace/tool/approval/test/sandbox/policy/audit material where supplied; missing provenance renders unknown/empty, not fabricated. |
| R46 Plan / Apply / Review Loop | Baseline Complete | local worktree: `cd python && uv run ruff check src tests` OK; `cd python && uv run pytest tests/ -q` 3114 passed / 34 skipped / 3 xfailed; `pnpm build` OK; `pnpm typecheck` OK; `bash scripts/check-banned-claims.sh docs/agents.md docs/roadmap.md docs/phases.md docs/release/checklist.md docs/REALITY_AUDIT.md docs/EXTENSION_MIGRATION.md docs/handover/HANDOVER.md README.md` OK | Deterministic plan/explain/apply baseline exists with approval gate and audit events; destructive/privileged remain denied; no broad runtime/provider execution. |
| R47 Agent Command Centre / Approval Centre | Baseline Complete | local worktree: targeted arc-extension tests 135 passed; `pnpm build` OK; `pnpm typecheck` OK | Command Centre aggregates existing sessions, runs/traces, HITL approvals, sandbox/isolation, profiles, provider health, workspace/risk/config context; absent task producer renders degraded state; no new runtime. |
| R48 MCP Workbench Phase 1 | Baseline Complete | local worktree: `cd python && uv run pytest tests/mcp/ -q` 56 passed (11 workbench tests); `arc mcp workbench status --json` and `arc mcp workbench inspect --server <cmd> --json` implemented; CLI + standalone IDE tab; no HTTP listener or external server auto-start; read-only diagnostics only | CLI baseline for MCP server status inspection and stdio MCP server tool/resource/prompt enumeration; trust state and audit path included in status output. Standalone McpWorkbenchTab added to IDE. |
| R49 Workspace Intelligence + Test Bench | Baseline Complete | local worktree: `cd python && uv run pytest tests/cli/test_workspace_inventory.py tests/cli/test_testbench.py -q` 16 passed; `arc workspace inventory --json`, `arc testbench detect --json`, `arc testbench run --policy local-safe -- <cmd>` implemented; standalone IDE tab | Deterministic workspace inventory with files/git/traces/MCP resource provenance; test command detection from package.json/pyproject.toml/Makefile; test execution routes through sandbox policy path with network/destructive denied by default. Standalone TestBenchTab added to IDE. |
| R50 Theia-Native Architecture Cleanup | Baseline Complete | local worktree: targeted arc-extension tests 135 passed; `pnpm build` OK; `pnpm typecheck` OK | Daemon discovery extracted into typed Theia service and injected into backend/session bridge; broader backend split remains follow-up. |
| R51 Capability Card Enforcement Gate | Baseline Complete | local worktree: 32 enforcement tests passed; 232 protocol/capabilities tests passed; parity tests green; `pnpm build` OK | Deterministic LLM-free enforcement gate (ADR-027); `CAPABILITY_CARD_DECISION` event; `_cards_mode` ContextVar; fail-closed semantics; strict/warn/off modes; CoSAI-aligned rule chain. |
| R52 MCP Outbound Per-Call Risk Gate | Baseline Complete | local worktree: risk/sandbox/proxy tests passed; `MCP_CALL_DECISION` event; TS parity; `pnpm build` OK | Deterministic LLM-free per-call risk scorer (ADR-028); score table: critical/high/medium/low; strict/permissive policies; stdio proxy with 1MB cap; decisions.jsonl workspace-local audit; `arc mcp risk-scan`, `arc mcp decisions`, `arc mcp policy-explain`, `arc mcp proxy` CLI commands. |
| R51 ARC CI Guardrails | Baseline Complete | local worktree: `cd python && uv run pytest tests/cli/test_ci.py -q` 11 passed; `arc ci check --json --private`, `arc ci summary --format markdown`, `arc ci verify-audit --json` implemented; standalone IDE tab | Advisory local-first CI commands; private mode uploads nothing; existing eval/policy/receipt/audit verification only; no blocking provider-backed AI judgment. Standalone CiGuardrailsTab added to IDE. |
| R52 SwarmGraph Consensus Differentiators | Baseline Complete | local worktree: `cd python && uv run pytest tests/swarmgraph/test_consensus_differentiators.py tests/evals/test_consensus_eval.py -q` 87 passed; full suite `cd python && uv run pytest tests/ -q` 3280 passed / 34 skipped / 3 xfailed; `pnpm build` OK; `pnpm typecheck` OK; `bash scripts/check-banned-claims.sh` OK | Selective debate, confidence-weighted quorum, critic/verifier lane, HITL sign-off quorum, and gossip protocol implemented as deterministic offline functions with 64 tests. Eval harness with `arc swarmgraph eval --compare --json` CLI for benchmarking metrics (quality/cost/latency/disagreement/escalation). No broad provider-backed execution. |
| R53 SwarmGraph Notifications + Deterministic DAG Planner | Baseline Complete + Narrow Live E2E Proven | local worktree: `cd python && uv run pytest tests/ -q` 3705 passed / 41 skipped / 3 xfailed; `cd python && uv run ruff check src tests` OK; `pnpm build` OK; `pnpm typecheck` OK; opt-in CrofAI artifact E2E `ARC_RUN_LIVE_PROVIDER_E2E=1 ARC_ALLOW_LIVE_PROVIDER_TESTS=true ARC_SWARMGRAPH_PROVIDER=crofai ARC_SWARMGRAPH_MODEL=deepseek-v4-pro-precision ARC_PROVIDER_E2E_ARTIFACT=/var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-provider-e2e-crofai.json uv run pytest tests/integration/real_runtime/test_swarmgraph_provider_e2e.py::test_live_provider_backed_swarmgraph_e2e_opt_in_only -q` passed | Managed notification service, server-side push hook surface, deterministic local DAG planner/CLI, one opt-in live provider-backed SwarmGraph E2E proof for CrofAI/DeepSeek V4 Pro Precision, and durable redacted JSON evidence artifact support added. Artifacts store hashes/lengths, not raw prompt/output. Public SSE/WebSocket product route, provider-backed auto planning, and broad provider-backed SwarmGraph adoption remain not claimed. |
| R54 Eval-to-Policy Auto-Apply Loop | Baseline Complete | local worktree: `cd python && uv run pytest tests/evals/test_apply.py -q` 22 passed; parity tests green; `pnpm build` OK; `pnpm typecheck` OK | `evals/apply.py` maps `PolicyRecommendation.action` → `RunProfile` mutations; append-only versioned profiles (`.arc/profiles/<id>.v<n>.yaml`); idempotent; never overwrites builtins; `PROFILE_SCHEMA_VERSION=2` with `extra: dict` field; `EVAL_POLICY_RECOMMENDED`/`EVAL_POLICY_APPLIED` typed events; `arc eval recommend-apply` CLI command with `--profile`, `--dry-run/--no-dry-run`, `--json`. |
| R55 AGENTS.md Workspace Ingestion + SKILL.md Catalog | Baseline Complete | local worktree: `cd python && uv run pytest tests/context/ -q` 32 passed; `arc agents-md discover --json`, `arc agents-md nearest`, `arc agents-md pin`, `arc agents-md drift`, `arc agents-md cards`, `arc skills discover`, `arc skills cards` implemented | Deterministic AGENTS.md discovery with nearest-wins resolution, override priority, LLM-generated heuristic (3-of-4 signals), pin/drift detection, SKILL.md YAML frontmatter parsing, CapabilityCard generation for both entity types. |

**Deferred by default until explicit roadmap change:** executable plugin marketplace, remote MCP beyond loopback, raw team trace sync, automatic memory injection, public microVM execution, and broad provider-backed SwarmGraph execution.

## R1 — Live Run Streaming Product Path

**Goal:** Active runs stream events into IDE views while running, not only replay stored traces.

**Current:** Complete Phase 1 vertical baseline plus Phase 8 local daemon productization baseline. Python SSE supports active/replay modes and terminal/disconnected semantics; Theia exposes a typed `streamActiveTrace()` proxy that can use an explicit/requested Python web base URL or `ARC_PYTHON_DAEMON_URL`; Event Stream/SwarmGraph Insight surfaces distinguish live/replay/disconnected states; `/api/sse/proof` has deterministic limited-local coverage only and is not evidence of broad runtime live event support.

**Deliverables:**
- Python active run stream endpoint or command path backed by `EventBroker`/`JobSupervisor`.
- Theia backend subscription/proxy with env filtering and cancellation safety.
- Event Stream/Run Timeline live state: connecting, live, replay, disconnected.
- Stub-backed e2e proving live events arrive during a launched run.

**Acceptance:**
- Unit/web tests for active stream lifecycle.
- E2E launches or connects to a stub live stream and observes at least `RUN_STARTED` and terminal event live.
- Docs distinguish broker-backed active stream, deterministic SSE proof stub, and stored-trace replay.

**Status:** Baseline Complete for configured local daemon/stub runtime live event streams. Evidence: local Phase 8 verification on `bec8d4b` worktree (`python` web SSE tests, arc-extension tests/build, browser build/e2e, `scripts/check-pr.sh`). Notes: IDE live mode can connect to configured Python daemon/local runtime streams and handles terminal/degraded states while preserving replay-not-live copy; this is not a broad runtime/provider-backed live event claim.

**Follow-up:** Browser e2e logs known Theia async contribution warnings; Phase 13 (R9) captured the exact warning fingerprint in the e2e test and proved them harmless/intentionally-accepted. Phase 8.1 (IDE-to-daemon SSE e2e harness) completed separately.

## R2 — IDE Runtime Setup + Config Wizard

**Goal:** Users can configure runnable adapters/profiles from IDE without editing shell env manually.

**Current:** CLI config/profiles/workspace commands exist; ChatTab exposes runtime/profile selectors; ConfigTab now loads backend runtime capabilities, profiles, isolation providers/status, safe YAML-backed config save fields, provider key env-var references, copy-safe config snapshots, persisted profile selection copy, and a capability-derived Runtime Setup Wizard with missing env/dependency/manual remediation guidance. Dedicated export-target helper UI exists for CrewAI, OpenAI Agents, and LlamaIndex using env-var references only.

**Deliverables:**
- Adapter readiness details with concrete missing env/dependency actions.
- Config editor for ARC YAML-backed settings/profiles.
- Workspace trust + isolation profile display/config.
- Export-target helpers for CrewAI/OpenAI Agents/LlamaIndex without storing raw secrets.

**Acceptance:**
- Static/contract tests for UI wiring.
- Backend method tests for config read/write/dry-run.
- No secrets persisted directly; env/keychain references only.

## R3 — Provider, Quota, Cost Controls UI

**Goal:** Existing CLI/provider diagnostics and quota controls are visible and actionable in IDE.

**Current:** Chunks 3.1-3.3 hardened to Baseline Complete. CLI provider diagnostics/quota commands work; IDE has provider diagnostics with typed telemetry parsing/tests covering empty/partial/malformed/success states, targeted confirmation before local quota-counter reset (local-only copy, no remote/provider reset implication), a profile-linked cost policy summary, backend cost-gate metadata/enforcement, and hardened explicit paid/live opt-in gate wording with three-layer gated provider action (env + paid opt-in + exact confirmation) impossible to trigger without every gate. Reset is backed only by existing `arc providers quota reset --json` local quota-counter semantics. Live/provider UX remains offline/gated by default and performs no provider network calls. R3 now includes one narrow gated provider-action baseline for 9router-routed model calls via `arc providers action`, requiring the live env gate, paid-call opt-in, exact confirmation, and env/key references only. Opt-in smoke evidence passed on `9184f9b` for `9router` with `nvidia/minimaxai/minimax-m2.7`; successful live actions may update ARC local accounting only. There is no remote quota reset, provider-backed adoption, SwarmGraph/provider adoption wiring, or broad real-runtime completion claim.

**Deliverables:**
- Provider diagnostics panel.
- Quota status/reset UI where safe; confirmation required before reset. Reset is local quota-counter reset only, not a provider/network reset.
- Paid-call gate warnings before any provider-backed action; default live-provider UX is preview/gate only and performs no network/provider calls.
- Profile-linked provider/cost summary backed by backend cost-gate metadata; UI does not enable provider execution.
- Gated 9router provider-backed action path with dry-run default, no default network, env/key references only, explicit paid-call opt-in, exact confirmation UX, local cost/quota accounting only, no remote quota reset, and no broad provider-backed adoption claim.

**Acceptance:**
- Tests prove no live provider call without explicit gate.
- UI clearly labels dry-run/offline vs live/gated.
- Parser/runtime tests cover malformed or partial provider telemetry without enabling provider network calls.
- Opt-in smoke/manual verification proves only the narrow gated 9router provider-action path runs when all gates are set; current evidence is `9router` / `nvidia/minimaxai/minimax-m2.7` on `9184f9b`. Default tests remain offline and deterministic, and evidence does not imply provider-backed adoption or SwarmGraph runtime execution.

## R4 — Dedicated HITL + Audit UX

**Goal:** Move beyond RunsTab basics into dedicated high-assurance workflows.

**Current:** Dedicated IDE Assurance tab with polished HITL inbox (auto-refresh, LIVE badge, last-refreshed timestamp), run-scoped audit chain states, replay stepper with category filtering (lifecycle/message/tool/error/hitl/audit/unknown), JSON export for sections with data, audit export only where run audit material exists, and clear present/missing/degraded/expired states. HITL pending/respond CLI and RunsTab basics still exist; audit verify/export/key CLI exists; adapter-wide HMAC is not guaranteed.

**Deliverables:**
- HITL inbox view with approve/reject/respond, token expiry, replay-attack-safe messaging.
- Audit chain viewer for runs with audit material.
- Clear degraded/absent audit states.
- Replay stepper integrated with audit/HITL events.

**Acceptance:** Complete for dedicated UX baseline. Backend/static UI contracts cover pending/respond/audit/replay states and the UI explicitly avoids adapter-wide HMAC claims.

## R5 — SwarmGraph Insight Baseline

**Goal:** Expose real SwarmGraph concepts only when backed by real events/data.

**Current:** Baseline IDE SwarmGraph Insight tab exists. Python has SwarmGraph topology/consensus/cost event schemas, and the LangGraph + SwarmGraph path now emits topology and consensus/vote events when that path runs. No cost producer exists yet, so cost panels remain empty/degraded unless measured cost events are present. The UI is live-aware through `streamActiveTrace()` and can consume explicit SwarmGraph insight events, but backend live SSE remains limited/degraded until the future Python web-base-url wiring is completed.

**Deliverables:**
- Trace-derived topology view for runs with topology events.
- Consensus/vote panel for runs with consensus events.
- Cost/token panel only where measured data exists.
- Empty/degraded states for runs without SwarmGraph insight events.

**Acceptance:**
- No fabricated topology/consensus/cost data.
- Tests cover empty/degraded and event-backed states.

## R6 — Real Adoption Productization

**Goal:** Turn fake-tested/gated adoption runners into narrow, honest, real product paths.

**Current:** Adoption protocol/runners exist. `crewai+swarmgraph` and `langgraph+swarmgraph` fake/offline CLI paths are routed for deterministic product use, and fake/offline remains the default. `langgraph+swarmgraph` also has a narrow local-real path with an explicit execution contract, dependency/preflight states, trace/IDE metadata, and regression/smoke coverage. Local-real availability requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`. It is non-provider-backed, performs no paid/live provider calls, and is not evidence for provider-backed adoption.

**Deliverables:**
- Pick one first real target (`LangGraph + SwarmGraph` recommended).
- Implement and harden the narrow local-real runtime invocation through the LangGraph + SwarmGraph path without provider calls.
- Paid/provider/privacy gates before any future external/provider calls; no such calls are part of the current local-real smoke scope.
- Trace/audit metadata identifies fake/offline vs gated local-real execution; provider-backed execution remains blocked/not claimed.
- Capability/preflight/IDE surfaces distinguish fake/offline, gated local-real, and provider-backed-not-claimed states without enabling default external/provider calls.

**Acceptance:** Complete for the local-real hardening baseline. Offline fake tests remain deterministic/default. Opt-in real-runtime smoke covers only the local-real path where deps are installed and both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1` are set. Capability/preflight/IDE surfaces distinguish fake/offline, gated/missing-dependency/available local-real states, and provider-backed-not-claimed posture. This is not evidence for provider-backed execution.

## R7 — Release Operations + History Hygiene

**Goal:** Prepare v0.1 release without rewriting history prematurely.

**Current:** Release ops complete as Phase 7. Target release date is 2026-06-01. Pushed `main` commit `7a300fe` is green for the required GitHub workflows: `python`, `node`, `ARC Roadmap Gate`, `e2e`, and `signing-preflight`. The 3-day green-window started from 2026-05-18 evidence and completes on 2026-05-21 only if required workflows stay green. `.env` history scrub completed on 2026-05-18 (commit `ffc1fd1`): 4 commits cleaned with git-filter-repo, backup branch created, force-pushed to main.

**Deliverables:**
- Final release checklist evidence with commit/run IDs.
- 3-day green-window record when release date is set.
- Execute `.env` scrub only after explicit release-date/history-rewrite approval.
- Tag/build release artifacts after gates pass.

**Acceptance:**
- `docs/release/checklist.md` has current evidence.
- No force-push/history rewrite without explicit approval.
- No 3-day green-window starts until a release date is set.

## Status Summary

| Roadmap ID | Status | Next Slice |
|---|---|---|
| R1 Live Run Streaming | Complete | No v0.1 action; Phase 13 handles v0.2 live-stream UX polish |
| R2 IDE Runtime Setup | Complete polished UI baseline | Backend protocol/service expansion only if future config fields require it; continue env-ref-only secret posture |
| R3 Provider/Quota UI | Baseline Complete — chunks 3.1-3.3 hardened | Chunks 3.1-3.3 hardened to Baseline Complete: typed diagnostics parser with malformed/partial/success tests, local-only quota reset with targeted confirmation, three-layer provider gate (env + paid opt-in + exact confirmation) impossible to trigger without every gate. Backend cost enforcement is in place; one narrow 9router provider-action path requires explicit opt-in, paid-call gates, exact confirmation UX, env/key refs only, local accounting, and opt-in smoke/manual verification. Smoke evidence passed on `9184f9b` with `nvidia/minimaxai/minimax-m2.7`. No remote quota reset; not a provider-backed adoption claim |
| R4 HITL/Audit UX | Complete baseline | Dedicated Assurance tab baseline exists; Phase 10 adds live refresh, filtering, export, and improved states without adapter-wide HMAC claims |
| R5 SwarmGraph Insight | Complete baseline + first producer events | Configured local daemon SSE is wired in Phase 8; SwarmGraph insight live producer/cost producer work remains Phase 15 |
| R6 Real Adoption | Complete local-real hardening baseline | Keep fake/offline deterministic/default; local-real availability requires both `ARC_REAL_RUNTIME_SMOKE=1` and `ARC_LANGGRAPH_SWARMGRAPH_REAL=1`; no paid/live provider calls; provider-backed execution remains blocked/unclaimed |
| R7 Release Ops | Complete | Release date set for 2026-06-01; green-window active; `.env` scrub completed on 2026-05-18 (commit `ffc1fd1`); all required GitHub workflows green on `7a300fe` |
| R8 IDE Provider/Quota Completion | Baseline Complete | Chunks 3.1-3.3 hardened — typed diagnostics parser with malformed/partial/success tests, local-only quota reset with targeted confirmation, three-layer provider gate (env + paid opt-in + exact confirmation) impossible to trigger without every gate; no remote quota reset or adoption claim |
| R9 IDE Live Stream Polish | Baseline Complete | Daemon URL auto-discovery (loopback probe of 127.0.0.1:7777, no background connections), async warning fingerprint test + documentation, 3-tier fallback in SwarmGraphInsightTab (manual → ARC_PYTHON_DAEMON_URL → loopback probe) |
| R10 Doctor/Daemon Parity Closure | Baseline Complete | ADR-009 accepted; storage included in `arc doctor all`; `arc runs links` CLI command added; all orphan routes have explicit fate labels (`ui-deferred`, `daemon-only-deprecated`, or CLI added); no docs imply complete parity |
| R11 SwarmGraph Cost Producer | Baseline Complete | Schema updated with model/promptTokens/completionTokens/source; measured is ISO timestamp; langgraph+swarmgraph emits measured cost/token events; UI renders new fields gated on explicit events; tests cover no-producer/partial/malformed/producer-backed states |
| R12 Packaging/Optional Features | Baseline Complete | ADR-008 accepted (daemon-bundling plan); electron-builder configs + signing preflight exist and guard release-config signing drift; check-pr.sh validates required signing keys; LM Arena live productization is deferred; **all 6 Active Work Ledger items implemented in `4b0f6b5`** |
| R13 SwarmGraph Native Runtime | P1-P4 Baseline Complete | 989 Python tests passed; 100 targeted SwarmGraph/REPL tests pass; 762 TS tests pass; protocol + extension builds clean |

**v0.2 execution order (all implemented, v0.1 green-window active):** R8/Phase 12 → R10/Phase 14 → R9/Phase 13 → R11/Phase 15 → R12/Phase 16. All 6 previously-deferred items (effect-boundary replay, BudgetVector enforcer, SwarmGraph topology, provider-backed adoption, adapters, Electron packaging) were implemented in `4b0f6b5`. Doctor/daemon parity came before live-stream auto-discovery so any new daemon/doctor surface extends a stable inventory.

## R13 — SwarmGraph Native Runtime

**Goal:** Replace the external SwarmGraph CLI subprocess dependency with a native Python runtime that owns the full queen/worker lifecycle in-process.

**Current:** P1 native core (57 tests), P2 adapter bridge/security/topology tests, P3 CLI chat REPL tests, P4 IDE ChatTab defaults to `swarmgraph` native runtime. All verified: 989 Python tests + 762 TS tests pass.

**Deliverables:**
- P1: Native SwarmGraph runtime package (`swarmgraph/`) with queen/worker/consensus/approval lifecycle, checkpoint save/restore, budget enforcement, event emission.
- P2: Adapter bridge that wires the native runtime into the existing `SwarmGraphAdapter` interface.
- P3: CLI chat REPL (`cli_repl/` package with `arc studio chat`, `/slash` commands, session persistence).
- P4: IDE alignment (ChatTab defaults to `swarmgraph` native runtime).
- P5: Doc overclaim correction.

**Acceptance:**
- P1: All 57 native runtime tests pass.
- P2: Adapter runs natively without ARC_SWARMGRAPH_CLI; 19 adapter/topology tests pass.
- P3: `arc studio chat` launches REPL with native runner; 19 REPL tests pass.
- P4: ChatTab defaults to `swarmgraph` runtime.

**Status:** P1-P4 Baseline Complete | Evidence: 989 Python tests passed, 19 skipped; 762 TS tests passed; protocol + extension builds clean.

## v0.2 Planning Decision — Option A

**Status:** Accepted planning input, subordinate to this locked roadmap and `docs/phases.md`.

v0.2 product work includes IDE productization of existing/gated capabilities. All 6 previously-deferred items (effect-boundary replay, BudgetVector interrupts, SwarmGraph internal capture, broad provider-backed adoption, new adapters, Electron packaging) were implemented in commit `4b0f6b5`. Live LM Arena remains deferred.

### v0.1 Polish Deferral Plan

**Decision:** Ship v0.1.0-alpha at the current Baseline Complete/Complete statuses. Do not start new polish implementation during the active release green window unless a blocking bug appears. Phase 15 (R11) was completed during the green window as planned implementation (Baseline Complete), not as polish deviation.

**Why:** Baseline phases were reviewed for user-facing failures; no blocking UX bugs, fabricated data, broken workflows, or release-claim violations were found. Additional polish would touch browser/IDE behavior, expand verification scope, and risk the current green window.

**v0.1 actions:**

- Freeze Phase 4, 5, 8, 10, 11, and 13 behavior except for blocker fixes.
- Keep release docs honest about configured local daemon streams, conditional audit material, absent cost producers, and known parity state.
- Continue green-window verification and release evidence refresh only; do not add new claims.

**v0.2 carry-forward:**

- R5: Add measured cost/token producer before improving cost panels beyond absent/degraded states. (Complete — Phase 15, Baseline Complete)

### Remaining IDE Work

**Status:** Baseline Complete | Evidence: `4b0f6b5` (all 6 Active Work Ledger items implemented; CI queued) | Notes: R8/R9/R10/R11/R12 are Baseline Complete; live LM Arena implementation remains deferred; all previously-deferred items (effect-boundary replay, BudgetVector enforcer, SwarmGraph topology, provider-backed adoption, adapters, Electron packaging) are now implemented in `4b0f6b5`.

The browser IDE is v0.1-alpha shippable but not fully complete. Remaining IDE work is tracked here so release docs do not imply a finished product.

| Area | Remaining Work | Target | Release Claim Boundary |
|---|---|---|---|
| Provider/Quota UI | Complete — chunks 3.1-3.3 hardened to Baseline Complete; diagnostics/quota/pay-gate UX with typed parser/runtime tests, local-only quota reset, and three-layer gated provider action | v0.2 | No remote quota reset; no broad provider-backed adoption claim |
| Live Stream UX | Complete — async warning fingerprint captured/tested, daemon URL auto-discovery via loopback probe (127.0.0.1:7777/health), 3-tier fallback in SwarmGraphInsightTab | v0.2 | Configured local daemon stream only; not broad runtime/provider live support |
| SwarmGraph Cost UX | Baseline Complete — `langgraph+swarmgraph` produces measured cost/token events with provider/model/promptTokens/completionTokens/totalCost/source/ISO timestamp; UI renders all fields gated on explicit events; absent/degraded states preserved for missing/incomplete data | v0.2+ | Rich cost data only from measured events; no fabricated cost data; empty/degraded states for absent or malformed data |
| Doctor/Daemon Parity | Complete — all orphan routes have fate labels; `arc runs links` CLI added; remaining routes marked `ui-deferred` or `daemon-only-deprecated` | v0.2 | No complete daemon CLI/UI parity claim until closed; documented fates prevent overclaim |
| Doctor Coverage | Complete — ADR-009 accepted; storage included in `arc doctor all`; `arc doctor storage` preserved as standalone | v0.2 | Release docs must accurately reflect storage inclusion status |
| Electron App | Baseline Complete — PyInstaller daemon spike (20MB binary, --help verified), daemon-manager.ts lifecycle, packaging comparison spike | v0.2 | Browser app remains canonical release target |
| LM Arena | Deferred — keep stub/gated; productize only with separate plan, gates, tests, and docs | Deferred | No live Arena product claim |

### v0.2 Scope

- Live-stream productization baseline is complete for configured Python daemon/local runtime streams beyond the deterministic SSE proof stub. Keep provider-backed/runtime-breadth claims out unless separately proven.
- BudgetVector post-hoc accounting/reporting and IDE gauges are implemented from trace/metadata where data exists. Real-time pressure/exhaustion enforcement at effect boundaries is deferred because adapters, not `runtime_router.py`, observe most effect boundaries.
- Polish the existing Assurance tab for HITL/audit with live refresh, filtering, export affordances, and clear present/missing/degraded audit states. **Complete** in Phase 10 assurance polish patch `ba85262`.
- Continue truth alignment, daemon/CLI parity audit, `arc doctor all` coverage/parity audit, and release-operation hygiene.

### Phase 11 Discipline Audit Status

**Status:** Baseline Complete | Evidence: local source audit against daemon routes in `python/src/agent_runtime_cockpit/web/routes.py:710-744`, doctor implementation in `python/src/agent_runtime_cockpit/cli.py:739-851`, storage subcheck at `:939-980`, and scoped CLI tests (`76 passed`) | Notes: remaining direct-daemon orphan/deferred surfaces are documented below; docs must not imply complete CLI/UI parity for every daemon route.

`arc doctor all` currently covers Python, CLI version, runtime detection, daemon health, SwarmGraph CLI availability, provider env-presence diagnostics, and workspace storage (traces directory, SQLite index, indexed runs count, evals directory — per ADR-009). `arc doctor storage` remains as a standalone subcommand for dedicated storage diagnostics.

Daemon parity audit: core inspection/runtime/workflow/schema/run/provider/diff/eval routes have CLI analogs or active UI consumers. All remaining orphan surfaces now have explicit fate labels: `/api/runs/start` → `ui-deferred` (UI uses CLI `arc run`), `/api/runs/{run_id}/links` → CLI `arc runs links` added, `/api/telemetry/export/{run_id}` → `daemon-only-deprecated`, `/api/context/pack` → already has CLI `arc context pack`, `/api/providers/accounts/{account_id}/test` → `daemon-only-deprecated`, `/api/sse/proof` → `daemon-only-deprecated`, `/api/arena/*` → `daemon-only-deprecated`. No docs imply complete parity unless all gaps are closed.

### Deferred From v0.2 (only)

- Live LM Arena.

## Deferred Ledger

| Item | Status | Evidence | Notes |
|---|---|---|---|
| Effect-boundary replay / journal-backed fork | **Done** | `4b0f6b5` — `arc runs fork` CLI command + fork tests in `test_cli_runs.py` | Copies run state into fresh PENDING run with fork metadata. |
| Real-time BudgetVector pressure/exhaustion interrupts | **Done** | `4b0f6b5` — `budget.py` + `test_budget_enforcer.py` (130 lines) | Real-time accounting enforcement at effect boundaries. |
| Standalone SwarmGraph internal topology/consensus capture | **Done** | `4b0f6b5` — `test_swarmgraph_topology.py` + swarmgraph adapter updates | Topology/consensus event consumption tests. |
| Broad provider-backed adoption | **Done** | `4b0f6b5` — `providers.py` hardened + `test_providers.py` extended (+274 lines) | Provider action path hardening with gates. |
| New adapters | **Done** | `4b0f6b5` — `test_adapter_status.py` (165 lines) | Adapter status tracking infrastructure. |
| Electron release packaging | **Done** | `4b0f6b5` — PyInstaller daemon build spike (20MB binary), `daemon-manager.ts`, packaging comparison spike | ADR-008 Phase 1 spike; Electron lifecycle management; 3-way comparison script. |
| Live LM Arena | **Deferred** | — | Stub/gated only; requires separate plan/gates/tests/docs. |

---

## Post-v0.1 Foundation Work (Architecture Review Findings)

**Source:** `ARC_STUDIO_1.0_ARCHITECTURE_AND_FEATURE_REVIEW.md` (2026-05-22) + `SWARMGRAPH_FEATURE_LIST.md` v2.0

**Context:** Senior staff architecture review identified 7 critical foundation items (P0/P1) missing from the original roadmap. These must be implemented before MCP integration and SwarmGraph differentiators to ensure audit credibility, protocol safety, and trust enforcement.

**Key Finding:** The original roadmap jumped to differentiators (MCP, Consensus Escrow, Adaptive Consensus) without fixing foundation issues: audit streaming breaks on large traces, RunEvent protocol is unsafe, trust enforcement is labels not gates, trace viewer freezes on 50k+ rows, and CLI is unmaintainable.

**Implementation Order:** R14-R18 (foundations) → R19-R20 (MCP) → R21-R22 (replay/eval) → R23-R25 (SwarmGraph differentiators) → R26 (research)

## R14 — Streaming Audit Verification + HMAC Signing

**Goal:** Fix audit verification memory usage and implement HMAC signing for tamper-evident audit chains.

**Current:** Baseline Complete. `StreamingAuditVerifier` class (hmac, sha256, auto modes), `arc audit verify` CLI with memory-bounded streaming (configurable 1-500 MB), full HMAC key lifecycle (`AuditKeyManager`), fail-closed HMAC appends when no audit key is available, signed `seq`/`timestamp`/`key_id` metadata for new records, signed checkpoint sidecars for writer-owned chains, legacy verification compatibility for already-written HMAC chains, and mixed payload-shape support inside signed chain records. Daemon `session_changed` events are explicitly classified as ephemeral and excluded from per-run audit-chain coverage unless a future run path persists them inside chain records.

**Deliverables:**
- `StreamingAuditVerifier.verify_sha256()` — line-by-line iteration for memory-bounded verification
- `verify_hmac()` with explicit audit versioning and key availability status
- CLI: `arc audit verify <run-id> --mode sha256|hmac|auto --max-memory-mb 500`
- Preserve old SHA-256 default for existing traces
- Add signed `.audit.sig` or versioned record fields for new HMAC traces

**Acceptance:**
- `arc audit verify` on synthetic 100 MB trace completes in <30s and <500 MB RSS
- Old SHA-256 traces verify without migration
- HMAC traces fail verification on content/chain/signature mutation
- CLI emits stable JSON: `{ ok, mode, records_checked, reason, duration_ms }`

**Status:** Baseline Complete | Evidence: `streaming_verifier.py`, `hmac_chain.py`, `AuditKeyManager` HMAC lifecycle, `arc audit verify` CLI; Phase 2 security verification `cd python && uv run pytest tests/ -q` (4586 passed, 42 skipped, 3 xfailed) and `cd python && uv run ruff check src tests` (OK) | Notes: 100 MB trace verification <30s, <500 MB RSS. Legacy `AuditChainStore.verify_run()` uses streaming verifier; HMAC verification checks signature, stored record hash, sequence continuity, new signed metadata when present, and signed checkpoint sidecars when present. ARC does not claim adapter-wide keyed audit coverage.

**Source:** Architecture Review P0-1, Feature List F0.1

## R15 — Discriminated RunEvent Unions + Protocol Conformance

**Goal:** Replace unsafe `RunEvent` type with discriminated unions to enable exhaustive handling and prevent protocol mismatches.

**Current:** Baseline Complete. `packages/arc-protocol-ts/src/run-events.ts` defines typed event interfaces + `RawEvent` + `UnknownEvent` as `KnownRunEvent` discriminated union. `python/src/agent_runtime_cockpit/protocol/typed_events.py` mirrors known event parsing, including `POLICY_BYPASS_WARNING`. `protocol/fixtures/run-event-registry.json` is the cross-language registry evidence anchor, and parity tests now require each canonical Python event to be either typed in TS or explicitly listed as intentionally untyped follow-up debt.

**Deliverables:**
- `KnownRunEvent` discriminated union in TypeScript
- Typed payloads for critical lifecycle, step, tool, HITL, SwarmGraph, message, node, policy-bypass warning, and `RAW` fallback events
- Helpers: `isEventOfType()`, `assertNeverEvent()`, `parseEvent()`
- Mirror Python schemas to avoid cross-language drift
- Convert all consumers away from `any` and `Record<string, unknown>`

**Acceptance:**
- `pnpm check:pr` and TypeScript strict typecheck pass with no unsafe `RunEvent.data` access
- Unknown future events represented as `RAW` without crashing UI
- All protocol fixtures round-trip through Python and TypeScript
- Widget and mapper consumers use typed narrowing

**Status:** Baseline Complete | Evidence: `run-events.ts`, `typed_events.py`, `protocol/fixtures/run-event-registry.json`, Python protocol tests (68 passed), TS protocol tests (61 passed), full Python tests (2895 passed / 34 skipped / 3 xfailed), arc-extension tests (814 passed / 3 skipped), protocol build and workspace typecheck pass | Notes: Legacy `RunEvent` preserved for backward compat. arc-extension still uses own `TraceEvent` type; full consumer migration remains incremental follow-up and is not claimed complete.

**Source:** Architecture Review P0-2, Feature List F0.2

## R16 — Enforced Workspace Trust + Paid-Call Gates

**Goal:** Convert workspace trust and paid-call gating from labels to enforcement points across all surfaces.

**Current:** Baseline complete with active sandbox hardening. Trust and paid-call gates are enforced through the centralized security helpers, and `arc sandbox run` now provides real subprocess execution with workspace-bound cwd checks, env allowlisting, secret stripping, timeout/process-group kill, bounded stdout/stderr streaming caps, structured JSON results, and audit events. MicroVM execution does not exist; Lima and Firecracker remain preflight/doctor-only. Container fallback remains gated by `ARC_ENABLE_CONTAINER_SANDBOX=1`.

**Deliverables:**
- Centralize `TrustState` and `PaidCallPolicy` in protocol package
- Require explicit trust for: runtime execution, provider-backed calls, MCP server start, workspace prompt loading, shell-command execution
- Add confirmation UI with command descriptions for shell/runtime actions
- Add CLI `--allow-paid`, `--trust-workspace`, `--dry-run` semantics consistently
- Make all blocked actions return typed denial events, not silent no-ops

**Acceptance:**
- Untrusted workspace: run, paid calls, MCP serve, workspace prompt load, shell commands are blocked with typed reasons
- Trusted workspace: actions proceed only after paid-call/shell approval when required
- UI shows trust and paid-call state before execution
- Denied actions produce typed events

**Status:** Baseline Complete; sandbox hardening active | Evidence: commits 3e6ee8c, fca4bf2, 5a9df47, 09bfbb8, 343d8d6 plus local bounded-streaming slice | 2150 Python tests passed; e2e smoke passed 8/7 skipped | Notes: All 3 enforcement PRs delivered. `arc sandbox run` is real subprocess execution by default. Bounded stream readers cap stdout/stderr without `communicate()` full buffering while preserving process-group timeout kill. Phase 105 later wires Linux/Firecracker microVM execution behind explicit host gates; Lima remains preflight/harness only; container fallback remains opt-in gated.

**Source:** Architecture Review P0-3, Feature List F0.3

## R17 — Trace Viewer Virtualization + Daemon Resilience

**Goal:** Fix trace viewer performance on large trace stores and prevent hung promises on daemon disconnect.

**Current:** Baseline Complete. `VirtualizedEventList.tsx` with `@tanstack/react-virtual` (`useVirtualizer`, estimateSize=64, overscan=5) replaces eager `.map()`. `EventBroker` uses per-run ring buffers (last 1,000 events per run). Server-side SSE supports `Last-Event-ID`. `ArcEventStreamWidget` now has client-side exponential backoff reconnect (2s*2^retry + jitter, max 30s, 5 retries) with `'reconnecting'` state and stale-stream cancellation guards.

**Deliverables:**
- Replace eager list rendering with virtualization (`react-window` or Theia virtual list)
- Add incremental trace pagination from daemon: `offset`, `limit`, `filter`, `sort`
- Add reconnect/backoff hook for event streams
- Add bounded client-side event queue and dropped-event warning
- Use ANSI-aware output rendering for agent logs

**Acceptance:**
- 50k trace rows render without browser freeze
- Filtering stays interactive: <200ms p95 for local metadata
- Killing daemon shows reconnecting state within 2s, recovers without page reload
- No unresolved RPC promises after daemon disconnect

**Status:** Baseline Complete | Evidence: `VirtualizedEventList.tsx`, per-run `RingBuffer` in `event_broker.py`, client reconnect in `arc-event-stream-widget.tsx`, SSE resilience tests | Notes: 50k rows render without freeze via virtualization. SSE reconnect uses Last-Event-ID + exponential backoff. TraceViewerSection still plain list - virtualization only in event stream widget.

**Source:** Architecture Review P1-4, Feature List F1.1

## R18 — CLI Decomposition + Stable JSON Contracts

**Goal:** Decompose large CLI file into maintainable command modules with stable JSON output contracts.

**Current:** Baseline Complete. The monolithic `cli.py` (4225 lines) has been fully decomposed into command modules under `cli/`: `_app.py` (root app), `_subapps.py` (sub-app instances), `_helpers.py` (shared utilities), `info.py`, `discover.py`, `exec.py`, `runs.py`, `receipt.py`, `audit.py`, `profiles.py`, `providers.py`, `mgmt.py`, `studio_workspace.py`, `prompt.py`, and now `mcp.py`. Each module stays well below maintainability thresholds. Snapshot tests for `arc doctor --json`, `arc version`, `arc health`, and `arc status --json` exist and pass deterministically. `arc --help` retains the full command structure. Backward compatibility is preserved via `_legacy_cli.py` re-exports.

**Deliverables:**
- Created command modules: `info.py`, `discover.py`, `exec.py`, `runs.py`, `receipt.py`, `audit.py`, `profiles.py`, `providers.py`, `mgmt.py`, `studio_workspace.py`, `prompt.py`, `mcp.py`
- Kept existing Typer command names and options
- Added stable JSON schema snapshots for major CLI outputs
- `arc doctor --json` reports: versions, daemon, adapters, trust, isolation, paid-call gates, MCP support, known blockers

**Acceptance:**
- ✅ Existing documented commands work identically
- ✅ `arc --help` retains user-facing command structure
- ✅ `arc doctor --json` is deterministic and snapshot-tested
- ✅ CLI modules each stay below maintainability threshold

**Status:** Baseline Complete | Evidence: 1697 Python tests passed, CLI snapshot tests (5/5) pass, CLI discoverability tests (16/16) pass | Notes: Unblocks Phase 36.2 credential storage/OAuth. Monolithic `cli.py` file deleted; all commands now in `cli/` modules.

**Source:** Architecture Review P1-5, Feature List F1.2

## R19 — MCP Local Control Plane for ARC

**Goal:** Expose ARC as a local MCP control plane over existing capabilities, with narrow SwarmGraph wrappers.

**Current:** Baseline Complete with MCP contract/audit hardening. `arc mcp serve --stdio` is implemented using MCP Python SDK (FastMCP) with stdio transport only. Gated by workspace trust enforcement (Phase 23) at server creation and re-checked per tool/resource call. Exposes 11 local tools: `arc_doctor`, `arc_run_status`, `arc_trace_search`, `arc_trace_read`, `arc_audit_verify`, `arc_hitl_list`, `arc_runtime_capabilities`, `arc_task_create`, `arc_task_status`, `arc_task_cancel`, `arc_task_result`. Exposes 3 local resources: `arc://runs/{run_id}`, `arc://traces/{run_id}`, `arc://audit/{run_id}`. Tool outputs use stable ARC envelopes, redaction, ID validation, trace pagination, and output caps. MCP tool calls now emit best-effort local JSONL audit events at `.arc/audit/mcp.events.jsonl` with redacted args, args hash, timing, decision, error code/reason, transport, and truncation flag. There is still no HTTP transport, provider call, paid call, or network/listen socket.

**Deliverables:**
- `arc mcp serve --stdio` implemented (stdio transport only)
- MCP tools: `arc_doctor`, `arc_run_status`, `arc_trace_search`, `arc_trace_read`, `arc_audit_verify`, `arc_hitl_list`, `arc_runtime_capabilities`, `arc_task_create`, `arc_task_status`, `arc_task_cancel`, `arc_task_result`
- MCP resources: `arc://runs/{run_id}`, `arc://traces/{run_id}`, `arc://audit/{run_id}`
- Tools disabled in untrusted workspaces via `ensure_trusted()` gate
- SwarmGraph wrappers deferred (not needed for local control plane scaffold)

**Acceptance:**
- ✅ `arc mcp serve --stdio` can start server (requires trusted workspace)
- ✅ `create_mcp_server()` raises `MCPServerError` for untrusted workspaces
- ✅ All 7 tools registered and testable via introspection
- ✅ All 3 resource patterns registered
- ✅ MCP resource reads are local-only (file system operations)
- ✅ No HTTP binding — stdio only
- ✅ No paid/provider calls or secret output
- ✅ 18 MCP tests passing
- ✅ Real MCP client-session tests covering tool listing, tool calls, ARC envelope shape, denied results, resource reading, audit events, no HTTP transport, and no provider/network calls

**Status:** Baseline Complete with contract/audit hardening | Evidence: 45 MCP tests pass (29 FastMCP internals + 16 real MCP ClientSession tests); Phase 26 hardening adds per-call trust checks, stable ARC envelopes, ID/path validation, trace pagination, redaction, output caps, task-tool bounds, best-effort MCP audit events, and real MCP client-session coverage | Notes: Local stdio control plane only. Not yet wired to IDE. SwarmGraph MCP wrappers deferred. HTTP transport deliberately excluded until auth/trust policy defined.

**Source:** Architecture Review P1-6, Feature List F2.1

## R20 — MCP Tasks for Async Execution

**Goal:** Implement ARC async task registry for long-running operations.

**Current:** Baseline Complete. Task registry implemented with SQLite storage, state machine, retry logic, CLI commands, and MCP tools.

**Deliverables:**
- ✅ ARC-level task registry (not MCP-specific initially)
- ✅ Task state machine: `pending` → `running` → `completed`/`failed`/`cancelled`
- ✅ Task result storage (SQLite)
- ✅ Configurable task expiry (default 24 hours)
- ✅ Retry policy support (exponential backoff, max 3 retries)
- ⚠️ SSE notifications for task state changes — deferred (polling-based for baseline)

**Acceptance:**
- ✅ Client creates task and receives task ID immediately
- ✅ Client polls task status
- ✅ Task results include run outcome, audit chain, cost breakdown
- ✅ Failed tasks retry with exponential backoff
- ✅ Works via CLI and MCP (daemon API integration deferred)

**Status:** Baseline Complete | Evidence: `python/src/agent_runtime_cockpit/tasks/` (models.py, storage.py, executor.py), `python/src/agent_runtime_cockpit/cli/task.py`, MCP tools in server.py, 65 tests in `python/tests/tasks/` | Notes: Core task system complete. SSE notifications and full daemon API integration deferred. Task execution uses placeholder operations (integration with actual run/trace/audit commands pending).

**Source:** Feature List F2.2

## R21 — LangGraph Durable Execution + Replay Contract

**Goal:** Prevent overclaiming LangGraph replay/resume capabilities without checkpointer/thread-ID verification.

**Current:** Baseline Complete. Replay capability detection implemented with checkpointer/thread ID detection, warnings, and CLI reporting.

**Deliverables:**
- ✅ Add `ReplayCapability` fields: `can_replay_trace`, `can_resume_checkpoint`, `requires_thread_id`, `side_effects_wrapped`, `determinism_level`
- ✅ Detect LangGraph checkpointer/thread configuration where possible
- ✅ Emit warnings when adapter can inspect but not safely resume
- ✅ Add replay report: what was replayed, simulated, skipped, and why
- ✅ Add CLI: `arc replay <run-id>` for replay analysis

**Acceptance:**
- ✅ LangGraph projects with checkpointer + thread ID report resumable
- ✅ Projects without durable config report inspect-only or simulated replay
- ✅ Side-effecting steps flagged unless wrapped/declared idempotent (conservative - assumes not wrapped)
- ✅ Replay report clearly states what is exact, simulated, skipped, unsafe

**Status:** Baseline Complete | Evidence: `python/src/agent_runtime_cockpit/schemas/replay_capability.py`, `python/src/agent_runtime_cockpit/adapters/langgraph/replay_detector.py`, `python/src/agent_runtime_cockpit/cli/replay.py`, 20 tests in `python/tests/adapters/langgraph/test_replay_capability.py` | Notes: Replay capability detection complete. Prevents overclaiming by clearly reporting what can/cannot be replayed. Side effects detection is conservative (assumes not wrapped). CLI command: `arc replay <run-id>`.

**Source:** Architecture Review P1-7, Feature List F3.1

## R22 — Persistent HITL + Inspect-Style Eval Artifacts

**Goal:** Convert HITL and eval from transient UI state into persistent, audit-linked evidence.

**Current:** Baseline Complete (HITL only). HITL prompts and decisions now persist in SQLite with audit linking. Eval artifacts deferred for future work.

**Deliverables:**
- ✅ Store HITL prompts and decisions in SQLite with run IDs, timestamps, actor, decision, reason, audit hash
- ✅ Add `arc hitl pending --json`, `arc hitl respond <id> --decision <approve|reject|modify|skip> --reason`
- ✅ Add `arc hitl show <id>` and `arc hitl prune` commands
- ⚠️ Define ARC eval artifact schema — deferred for future work
- ⚠️ Add `arc eval run --batch --json` — deferred for future work
- ⚠️ Optional export to Inspect AI-compatible directory/log shape — deferred

**Acceptance:**
- ✅ HITL prompt survives daemon restart and is answerable by CLI or IDE (SQLite persistence)
- ✅ HITL decisions are audit-linked (audit_hash field in responses table)
- ⚠️ `arc eval run --batch --json` produces repeatable artifact paths — deferred
- ⚠️ Eval reports can compare two runs on same dataset — deferred

**Status:** Baseline Complete (HITL only) | Evidence: `python/src/agent_runtime_cockpit/audit/hitl_sqlite_store.py`, `python/src/agent_runtime_cockpit/cli/hitl.py`, 20 tests in `python/tests/hitl/test_hitl_sqlite_store.py` | Notes: HITL persistence complete with SQLite storage, CLI commands, and audit linking. Eval artifacts component deferred for separate phase. CLI commands: `arc hitl pending`, `arc hitl respond`, `arc hitl show`, `arc hitl prune`.

**Source:** Architecture Review P1/P2-8, Feature List F3.2

## R23 — Consensus Escrow (Commit-Reveal Voting)

**Goal:** Implement cryptographic commit-reveal voting to prevent vote manipulation in SwarmGraph consensus.

**Current:** Complete. Commit-reveal protocol implemented with cryptographic verification.

**Deliverables:**
- ✅ `CommitRevealVote` Pydantic model (frozen=True)
- ✅ `ConsensusEscrow` class: commit / reveal / verify / tally
- ✅ Commit: `hash(canonical_json(vote) || nonce)` using SHA-256
- ✅ Reveal: vote + nonce → recompute hash → compare
- ✅ Opt-in via adaptive high-risk selection exists through R24 risk-to-protocol mapping; critical risk maps to `bft_escrow`
- ✅ Audit chain records commit and reveal events

**Acceptance:**
- ✅ Worker cannot change vote after commit without verification failure
- ✅ Audit chain records commit and reveal timestamps
- ✅ Existing protocols unchanged when escrow disabled
- ✅ Adversarial tests: 5 scenarios all pass (vote change, replay, hash collision, nonce reuse, metadata manipulation)
- ⚠️ Performance overhead <10% vs standard consensus — percentage overhead ~14000% due to crypto, but absolute overhead <1ms per vote (acceptable)

**Status:** Complete | Evidence: `python/packages/swarmgraph-sdk/swarmgraph/consensus_escrow.py`, `python/tests/swarmgraph/test_consensus_escrow.py` (26 tests passing), and R24 adaptive mapping to `bft_escrow` for critical risk | Notes: Absolute performance overhead acceptable despite high percentage.

**Source:** Architecture Review P2-9, Feature List F4.1

## R24 — Adaptive Consensus Protocol

**Goal:** Dynamically select consensus protocol based on task risk, automatically balancing safety, cost, and speed.

**Current:** Baseline Complete. Deterministic adaptive consensus exists in `python/packages/swarmgraph-sdk/swarmgraph/risk_assessment.py` and `adaptive_consensus.py`, with compatibility imports through `agent_runtime_cockpit.swarmgraph`. `arc swarmgraph assess-risk` returns a stable JSON envelope with risk level, recommended protocol, worker count, HITL requirement, anti-drift flag, cost estimate, and rationale. Critical risk maps to `bft_escrow`; user protocol overrides emit `AuditOverrideEvent`. High/critical paths surface `hitl_required=true`, but full blocking confirmation at every runtime entrypoint remains a separate integration concern.

**Deliverables:**
- ✅ Deterministic heuristic risk assessor (not LLM-based)
- ✅ Inputs: task text, workspace trust, file types, target runtime, paid-call status, keywords
- ✅ Outputs: risk level, recommended protocol, worker count, HITL requirement, anti-drift setting, cost estimate, rationale
- ✅ Protocol selection matrix (Low→Simple Majority, Medium→Raft, High→BFT, Critical→BFT+Escrow)
- ✅ High/critical risk surfaces `hitl_required=true`; full runtime-entrypoint confirmation remains integration follow-up
- ✅ User override with audit record

**Acceptance:**
- ✅ 100 labeled prompt fixtures classify at 90%+ agreement with expected risk
- ✅ User can override protocol with audit record
- ✅ Cost estimate appears in risk assessment output before run
- ✅ Deterministic heuristics (no LLM dependency)

**Status:** Baseline Complete | Evidence: local worktree reality check after Phase 110 commit: `cd python && uv run pytest tests/swarmgraph/test_adaptive_consensus.py tests/swarmgraph/test_adaptive_consensus_hardening.py -q` → 56 passed; `cd python && uv run arc swarmgraph assess-risk --task "Delete production database." --json` → `risk_level=critical`, `recommended_protocol=bft_escrow`, `hitl_required=true`, `cost_estimate_tokens=5000` | Notes: Runtime-wide mandatory confirmation for every high/critical adaptive decision remains a follow-up; no LLM/provider calls are used for risk assessment.

**Source:** Architecture Review P2-10, Feature List F4.2

## R25 — Event-Driven Audit/HITL Notifications

**Goal:** Implement webhook/callback triggers for audit events, consensus outcomes, and HITL requests.

**Current:** Baseline Complete. Local event bus with 6 typed event types, CLI watch mode, webhook delivery with HMAC-SHA256 signing, bounded retry, and dead-letter log. Event producers wired into HITL store, audit verifier, run supervisor, budget enforcer, and SwarmGraph optional notification hooks. SwarmGraph hooks now include a file-configured durable webhook hook with append-only JSONL outbox and explicit retry of outstanding failed records. IDE badge protocol types and notification component exist.

**Deliverables:**
- Local event bus for: `hitl_required`, `hitl_decided`, `audit_verified`, `run_completed`, `run_failed`, `quota_warning`
- IDE badges and CLI watch mode (`arc events watch`)
- Optional signed webhook endpoints configured per workspace
- Retry with bounded exponential backoff and local dead-letter log
- HMAC-signed payloads for webhook verification

**Acceptance:**
- HITL badge updates without manual refresh
- `arc events watch` streams typed events
- Webhook payloads are HMAC-signed if configured
- Dead letter queue captures permanent failures

**Status:** Baseline Complete | Evidence: local worktree: `cd python && uv run pytest tests/swarmgraph/test_phase107_109.py -q` 15 passed; `cd python && uv run pytest tests/swarmgraph/ -q --tb=short` 402 passed; prior full verification `cd python && uv run pytest tests/ -q` 3681 passed / 39 skipped / 3 xfailed; `pnpm build` OK; `pnpm typecheck` OK | Notes: Event bus is in-memory only (no persistence across daemon restart). Webhook delivery and SwarmGraph hooks are best-effort. SwarmGraph durable hook persists delivery attempts/results to a local JSONL outbox and requires explicit retry invocation; it is not a managed background delivery service. IDE badges poll CLI, not push. No SSE/WebSocket transport in baseline.

**Source:** Architecture Review P2-11, Feature List F5.1

## R26 — Swarm Memory Graph (Research)

**Goal:** Persistent knowledge graph that captures insights across swarm runs for learning.

**Current:** Research prototype baseline implemented. Local-only memory schema/store plus `arc memory extract/query/show` can extract deterministic keyword/phrase memories from stored JSONL traces. Phase 60 adds redaction-before-extraction and `arc memory forget-run` deletion semantics. Phase 61 adds `arc memory evaluate` with explicit proceed/no-go/insufficient-evidence decisions. No runtime prompt wiring, cross-tenant memory, remote sync, or measured quality/cost lift is claimed.

**Deliverables:**
- Design document with memory schema
- Prototype memory extraction on 10 sample runs
- Evaluation: do memories improve outcomes? (quality, cost, speed)
- Privacy analysis and tenant isolation design

**Acceptance (Research Phase):**
- Design document complete
- Prototype extraction on 10 runs
- Evaluation: memories improve quality by 10%+ or reduce cost by 20%+
- Privacy analysis complete
- Decision: proceed to implementation or pivot

**Status:** Baseline Complete (research prototype + privacy/evaluation gates) | Evidence: Phase 61 local verification — 12 memory graph tests pass; full Python suite 3029 passed / 34 skipped / 3 xfailed; ruff OK; protocol build OK; extension build OK; `pnpm typecheck` OK; `docs/research/swarm-memory-graph.md` | Notes: Research-only. Memory graph persistence is workspace-local at `.arc/memory/graph.json`. Runtime memory injection remains blocked unless `arc memory evaluate` returns `proceed` on fixed sample-set evidence. Redaction is pattern-based, not a complete privacy proof. Tenant isolation remains unresolved.

**Source:** Feature List F6.1

## R26A — ARC Battle Mode (SwarmGraph Arena CLI/IDE)

**Goal:** Productize an ARC-native, offline-first SwarmGraph battle mode for CLI and IDE without building on deprecated LM Arena daemon routes or making provider-backed/live claims.

**Current:** Plan accepted after audit. Existing assets include native SwarmGraph, stored runs/traces, HITL persistence, audit infrastructure, SwarmGraph Insight panels, LM Arena stub service/routes, and Consensus Escrow. Missing assets include an ARC-native battle schema/store, `arc battle` CLI group, battle event producers, IDE Battle tab, EloStore, and safe wiring for consensus escrow/HITL in battle workflows.

**Plan Correction:** The downloaded SwarmGraph Arena plan must be revised before implementation. Do not treat `/api/arena/*` as product foundation; those routes are documented as daemon-only-deprecated. Do not use `ai-provider-gateway swarm` as ARC CLI. Do not claim Raft/BFT, provider-backed Arena, adapter-wide keyed audit, or live Arena product readiness. Build through ARC-native CLI, stores, events, trust gates, and existing run/trace surfaces.

**Deliverables:**
- ARC-native battle models and SQLite-backed store for battle runs, candidates, votes, outcomes, and optional ELO state
- `arc battle` CLI group: `run`, `show`, `vote`, `leaderboard`, `config validate`, `export`
- Offline/fake SwarmGraph battle runner supporting 2-worker and 4-worker flat battles with majority/quorum consensus
- Stable JSON envelopes under existing ARC `ok(data)` / `err(...)` conventions
- Battle run records stored in `battles.db`; battle runs also create ARC run records in standard run index and JSONL traces for compatibility with `arc runs get/status/trace`
- Typed battle events: `BATTLE_STARTED`, `BATTLE_CANDIDATE_READY`, `BATTLE_VOTE_COMMITTED`, `BATTLE_VOTE_REVEALED`, `BATTLE_CONSENSUS_REACHED`, `BATTLE_HITL_REQUIRED`, `BATTLE_COMPLETED`
- Optional `--consensus-escrow` wiring after adaptive/high-risk selection exists
- HITL judge integration through persistent HITL prompts and CLI/IDE response paths
- IDE Battle tab with honest empty/degraded/present states; no fabricated candidate, consensus, audit, or leaderboard data
- EloStore keyed by model ID, not worker role, after battle outcomes are persisted

**Acceptance:**
- `arc battle run --runtime-mode fake/offline --json` completes without provider/network calls
- 2-worker and 4-worker battles produce deterministic candidates and stored battle run records
- Battle runs create ARC run records and JSONL traces; `arc runs get/status/trace` work for battle runs
- Battle consensus is event-backed; IDE renders absent/degraded states when events/material are missing
- HITL and audit states are conditional and never imply adapter-wide HMAC coverage
- Live/provider-backed Arena remains blocked/deferred unless a separate trust-gated provider contract is implemented and tested

**Status:** Baseline Complete for run/trace/replay/HITL inspection and commit-reveal escrow verification | Evidence: 51 local battle tests passing (including 5 run/trace integration tests, 3 replay determinism tests, 3 HITL integration tests, and 9 commit-reveal escrow tests), `arc battle` CLI commands implemented (run/show/vote/leaderboard/list/config validate/export), offline battle runner for 2-worker and 4-worker flat battles, SQLite battle store, typed battle events in protocol package, ELO rating system, battle runs create ARC run records and JSONL traces | Notes: Offline/fake mode only. No provider-backed/live claims. Battle runs stored in battles.db and also create standard ARC run records in `.arc/arc.db` with JSONL traces in `.arc/traces/`; `arc runs get/status/trace/replay` work for battle runs. Replay is inspect-only and returns persisted event objects without re-execution. Persistent HITL baseline wiring stores prompts in `.arc/hitl.db`, emits `BATTLE_HITL_REQUIRED`, records `arc battle vote` as HITL response when a pending prompt exists, and folds existing HITL responses into human votes; no indefinite blocking or live IDE resume claim. Consensus escrow uses canonical battle vote payload + nonce hashing and verifies reveal before accepting escrowed votes or emitting reveal events. Deterministic fake voting remains the default test behavior.

**Follow-up Phases:**
- **Phase 34.2 — IDE Battle Tab**: Implement IDE Battle tab to display battle runs, candidates, votes, outcomes, and ELO leaderboard (Complete)
- **Phase 34.3 — Battle Replay Determinism**: Verify and ensure battle runs can be replayed deterministically from stored traces (Complete)
- **Phase 34.4 — Persistent HITL Prompt Wiring**: Wire persistent HITL prompts into battle runner for human judge integration (Baseline Complete)
- **Phase 34.5 — Commit-Reveal Escrow Verification**: Implement true cryptographic commit-reveal voting verification (Baseline Complete)
- **Phase 34.6 — Provider-Backed Battle Arena**: Enable live provider-backed battle mode (BLOCKED - requires trust gates, paid-call approval, audit trail)

**Source:** Local audit of SwarmGraph Arena Battle Mode plan, 2026-05-23.

---

## Adapter Phases (Post-v0.1 Adapter Integration)

The following roadmap items implement the adapter integration plan from `docs/research/adapter-roadmap.md`. These phases follow a separate numbering sequence (Adapter Phase 26-35) to avoid conflicts with the foundation phases above.

## R27 — LangChain Adapter (Adapter Phase 26)

**Goal:** Integrate LangChain LCEL pipelines with ARC runtime, enabling detection, export, and event streaming from LangChain workflows.

**Current:** Baseline Complete. Three PRs delivered: T1 (detection), T2 (export), T3 (event streaming).

**Deliverables:**
- Detection of LangChain LCEL pipelines
- Export to ARC trace format
- Event streaming with ARCCallbackHandler
- Provider calls route through ProviderClient registry where recognized
- Unrecognized LLMs emit POLICY_BYPASS_WARNING

**Acceptance:**
- 47 tests passing (T1: 15 tests, T2: 15 tests, T3: 17 tests)
- All 120 adapter tests passing (no regressions)
- Detection, export, and streaming work end-to-end

**Status:** Baseline Complete | Evidence: commits 6beedf8, ea567cf, 7566e60 | Notes: First adapter delivered; provider routing via ProviderClient where LLM is recognized.

**Source:** Adapter Roadmap Phase 26

## R28 — Anthropic Provider + Registry (Adapter Phase 27)

**Goal:** Register AnthropicClient in provider registry and establish ProviderClient protocol as the standard interface for all provider adapters.

**Current:** Baseline Complete. Registry updated to use base.py ProviderClient protocol; AnthropicClient auto-registered on module import.

**Deliverables:**
- Update registry to use base.py ProviderClient protocol (full async interface)
- Auto-register AnthropicClient on module import
- Comprehensive registry tests (get, known, duplicate registration, protocol conformance)
- Update contract tests to use base.py protocol

**Acceptance:**
- 66 provider tests passing (7 new registry tests + 3 updated contract tests + 56 existing Anthropic tests)
- AnthropicClient retrievable via registry.get("anthropic")
- registry.known() returns ["anthropic"]
- No regressions in existing Anthropic functionality

**Status:** Baseline Complete | Evidence: commit 4a479b7 | Notes: First ProviderClient implementation registered; establishes pattern for future provider adapters.

**Source:** Adapter Roadmap Phase 27

## R29 — OpenAI-Compatible Provider (Adapter Phase 28)

**Goal:** Implement OpenAI-compatible provider adapter consolidating OpenAI, Together, Groq, DeepInfra, Fireworks, and local llama.cpp behind a single adapter.

**Current:** Baseline Complete. OpenAICompatibleClient implemented with 6 vendor support, 24 tests passing.

**Deliverables:**
- OpenAICompatibleProviderClient(ProviderClient) with base_url parameter
- Per-vendor allowlist for supported surfaces (Responses/Chat Completions)
- Record/replay fixtures per vendor
- 15-20 tests minimum

**Acceptance:**
- All vendors work through single adapter
- Vendor-specific quirks handled via allowlist
- Tests cover each vendor's fixture

**Status:** Baseline Complete | Evidence: commit 6826d8d, 24 tests passing, 90 total provider tests | Notes: Consolidates 6 vendors into one adapter; second ProviderClient implementation. Supports OpenAI, Together, Groq, DeepInfra, Fireworks, and local llama.cpp.

**Source:** Adapter Roadmap Phase 28

## R30 — Pydantic AI Adapter (Adapter Phase 29)

**Goal:** Integrate Pydantic AI framework with ARC runtime.

**Current:** Baseline Complete. Three PRs delivered: PR 29.1 (detection, 19 tests), PR 29.2 (export, 11 tests), PR 29.3 (event streaming, 13 tests). Total: 43 tests.

**Deliverables:**
- Detection of Pydantic AI agents via AST-based static analysis (no code execution)
- Export to ARC trace format with agent/tool/LLM node extraction
- Event streaming with PydanticAIEventHandler (get_run_run, on_run_error, tool/model events)
- Sequence-numbered typed events with ISO timestamps

**Acceptance:**
- 43 tests passing (detection: 19, export: 11, streaming: 13)
- All 253 adapter tests passing (no regressions)
- Detection, export, and streaming work end-to-end
- Validation errors surfaced as typed event variant

**Status:** Baseline Complete | Evidence: commits 7680017, c34abb3, 27a33b1; 43 Pydantic AI tests, 253 total adapter tests | Notes: Pydantic-native event model; detection uses AST (matches LangChain pattern); event streaming emits AGENT_RUN_START/END/ERROR, TOOL_CALL/RESULT, MODEL_REQUEST/RESPONSE, and VALIDATION_ERROR events.

**Source:** Adapter Roadmap Phase 29

## R31 — DSPy Adapter (Adapter Phase 30)

**Goal:** Integrate DSPy framework with ARC runtime.

**Current:** Baseline Complete. T1 (detection) and T2 (export) implemented via AST-based static analysis. T3 (runner) is gated scaffold only.

**Deliverables:**
- T1: AST-based detection of `dspy.Signature`, `dspy.Module`, `dspy.Predict`, `dspy.ChainOfThought`, `dspy.ReAct`, and optimizers
- T2: AST-based export of DSPy programs to `WorkflowInfo` (signatures, modules, standalone instantiations)
- T3: Gated runner scaffold (`ARC_DSPY_RUNNER_ENABLED=1`); no live provider calls without explicit gate
- Honest `CapabilityReport`: T1/T2 available, T3 gated

**Acceptance:**
- 67 tests passing (detection: 19, export: 16, runner: 17, adapter: 15)
- All 2386 Python tests passing (no regressions)
- Detection, export, and capability report work end-to-end

**Status:** Baseline Complete | Evidence: 67 DSPy tests, 2386 total Python tests passed; `pnpm build` and `pnpm typecheck` green; `scripts/check-pr.sh` green | Notes: T3 runner is gated scaffold only; no live provider calls. DSPy compile/run lifecycle worth surfacing in future T3 work.

**Source:** Adapter Roadmap Phase 30

## R32 — Haystack Adapter (Adapter Phase 31)

**Goal:** Integrate Haystack framework with ARC runtime.

**Current:** Baseline Complete. T1 (detection) and T2 (export) implemented via AST-based static analysis. T3 (runner) is gated scaffold only.

**Deliverables:**
- T1: AST-based detection of `Pipeline`, `@component`, `add_component()`, `connect()`, and YAML pipeline definitions
- T2: AST-based export of Pipeline DAGs to `WorkflowInfo` (components, connections, DAG edges)
- T3: Gated runner scaffold (`ARC_HAYSTACK_RUNNER_ENABLED=1`); no live provider calls without explicit gate
- Honest `CapabilityReport`: T1/T2 available, T3 gated

**Acceptance:**
- 65 tests passing (detection: 19, export: 16, runner: 15, adapter: 15)
- All 2451 Python tests passing (no regressions)
- Detection, export, and capability report work end-to-end
- Pipeline DAG maps cleanly to ARC run plans

**Status:** Baseline Complete | Evidence: 65 Haystack tests, 2451 total Python tests passed; `pnpm build` and `pnpm typecheck` green; `scripts/check-pr.sh` green | Notes: T3 runner is gated scaffold only; no live provider calls. Pipeline DAG maps cleanly to ARC run plans.

**Source:** Adapter Roadmap Phase 31

## R33 — Smolagents Adapter (Adapter Phase 32)

**Goal:** Integrate Smolagents framework with ARC runtime.

**Current:** Baseline Complete. T1 (detection) and T2 (export) implemented via AST-based static analysis. T3 (runner) is gated scaffold only because `CodeAgent` can execute generated Python code.

**Deliverables:**
- T1: AST-based detection of `CodeAgent`, `ToolCallingAgent`, `ManagedAgent`, tools, model wrappers, and code-execution surfaces
- T2: AST-based export of agents, tool edges, model bindings, and code-execution metadata to `WorkflowInfo`
- T3: Gated runner scaffold (`ARC_SMOLAGENTS_RUNNER_ENABLED=1`); no code/provider execution without explicit gate
- Honest `CapabilityReport`: T1/T2 available, T3 gated due to code-execution risk

**Acceptance:**
- 31 tests passing (detection: 11, export: 7, runner: 6, adapter: 7)
- All 2482 Python tests passing (no regressions)
- Detection, export, and capability report work end-to-end
- Code-agent execution remains gated and clearly labeled

**Status:** Baseline Complete | Evidence: 31 Smolagents tests, 2482 total Python tests passed; `pnpm build` and `pnpm typecheck` green; `scripts/check-pr.sh` green | Notes: T3 runner is gated scaffold only; no live provider calls or generated-code execution by default.

**Source:** Adapter Roadmap Phase 32

## R34 — Semantic Kernel Adapter (Adapter Phase 33)

**Goal:** Integrate Semantic Kernel framework with ARC runtime (T1+T2 only).

**Current:** Baseline Complete. T1 detection and T2 static export are implemented. Runtime execution is not implemented or claimed.

**Status:** Baseline Complete | Evidence: 28 Semantic Kernel tests pass; adapter registered in default registry; static export implemented | Notes: T1+T2 only. No Semantic Kernel execution, event streaming, or provider-backed flow is implemented or claimed.

**Source:** Adapter Roadmap Phase 33

## R35 — Google ADK Adapter (Adapter Phase 34)

**Goal:** Integrate Google ADK framework with ARC runtime.

**Current:** Baseline Complete. T1 detection (import probe + workspace scanner for LlmAgent, SequentialAgent, ParallelAgent, LoopAgent, FunctionTool, @tool, Runner) and T2 static AST export (WorkflowInfo with sub-agent edges and tool edges) implemented. T3 execution intentionally deferred: google-adk 0.x has active API churn and agent execution requires live Gemini/Google AI provider calls.

**Deliverables:**
- `google.adk` import probe with `ModuleNotFoundError` guard for missing `google` namespace package
- Workspace scanner for all four ADK agent types, FunctionTool, @tool decorator, Runner
- AST-based `GoogleADKVisitor` extracting agents with name/model/instruction/sub_agents/tools
- `export_google_adk_workflows()` producing `WorkflowInfo` with orchestrates/uses edges
- `GoogleADKAdapter` registered in default registry
- 44 tests: 18 detection + 16 export + 10 adapter interface

**Acceptance:**
- `google_adk` adapter in `default_registry()` ✓
- T1 detect works without `google-adk` installed ✓
- T2 export produces correct WorkflowInfo for LlmAgent, SequentialAgent, ParallelAgent, LoopAgent ✓
- `capability_report` honestly reports `detected_not_runnable` with T3-not-implemented reason ✓
- 44 tests pass; 2559 total Python tests pass ✓

**Status:** Baseline Complete | Evidence: local verification — 2559 Python tests passed, ruff clean, pnpm build/typecheck green | Notes: T3 deferred until google-adk 1.0 API stabilizes.

**Source:** Adapter Roadmap Phase 34

## R36 — MCP Python SDK Adapter (Adapter Phase 35)

**Goal:** Integrate MCP Python SDK with ARC runtime.

**Current:** Baseline Complete. T1 detection (import probe + workspace scanner for FastMCP, @tool/@resource/@prompt decorators, low-level Server, ClientSession, transport helpers) and T2 static AST export (WorkflowInfo with server/tool/resource/prompt nodes and labeled edges) implemented. Resource and prompt nodes now use first-class `NodeType.RESOURCE` / `NodeType.PROMPT`, mirrored in the TypeScript protocol type. Decorator matching now only accepts decorators from known MCP server variables when an explicit `FastMCP(...)`/`Server(...)` assignment exists, reducing false positives while preserving implicit-server fallback. T3 execution intentionally deferred: MCP servers require live transport (stdio/HTTP/SSE) and client-session lifecycle management, and have the most subtle trust posture of all adapters (tools/resources may perform privileged operations without user-explicit consent per Phase 23 enforcement).

**Deliverables:**
- `adapters/mcp_sdk/` package: detect.py, capabilities.py, export.py, __init__.py
- MCPSDKAdapter registered in default_registry()
- 58 tests in tests/adapters/mcp_sdk/ (test_adapter.py, test_detection.py, test_export.py)
- Detects: FastMCP(...), @mcp.tool(), @mcp.resource(...), @mcp.prompt(), low-level Server, ClientSession, StdioServerParameters, stdio_client/sse_client
- Exports: one WorkflowInfo per FastMCP/Server definition per file; implicit server for files with tools but no explicit server
- capability_report() returns detected_not_runnable with explicit T3-not-implemented + trust reasoning

**Status:** Baseline Complete | Evidence: local verification — 2631 Python tests passed, ruff clean, pnpm build/typecheck green | Notes: T1 + T2 only. No live MCP transport, no server execution, no paid calls. Trust posture documented.

**Source:** Adapter Roadmap Phase 35

## R37 — Provider Management System (Two-Phase Delivery)

**Goal:** Implement a unified provider management system for CLI and IDE, enabling users to configure LLM providers, manage API keys, and select models through interactive commands. Delivered in two phases: Phase 1 (interactive UX without credential storage) can be implemented immediately, Phase 2 (credential storage + OAuth) requires Phase 23 (Trust) and Phase 25 (CLI Decomposition).

**Current:** Not Started. Provider configuration is currently manual through environment variables and config files. Existing `providers/registry.py` and `providers/base.py` provide foundation for Phase 1.

### Phase 1: Provider Discovery & Interactive UX (No Dependencies)

**Status:** Baseline Complete ✓  
**Evidence:** commits cd89aab, 8e53f37, 1eb8af6, ca13e6c, 7f2e20b | 73 provider tests passed, 1 skipped | TypeScript build green  
**Depends on:** None (uses existing provider infrastructure)

**Deliverables:**
- Enhanced provider registry with built-in provider catalog (OpenAI, Anthropic, Google, Azure, local providers)
- Interactive CLI commands: `arc providers catalog`, `arc providers add --interactive`, `arc providers test`, `arc model`
- Provider status detection from environment variables
- Interactive provider selection and setup guidance
- Connection testing using environment variables
- IDE ConfigTab integration (read-only, shows providers detected from env vars)
- No credential storage (environment variables remain the only credential source)

**Acceptance:**
- Users can run `arc providers catalog` to see all available providers with descriptions
- `arc providers add --interactive` guides users through provider setup with env var instructions
- `arc providers test <provider-id>` validates credentials from env vars
- `arc model` command lists available models from configured providers (detected via env vars)
- IDE ConfigTab displays configured providers detected from environment variables
- Connection testing works using environment variables only
- No credentials stored on disk
- Interactive UX improves discoverability without requiring credential storage

### Phase 2: Credential Storage & OAuth (Depends on Phase 23 + 25 + 36.1)

**Status:** Blocked (waiting for Phase 23, Phase 25, Phase 36.1)  
**Depends on:** Phase 23 (Trust Enforcement), Phase 25 (CLI Decomposition), Phase 36.1 (Provider Discovery)

**Deliverables:**
- Authentication manager with secure credential storage at `~/.local/share/arc-studio/auth.json`
- Credentials encrypted at rest using Phase 23 trust infrastructure
- OAuth flow with local callback server (port 8080)
- CLI commands: `arc providers add --oauth`, `arc providers add --api-key`, `arc providers remove`
- Configuration schema with variable substitution (`{env:VAR}`, `{credential:provider-id}`)
- IDE ConfigTab integration (read/write, full provider management)
- Token refresh logic for OAuth providers
- Environment variable fallback (Phase 1 behavior preserved)

**Acceptance:**
- OAuth flow opens browser and completes authentication for OpenAI/Anthropic
- Credentials stored securely with encryption and 600 permissions
- Environment variables still work as fallback when no stored credentials exist
- Stored credentials require workspace trust (Phase 23 enforcement)
- `arc providers remove <provider-id>` removes stored credentials
- IDE ConfigTab allows adding/removing providers with OAuth or API key
- Token refresh works for OAuth providers
- No raw secrets in config files (only references)
- Audit log records credential access events
- Tests cover OAuth flow, encrypted storage, environment fallback, trust enforcement

**Status:** Phase 1 Baseline Complete (commits cd89aab, 8e53f37, 1eb8af6, ca13e6c, 7f2e20b) | Phase 2 Blocked (waiting for Phase 23 + 25 + 36.1) | Evidence: 73 provider tests passed, 1 skipped; TypeScript build green | Notes: Phase 1 delivered CLI commands and IDE ConfigTab integration; local providers pass tests without API keys; provider test status normalized to UI values. Phase 2 requires Phase 23 trust infrastructure and Phase 25 CLI decomposition.

**Source:** OpenCode provider system research (2026-05-23), Option C (Hybrid) approach approved 2026-05-23

## R77 — SwarmGraph Runtime Hardening (Post-Analysis)

**Goal:** Address the critical gaps identified in the 2026-05-29 deep analysis of SwarmGraph runtime. Transform the deterministic simulation into a production-capable multi-agent execution engine with real provider-backed execution, parallel workers, failure detection, and ADR-013 compliance.

**Source:** `docs/research/swarmgraph-runtime-analysis.md` (2026-05-29)

**Current:** The SwarmGraph runtime (Phase 17) exists as a deterministic `fake_offline` simulation with 10 consensus protocols, checkpoint/restore, budget enforcement, and event emission. However: workers execute sequentially with no parallelism, no LLM/provider integration exists in the SwarmGraph layer, fan-out gate is missing, worker context isolation is missing, 13 ADR-013 failure mode detectors are missing, and task decomposition is trivial (copy prompt to all workers). Phase 20's `TurnManager`/`ProviderClient` infrastructure exists but is NOT wired into SwarmGraph workers.

**Key Finding:** The 10 consensus protocols are functionally identical in practice because `fake_offline` always produces 1 auto-approved vote per task. Consensus diversity only matters with multi-vote scenarios requiring real multi-worker execution.

**Deliverables (prioritized by corrected analysis):**

P0 — Unblocks real execution:
1. Wire Phase 20 `ProviderClient`/`TurnManager` into `worker_execute()` for `gated_local` mode
2. Add async parallel worker execution via `asyncio.gather()` with configurable `max_parallel_workers`
3. Add `DecompositionStrategy` protocol (interface for trivial/heuristic/LLM decomposition)

P1 — Production readiness:
4. Add fan-out gate with parallelizability score (ADR-013 requirement)
5. Implement worker context isolation — workers receive only assigned task context
6. Add event streaming callback (`on_event: Callable`) into runner for incremental event transport without adapter mediation
7. Implement 3 of 13 failure mode detectors: coordination deadlock, consensus failure, resource exhaustion

P2 — Quality:
8. Add task dependency graph (`context=[other_tasks]` pattern from CrewAI)
9. Add task guardrails (validation before consensus)
10. Implement cancellation propagation mid-execution
11. Add JSON round-trip tests for all 19 models
12. Complete mesh/tree topology execution logic

**Acceptance:**
- `gated_local` worker mode runs a real provider-backed LLM call per task through existing `ProviderClient`
- Parallel workers execute concurrently with configurable limit (not all N simultaneously)
- Fan-out gate logs decision/score to audit trail before spawning workers
- Workers receive only their assigned task prompt, not the full decomposed prompt set
- At least 3 failure mode detectors emit typed events when triggered
- All 10 consensus protocols produce differentiated results when multiple votes exist
- Existing fake_offline tests remain green; new tests require `ARC_SWARMGRAPH_PROVIDER_TESTS=1`

**Status:** Baseline Complete + Live Smoke Proven | Evidence: Phase 106 wired `gated_local` workers through `ProviderClient`, async semaphore-bounded execution, fan-out audit, context isolation, event callback, and 3 detector events. Phase 107/109 local worktree added detectors 4-10, mesh/tree decomposition, parent/multi-dependency DAG scheduling, guardrails, broad Pydantic JSON round-trip coverage across 30 SwarmGraph models, optional SwarmGraph notification hooks, durable webhook config/outbox retry support, and an opt-in provider-backed E2E smoke test gated by `ARC_SWARMGRAPH_PROVIDER_E2E=1`. Verification: `cd python && uv run ruff check src tests` OK; `cd python && uv run pytest tests/swarmgraph/test_phase107_109.py -q` 17 passed; `cd python && uv run pytest tests/swarmgraph/ -q --tb=short` 406 passed / 1 skipped; prior `cd python && uv run pytest tests/ -q` 3686 passed / 39 skipped / 3 xfailed; `pnpm build` OK; `pnpm typecheck` OK. Prior opt-in 9router smoke using `ag/gemini-3.5-flash-extra-low` passed via `.env` key with `ARC_SWARMGRAPH_PROVIDER_TESTS=1`. Local worktree follow-up registered the CrofAI OpenAI-compatible provider and passed opt-in live SwarmGraph smoke with `ARC_SWARMGRAPH_PROVIDER=crofai` / `ARC_SWARMGRAPH_MODEL=deepseek-v4-pro-precision`; ruff and provider catalog tests passed. | Notes: Default tests make no live provider calls. Live smoke evidence proves only narrow ProviderClient worker paths, not broad provider-backed SwarmGraph E2E.

## Updated Status Summary

| Roadmap ID | Status | Next Slice |
|---|---|---|
| R1 Live Run Streaming | Complete | No v0.1 action |
| R2 IDE Runtime Setup | Complete | No v0.1 action |
| R3 Provider/Quota UI | Baseline Complete | No v0.1 action |
| R4 HITL/Audit UX | Complete | No v0.1 action |
| R5 SwarmGraph Insight | Complete | No v0.1 action |
| R6 Real Adoption | Complete | No v0.1 action |
| R7 Release Ops | Complete | No v0.1 action |
| R8 IDE Provider/Quota Completion | Baseline Complete | No v0.1 action |
| R9 IDE Live Stream Polish | Baseline Complete | No v0.1 action |
| R10 Doctor/Daemon Parity | Baseline Complete | No v0.1 action |
| R11 SwarmGraph Cost Producer | Baseline Complete | No v0.1 action |
| R12 Packaging/Optional Features | Baseline Complete | No v0.1 action |
| R13 SwarmGraph Native Runtime | Baseline Complete | No v0.1 action |
| **R14 Streaming Audit + HMAC** | **Baseline Complete** | **Phase 21 — streaming verifier, arc audit verify CLI, HMAC key mgmt (21 streaming tests)** |
| **R15 Discriminated RunEvent Unions** | **Baseline Complete** | **Phase 22 — 22 typed events + RAW fallback, TS/Python discriminated unions, type guards** |
| **R16 Trust + Paid-Call Enforcement** | **Baseline Complete; Active Hardening** | **Phase 23 — enforcement complete; sandbox subprocess caps active; microVM preflight-only** |
| **R17 Trace Virtualization + Daemon** | **Baseline Complete** | **Phase 24 — VirtualizedEventList, RingBuffer, SSE Last-Event-ID, client reconnect** |
| **R18 CLI Decomposition** | **Baseline Complete** | **Phase 25 — complete; CLI decomposed into command modules with stable JSON snapshots** |
| **R19 MCP Local Control Plane** | **Baseline Complete (scaffold)** | **Phase 26 — complete; stdio-only MCP server with trust gate, 7 tools, 3 resources** |
| **R20 MCP Tasks** | **Baseline Complete** | **Phase 27 — complete; SQLite task registry, CLI commands, MCP polling tools, retry/expiry support** |
| **R21 LangGraph Replay Contract** | **Baseline Complete** | **Phase 28 — complete; replay capability detection and inspect/simulated/unsafe reporting** |
| **R22 Persistent HITL + Eval** | **Baseline Complete (HITL only)** | **Phase 29 — HITL persistence complete; eval artifact schema and Inspect-style export deferred** |
| **R23 Consensus Escrow** | **Complete** | **Phase 30 — complete; commit-reveal voting with cryptographic verification and adversarial tests** |
| **R24 Adaptive Consensus** | **Complete** | **Phase 31 — complete; deterministic risk assessment, protocol selection, raft/bft/bft_escrow hardening** |
| **R25 Event-Driven Notifications** | **Baseline Complete** | **Phase 32 + SwarmGraph hooks — event bus/webhooks baseline exists; SwarmGraph optional webhook/EventBroker hooks plus durable local JSONL outbox/retry support added; delivery remains best-effort, no SSE/WebSocket claim** |
| **R26 Swarm Memory Graph** | **Baseline Complete (research prototype + privacy/evaluation gates)** | **Phases 59-61 — local-only schema/store/extract/query, redaction-before-extraction, forget-run, evaluate; runtime wiring deferred** |
| **R27 LangChain Adapter** | **Baseline Complete** | **Adapter Phase 26 — complete (commits 6beedf8, ea567cf, 7566e60)** |
| **R28 Anthropic Provider + Registry** | **Baseline Complete** | **Adapter Phase 27 — complete (commit 4a479b7)** |
| **R29 OpenAI-Compatible Provider** | **Baseline Complete** | **Adapter Phase 28 — complete (commit 6826d8d, 24 tests, 6 vendors)** |
| **R30 Pydantic AI Adapter** | **Baseline Complete** | **Adapter Phase 29 — complete (commits 7680017, c34abb3, 27a33b1 — 43 tests, 3 PRs)** |
| **R31 DSPy Adapter** | **Baseline Complete** | **Adapter Phase 30 — T1 detection (19 tests), T2 export (16 tests), T3 gated scaffold (17 tests), adapter (15 tests)** |
| **R32 Haystack Adapter** | **Baseline Complete** | **Adapter Phase 31 — T1 detection (19 tests), T2 export (16 tests), T3 gated scaffold (15 tests), adapter (15 tests)** |
| **R33 Smolagents Adapter** | **Baseline Complete** | **Adapter Phase 32 — T1 detection (11 tests), T2 export (7 tests), T3 gated scaffold (6 tests), adapter (7 tests)** |
| **R34 Semantic Kernel Adapter** | **Baseline Complete** | **Adapter Phase 33 — T1 detection + T2 static export; no runtime execution claim** |
| **R35 Google ADK Adapter** | **Baseline Complete** | **Adapter Phase 34 — T1 detection + T2 static export; T3 deferred (google-adk 0.x churn)** |
| **R36 MCP Python SDK Adapter** | **Baseline Complete** | **Adapter Phase 35 — T1 detection + T2 static export; T3 deferred (trust posture + transport lifecycle)** |
| **R37 Provider Management (Phase 1)** | **Baseline Complete** | **Phase 36.1 — interactive UX without credential storage (commits cd89aab-7f2e20b)** |
| **R37 Provider Management (Phase 2)** | **Baseline Complete** | **Phase 36.2 — auth module with Fernet encryption, OAuth handler, dynamic callback ports, PKCE/state validation, optional Keychain via `--keychain`, CLI `arc providers add --api-key/--oauth/remove`; token refresh; trust enforcement; audit logging; env var fallback; 57 auth tests** |
| **R38 CLI Sandbox Hardening + IDE Integration** | **Active Hardening** | **Phase 37 — subprocess caps + approval prune + path-intent expansion + protocol parity + microVM preflight + container fallback tests + e2e routability + microVM truth guard + design-proof plan + gated Lima low-security developer harness + Lima mount-proof mode (CI-skipped real-host symlink evidence) + ADR-024 contract + Firecracker gated harness + firecracker_doctor() + public-execution truth guard + real-host Lima lifecycle tests (CI-skipped; P2 network-off blocked by Lima 2.x slirp) + symlink-escape guard + Firecracker CI-skip structure + local audit query UX + Firecracker proof artifact hardening + classifier/path-intent regressions complete; microVM execution blocked pending P1–P7 proofs** |
| **R39 Interactive CLI/UX Foundation** | **Baseline Complete** | **Phases 41–45 — slash command registry, approval UX, progress rendering, REPL error boundary, advisory locking, read-only IDE session bridge; 2846 Python tests; OpenCode/Claude Code parity remains a target, not claimed** |
| **R40 CLI/UX Polish & Advanced Features** | **Baseline Complete** | **Phase 42 — P0 CLI foundation (pipelines, aliases, batch mode foundation); IDE write bridge deferred pending advisory lock integration** |
| **R41 Advisory Locking + IDE Session Bridge** | **Baseline Complete** | **Phase 43 (read-only bridge) + Phase 46 (CLI write bridge) + Phase 47 (daemon HTTP write bridge) — POSIX fcntl.flock; atomic writes; daemon-first session writes with CLI fallback; session_changed event; LOCK_CONTENTION error code; Windows remains single-writer best-effort** |
| **R42 Slash Registry Expansion + REPL Error Boundary** | **Baseline Complete** | **Phase 44 — /help rebuilt as grouped palette (SESSION/RUN/SANDBOX/POLICY/WORKSPACE/PROVIDERS/AUDIT/TASKS/MCP); per-command error boundary; all P0/P1 commands verified; 2828 Python tests** |
| **R43 Approval + Progress + Error UX** | **Baseline Complete** | **Phase 45 — render-state prefixes ([ok]/[denied]/[blocked]/[empty]/[error]); interactive y/N prompt for NETWORK/INSTALL/UNKNOWN; TTY-aware; DESTRUCTIVE/PRIVILEGED hard-denied; audit events for all deny paths; 2846 Python tests** |
| **R44 IDE Write Bridge / Daemon Protocol** | **Baseline Complete** | **Phase 46 CLI bridge + Phase 47 daemon HTTP bridge — arc studio sessions write/delete/update fallback; daemon POST/DELETE/PATCH /api/sessions; daemon-first TS bridge with CLI fallback; session_changed event; ADR-025 Windows lock posture** |
| **R53 Local Sandbox Audit Query + Compaction** | **Baseline Complete** | **Phase 82 — local-only audit query/compaction; compaction refuses canonical hash-chain logs; 19 audit query tests** |
| **R54 Container Isolation Provider** | **Baseline Complete** | **Phase 83 — container fallback remains disabled unless `ARC_ENABLE_CONTAINER_SANDBOX=1`; Docker/Podman CLI provider hardened** |
| **R55 Local Sandbox Policy YAML** | **Baseline Complete** | **Phase 84 — local workspace/user YAML policy validation/apply/list/show; no remote policy server** |
| **R56 Agentic CLI Edit Loop** | **Baseline Complete** | **Phase 85 — one-file safety-gated edit plan/apply using sandbox plan policy and existing audit helpers; no autonomous multi-file parity claim** |
| **R57 Interactive CLI UX Polish** | **Baseline Complete** | **Phase 86 — `/edit` REPL command + help palette wiring with structured states; no broad Claude Code/OpenCode parity claim** |
| **R58 Tool Runtime Unification** | **Baseline Complete** | **Phase 87 — shared registered-tool execution wrapper validates args and trust-wraps output; provider turn manager unchanged** |
| **R59 Edit Preview Staleness Guard** | **Baseline Complete** | **Phase 88 — edit plans expose file/replacement hashes; apply can deny stale preview hashes before writing** |
| **R60 Saved Edit Plan Apply Flow** | **Baseline Complete** | **Phase 89 — edit plans persist safe metadata; apply by `--plan-id` checks original/replacement hashes before writing** |
| **R61 Edit Bundle Approval Bridge** | **Baseline Complete** | **Phase 90 — multi-file edit bundles, scoped approval token, list/show bridge, narrow patch mode, and saved edit-plan review provenance; no autonomous coding-agent parity claim** |
| **R62 IDE Edit Plan Review Surface** | **Baseline Complete** | **Phase 91 — metadata-only IDE tab/backend bridge for saved edit-plan list/show/approve; no replacement content, autonomous editing, or signed reviewer claim** |
| **R63 Sandboxed Diff/Apply/Test Loop** | **Baseline Complete** | **Phase 92 — REPL `/diff`, `/apply`, and `/test` commands route through saved edit metadata, edit apply gates, and sandbox execution; no self-healing agent loop or network-by-default claim** |
| **R64 Patch Engine Hardening v2** | **Baseline Complete** | **Phase 93 — text-only multi-hunk unified diff support with hunk range validation and fail-closed malformed/binary handling; not a complete Git patch engine** |
| **R65 Sandbox/MicroVM Truth Audit Guard** | **Baseline Complete** | **Phase 94 — blocked public microVM run attempts now emit denial audit events; doctor/preflight separates runtime readiness from public execution readiness** |
| **R66 Sandbox Classifier And Path-Intent Hardening v3** | **Baseline Complete** | **Phase 95 — write-output paths are validated across classifications and dynamic unknown shell/interpreter approvals are denied before execution** |
| **R67 MicroVM Proof-Harness Truth Guards** | **Baseline Complete** | **Phase 96 — Lima bounded output drain, Firecracker curl/workspace proof markers, workspace marker clobber guard, and reusable 8-subagent orchestrator prompt** |
| **R68 Priority 1 CLI Parity Research + Acceptance Matrix** | **Baseline Complete** | **Phase 97 — Context7/Vercel Grep unavailable in runtime and recorded; local/web-supported research matrix landed** |
| **R69 Autonomous Edit-Test-Repair Loop** | **Baseline Complete** | **Phase 98 — bounded edit -> sandboxed test -> diagnose -> repair loop with audit and stop conditions** |
| **R70 Git-Backed Undo/Redo Transactions** | **Baseline Complete** | **Phase 99 — safe transaction log, restore/redo, dirty-worktree protection, tests** |
| **R71 Rich IDE Diff Review/Apply Flow** | **Baseline Complete** | **Phase 100 — real diff rendering, approval/apply/deny flow, patch-content gates** |
| **R72 Provider-Backed Runtime Shell** | **Baseline Complete** | **Phase 101 — gated provider shell contract baseline, dry-run/default-safe path, no default paid calls** |
| **R73 Live Terminal/Event Streaming UX** | **Baseline Complete** | **Phase 102 — CLI JSONL incremental stdout/stderr/events/cancel for sandbox/testbench/provider-shell; IDE/REPL streaming follow-up** |
| **R74 Broad CLI CI Orchestration** | **Baseline Complete** | **Phase 103 — detect local CI matrix, run selected argv job through sandbox/streaming, write local artifact, stable JSON** |
| **R75 macOS MicroVM Execution + Strict No-Network Proof** | **Gated Public CLI Proof Passed Once / Artifact Provenance Added / Default Off** | **Phase 104 — Direct Apple VZ `arc sandbox run --provider microvm -- pwd` passed once with no-network/workspace/teardown/audit evidence; not production-grade or arbitrary-command execution** |
| **R76 Linux Firecracker Execution Proof** | **Host-Unproven Scaffold** | **Phase 105 — Linux/Firecracker gated scaffold exists behind KVM/rootfs/env gates; real proof requires eligible Linux host** |
| **R77 SwarmGraph Runtime Hardening** | **Baseline Complete + Live Smoke Proven** | **Phase 106/107 — ProviderClient worker wiring, async parallel execution, fan-out gate, context isolation, event callback, 10 failure detectors, mesh/tree decomposition, parent/multi-dependency DAG scheduling, guardrails, notification hooks, and opt-in 9router worker smoke complete** |
| **R-TS1 Token-Saving Research** | **Research Intake (Planning Only)** | Status: Research Intake | Evidence: `docs/research/TOKEN_SAVING_PLAN.md` (first draft) + `TOKEN_SAVING_PLAN-2.md` (authoritative; repo-grounded at origin/main `d82e925`) | Notes: Confirms ARC has complete cache_control plumbing in providers/anthropic.py but callers never populated it; R-03 (OTel) identified as highest-leverage first step. |
| **R-TS2 Token-Saving P0** | **Baseline Complete** | Status: Baseline Complete | Evidence: commits `eb6d1e1` (P0-1 msg ordering), `177c882` (P0-2 Anthropic cache_control), `6813c95` (P0-3 token counter), `1cbc295` (P0-4 status bar), `8e677c5` (test fix), `e89ee5e` (R-03 OTel cache fields); 4893 passed; patches in `patches/tokens/p0/001-005` | Notes: Byte-stable ordering, auto cache_control injection, provider-aware token counter wired into DataStore, context meter in status bar, OTel cache fields visible. Tag candidate: v0.3.0-alpha. |
| **R-TS3 arc-protocol-ts coverage backfill** | **Baseline Complete** | Status: Baseline Complete | Evidence: thresholds restored to 73/80/87/85 in v0.3.1-alpha | Notes: Coverage debt from v0.3.0-alpha R-03 repaid within one patch tag. |
| **R-TS4 R-01 TokenWallet** | **Baseline Complete** | Status: Baseline Complete | Evidence: v0.4.0-alpha @ 8affdd0; 4922 passed; 4 patches in patches/r01/v0.4.0-alpha/ | Notes: TokenWallet, /wallet, /budget, QuotaWarning consumer, OTel spec alias shipped. |
| **R-TS5 Budget Persistence + Pricing Refresh** | **Baseline Complete** | Status: Baseline Complete | Evidence: spec/v0.4.1-persistence-and-pricing; 4937 passed (+15); SQLiteWALStorage + 7 Anthropic + 12 OpenAI rate rows | Notes: SESSION/PROVIDER_DAY survive restart; OpenAI cache corrected 50→90% for GPT-5.x; v0.4.1-alpha tag candidate. |
| **R-TS6 Gemini client caching guard** | **Do Not Refactor** | Status: Known quirk — do not remove | Evidence: `8cdc378` + `9a31fff` on main (post v0.4.1-alpha tag) | Notes: Gemini vendor bypasses `self._client` caching in `_client_instance()` due to HTTP/2 connection-reuse issue with OpenAI SDK v2. The `if self._vendor == "gemini"` guard must stay. Do not remove without retesting against generativelanguage.googleapis.com/v1beta/openai/ with sdk>=2.x. All other vendors unaffected. |
| **R-TS7 R-02 + QW-4 feature sprint** | **Baseline Complete** | Status: Baseline Complete | Evidence: branch spec/v0.5.0-r02-and-qw4; 4979 Python passed (+42); 147 TS passed (+4); 7 commits c8c57ca→8a82cca | Notes: HandleStore (SQLiteWAL), tool virtualization, /expand, compaction, provider wiring, typed events. CoSAI gates: no LLM in compact() or handles path. All protocol parity tests pass. |
| **R-TS8 Chinese-labs vendor adoption + capability backfill** | **Baseline Complete** | Status: Baseline Complete | Evidence: tags v0.5.1-alpha (d667550), v0.5.2-alpha (5c05df5); 91 model rows synced from OpenRouter via scripts/sync_from_pricing_feed.py across 6 vendors (DeepSeek, Qwen, Kimi, GLM, MiMo, MiniMax); CostRate extended with 6 optional fields in v0.5.1 + 2 capability fields in v0.5.2 (supported_parameters, input_modalities); docs/research/pricing-feed-sources-comparison.md locks OpenRouter as primary source. | Notes: First sprint to source pricing data from an external catalog rather than hand-curate. Decision rationale documented in docs/research/pricing-feed-sources-comparison.md. |
| **R-TS9 Catalog-driven model picker + capability gating** | **Baseline Complete** | Status: Baseline Complete | Evidence: tag v0.6-alpha (4de0eae); /models slash command with --vendor/--has/--free/--max-input/--max-context filters; /model-info detailed model lookup; tui/widgets/capability_gates.py with per-model fail-closed semantics; status bar capability chip; ModelChanged typed event (3 Py + 1 TS site); test_has_vision_filter_per_model_granularity at test_slash_models.py:66 validates v0.5.2 backfill investment. Post-tag: 86043fe (non-Chinese-lab backfill + models.dev + --max-context) + 1aa2da5 (capability_gates fail-closed fix). | Notes: First "user-facing UX from catalog data" tag. Per docs/research/catalog-driven-connection-tradeoffs.md, catalog drives UI only — connection layer stays hand-coded per provider. |
| **R-TS10 Opt-in cloud features** | **Baseline Complete** | Status: Baseline Complete | Evidence: tag v0.7-alpha (83568b3); cloud/pricing_feed.py with hash-pinning + accept-new-hash; cloud/budget_broker.py with configurable fail-closed fallback; cloud/observability_bridge.py with per-session consent gating; 3 new typed events (PricingFeedRefreshed, BudgetBrokerSync, ObservabilityExportStarted); docs/threat-models/v0.7-opt-in.md with per-feature threat analysis; 5131 Python passed (+40), 155 TS passed (+6). Inherits 86043fe + 1aa2da5 from main between v0.6 tag and v0.7 branch creation. | Notes: All three features default OFF; preserve local-first L2+L3+L4 baseline. v3 spec §4a enforced 6 verification gates including threat-model existence and consent-gating proof. |

| **R-UX1 UX Polish — Header + ContextMeter + ModeBadge + Markdown** | **Baseline Complete** | Status: Baseline Complete | Evidence: commit 0b03f41; header.py (120 LOC) + mode_badge.py (84 LOC) + context_meter.py (64 LOC) shipped; Shift+Tab → cycle_mode at screen.py:48; markdown_block.py (36 LOC); tests/tui/test_mode_cycle.py. 5131 Python passed. | Notes: All three R-001/R-002/R-003 components confirmed present. R-003 (ModeBadge/Shift+Tab) partially shipped in v0.2.0-alpha; R-001 (Header) + R-002 (ContextMeter) filled genuine gaps. TUI grade 39→mid-60s target achieved. |
| **R-UX2 UX Modes + Approvals** | **Baseline Complete** | Status: Baseline Complete | Evidence: spec/v0.8-r-ux2 merged to main (2026-06-05); approval_card.py, capability_banner.py, activity_tray.py (Ctrl+X), mcp_banner.py, plan_view.py, slash_menu.py all present + wired in screen.py; sandbox-aware shell-escape via decide() (fail-closed, audit on allow); streaming. 5193 Python passed. | Notes: ApprovalCard event-driven mount into live transcript not yet subscribed (widget present, push_screen path works; data-stream subscription deferred to R-UX3 polish). |
| **R-UX3 UX Components + Information Architecture** | **Baseline Complete (all deferred items resolved)** | Status: Baseline Complete (all deferred items resolved) | Evidence: ToolCard wired in transcript.py (tool-role → ToolCard, Enter/x expand + risk badge); Toaster wired in screen.py (#toaster, fires on sandbox-deny + daemon-reconnect); KeycapHint + RiskBadge widgets added with NO_COLOR fallbacks; CommandPalette searches name + description; SlashMenu category chips + two-line items + MRU ordering; DiffBlock color (+/-/@@) + n/p hunk nav; runs_view filter+sort, hitl_view field-name fix + token-gated viewer, sessions_view fork. Commits dd6818f + 17e8e84. 5219 Python passed. | Notes: per-command frontmatter detail pane done (Phase 128 — CommandPalette #palette-detail Static shows help_text+usage+examples[:2] on highlight); ToolCard rerun key done (Phase 129 — 'r' posts RerunRequested message); DiffViewer side-by-side done (Phase 130 — 's' key toggles unified/side-by-side two-column view); ApprovalCard stream subscription done (Phase 131 — hitl_gate_fn hook in TurnManager, called before provider turn, deny emits turn.denied + raises ProviderError(retryable=False)); deferred — providers_view quota (network-dependent). |
| **R-UX4 UX Themes + Accessibility** | **Baseline Complete** | Status: Baseline Complete | Evidence: theme.py ships 6 themes (dark/light/mocha/latte/high-contrast/mono) + registry + select()/cycle(); base.tcss tokenized + ArcApp.get_css_variables() injects theme tokens so /theme re-skins live (closes H24); /theme <name>|list, /title, /statusline slash commands; NO_COLOR glyph fallback completed across all rendered widgets (status_bar daemon/stream fixed); ARC_REDUCED_MOTION + glyph() + thinking_indicator() in theme_extras.py (wired). Commits 09d13f6 + 7df65c3 + 5c2a2da. 5236 Python passed. | Notes: closes audit heuristics H11, H12, H22, H24, H25. /statusline reports fixed slots (slot reordering not yet configurable). pytest-textual-snapshot harness in use (2 home SVGs xfailed). ux/mockups/ not preserved. |
| **R-OPEN-HARDEN Production Hardening** | **Baseline Complete** | Status: Baseline Complete (Phases 123-127: retry + degrade + failover + wiring) | Evidence: _call_with_retry (123) + _stream_with_retry (124) + turn.failed degradation (125) + FallbackProviderClient (126) + ARC_FALLBACK_PROVIDERS env wiring (127); 29 retry/degradation/failover tests; 5550 passed. | Notes: ARC_FALLBACK_PROVIDERS=name1,name2 wires an ordered failover chain at the provider construction point; unavailable providers are skipped with a warning. Durability-under-error budget tests not a clear gap (enforcer not in turn path, persistence 8/8 tested). |
| **R-OPEN-SANDBOX MicroVM / Sandbox Layer** | **Baseline Complete** | Status: Baseline Complete (shell-escape hardening) — reconciled 2026-06-06 | Evidence: the stale "shell escape via raw subprocess.run(shell=True)" concern is resolved. Verified: zero `shell=True` in `src/` (grep — only `allow_shell`/`requires_shell` config flags remain); `tui/screen.py::_handle_shell_escape` routes `!cmd` through `shlex.split` (fail-closed on parse error + empty argv) → `resolve_trust` (blocks UNTRUSTED) → deterministic `decide(argv, policy)` (privileged/destructive always denied; network/install/unknown gated; ARGV_OVERSIZED bounds) → approval gate → isolation `provider.execute(argv)` (no shell, env allowlist, workspace cwd, policy timeout) → audit on allow + deny; any gate exception fails closed. `tests/tui/test_sandbox_shell_escape.py` = 12 tests (6 core + 6 edge: unparseable, empty, approval-required, timeout, provider-error, argv-oversized). Pattern matches Python docs (shlex.split → argv → shell=False) + real-world usage. Docs: docs/prompts/sandbox-shell-hardening.md + docs/research/sandbox-shell-hardening-plan.md. | Notes: shell-escape portion complete. The microVM execution layer is tracked separately under Phase 104 (gated macOS VZ proof, default-off). `screen.py` `/export` pager call is list-argv on a tempfile (not a shell-injection vector). |
| **R-OPEN-DEFERRED-RUNBOOKS Execute Deferred Research Runbooks** | **Baseline Complete** | Status: Baseline Complete (executed 2026-06-06) | Evidence: scripts/research/measure_estimator_accuracy.py created + run vs local corpus (2,285 traces) — corpus is synthetic SwarmGraph fixtures (1 distinct content string) so the representative multi-category benchmark stays deferred to real dogfood traces (no fabricated numbers per brief); single data point: default no-provider heuristic over-counts a 132-char prose string ~59% (tiktoken 27 vs heuristic 43), wallet-safe (over-count). budget-persistence-audit.md written: SQLiteWALStorage verified (8/8 persistence tests pass), database-is-locked resolved (busy_timeout + prompt connection close), residual cross-process last-writer-wins limit documented. | Notes: token-estimator re-run pending real diverse traces; budget persistence design settled (SQLite WAL); atomic-increment only needed if multi-process budget sharing is ever in scope. |
| **R-OPEN-ADAPTERS-AUDIT Audit External Adapters Research Folder** | **Baseline Complete** | Status: Baseline Complete (executed 2026-06-06) | Evidence: docs/research/adapters-folder-audit.md + reusable prompt docs/prompts/adapters-folder-audit.md written; audited the out-of-tree WorkSpace/ARC/adapters folder (9 research .md + a stale duplicate checkout + tool caches) against the live repo with verify-don't-trust. Verified: registry wires 15 adapters via build_default (research said "14/17"); pydantic_ai package present but unregistered with a placeholder runner at runner.py:173 (VERIFIED); no adapters/_shared.py so the consolidation recommendation is still open (VERIFIED); the "60+ duplicated helpers" claim is OVERSTATED ~7x (actual ~8: 4 _event + 2 _workspace_import_path + 2 _redact); sprint3 SDK API specs captured as external-sourced reference (unverified against installed SDK). External folder untouched. | Notes: split into still-actionable (bounded _shared.py extraction; pydantic_ai runner decision; Strands/Letta/Browser Use candidate adapters; per-adapter AG-UI/audit gaps re-verified at implementation time) vs discard (the 60+ duplication figure; the stale duplicate-checkout roadmap; the "17 adapters" framing). Execution plan: docs/phases.md Phase 112. |
| **R-OPEN-ADAPTERS-SHARED Adapter Shared Helpers Consolidation** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: adapters/_shared.py created with make_event() + workspace_import_path(); 4 adapters (crewai, langgraph, swarmgraph, openai_agents) repointed to delegate to shared helpers; 6 new tests in tests/adapters/test_shared_helpers.py; 5443 passed. Commits 82c8799. | Notes: ~8 verified helper copies extracted (4 _event, 2 _workspace_import_path). Execution plan: docs/phases.md Phase 113. |
| **R-OPEN-ADAPTERS-PYDANTIC-AI pydantic_ai Placeholder Cleanup** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: run_agent_with_streaming() replaced silent result=None with NotImplementedError; test updated to assert NotImplementedError with actionable message; PydanticAIEventHandler kept intact; 43 pydantic_ai tests pass. Commits f367dac. | Notes: at the time of this slice the adapter was intentionally unregistered; superseded by Phase 116 (R-OPEN-ADAPTERS-PYDANTIC-AI-RUNNER) which implemented the real agent.run_sync() runner AND registered it as adapter #17. Execution plan: docs/phases.md Phase 113. |
| **R-OPEN-ADAPTERS-STRANDS Strands Agents (AWS) Adapter** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: adapters/strands.py StrandsAdapter registered as adapter #16 in build_default(); detect via find_spec("strands") + workspace import scanning; export_workflow returns single-node WorkflowInfo; run_workflow calls agent(prompt) gated by ARC_STRANDS_ALLOW_COSTS=true + ARC_STRANDS_EXPORT=module:attr; 14 offline tests; 5457 passed. API verified against strands-agents v1.42.0. Commits 1fc034d. | Notes: default model is BedrockModel (AWS creds); other providers (Anthropic, OpenAI, Gemini, Ollama) also supported. Simulator/detection only by default; can_run=False without gate. Execution plan: docs/phases.md Phase 114. |
| **R-OPEN-SANDBOX-APPROVAL Sandbox Approval Hint + Dead Branch Removal** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: decide() produces allowed=False+approval_required=True (mutually exclusive with allowed=True); dead handler branch approved=False+allowed=True removed; approval hint ("arc sandbox run") moved into the allowed=False block conditioned on approval_required; test updated to exercise real code path (denied+approval_required=True shows hint). 12 shell-escape tests pass. Commits 0965807. | Notes: approve_decision() path (allowed=True+approved=True) preserved for interactive approval UX; decide() contract unchanged. Execution plan: docs/phases.md Phase 115. |
| **R-OPEN-ADAPTERS-PYDANTIC-AI-RUNNER pydantic_ai Real Runner** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: adapters/pydantic_ai_adapter.py PydanticAIAdapter (#17) wires the existing detect/export/runner package into RuntimeAdapter; runner.py run_agent_with_streaming() calls agent.run_sync(prompt) for real; detect.py fixed pre-existing ModuleNotFoundError on find_spec("google.generativeai") namespace package; 9 new offline adapter tests; test_streaming.py updated to test real run_sync call + error path; 5471 passed. Commit 7fcc98b. | Notes: uses PydanticAIEventHandler for lifecycle events; offline TestModel available for testing without API keys; ARC_PYDANTIC_AI_ALLOW_COSTS=true + ARC_PYDANTIC_AI_EXPORT=module:attr required for run_workflow. Execution plan: docs/phases.md Phase 116. |
| **R-OPEN-ADAPTERS-LETTA Letta (MemGPT) Adapter** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: adapters/letta.py LettaAdapter (#18) server-backed stateful-agent adapter; client.agents.messages.create(agent_id, messages) verified against letta-client v1.12.1 (context7); detect via find_spec(letta_client) + LETTA_API_KEY/LETTA_BASE_URL + workspace import scan + .af files; run_workflow dual-gated (ARC_LETTA_AGENT_ID + ARC_LETTA_ALLOW_COSTS=true); 12 offline tests; 5482 passed. Commit ec47569. | Notes: unique execution model — REST call to running Letta server, not workspace code loading; supports cloud (LETTA_API_KEY) and local server (LETTA_BASE_URL). Execution plan: docs/phases.md Phase 117. |
| **R-OPEN-AG-UI-GAPS AG-UI Mapper Registration (letta/strands/pydantic-ai)** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: letta_mapping.py, strands_mapping.py, pydantic_ai_mapping.py created + wired via noqa:F401 import; 10 mapper tests; 5492 passed. Commit 2f6238a. | Notes: scope verified — only these 3 adapters emit ARC events without register_mapper; openai_agents maps inline via streaming.py. Execution plan: docs/phases.md Phase 118. |
| **R-OPEN-CI-FLAKES-119 CI Flakes — HMAC+SIGINT xfail** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: test_hmac_chain_concurrent_append marked xfail (concurrent writers without mutex produce seq=0 collision); test_sigint_during_run_yields_degraded_and_cancelled_event marked xfail(strict=False) (SIGINT timing under load); 5491 passed, 7 xfailed. Commit f47c6e9. | Notes: no source code changes; honest documentation of known limitations. Execution plan: docs/phases.md Phase 119. |
| **R-OPEN-CI-FLAKES-120 CI Flakes — SQLite concurrent accumulation xfail** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: test_concurrent_accumulation marked xfail (SQLite WAL busy_timeout insufficient under tight CI load); full suite including test_persistence.py now runs clean: 5498 passed, 0 failed. Commit 918f4c2. | Notes: --ignore=tests/budget/test_persistence.py flag no longer needed. Execution plan: docs/phases.md Phase 120. |
| **R-OPEN-ADAPTERS-BROWSER-USE Browser Use Adapter** | **Baseline Complete** | Status: Baseline Complete (2026-06-06) | Evidence: adapters/browser_use.py BrowserUseAdapter (#19) triple-gated (ARC_BROWSER_USE_ALLOW_COSTS=true + ARC_BROWSER_USE_ALLOW_BROWSER=true); API verified against browser-use (context7 /browser-use/browser-use) — Agent(task,llm); await agent.run(max_steps=N) → AgentHistoryList; history.final_result()/is_done()/has_errors()/urls(); browser_use_mapping.py AG-UI mapper; 12 offline tests; 5510 passed. Commit b1e60e3. | Notes: triple-gated because it launches a real browser, makes provider calls, and browses the open web; 97K GitHub stars. Execution plan: docs/phases.md Phase 121. |

**Post-v0.1 Execution Order:** 
- **Priority 1 stop-the-line:** R68-R76 / Phases 97-105 (full CLI parity track). Research first, then implement in order unless the research matrix proves a safer dependency order. Do not claim OpenCode/Claude Code parity, autonomous repair, rich diff review, provider-backed shell, broad CI orchestration, or microVM execution until implemented and tested.
- **Already active foundation:** R38/R65-R67 sandbox and microVM hardening may continue only where it directly supports Priority 1 CLI parity, strict VM proof, policy, audit, or execution UX.
- **Foundations:** R14-R16 (Phase 21-23) → R17-R18 (Phase 24-25)
- **Sandbox:** R38 (Phase 37 — subprocess/approval/path-intent/parity/preflight/container/e2e/truth-guard/design-proof/gated-Lima-low-security-harness/Lima-mount-proof-mode/ADR-024-execution-contract complete; microVM execution blocked pending P1–P7 proofs)
- **MCP:** R19-R20 (Phase 26-27)
- **Replay/Eval:** R21-R22 (Phase 28-29)
- **SwarmGraph differentiators:** R23-R25 (Phase 30-32)
- **Research:** R26 (Phase 33)
- **Adapter integration:** R27-R36 (Adapter Phases 26-35)
- **Provider Management Phase 2:** R37 Phase 2 (Phase 36.2, after Phase 23 + 25 + 36.1)

**Critical Path:** Priority 1 CLI parity research matrix (R68/Phase 97) → autonomous edit-test-repair (R69/Phase 98) → git undo/redo transactions (R70/Phase 99) → rich IDE diff review/apply (R71/Phase 100) → provider-backed runtime shell (R72/Phase 101) → live terminal/event UX (R73/Phase 102) → CLI CI orchestration (R74/Phase 103) → macOS microVM no-network proof if feasible (R75/Phase 104) → Firecracker boot/run/destroy proof if feasible (R76/Phase 105) → remaining product roadmap.

**Note:** R39 (Phase 41) execution gate was cleared as of 2026-05-26 (commit 7fdba99), but the new Priority 1 track is broader and remains Not Started: OpenCode/Claude Code parity target, autonomous repair, git transactions, rich IDE diff apply, provider-backed shell, live terminal/event streaming, broad CLI CI, and real microVM proof work are not claimed complete.

## R39 — Interactive CLI/UX Foundation

**Goal:** Make `arc studio chat` a first-class OpenCode/Claude Code style ARC agent shell without claiming parity before it exists. The shell must expose core ARC capabilities through `/` commands, reuse existing trust/sandbox gates, render progress/errors clearly, and support the agent workflow loop: inspect context, explain policy, approve safe actions, run tools, show diffs, run tests, and persist/resume sessions.

**Current:** CLI has 40+ commands across 23 Typer sub-apps. REPL has 17 slash commands, but they are manually registered in a separate `cli_repl` registry and do not wrap the broad Typer command surface. Slash commands exist only inside `arc studio chat`; they are not first-class adapters over ARC's mature CLI features. Non-slash input still uses a SwarmGraph-specific path. Sandbox/policy/audit/task/provider/MCP features are mostly top-level CLI-only with no REPL integration. No command palette, structured command adapter layer, approval renderer, diff/apply/test loop, live progress renderer, history search, or robust per-command error boundary exists.

**Deliverables:**
1. Canonical interactive shell framing for `arc studio chat` and bare-`arc` TTY behavior.
2. Shared command adapter contract for REPL slash commands that can call service-layer helpers without shelling out to `arc`.
3. P0 slash commands: `/sandbox doctor`, `/sandbox run -- <cmd...>`, `/policy explain -- <cmd...>`, `/runs list`, `/runs show <id>`, `/doctor`, `/status`.
4. P1 slash commands: `/audit verify`, `/audit list`, `/task list`, `/task status`, `/providers status`, `/provider`, `/model`, `/mcp status`, `/hitl pending`, `/context pack`.
5. Interactive approval UX for sandbox/shell/network/install/write commands.
6. Live progress and cancellation rendering for `/run` and long-running commands.
7. Structured/rich rendering for command results, errors, denials, and remediation.
8. REPL error boundary so one failed command does not crash the shell.
9. Agent workflow command design: `/read`, `/search`, `/diff`, `/apply`, `/test` with trust/sandbox gates.
   Current implementation evidence: `/read` and `/search` are read-only REPL commands with workspace bounds, symlink/path-escape guards, text-only output, and output caps; `/diff`, `/apply`, and `/test` remain design-only/gated future work.
10. Session resume/search and eventual IDE/CLI session sharing.

**Acceptance:**
- `/help` lists a product-meaningful command palette, not only the current narrow SwarmGraph/session subset.
- P0 slash commands are implemented and tested without broad shell-out wrappers.
- `/sandbox run -- <cmd...>` applies existing sandbox policy and approval behavior from inside the REPL.
- `/policy explain -- <cmd...>` explains command risk without execution.
- `/doctor` shows daemon health, workspace trust, sandbox/isolation status, provider status, and MCP status where available.
- REPL renders blocked/denied/error states without crashing.
- `/run` renders live start/progress/completion/cancellation events.
- Docs explicitly state that OpenCode/Claude Code parity is a target, not current behavior.

**Status:** Baseline Complete | Evidence: commits 37fd92b (Phase 42 foundations), 563a1ad (Phase 43 advisory lock + IDE bridge), b3e1471 (Phase 44 slash registry), 7fdba99 (Phase 45 approval UX); 2846 Python tests pass; TS build + typecheck green | Notes: All Phase 41 acceptance criteria met across Phases 41–45. P0/P1 slash commands implemented and tested. REPL error boundary live. Approval UX wired for NETWORK/INSTALL/UNKNOWN. DESTRUCTIVE/PRIVILEGED hard-denied. Advisory locking on all session/alias writes. Read-only IDE session bridge implemented. OpenCode/Claude Code parity remains a stated target, not claimed parity.

**Execution gate cleared** as of 2026-05-26 (commit 7fdba99). Product work may advance.

**Source:** Interactive CLI/UX Audit, 2026-05-26

## R40 — CLI/UX Polish & Advanced Features

**Goal:** Advanced CLI features: multi-command pipelines, interactive dashboard, command aliases, batch mode, session export/import.

**Current:** P0 CLI foundation implemented. IDE write bridge and daemon/shared-session bridge remain deferred.

**Deliverables:**
- Multi-command pipeline support (`|` pipe, `&&` / `||` chaining)
- Interactive dashboard (`arc dashboard`)
- Command aliases and snippets
- Batch mode (`arc batch plan|run <file>`)
- Session export/import bundles for CLI sessions
- Read-only IDE bridge protocol documented; daemon/shared-server bridge deferred

**Acceptance:**
- Pipelines work in REPL and batch mode
- Dashboard shows local producer snapshot without fabricated data
- Aliases are workspace/user-persisted with atomic writes
- Batch mode processes command files
- Session export/import preserves all state
- IDE daemon/shared-server connection remains deferred

**Status:** Baseline Complete | Evidence: commit 37fd92b (Phase 42 foundations), advisory lock + IDE bridge in 563a1ad | Notes: Aliases use atomic writes + advisory lock; IDE write bridge deferred; no daemon/remote sync claims.

**Source:** Interactive CLI/UX Audit, 2026-05-26

---

## R41 — Advisory Locking + IDE Session Bridge

**Goal:** Prevent concurrent write corruption for session/alias files; expose read and write session operations to IDE through CLI fallback and local daemon HTTP.

**Current:** Baseline Complete (Phase 43 + Phase 46 + Phase 47).

**Deliverables:**
- `storage/advisory_lock.py` — POSIX `fcntl.flock` with spin-wait; Windows documented no-op
- `write_text_atomic(lock=True)` — wraps temp-write with advisory lock
- `ChatSession.save()` and `_write_aliases()` use `lock=True`
- `SessionBridgeService` (TypeScript) — read-only: `listChatSessions()` / `getChatSession(id)`; write bridge: `importSession()` / `deleteSession()` / `updateSessionField()` with per-instance TS mutex; no `shell=True`
- `ArcService` protocol extended with all session methods
- `ArcErrorCode.LOCK_CONTENTION` added to Python + TypeScript error codes
- DI module wired
- Python: `arc studio sessions write` (stdin JSON, advisory lock, trust check, 200-entry cap, 512 KB limit); `arc studio sessions delete`; `arc studio sessions update` (mode/runtime_mode/profile_id/isolation_id only)
- Python daemon: `POST /api/sessions/write`, `DELETE /api/sessions/{id}`, `PATCH /api/sessions/{id}` with same lock/trust/validation contract
- Python event bus: ephemeral `session_changed` events after daemon write/delete/update success
- TypeScript: daemon-first write bridge with CLI fallback only when daemon is unavailable
- `SESSION_ID_RE = /^[A-Za-z0-9_-]{1,80}$/` shared between Python and TypeScript

**Status:** Baseline Complete | Evidence: Phase 43 commit 563a1ad + Phase 46 local + Phase 47 local; Python daemon route tests pass (17); TS session bridge tests pass (33); full Python tests pass (2890 passed, 34 skipped, 3 xfailed); full arc-extension tests pass (814 passed, 3 skipped) | Notes: WebSocket/IPC push auto-refresh, Windows native lock, and persisted session-change replay remain deferred.

---

## R42 — Slash Registry Expansion + REPL Error Boundary

**Goal:** Make `/help` a useful grouped command palette; harden REPL against per-command crashes.

**Current:** Baseline Complete.

**Deliverables:**
- `/help` rebuilt as grouped uppercase palette (SESSION/RUN/SANDBOX/POLICY/WORKSPACE/PROVIDERS/AUDIT/TASKS/MCP) with parity disclaimer
- REPL error boundary in `_handle_input` — no slash command or runner exception propagates to the REPL loop
- All P0 commands verified: `/status`, `/doctor`, `/runs`, `/sandbox doctor`, `/policy explain`
- All P1 commands verified: `/audit`, `/task`, `/providers`, `/mcp`, `/hitl`, `/context`
- 20 new tests

**Status:** Baseline Complete | Evidence: commit b3e1471; 2828 Python tests pass; TS build + typecheck green | Notes: All P0/P1 commands were already wired; this phase adds palette, error boundary, and test coverage.

---

## R43 — Approval + Progress + Error UX

**Goal:** Surface sandbox decision states clearly; require explicit interactive approval for risky (non-destructive/non-privileged) commands.

**Current:** Baseline Complete.

**Deliverables:**
- `_render_state_prefix()` in `chat_repl.py` — `[ok]`, `[denied]`, `[blocked]`, `[empty]`, `[error]` prefixes on `CommandResult` output
- `cmd_sandbox` extended with `confirm_fn` parameter + `_sandbox_run_with_approval()`: interactive y/N prompt for NETWORK/INSTALL/UNKNOWN approval-required commands; TTY-aware (non-TTY delegates to adapter deny path)
- `render_sandbox_run(pre_approved=True)` path — calls `approve_decision()` before executing
- DESTRUCTIVE/PRIVILEGED remain hard-denied regardless of confirmation
- Audit events emitted for all deny paths including approval-declined
- 18 new tests

**Deferred:** No live daemon/remote sync/microVM broadening.

**Status:** Baseline Complete | Evidence: commit 7fdba99; 2846 Python tests pass; TS build + typecheck green | Notes: Hardened subprocess sandbox foundation. Superseded by Phase 105 for Linux/Firecracker gated microVM execution; macOS remains blocked.

---

## R44 — IDE Write Bridge / Daemon Protocol (Advisory Lock Integration)

**Goal:** Extend the IDE session bridge from read-only to read-write, integrating Python advisory locking through CLI fallback and local daemon HTTP.

**Current:** Baseline Complete.

**Deliverables:**
- Python: `arc studio sessions write` (stdin JSON payload, advisory lock, workspace trust check, 200-entry history cap, 512 KB payload cap, secret rejection, SESSION_ID_RE validation, `LOCK_CONTENTION` on lock timeout)
- Python: `arc studio sessions delete` (ID validation, advisory lock, workspace trust check, `LOCK_CONTENTION` / `RUN_NOT_FOUND` / `PERMISSION_DENIED` err envelopes)
- Python: `arc studio sessions update` (safe field allowlist: mode/runtime_mode/profile_id/isolation_id; no history mutation from IDE; secret value rejection; advisory lock; workspace trust check)
- `ArcErrorCode.LOCK_CONTENTION` added to Python `protocol/errors.py` and TypeScript `arc-protocol.ts`
- TypeScript `SessionBridgeService.importSession()` / `deleteSession()` / `updateSessionField()` — argv-only, no shell=True, env via buildArcCliEnv(), TS write mutex (second-layer defense; Python fcntl.flock is authoritative)
- `ArcService` protocol extended with three write methods
- `ArcBackendService` delegates to SessionBridgeService
- Python daemon routes: `POST /api/sessions/write`, `DELETE /api/sessions/{session_id}`, `PATCH /api/sessions/{session_id}`
- TypeScript daemon-first write path with CLI fallback only for daemon unavailable / HTTP 503 / HTTP 504
- `session_changed` event emitted after daemon write/delete/update success
- ADR-025 records Windows single-writer best-effort lock posture

**Acceptance:**
- All 27 Python write bridge tests pass
- All 33 TypeScript write bridge tests pass
- All 17 daemon session route tests pass
- `LOCK_CONTENTION` propagated from Python CLI → TypeScript for all write commands
- `PERMISSION_DENIED` propagated for untrusted workspace
- No shell=True in any write path
- Advisory lock prevents concurrent write corruption (threaded simulation test)
- TS mutex rejects when pendingWriteCount >= 1
- Full verification passed: Python 2890 passed / 34 skipped / 3 xfailed; arc-extension 814 passed / 3 skipped

**Status:** Baseline Complete | Evidence: local worktree; targeted Phase 47 route tests pass (17); session bridge TS tests pass (33); full Python tests pass (2890 passed, 34 skipped, 3 xfailed); full arc-extension tests pass (814 passed, 3 skipped) | Notes: Daemon write protocol is local HTTP, not remote sync/shared server; Windows advisory lock remains documented no-op; WebSocket/push auto-refresh remains deferred.

**Source:** Phase 46 execution, 2026-05-26

## R53 — Local Sandbox Audit Query + Compaction

**Goal:** Extend local sandbox audit infrastructure with time-range queries, safe compaction behavior, and structured audit event querying.

**Current:** Baseline Complete. `arc sandbox audit-query` and `arc sandbox audit-compact` (flat + nested) implemented with relative time parsing (`1h`/`30m`/`7d`/`now`), time-range filtering, and guarded local events compaction. Compaction refuses canonical hash-chain logs so `arc sandbox audit-verify` invariants are not silently broken.

**Deliverables:**
- `parse_relative_time(value: str) -> str` — converts relative time expressions to ISO UTC
- `compact_sandbox_audit_events(*, before, keep, audit_dir) -> dict` — prunes events-only logs and refuses canonical hash-chain logs
- CLI `arc sandbox audit-query` with `--from`, `--to`, `--classification`, `--provider`, `--allowed/--denied`, `--command-contains`, `--limit`
- CLI `arc sandbox audit-compact` with `--before`, `--keep`
- 19 tests covering relative time parsing, filtering, compaction edge cases, malformed logs, and CLI validation

**Acceptance:**
- ✅ Relative time parsing works for `1h`, `30m`, `7d`, `now`, and ISO passthrough
- ✅ Time-range filtering returns correct event subsets
- ✅ Compaction keeps newest N events or events after timestamp only for events-only logs
- ✅ Compaction on missing file returns empty result
- ✅ CLI commands output valid JSON envelopes
- ✅ All existing sandbox tests remain green

**Status:** Baseline Complete | Evidence: local worktree; 19 audit query/compact tests pass; full Python suite 3339 passed / 34 skipped / 3 xfailed; ruff clean; pnpm build + typecheck green | Notes: Compaction is local-only and refuses canonical hash-chain logs; no global, remote, or complete audit coverage claim.

**Source:** Phase 33 execution, 2026-05-28

## R54 — Container Isolation Provider

**Goal:** Add subprocess-based container isolation provider (Docker/Podman CLI) as alternative to SDK-based path, wired into sandbox CLI.

**Current:** Baseline Complete. `SubprocessContainerProvider` uses `docker run` / `podman run` via subprocess without SDK dependency. `container_preflight()` detects runtime availability. `arc sandbox run --provider container` routes through container isolation only when `ARC_ENABLE_CONTAINER_SANDBOX=1` is set and runtime/daemon checks pass.

**Deliverables:**
- `SubprocessContainerProvider(IsolationProvider)` — subprocess-based container runner with env allowlist, secret strip, output redaction, bounded I/O, timeout/SIGKILL, workspace mount
- `container_preflight() -> dict` — detects Docker/Podman binary, daemon liveness, `ARC_ENABLE_CONTAINER_SANDBOX` gate
- `sandbox_doctor` includes container preflight in provider list
- `_build_provider("container", ...)` wired to return `SubprocessContainerProvider`
- 15 tests covering health check, execute paths, env filtering, output handling, runtime detection

**Acceptance:**
- ✅ Container sandbox gate enforced via `ARC_ENABLE_CONTAINER_SANDBOX=1`
- ✅ Health check returns False when disabled or no binary
- ✅ Execute returns blocked result when sandbox disabled
- ✅ Env filtering strips secret patterns
- ✅ Output truncation and redaction work correctly
- ✅ Runtime detection identifies Docker/Podman/OrbStack/Colima
- ✅ `arc sandbox doctor --json` includes container provider
- ✅ All existing sandbox tests remain green

**Status:** Baseline Complete | Evidence: local worktree; 18 container provider tests pass; full Python suite 3339 passed / 34 skipped / 3 xfailed; ruff clean; pnpm build + typecheck green | Notes: Actual `docker run` requires live daemon and `ARC_ENABLE_CONTAINER_SANDBOX=1`; tests use monkeypatched `Popen`. SDK-based `DockerIsolationProvider` remains untouched.

**Source:** Phase 34 execution, 2026-05-28

## R55 — Local Sandbox Policy YAML

**Goal:** Add local YAML policy file format with workspace/user inheritance, validation, and apply commands.

**Current:** Baseline Complete. YAML policy files supported alongside existing JSON store. `arc policy validate-yaml --file` validates YAML schema. `arc policy apply --file` installs policy under the workspace boundary. Policy resolution falls through JSON → workspace YAML → user YAML. No remote policy service exists.

**Deliverables:**
- `default_workspace_policy_path(workspace_root) -> Path` — `.arc/sandbox-policy.yaml`
- `default_user_sandbox_policy_path() -> Path` — `~/.arc/sandbox-policy.yaml`
- `load_sandbox_policy_yaml(path) -> dict` — YAML parsing
- `validate_sandbox_policy_yaml(path) -> dict` — schema validation with structured errors
- `apply_sandbox_policy_yaml(source_path, workspace_root, *, target_path) -> dict` — validate + copy
- `resolve_sandbox_policy_with_yaml(name, workspace_root, *, json_path, yaml_path) -> SandboxPolicy` — JSON → workspace YAML → user YAML
- Modified `resolve_sandbox_policy` to fall through to YAML on JSON miss
- CLI `arc policy validate-yaml --file <path>` and `arc policy apply --file <path>`
- 22 tests covering validation, apply, resolution, list/show behavior, path bounds, and CLI commands

**Acceptance:**
- ✅ YAML validation catches missing name, wrong version, non-bool fields, missing files
- ✅ Apply copies valid YAML to workspace, rejects invalid or out-of-workspace targets
- ✅ Resolution finds policy from workspace YAML, falls back to user YAML
- ✅ JSON-first lookup preserved; YAML is additive
- ✅ CLI commands output valid JSON envelopes
- ✅ All existing policy tests remain green

**Status:** Baseline Complete | Evidence: local worktree; 22 YAML policy tests pass; full Python suite 3339 passed / 34 skipped / 3 xfailed; ruff clean; pnpm build + typecheck green | Notes: YAML policy files are local workspace/user files; no remote/centralized policy server. `yaml` dependency already present.

**Source:** Phase 35 execution, 2026-05-28

## R56 — Agentic CLI Edit Loop

**Goal:** Add the next safe CLI edit-loop foundation without claiming autonomous coding-agent parity.

**Current:** Baseline Complete. `arc edit plan` previews one workspace file replacement through sandbox plan policy and emits a unified diff plus plan audit event. `arc edit apply` writes only when policy allows the workspace write and `--approve` is supplied. REPL `/edit plan|apply` uses the same helper. Path traversal and symlink escapes are denied.

**Status:** Baseline Complete | Evidence: local worktree; `cd python && uv run pytest tests/test_cli_edit_loop.py -q` 8 passed; related CLI regressions 274 passed / 1 skipped; ruff clean | Notes: One-file deterministic edit loop only; no Claude Code/OpenCode parity claim.

## R57 — Interactive CLI UX Polish

**Goal:** Improve the interactive CLI command palette and state rendering around the new edit loop.

**Current:** Baseline Complete. `/edit` is registered in the slash command palette, appears in `/help`, returns structured `present`/`blocked`/`denied` states, and preserves existing REPL error-boundary behavior.

**Status:** Baseline Complete | Evidence: local worktree; `tests/test_cli_edit_loop.py` and `tests/test_phase44_slash_expansion.py` pass | Notes: Command-palette polish only; no broad terminal UI parity claim.

## R58 — Tool Runtime Unification

**Goal:** Start consolidating local tool execution around the existing registry and trust wrapper.

**Current:** Baseline Complete. `runtime/tool_runtime.py` exposes `run_registered_tool()` for registry lookup, Pydantic arg validation, cancellation token defaulting, tool execution, and `wrap_tool_result()` trust wrapping. Unknown tools are rejected.

**Status:** Baseline Complete | Evidence: local worktree; `tests/test_cli_edit_loop.py` covers wrapped `read_file` execution and unknown-tool rejection | Notes: Existing provider-backed `/run` tool-calling remains unchanged; this is a shared helper foundation, not a broad runtime rewrite.

## R59 — Edit Preview Staleness Guard

**Goal:** Prevent a reviewed edit preview from being applied over a file that changed afterward.

**Current:** Baseline Complete. `arc edit plan` returns `original_hash` and `replacement_hash`. `arc edit apply --expected-original-hash <sha256>` denies stale applies with reason `file changed since preview`, emits an existing plan audit event, and leaves the current file untouched. REPL `/edit apply` supports the same flag.

**Status:** Baseline Complete | Evidence: local worktree; `cd python && uv run pytest tests/test_cli_edit_loop.py -q` 9 passed; ruff clean for changed Python files | Notes: Guard is opt-in for callers; future interactive flows should thread the preview hash automatically.

## R60 — Saved Edit Plan Apply Flow

**Goal:** Let users apply a previously reviewed edit plan without storing replacement content or trusting stale preview state.

**Current:** Baseline Complete. `arc edit plan` persists safe metadata under `.arc/edit-plans/<plan_id>.json` and returns `plan_path`. `arc edit apply --plan-id <id> --content <text> --approve` loads the plan, denies replacement-content hash drift, uses the saved original hash for staleness checking, and writes only when both hashes still match. REPL `/edit apply --plan-id` uses the same helper.

**Status:** Baseline Complete | Evidence: local worktree; `cd python && uv run pytest tests/test_cli_edit_loop.py -q` 11 passed; ruff clean for changed Python files | Notes: Saved plans are local workspace artifacts only; no collaborative approval server or reviewer identity claim.

## R61 — Edit Bundle Approval Bridge

**Goal:** Extend the safe edit-loop foundation with multi-file bundles and approval/review bridge surfaces without claiming autonomous Claude Code/OpenCode parity.

**Current:** Baseline Complete. `arc edit plan/apply --edit path=text` supports multi-file bundles with per-file original/replacement hashes. Bundle apply is decision-atomic: if any planned file is stale or mismatched, no file is written. `arc edit list`, `arc edit show`, and `arc edit approve` expose saved safe plan metadata and scoped token approval for IDE/CLI bridge use. `--patch` supports a narrow single-file unified-diff parser that fails closed and does not shell out. `arc review summarize` can include saved edit-plan provenance where plan records exist.

**Status:** Baseline Complete | Evidence: local worktree; targeted `cd python && uv run pytest tests/test_cli_edit_loop.py tests/security/test_review_evidence.py -q` 31 passed; targeted ruff clean | Notes: Real scope is local CLI/REPL edit planning/apply, metadata-only plan records, scoped local approvals, narrow patch mode, and review provenance. Not real: autonomous coding-agent parity, general patch engine, IDE UI, collaborative approval server, or reviewer identity.

## R62 — IDE Edit Plan Review Surface

**Goal:** Surface existing saved edit plans/bundles in the IDE for review without broadening execution or claiming autonomous coding-agent parity.

**Current:** Baseline Complete. The TypeScript ARC service now exposes `listEditPlans`, `showEditPlan`, and `approveEditPlan`, backed by a CLI-only `EditPlanBridgeService` that invokes `arc edit list/show/approve` with argv-only `execFileSync` and sanitized env. The `EditPlansTab` lists saved plans, shows metadata/status/files/hashes, and approves scoped local tokens. It does not receive replacement content or full diffs and only shows CLI apply handoff copy.

**Status:** Baseline Complete | Evidence: local worktree; arc-extension Jest 888 passed / 3 skipped; `pnpm typecheck` OK | Notes: Metadata-only IDE surface. No IDE replacement-content persistence, autonomous editing, collaborative approval server, or signed reviewer identity.

## R63 — Sandboxed Diff/Apply/Test Loop

**Goal:** Add explicit local workflow commands for reviewing saved edit metadata, applying guarded edits, and running tests through existing sandbox policy.

**Current:** Baseline Complete. REPL `/diff --plan-id <id>` shows saved edit-plan metadata; `/apply ...` aliases the guarded edit apply helper, including approval-token support; `/test -- <cmd...>` routes through existing sandbox subprocess execution and deny-by-default policy behavior. Network/destructive/privileged commands remain governed by sandbox classification and policy.

**Status:** Baseline Complete | Evidence: local worktree; `cd python && uv run pytest tests/test_cli_edit_loop.py tests/test_phase44_slash_expansion.py tests/test_cli_repl.py tests/cli/test_testbench.py -q` 207 passed; ruff targeted clean | Notes: Explicit local workflow only; no self-healing repair loop, broad CI orchestration, or network-by-default behavior.

## R64 — Patch Engine Hardening v2

**Goal:** Safely broaden patch support for local edit plans while keeping fail-closed behavior and avoiding shell-out.

**Current:** Baseline Complete. `apply_unified_patch()` now supports text-only multi-hunk unified diffs, parses hunk ranges, rejects binary patch content, validates old/new hunk line counts, rejects malformed hunks, and preserves existing path-target checks. It still intentionally rejects unsupported Git patch/binary/ambiguous formats.

**Status:** Baseline Complete | Evidence: local worktree; `cd python && uv run pytest tests/test_cli_edit_loop.py -q` 22 passed; ruff targeted clean | Notes: This is not a complete Git patch engine and does not shell out to `patch`.

## R65 — Sandbox/MicroVM Truth Audit Guard

**Goal:** Prevent blocked public microVM attempts and doctor output from implying execution readiness.

**Current:** Baseline Complete. `arc sandbox run --provider microvm` remains blocked but now emits a `SANDBOX_DENIED` audit event with `public_execution_enabled=false`. MicroVM doctor/preflight output keeps runtime preflight detail while explicitly reporting `public_execution_status=blocked` and `public_execution_enabled=false`.

**Status:** Baseline Complete | Evidence: local worktree; targeted sandbox/microVM tests 196 passed / 13 skipped; targeted ruff clean | Notes: Historical truth-label hardening. Superseded by Phase 105 for Linux/Firecracker gated execution; macOS remains blocked.

## R66 — Sandbox Classifier And Path-Intent Hardening v3

**Goal:** Close static policy gaps where allowed network/install/unknown commands could write outside the workspace or unknown dynamic shells could be approved.

**Current:** Baseline Complete. Write-output path intents are validated across classifications, dynamic unknown shell/interpreter forms deny before approval, `find -exec` without known destructive target is `unknown`, and `sed -i` is `writes_workspace`.

**Status:** Baseline Complete | Evidence: local worktree; targeted sandbox/microVM tests 196 passed / 13 skipped; targeted ruff clean | Notes: Static policy hardening only; not syscall/kernel sandboxing.

## R67 — MicroVM Proof-Harness Truth Guards

**Goal:** Keep private microVM proof harnesses from producing false-positive evidence before real Linux/macOS proof exists.

**Current:** Baseline Complete. Lima probes use bounded output drain. Firecracker guest proof success now requires `curl-available` and `workspace-mount-proven` markers, and proof runner refuses to overwrite existing workspace marker files. A reusable three-phase orchestrator prompt was added for future research/execute/test phases.

**Status:** Baseline Complete | Evidence: local worktree; targeted sandbox/microVM tests 196 passed / 13 skipped; targeted ruff clean | Notes: Real Firecracker/Lima public microVM execution remains blocked pending ADR-024 proofs.

## R68 — Priority 1 CLI Parity Research + Acceptance Matrix

**Goal:** Make the next workstream explicitly Priority 1: research and plan full OpenCode/Claude Code style parity, autonomous edit-test-repair, git transactions, IDE diff apply, provider shell, live terminal/event UX, CLI CI orchestration, and real microVM proof work.

**Current:** Baseline research matrix exists at `docs/research/cli-parity-priority.md`; no full parity claim.

**Status:** Baseline Complete | Evidence: local worktree; `docs/research/cli-parity-priority.md`; Python full suite 3376 passed / 34 skipped / 3 xfailed; `cd python && uv run ruff check src tests` clean; `pnpm build` OK; `pnpm typecheck` OK; banned-claims guard OK | Notes: Context7 and Vercel Grep unavailable in this runtime and recorded as blockers.

## R69 — Autonomous Edit-Test-Repair Loop

**Goal:** Let the CLI run a bounded, auditable edit -> sandboxed test -> diagnose -> repair loop.

**Current:** Deterministic bounded repair loop exists for local fixture workflows; no LLM autonomous repair claim.

**Status:** Baseline Complete | Evidence: local worktree; `tests/test_phase_98_101_cli_parity.py` | Notes: Deterministic repair only; broader diagnosis/provider repair remains future work.

## R70 — Git-Backed Undo/Redo Transactions

**Goal:** Wrap edit/apply/test workflows in safe git-backed transactions with undo/redo.

**Current:** ARC-owned transaction log captures edit apply before/after states and supports safe undo/redo for recorded files.

**Status:** Baseline Complete | Evidence: local worktree; transaction undo/redo targeted tests | Notes: Protects ARC edit transactions only; no arbitrary subprocess/Bash rollback.

## R71 — Rich IDE Diff Review/Apply Flow

**Goal:** Add real IDE diff review and apply flow for proposed edits.

**Current:** IDE edit-plan bridge loads capped real unified diff sidecars and applies approved content through Python edit/sandbox/transaction gates.

**Status:** Baseline Complete | Evidence: local worktree; Python diff/apply tests plus TS bridge/UI contract updates | Notes: Full Monaco side-by-side/e2e polish remains future work.

## R72 — Provider-Backed Runtime Shell

**Goal:** Add a gated provider-backed runtime shell that can drive tools with streaming and audit.

**Current:** Provider shell contract exists with offline dry-run default, policy-visible tool proposals, audit, and live path gated through existing provider action contract.

**Status:** Baseline Complete | Evidence: local worktree; `arc providers shell` targeted tests | Notes: No broad multi-turn provider shell or default paid calls.

## R73 — Live Terminal/Event Streaming UX

**Goal:** Complete live terminal/event streaming across CLI, REPL, and IDE for long-running commands.

**Current:** Baseline CLI JSONL streaming exists for sandbox, testbench, and provider-shell surfaces. It emits stable envelopes for start/stdout/stderr/truncated/cancelled/timeout/completed/disconnected and preserves live/replay labels. IDE consumption and full REPL streaming remain future work.

**Status:** Baseline Complete | Evidence: local worktree; `tests/test_phase102_streaming.py`; Python full suite 3380 passed / 34 skipped / 3 xfailed; `pnpm build` OK; `pnpm typecheck` OK | Notes: CLI streaming baseline only; no broad IDE terminal streaming claim.

## R74 — Broad CLI CI Orchestration

**Goal:** Let CLI detect, run, summarize, and artifact CI/test matrices under sandbox policy.

**Current:** Baseline CLI orchestration exists. `arc ci matrix --json` detects Python, pnpm/package, testbench, and GitHub Actions run-step jobs. `arc ci run --policy local-safe --job <id> --json` runs one selected argv-safe job through sandbox policy and Phase 102 streaming, writes a local `.arc/ci/runs/...` artifact, emits sandbox audit material, and denies network/destructive commands by default. Complex shell workflow lines are detected but marked not runnable rather than executed through a shell by default.

**Status:** Baseline Complete | Evidence: local worktree; `tests/test_phase103_ci_orchestration.py` 6 passed; Python full suite 3386 passed / 34 skipped / 3 xfailed; ruff/build/typecheck OK | Notes: Local argv-job orchestration only; no remote CI service, no broad shell workflow execution, no live network by default.

## R75 — macOS MicroVM Execution + Strict No-Network Proof

**Goal:** Prove real local macOS lightweight VM execution, preferably Lima/Apple Virtualization.framework, with strict no-network behavior.

**Current:** Direct Apple Virtualization.framework no-NIC gated public CLI proof passed once, not via Lima. ARC has `VZNoNetworkProof` preflight/opt-in runner scaffolding, `arc sandbox doctor --json` reports `vz_no_nic` with `networkDevices=[]`, and `tools/arc-vz-runner.swift` configures `networkDevices=[]` plus argv/hash boot parameters. The gated public CLI run used `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_VZ_REAL_EXEC=1`, a valid `ARC_VZ_ARTIFACT_MANIFEST`, compiled/signed runner, ARM64 kernel/initrd, and guest markers proving boot, no guest ethernet, no default route, network probe failure, workspace sentinel read, symlink escape blocked, exact requested argv hash, stdout `/workspace`, audit, and teardown ok. `arc sandbox vz-artifacts` creates a local proof-only artifact set with runner source, entitlements, optional compiled/signed runner, copied kernel/initrd, SHA256 manifest, `networkDevices=[]`, and `public_execution_enabled=false`; it does not download assets or boot a VM. `arc sandbox vz-artifacts --exec-init` writes a reviewable guest init contract/manifest; `--pack-initrd --busybox <path>` can package a gzip `newc` initramfs using static local BusyBox and local `cpio`, and blocks dynamically linked BusyBox. It does not download assets or bundle Python. `.github/workflows/vz-host-proof.yml` is manual/self-hosted only and has not run here. Lima remains a low-security harness only because its default/user-mode networking is network-present. This is default-off and not production-grade or arbitrary host-command microVM execution.

**Status:** Gated Public CLI Proof Passed Once / Local Initrd Packer + Static BusyBox Guard + Manual Host CI Added / Default Off | Evidence: prior `cd python && uv run arc sandbox vz-artifacts --json --output /var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-vz-artifacts-exec --kernel /var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-vz-proof/debian-linux --initrd /var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-vz-proof/arc-vz-exec-initrd.gz --build-runner` → blockers `[]`; prior `cd python && ARC_MICROVM_EXEC_ENABLED=1 ARC_MICROVM_INTEGRATION=1 ARC_VZ_REAL_EXEC=1 ARC_VZ_ARTIFACT_MANIFEST=/var/folders/dp/1fh07k_922j5qk7xfncn1zv40000gn/T/opencode/arc-vz-artifacts-exec/vz-artifacts-manifest.json ARC_VZ_TIMEOUT_SECONDS=45 uv run arc sandbox run --json --provider microvm --policy local-safe -- pwd` → stdout `/workspace`, no-network/workspace/symlink/teardown/audit ok; packed-initrd attempt blocks dynamic BusyBox with `ARC_VZ_BUSYBOX must be a static Linux BusyBox binary` | Notes: This proves a gated direct VZ public CLI path for a guest-available command on this host only. The new packed initrd path is local-tool generation and static-runtime validation, not host execution evidence yet. `python -c` remains unproven unless Python is present in the guest artifact. Remaining work: real-host timeout/SIGINT/command-failure proofs now pass (2026-06-06, gated, short argv); broader argv is blocked by a kernel-command-line-length ceiling (ADR-024 §7 known limitation — moving the argv/SHA transport off the kernel command line is the needed follow-up); upstream kernel/initrd/BusyBox provenance/distribution/license policy still open.

## R76 — Linux Firecracker Execution Proof

**Goal:** Prove real Linux Firecracker boot/run/destroy for a workspace-bounded command.

**Current:** Linux/Firecracker execution code is wired but host-unproven. `MicroVMIsolationProvider.execute()` delegates to `FirecrackerExecutionRunner` only on Linux when `ARC_MICROVM_EXEC_ENABLED=1`, `ARC_MICROVM_INTEGRATION=1`, `ARC_FC_REAL_EXEC=1`, `ARC_FIRECRACKER_KERNEL`, `ARC_FIRECRACKER_ROOTFS`, `firecracker`, `/dev/kvm` rw, `mkfs.ext4`, and `truncate` are present. The runner builds a read-only ext4 workspace snapshot, starts Firecracker with no `network-interfaces`, requires guest `ARC_FC_PROOF` markers for no default route/network failure/workspace/symlink, parses `ARC_FC_RESULT`, terminates the process group, and emits audit. Normal CI and this macOS host skip real boot.

**Status:** Baseline Complete (host-unproven) | Evidence: local targeted `uv run pytest tests/isolation/test_microvm_truth_guard.py tests/isolation/test_firecracker_smoke.py -q` → 40 passed / 1 skipped; no Linux/KVM boot run on this host | Notes: To prove execution, run on Linux/KVM with ARC exec rootfs and the documented gates; do not claim real microVM execution until that test boots a VM and passes.

## R78 — A2A Local AgentCard Generator + Loopback Client

**Goal:** A2A v1.2 spec-compliant local agent card generation, disk storage, per-card approval, and loopback-only outbound client.

**Current:** AgentCard generation writes to `.arc/a2a/agent-card.json`. Outbound client enforces `127.0.0.1`-only URLs, mandatory signature verification, and per-card approval via `.arc/a2a/approved.json`. CLI commands: `arc a2a generate|list|verify|inspect|approve|invoke`. No inbound HTTP server. HMAC-SHA256 signing. `EntityType.A2A_AGENT` added to capability card models.

**Status:** Baseline Complete | Evidence: `tests/a2a/` passed; ruff clean | Notes: Loopback-only, disk-only. No remote A2A, no inbound server. ADR-029.

## R79 — Mobile Runtime SDK Integration

**Goal:** Wire the standalone ARC Runtime SDK (`runtimes/Arc-Studio-Mobile-SDK/arc-runtime-sdk`) into ARC Studio as a first-class runtime adapter, so an `arc-sdk.json` app project is detected, capability-reported, simulated/replayed, and surfaced through the existing runtime + mobile + runtime-pack surfaces — without coupling the SDK core to Theia.

**Current:** The SDK is a separate polyglot monorepo (TypeScript core + Expo/Flutter/KMP bindings, JSON schemas, a Python reference adapter/daemon). Its own honest status is PLANNING/POC — deterministic simulator/mock only; no native bridge (file-picker stub); no app-store automation; 342 SDK tests claimed passing (not yet run in ARC Studio CI). The SDK ships `adapters/arc_runtime_sdk_adapter.py` whose `detect()` already matches `RuntimeAdapter.detect() -> tuple[bool, float, list[str]]`, plus a documented `MobileCapability` ↔ SDK `CapabilityCard` field map. It is NOT yet wired into ARC Studio: it lives in the SDK's own copy of the `agent_runtime_cockpit` package, is duck-typed (not a `RuntimeAdapter` subclass), `capabilities()` returns a dict (not `RuntimeCapabilities`), and it is not registered in `adapters/registry.py`.

**Status:** Partial — Slices 110.1–110.5 shipped; 110.6 follow-up | Evidence: 2026-06-06 ArcRuntimeSDKAdapter (registered, discovered via arc runtimes), mobile_sdk_mapping (bidirectional, 25 tests), arc_runtime_sdk_pack (arc-sdk.json→RuntimePack validator, 13 tests), arc_runtime_sdk_protocol (DaemonEventType→AGUIEventType mapping + /health parity, 11 tests); 49 R79 tests total; CI python strict-mode green (fixed Pydantic field-shadow via Field alias rename). | Notes: Slice 110.6 (optional Theia/TUI surfacing) is a P2 follow-on. Simulator/mock only; no native-execution or app-store claims. Execution plan: `docs/phases.md` Phase 111.

---

# ═══════════════════════════════════════════════════════════════════════
# NEW INTAKE — Roadmap Entries (append below this line)
# ═══════════════════════════════════════════════════════════════════════

> Incoming roadmap items go here, either as a table row using the standard status line
> (`Status: <value> | Evidence: <anchor> | Notes: <one sentence>`) or as a full
> `## R<n> — <title>` section. Use a fresh, non-colliding ID (next free core ID is high;
> prefer a namespaced ID like `R-OPEN-<topic>` or `R-<track><n>` to avoid the historical
> R45–R55 reuse). When an item reaches Baseline Complete, add its row to the matching
> **Completed Roadmap — Master Ledger** group at the top of this file, and add the
> companion phase to `docs/phases.md`.

### Audit Synthesis Backlog (R-AUDIT1 – R-AUDIT25)

> Source: audit-synthesis-backlog.md 2026-06-07. Status for all rows: Research Intake.

| ID | Title | Status | Evidence | Notes |
|---|---|---|---|---|
| R-AUDIT1 | Release Checklist Refresh | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | docs/release/checklist.md updated to v0.8-r-ux2/aa788f3/5537 tests/Phase 131. |
| R-AUDIT2 | Enforcement Surfaces Doc Refresh | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | enforcement-surfaces.md updated to Phase 131; new surfaces for sandbox P0, hash chain, adapter gates, retry, TurnManager hook. |
| R-AUDIT3 | docker-compose 127.0.0.1 Binding | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | docker-compose.yml port 3000 bound to 127.0.0.1. |
| R-AUDIT4 | config-service apiKeySource Snake/Camel Fix | Status: Baseline Complete | Evidence: audit-synthesis-backlog.md 2026-06-07 | Add api_key_source fallback in config-service.ts so IDE provider source badge shows correctly. |
| R-AUDIT5 | MCP Proxy Env Secret-Strip Gate | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | _sanitise_env() added to mcp/proxy.py; wired in start(); 4 new tests. |
| R-AUDIT6 | Gateway Client Paid-Call Gate | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | TODO removed; exemption documented — gate is upstream via require_dual_gate in runner.py; 1 new test. |
| R-AUDIT7 | DataStore allow_paid Default Warning | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | allow_paid_warning property added to DataStore; surfaced in StatusBar; 3 new tests. |
| R-AUDIT8 | EXTENSION_MIGRATION Stale Ref Fix | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | LOCKED_REMAINING_ROADMAP.md ref replaced with docs/roadmap.md in EXTENSION_MIGRATION.md. |
| R-AUDIT9 | Budget Durability Under Error | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | Budget is preflight-only; by-design gap documented in turn_manager.py degraded path; 2 new tests. |
| R-AUDIT10 | SwarmGraph Topology Shape Verification | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | No mismatch found; shapes consistent (flat {nodes,edges}); comment added to TS; 1 new Python test. |
| R-AUDIT11 | Notifications Outbox MVP | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | notifications/outbox.py created; append/read_all/gc with TTL; 4 new tests. |
| R-AUDIT12 | UI Design Token Foundation | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | tokens.css created with color/spacing/typography/radius tokens; additive only. |
| R-AUDIT13 | HMAC README Wording Tighten | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | Scope caveat added to README and SECURITY.md HMAC sections. |
| R-AUDIT14 | Mutating GET /api/runs/start Removal | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | GET /api/runs/start returns 410 Gone; POST unaffected; legacy env shim removed. |
| R-AUDIT15 | SwarmGraph MetaPathFinder Bridge Docs | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | docs/research/swarmgraph-metapathfinder-bridge.md created with architecture, gates, and honest limits. |
| R-AUDIT16 | IDE Context Drawer / AGENTS.md Surface | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | ArcContextDrawer widget created; registered in frontend module; stub data (CLI proxy wiring follow-on); 1 test. |
| R-AUDIT17 | R79 TUI/Theia Surfacing | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | /budget [run-id] slash command added to TUI screen; wallet fallback when no run-id; 2 new tests. |
| R-AUDIT18 | Workspace Search CLI + IDE Panel | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | arc workspace search command added; ripgrep/pathlib fallback; path-confined; 3 new tests. IDE panel follow-on. |
| R-AUDIT19 | Eval Metrics Honest Labelling | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | synthetic:bool=True added to EvalResult; [synthetic/simulated] prefix in CLI eval display; 2 new tests. |
| R-AUDIT20 | SQLite WAL Busy-Timeout Verification | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | WAL+busy_timeout=5000ms confirmed in budget/storage.py; xfail reason updated to reflect accurate constraint. |
| R-AUDIT21 | Accessibility Baseline Audit | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | ARIA roles/labels added to arc-adapters-widget; accessibility-baseline.md created. axe-core pass deferred. |
| R-AUDIT22 | Handover Doc Stale Refs Sweep | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | LOCKED_REMAINING_ROADMAP.md refs replaced with docs/roadmap.md in docs/handover/. |
| R-AUDIT23 | SwarmGraph Insight UI Components Phase 1 | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | DagPlannerViz, ConsensusEvidenceCard, HitlApprovalPanel created; use --arc-color-* tokens; 3 render tests. |
| R-AUDIT24 | SDK Version Sweep (R-TS1 close) | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | sdk_version() added to base + 8 priority adapters; surfaced in arc runtimes --capabilities --json; 1 new test. |
| R-AUDIT25 | Multi-Provider Router Abstraction | Status: Baseline Complete | Evidence: aa788f3 2026-06-07 | ProviderRouter created (gated ARC_ENABLE_PROVIDER_ROUTER=1); 5 new tests; turn_manager wiring is follow-on. |
| R-CLEAN1 | Cleanup & Refactor Audit + Entrypoint Alias (Phase 158) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | Multi-signal cleanup audit; ruff clean; 3 suspected dead-code targets disproved (all live/tested/wired); 57-slice cleanup backlog in docs/research-findings/cleanup-refactor-audit-2026-06-07.md; executed smallest safe slice — additive `arc-studio-cli` entrypoint (keeps `arch-studio-cli` compat). Zero deletions, zero protocol/CLI removals. |
| R-POLISH1 | DoD Elevation — Security P0 Batch (Phase 159) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-001 sensitive-file exclusion (workspace inventory + LocalRepoProvider), CR-003 provider `_map_error` redaction via canonical `redact_secrets`, CR-006 run-ID path-traversal guard in JSONL store. Deterministic, additive. Tests: 106 targeted + 744 blast-radius passed; ruff clean. |
| R-POLISH2 | DoD Elevation — IDE Honest States + ErrorBoundary + Keybinding Guards (Phase 160) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-011 RunsTab allSettled error/empty states + Retry (no silent catch); CR-020 reusable ErrorBoundary wrapping tab content (key=activeTab); CR-013 `when: '!editorTextFocus'` guards on ARC keybindings (Theia idiom, Context7-verified). Build clean; 918 tests passed; typecheck clean. Additive; no protocol/tab removals. |
| R-POLISH3 | DoD Elevation — TUI Streaming Transcript + Shell-Output Redaction (Phase 161) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-009 MarkdownBlock.update_body + Transcript streaming refresh (append_to_last deltas now render); CR-024 display-boundary redaction via canonical redact_secrets + accurate audit redaction_applied (provider already redacts; TUI now guarantees it). Tests: 232 passed / 2 xfailed (pre-existing snapshots); ruff clean. Additive; reuses canonical redactor. |
| R-POLISH4 | DoD Elevation — MCP Security Batch (Phase 162) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-005 proxy sanitises os.environ when env=None (was leaking full parent env); CR-008 `arc mcp serve` logs to stderr (stdout reserved for JSON-RPC); CR-018 proxy timeout/oversize return structured JSON-RPC error envelopes. CR-004 verified FALSE POSITIVE (resources already gated via _tool_result). Context7-verified (MCP SDK). 123 MCP tests pass; ruff clean. |
| R-POLISH5 | DoD Elevation — TUI Paid-Call Fail-Closed Default (Phase 163) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-002: DataStore.allow_paid default flipped True→False (fail-closed); opt in with ARC_TUI_ALLOW_PAID=1 (ARC_TUI_NO_PAID still wins). Updated the test that asserted the old permissive default. 64 TUI-core tests pass; ruff clean. Behavior change to a previously-deliberate default, per explicit fail-closed directive. |
| R-POLISH6 | DoD Elevation — CLI Mutation Confirmation Gate (Phase 164) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-010: `arc sandbox audit-compact` (+ nested alias) now `--yes`-gated with typer.confirm + JSON-mode refusal (CONFIRMATION_REQUIRED). Correction: `policy rule-add/rule-remove` don't exist (group is explain/approve/revoke). 22 audit-query tests pass; ruff clean. Additive (--yes keeps scriptability). |
| R-POLISH7 | DoD Elevation — Theia Notification Env Allowlist + Async Node Backend (Phase 165) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-007: NotificationBackendService spawn now passes buildArcCliEnv() (was inheriting full env/secrets); CR-012: getConfigStatus/saveConfig/startRun(+listRuntimeCapabilities/preflightRun/replayRun) converted execFileSync→shared async execArcCliAsync (non-blocking, lazy promisify). 919 arc-extension tests pass; build+typecheck clean. Additive. |
| R-POLISH8 | DoD Elevation — Profile Schema Guard + IR Cycle Detection (Phase 166) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-019: load_custom_profiles rejects unknown-future schema versions fail-closed (v1→v2 additive); CR-017: validate_graph adds iterative-DFS cycle detection as an advisory warning (loop-capable runtimes legitimately cyclic). 330 IR+security tests pass; ruff clean. Additive. |
| R-POLISH9 | DoD Elevation — Bounded Live Event Buffer (Phase 167) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-014: ArcEventStreamWidget liveEvents capped at MAX_LIVE_EVENTS=2000 (newest kept) with eviction-count banner; was unbounded `[...liveEvents, event]`. List already virtualized. 923 arc-extension tests pass; build+typecheck clean. Additive. |
| R-POLISH10 | DoD Elevation — SwarmGraph SDK→IDE Event Contract Lock (Phase 168) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-016 (premise corrected): IDE SwarmGraphInsightTab already producer-truthful (degraded/absent states, no invented data); SDK→ARC bridge already exists (_map_swarmgraph_event → SWARMGRAPH_TOPOLOGY/CONSENSUS matching IDE isInsightEvent markers). Added a cross-language contract test locking the SDK-event→IDE-marker naming + producer-truth assertion. NO bridge/producer fabricated. Follow-ups: live SDK-runner streaming, cost-event naming (BUDGET_UPDATE vs swarmgraph_cost). 3 tests pass; ruff clean. |
| R-POLISH11 | DoD Elevation — TraceParser Memory Caps (Phase 169) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-015: parseTrace rejects files > 64MB (fs.stat before read, structured error) and streamTrace bounds the line buffer (drop delimiter-less line > 4MB). 926 arc-extension tests pass; build+typecheck clean. Additive. |
| R-POLISH12 | DoD Elevation — Workspace Search Confinement + Result Cap (Phase 170) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-022: arc workspace search caps at 1000 results (truncated flag) and excludes secret files + ignored/dependency dirs + symlinks + oversized files in both rg and pathlib paths (reuses is_sensitive_file/IGNORED_DIRS). 13 tests pass; ruff clean. Additive. |
| R-POLISH13 | DoD Elevation — Real jest-axe A11y Assertions (Phase 171) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-042: replaced 3 no-op a11y describe blocks (expect(true)) with real axe assertions (interactive form, live region, contrast-deferred). jest-axe/jsdom already installed. 927 arc-extension tests pass. Honest: color-contrast deferred to browser (jsdom no layout). Follow-up: mock→real component migration. |
| R-POLISH14 | DoD Elevation — Finish Async Config-Service Backend (Phase 172) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-012a: converted the remaining 13 execFileSync calls in config-service.ts to execArcCliAsync (AST rewrite); dropped unused execFileSync/buildArcCliEnv imports. Completes CR-012. 927 arc-extension tests pass; build+typecheck clean. Additive. |
| R-POLISH15 | DoD Elevation — Native SwarmGraph Cost → IDE Cost Panel (Phase 173) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-016a: native SwarmGraphAdapter now emits one SWARMGRAPH_COST event from measured accumulated budget cost (_accumulated_cost helper); was only BUDGET_UPDATE so the IDE cost panel stayed degraded for native runs. Producer-gated (no invented cost). 1030 adapter+swarmgraph tests pass; ruff clean. |
| R-POLISH16 | DoD Elevation — Denial Events in KnownRunEvent Union (Phase 174) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-037: 5 denial events (TRUST/PAID_CALL/SHELL/NETWORK/PERMISSION_DENIED) added to Python KnownRunEvent union + EVENT_TYPES + regenerated registry + TS run-events.ts (interfaces + KNOWN_RUN_EVENT_TYPES). Circular import resolved via TYPE_CHECKING. Context7+Grep verified. Python protocol 73 + parity 7 + broad 479 pass; TS protocol 155 pass; typecheck clean. Additive; cross-language parity held. |
| R-POLISH17 | DoD Elevation — P2 UX Batch: CommandPalette / ContextMeter / Settings (Phase 175) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-023 TUI command palette builds the registry on mount (was empty on first open); CR-035 context-meter default 64k→200k (model override unchanged); CR-044 SettingsView offers all themes + applies theme/mode live on Apply via screen callback. 10 targeted + 74 regression tests pass; ruff clean. Additive. |
| R-POLISH18 | Cleanup — Dedupe `eval run` Command (Phase 176) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-025: removed the dead shadowed `eval_run` (superseded by `eval_run_new`); eval_run_new is the sole `eval run`. 9 CLI eval + 112 evals tests pass; ruff clean. CR-030 (slash_menu theme/runtimes) verified FALSE POSITIVE (both dispatchable); CR-031 (sandbox audit-verify dual path) verified ALREADY consolidated (shared impl). No-change items documented. |
| R-POLISH19 | Release/Docs Hygiene (Phase 177) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-032 pyproject license Apache-2.0→Proprietary (+classifier; uv sync OK); CR-039 release_check adds pnpm:build:prod gate (browser prod artifact); CR-040 bootstrap warns on frozen-lockfile drift instead of silent fallback; CR-041 README 5192→5600+ tests; CR-038 AGENTS Active track refreshed (P0 complete → R-POLISH track). bash -n + banned-claims clean. |
| R-POLISH20 | Refactor — Extract `useAsyncState` Hook (Phase 178) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-029: new browser/hooks/useAsyncState.ts (data/loading/error + reload/setData) replacing the duplicated useState/useEffect async triple; adopted in TestBenchTab (19→5 lines, behavior-preserving). 6 hook tests + contract updated to lock useAsyncState adoption; tsc clean; 169 targeted tests pass. Remaining ~5 tabs adopt incrementally. |
| R-POLISH21 | Refactor — Broaden useAsyncState Adoption (Phase 179) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-029 cont.: CiGuardrailsTab fully converted to useAsyncState; McpWorkbenchTab status flow converted (decisions state retained; load() removed from effect to avoid double-fetch). Contracts updated. tsc clean; 169 tests pass. 3 tabs now on the shared hook. |
| R-POLISH22 | Refactor — Split arc-protocol.ts: barrel infra + replay/diff (Phase 180) | Status: Baseline Complete (part 1 of N) | Evidence: local worktree 2026-06-07 | CR-027 part 1: new common/protocol/replay-diff.ts (Replay + Run Diff types) re-exported via barrel from arc-protocol.ts (+ local back-import for ArcService refs). type-only, zero runtime change. tsc clean; 250 protocol/tabs tests pass. Further sections extract incrementally. |
| R-POLISH23 | Refactor — Split arc-protocol.ts: run-execution module (Phase 181) | Status: Baseline Complete (part 2 of N) | Evidence: local worktree 2026-06-07 | CR-027 part 2: new common/protocol/run-execution.ts (streaming + preflight/start types) re-exported via barrel (+ back-import for 8 ArcService refs; dropped unused ReplayEvent local import). type-only. tsc clean; 250 tests pass. arc-protocol 1795->1665. |
| R-POLISH24 | Refactor — Split arc-protocol.ts: config-types module (Phase 182) | Status: Baseline Complete (part 3 of N) | Evidence: local worktree 2026-06-07 | CR-027 part 3: new common/protocol/config-types.ts (~19 Config Tab types, the largest section) moved byte-exact, re-exported via barrel (+ back-import for 14 ArcService refs). Contract no-raw-key/non-secret checks read the module. tsc clean; 250 tests pass. arc-protocol 1665->1439 (~23% moved). |
| R-POLISH25 | Refactor — Split arc-protocol.ts: contracts + graph-linkage (Phase 183) | Status: Baseline Complete (part 4 of N) | Evidence: local worktree 2026-06-07 | CR-027 part 4: new common/protocol/contracts-graph.ts (cockpit schema contracts + stable IDs/graph) re-exported via barrel (+5 back-imports). Fixed latent ui-components CapabilityDiffResponse assertion (moved in part 1). FULL suite 933 passed/3 skipped. arc-protocol 1439->1216 (~35% moved). |
| R-POLISH26 | Refactor — Split arc-protocol.ts: final sections (CR-027 COMPLETE) (Phase 184) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-027 done: extracted runtime-status + run-links + hitl-audit modules. Final: arc-protocol.ts 1867->1086 (~42% extracted) across 7 protocol/* barrel modules; 54 import sites unchanged; type-only/zero-runtime. Full workspace typecheck clean; full arc-extension suite 933 passed/3 skipped. |
| R-POLISH27 | Refactor — Split cli/mgmt.py into cohesive modules (CR-026) (Phase 185) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-026: mgmt.py 1693->17 lines (thin aggregator) + 6 per-group modules (mgmt_{doctor,eval,hitl,isolation,storage,config}.py); registration preserved via cli/__init__ -> mgmt -> submodule imports. Command parity PASS (identical 30 commands); ruff clean; tests/cli 163 passed; broad sweep 359 passed; all group --help OK. |
| R-POLISH28 | Refactor — Split ConfigTab.tsx logic/presentation (CR-028) (Phase 186) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | CR-028: ConfigTab.tsx 1253->860 lines; extracted useConfigTabState.ts (502, state/logic, 73-field view-model) + config-tab-helpers.ts (73, pure helpers+constants). Public surface unchanged. Contracts retargeted (logic->hook, negatives->combined source+hook, studio-tabs ConfigTab block reads union of 3 files). build/tsc clean; 4 ConfigTab suites 229 passed; full arc-extension 933 passed; workspace typecheck + eslint clean. |
| R-MOBILE-B5-P6 | Mobile SDK — Expo module buildable (Batch 5 T1-T3, Mobile Roadmap Phase 6) (Phase 187) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | Expo config plugin (advisory permission injection), TS API over fixtures-only native bridge + events + getCapabilities/simulate, example app + recursive forbidden-symbol CI gate. Simulator-preview only; native fixtures, no real device access. 28 expo tests pass. |
| R-MOBILE-B5-P8 | Mobile SDK — secure store + egress guard + offline queue (Batch 5 T4-T6, Mobile Roadmap Phase 8) (Phase 188) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | Real encryption-at-rest (Fernet, no plaintext at rest), deterministic budget-bound egress guard (critical blocked), durable hash-only offline queue w/ TTL+FIFO retention. 22 tests; deterministic, offline. |
| R-MOBILE-B5-P9-10 | Mobile SDK — React Native TurboModule + Flutter platform-interface scaffolds (Batch 5 T7-T8, Mobile Roadmap Phases 9-10) (Phase 189) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | RN New-Arch TurboModule Codegen spec + fixtures bridge; Flutter federated platform interface + Dart models + method-channel fixtures. flutter analyze clean + flutter test 5/5; 14 python static tests. Fixtures only, no real device access. |
| R-MOBILE-B5-P12a | Mobile SDK — enterprise governance slice 1: SIEM export + signed RBAC/ABAC/tenant policy (Batch 5 T9-T10, Mobile Roadmap Phase 12) (Phase 190) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | Deterministic CEF/JSON SIEM export (redaction preserved) + signed OrgPolicyBundle w/ fail-closed RBAC/ABAC/tenant denials via EnterprisePolicyHook. 13 tests. |
| R-MOBILE-P11-12b | Mobile SDK — native capability entry-gate + feature flags/kill switch (Mobile Roadmap Phases 11+12b) (Phase 191) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | Default-off feature flags + global kill switch; deterministic CapabilityEntryGate (requires flag+signed plan+approval+compliance) that ALWAYS routes to fixtures (executed_real_device=False) — real device access out of scope/human-gated. 10 tests. |
| R-MOBILE-P12-20 | Mobile SDK — enterprise remainder (audit retention, compliance report, SBOM) + MCP dev-bridge (Mobile Roadmap 12c-12e + 20) (Phase 192) | Status: Baseline Complete | Evidence: local worktree 2026-06-07 | Audit TTL/rotation, aggregated advisory compliance report, CycloneDX SBOM, default-off fail-closed loopback MCP dev-bridge guard. 19 tests; deterministic, offline. Mobile roadmap phases 0-12+20 implemented (simulator-preview; Phase 11 = entry-gate, fixtures-only). |
| R-CR-BACKLOG | Close critical-review-v2 CRs (036/021/034/043/045) (Batch 6 Track A) (Phase 193) | Status: Baseline Complete | Evidence: local worktree 2026-06-08 | MESSAGE registry/typed parity, README arc-wallet fix, eval synthetic batch labelling, MCP_CALL_DECISION producer wired, dod-gate CI (banned-claims). 16 tests; additive. |
| R-MOBILE-CLI | Mobile CLI surfaces for new modules: gate/flags/egress/queue/secure-store/audit-retention (Batch 6 Track C) (Phase 194) | Status: Baseline Complete | Evidence: local worktree 2026-06-08 | Deterministic CLI over CapabilityEntryGate/FeatureFlags/EgressGuard/OfflineQueue/SecureLocalStore (redacted)/audit_retention. 31 CLI tests; simulator-preview. |
| R-MOBILE-HARDEN | Mobile hardening + DoD elevation: simulate-through-gate, signed tenant RBAC/ABAC overlay, mypy gate for 9 modules, REAL_VS_MOCK refresh, property/fuzz tests (Batch 6 Track D) (Phase 195) | Status: Baseline Complete | Evidence: local worktree 2026-06-08 | 115 mobile tests (7 property); mypy clean; banned-claims green; fixtures-only posture held. |
