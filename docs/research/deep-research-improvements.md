# Deep Research Improvements Backlog

**Date:** 2026-05-27
**Source reports:** all unique `docs/research/deep-research-report*.md` files through `deep-research-report-9.md`, plus Theia architecture report copy.
**Status:** Candidate backlog. Not a roadmap/status source of truth.

## Improvement Principles

- Build from existing ARC primitives first: traces, runs, tasks, HITL, audit, sandbox policy, MCP stdio, memory prototype, provider registry, SwarmGraph events, Theia widgets/services.
- Prefer service/CLI foundations before broad IDE polish where behavior is not stable.
- Keep defaults offline, local, sandboxed, private, and dry-run unless explicit gates exist.
- Do not claim microVM execution without boot/run/mount/network/timeout/teardown tests.
- Do not enable memory auto-injection without eval-backed proceed decision, reviewed evidence packs, and privacy gates.
- Do not launch executable plugins or marketplace before signing, permission broker, sandbox, audit, disable/update controls, and stable contracts exist.
- Do not sync raw traces/team data by default; private mode is default and team mode is explicit.
- Do not treat AI review comments as merge gates; deterministic eval, policy, receipt, and provenance checks gate.

## P0 Candidate Improvements

### 1. Trace-Aware Review Mode MVP

**Goal:** Dedicated review surface linking diffs to run evidence.

**Why:** This is the strongest ARC-native differentiator: competitors have review UX, but ARC can tie review to traces, audit, HITL, SwarmGraph, policy, and tests.

**Initial scope:**

- Show grouped diff tree by task/file when evidence exists.
- For each hunk, show originating run step/tool/approval/test/checkpoint or `unknown/manual`.
- Link to trace step, audit record, policy decision, sandbox result, and test result where producers exist.
- Support accept/reject at hunk/file/task level only if backing edit state exists; otherwise inspect-only.
- Export review evidence summary with redaction status.

**Acceptance:**

- Missing producers render explicit absent/unknown states.
- No hunk provenance is fabricated.
- Review summary includes source run IDs, policy state, and verification state where available.

### 2. Plan / Apply / Review Loop

**Goal:** Deterministic plan-before-execution UX for shell/tool/runtime actions.

**Initial scope:**

- Use existing command classifier and `arc policy explain` semantics.
- Show intended files, read/write/network/install/destructive/privileged/unknown classifications.
- Show sandbox decision and approval requirement.
- Show provider/cost/risk estimates only where measured or configured; otherwise `unknown`.
- Record plan approval/denial audit events.
- Apply starts only from approved plan or explicit direct command.

**Acceptance:**

- Mutating action can be previewed before execution.
- Destructive/privileged remains hard-denied unless an existing explicit policy permits it.
- JSON output stable enough for IDE consumption.

### 3. Agent Command Centre / Approval Centre MVP

**Goal:** One supervisory surface for active/past sessions, runs, tasks, approvals, sandbox state, risk, provider, and workspace/worktree context.

**Initial scope:**

- Aggregate active/past runs from existing run index.
- Show session/task state from existing stores.
- Show pending HITL/sandbox/MCP approval count.
- Show sandbox/provider/trust labels.
- Link into Runs, Assurance, SwarmGraph Insight, Battle, and Review surfaces.
- No new execution mode.

**Acceptance:**

- User can see active work and blocked approvals in one view.
- Absent producers render empty/degraded states.
- No provider or sandbox behavior changes.

### 4. MCP Panel / Workbench Phase 1

**Goal:** Make current stdio MCP server visible and diagnosable before adding remote transport.

**Initial scope:**

- IDE panel listing ARC MCP status, local tools/resources/prompts, trust state, audit path.
- CLI `arc mcp status --json` if missing.
- Inspector-like diagnostics: list tools/resources/prompts, call safe read-only tool, validate envelope shape.
- Registry metadata research only; no one-click external server execution yet.

**Acceptance:**

- User can diagnose local MCP without leaving ARC.
- No HTTP listener added.
- No external MCP server auto-started.

### 5. First-Run Provider / Trust / Sandbox Wizard

**Goal:** Reduce setup friction while preserving trust and credential boundaries.

**Initial scope:**

- Doctor-driven onboarding checklist.
- Provider picker with env/keychain reference guidance.
- Local model autodetect for Ollama/OpenAI-compatible localhost where safe.
- Workspace trust explanation: restricted vs trusted.
- Sandbox policy explanation and default safe profile.
- Telemetry/crash consent split if telemetry exists.

**Acceptance:**

- New user can reach a safe local/offline run path without editing docs manually.
- No raw secret persisted in project config.
- Trust/sandbox mode visible before any shell/runtime action.

### 6. Workspace Intelligence Foundation

**Goal:** Deterministic context layer before broad semantic/RAG claims.

**Initial scope:**

- Index files, symbols where available, git metadata, prior traces, and MCP resources into one local context inventory.
- Explain why each context item was selected.
- Keep semantic embeddings optional and gated.
- Respect workspace trust, root scope, ignored files, and output caps.

**Acceptance:**

- Search returns files/symbols/traces/resources with provenance.
- Multi-root workspaces show root-qualified paths.
- No hidden network or provider calls in default indexing.

### 7. Structured Test Bench MVP

**Goal:** Make verification evidence first-class next to agent output.

**Initial scope:**

- Detect candidate test commands from package/project files and existing config.
- Let user run failing-only/rerun commands through existing sandbox/policy gates.
- Attach test output summaries and failure links to run/review evidence.
- Never infer pass/fail without command evidence.

**Acceptance:**

- Test command detection is reviewable and editable.
- Results link to run/review evidence.
- No live network required in tests.

### 8. Theia-Native Service Split Phase 1

**Goal:** Reduce ARC workbench/platform debt without rewriting product UX.

**Initial scope:**

- Audit `arc-backend-service.ts` responsibilities.
- Extract one or two high-risk domains first, likely daemon discovery and stream/session bridge.
- Move DTOs/contracts into `common/*` where missing.
- Keep backend-owned streams and one frontend session bridge singleton.
- Add lifecycle cleanup through backend/frontend contributions.

**Acceptance:**

- Existing protocol methods preserved.
- No duplicated frontend stream ownership for migrated path.
- Unit/static tests cover service boundaries.

## P1 Candidate Improvements

### 9. Memory SQLite Source Of Truth

**Goal:** Move memory from JSON research prototype toward local-first inspectable storage.

**Initial scope:**

- SQLite tables for memory items, evidence, edges, tombstones, retrieval logs.
- Import existing `.arc/memory/graph.json`.
- Keep JSON export for debugging.
- Add provenance fields and logical deletion.
- Runtime injection remains blocked.

**Acceptance:**

- `arc memory query/show/forget-run/evaluate` works against SQLite.
- Existing JSON memory can migrate or export.
- Deletion semantics distinguish logical vs physical.

### 10. OS-Level Sandbox Provider Phase 1

**Goal:** Add practical OS-level sandbox providers before VM/microVM execution.

**macOS scope:**

- Seatbelt/sandbox-exec provider behind doctor/preflight and explicit availability status.
- Workspace read/write profile, no network default, temp/cache allowance.
- Clear deprecation/future-risk note.

**Linux scope:**

- Bubblewrap provider with minimal filesystem view.
- Optional Landlock ABI detection layer.
- Seccomp profile research/prototype.

**Acceptance:**

- Provider reports unavailable/ready/blocked clearly.
- Tests prove workspace escape denial and network default-deny where supported.
- Subprocess provider remains fallback, not overclaimed as OS-level sandbox.

### 11. MCP Registry / External Server Management Phase 2

**Goal:** Add curated discovery and safe management for external MCP servers.

**Scope:**

- Registry metadata viewer.
- Project/user config diff preview.
- Server install plan, not auto-run by default.
- Health check and logs.
- Allowlist roots/domains/env references.

**Acceptance:**

- User can review exactly what a server would run and access.
- External server start requires explicit approval.
- Audit records install/enable/disable/start decisions.

### 12. Trace-To-Eval Dataset Builder

**Goal:** Convert ARC traces into regression datasets.

**Scope:**

- Select trace/run events as golden examples.
- Add labels/assertions/scorers metadata.
- Export compatible dataset bundle.
- CLI + IDE minimal UX.

**Acceptance:**

- User can promote a run to a golden/eval case.
- Eval output links back to source run/audit evidence.
- No fabricated pass/fail without scorer evidence.

### 13. Checkpoints / Revert / Fork UX

**Goal:** Productize safe rollback and branch exploration.

**Scope:**

- Expose existing fork/replay/session state in IDE and CLI.
- Add run checkpoint labels where data exists.
- Show diff from checkpoint to current state.

**Acceptance:**

- User can inspect and fork from known stored state.
- No deterministic replay claim unless execution is actually replayed.

### 14. Declarative Extension Packs

**Goal:** Start plugin ecosystem safely with no executable plugin code.

**Scope:**

- Manifest for prompt templates, workflow templates, slash command definitions, eval recipes.
- Local path install only.
- Schema validation and disable/remove commands.
- Audit install/enable/disable.

**Acceptance:**

- Declarative packs can be listed, validated, enabled, disabled.
- No process plugin, provider adapter, network, or shell permissions.

### 15. ARC CI Guardrails MVP

**Goal:** Make local-first evidence usable in PR/team workflows without mandatory raw trace upload.

**Scope:**

- `arc ci review` advisory checks from repo-local rules.
- `arc ci eval run` and `arc ci gate` against offline eval packs.
- `arc ci policy check` over canonical run manifest.
- `arc ci receipt sign` and `arc ci audit verify` for signed evidence.
- GitHub reusable workflow template as docs/scaffold first.

**Acceptance:**

- Private mode uploads nothing.
- PR output uses redacted summaries only.
- Blocking gates are deterministic eval/policy/receipt checks, not freeform AI comments.

### 16. SwarmGraph Consensus Differentiators Phase 1

**Goal:** Add measurable consensus improvements without broad provider-backed execution.

**Scope:**

- Selective debate escalation.
- Confidence-weighted quorum.
- Critic/verifier lane.
- Diversity-aware role/model cards.
- HITL sign-off quorum for red/black risk.
- Offline eval harness for cost/quality tradeoffs.

**Acceptance:**

- Fake/offline remains default.
- Provider-backed execution remains behind existing trust/paid/sandbox/approval/audit gates.
- Eval reports include quality, cost, latency, and disagreement metrics.

### 17. Multi-Root Trust And Root-Qualified Paths

**Goal:** Make workspace roots explicit across sessions, approvals, providers, and context.

**Scope:**

- Use root-qualified paths in approval cards and review evidence.
- Resolve provider/config scope folder -> workspace -> user -> default where Theia supports it.
- Treat no-root/empty windows as first-class restricted state.

**Acceptance:**

- Multi-root duplicate filenames remain distinguishable.
- Sandbox/write approvals show exact root scope.
- Tests cover single-root, multi-root, and no-root states.

## P2 Candidate Improvements

### 18. Streamable HTTP MCP Transport

**Goal:** Add remote-capable MCP transport safely.

**Blockers:**

- Auth model.
- Loopback token handling.
- Origin validation.
- SSRF-safe discovery.
- Session lifecycle tests.
- Audit/replay of calls.

**Acceptance:**

- Localhost-only default.
- Auth required by default.
- Inspector/client compatibility tests pass.
- Remote exposure explicitly gated.

### 19. Provider Gateway / Routing

**Goal:** Unified provider profile with fallback, budgets, health, local/cloud routing.

**Scope:**

- Dry-run routing plans first.
- Cost/budget policy display.
- Health checks and model catalog.
- No provider-backed adoption claim.

**Acceptance:**

- Default behavior makes no live provider call.
- Live calls require existing paid/provider gates.
- Cost/provider metadata marked measured/estimated/unknown.

### 20. Full Plugin Runtime

**Goal:** Execute plugin tools/adapters out-of-process under permission broker.

**Blockers:**

- Signed manifests.
- Permission broker.
- Sandbox provider.
- Audit event schema.
- Disable/revoke/update path.

**Acceptance:**

- Plugin cannot read/write/network outside granted scopes.
- Host owns secrets and redaction.
- Plugin invocation audit is complete.

### 21. Memory Retrieval / Suggest Mode

**Goal:** Move from inspect-only to suggested memory attachment.

**Blockers:**

- Retrieval eval suite.
- Privacy suite.
- Prompt-injection scanner.
- Provenance completeness.

**Acceptance:**

- ARC suggests memories but user chooses attachment.
- Suggestions include why, provenance, confidence, privacy label.
- Auto-injection remains disabled.

### 22. VM-Isolated macOS / Firecracker Linux Experiments

**Goal:** Prove high-isolation execution paths without overclaiming.

**Linux:** Firecracker experimental proof path.
**macOS:** Virtualization.framework/Lima/Tart Linux VM path, described as VM-isolated execution, not microVM execution.

**Acceptance:**

- Boot/run/mount/network/timeout/teardown tests.
- CI-skipped opt-in real-host tests with clear labels.
- No public execution claim until evidence exists.

## Research-Only / Avoid For Now

| Item | Reason |
|---|---|
| Public plugin marketplace | Unsafe before signing/review/sandbox/permissions. |
| Automatic memory injection | Requires eval/privacy proof. |
| Broad provider-backed SwarmGraph execution | Requires trust/paid/provider/budget/audit gates and tests. |
| macOS Firecracker microVM claim | Requires nested Linux/KVM path; not a normal macOS capability. |
| Docker Desktop as “microVM” | Misleading; container fallback only. |
| Remote MCP without auth | Explicitly unsafe. |
| Universal auto-approval / YOLO mode | Conflicts with ARC safety posture. |
| Full desktop-first packaging claim | Browser + daemon should remain canonical until desktop packaging is proven. |
| Raw trace/team sync by default | Violates local-first/private-by-default posture. |
| AI review as hard merge gate | Advisory output is not deterministic; use eval/policy/receipt gates. |

## Suggested Implementation Order

1. Trace-aware Review Mode MVP.
2. Plan / Apply / Review deterministic loop.
3. Agent Command Centre / Approval Centre aggregator.
4. Theia-native service split Phase 1 for bridge/stream/workspace foundations.
5. MCP Panel / local diagnostics.
6. First-run provider/trust/sandbox wizard.
7. Workspace Intelligence foundation.
8. Structured Test Bench MVP.
9. Memory SQLite/provenance migration.
10. OS sandbox provider phase 1.
11. Trace-to-eval dataset builder.
12. ARC CI guardrails MVP.
13. Declarative extension packs.
14. SwarmGraph consensus differentiators Phase 1.
15. MCP registry/external server management.
16. Streamable HTTP MCP transport.

## Implementation Plan Addendum

This plan is research-backed and candidate-only. Do not treat it as implementation status.

| Slice | Owner surface | Key files likely affected | Gate before start | Done means |
|---|---|---|---|---|
| Review evidence inventory | Python + TS protocol | `python/src/agent_runtime_cockpit/schemas/`, `packages/arc-protocol-ts/src/`, trace consumers | Confirm current producers for diffs/tests/tool IO/approvals | Gap table and no-fabrication UI contract |
| Plan / Apply / Review backend contract | Python CLI + protocol | `python/src/agent_runtime_cockpit/security/`, `python/src/agent_runtime_cockpit/cli/`, TS protocol | Existing sandbox classifier stable | Stable JSON plan envelope + approval audit event |
| Command/Approval Centre aggregator | IDE frontend/backend | `packages/arc-extension/src/browser/`, `packages/arc-extension/src/node/` | Producer inventory updated | Aggregates real runs/tasks/HITL/sandbox state only |
| Theia bridge split | TS backend/common/browser | `arc-backend-service.ts`, session bridge, common protocol | Tests for existing bridge behavior | One migrated domain has typed service + lifecycle cleanup |
| MCP panel | Python + TS IDE | MCP CLI/server, IDE panel | Stdio inventory stable | Local status/tools/resources/prompts visible, no HTTP |
| Workspace intelligence | Python + TS | context/index/search modules | Trust/root model defined | Deterministic local index + provenance explanations |
| Test bench | Python + TS | task/test detection/run evidence | Sandbox command run path stable | Test command detection + recorded evidence |
| CI guardrails | Python CLI + docs | new/extended `arc ci` commands | Eval/policy/receipt schemas stable | Private-mode no-upload CI commands with redacted summary |
| SwarmGraph consensus eval | Python | `swarmgraph/`, evals/tests | Offline benchmark fixtures | Selective debate/weighted/verifier metrics without provider calls |

## Claim Language

Use these terms until implementation and tests prove more:

| Area | Safe wording | Avoid |
|---|---|---|
| Review | “trace-aware review MVP” | “every change is fully proven” |
| Workspace intelligence | “deterministic context inventory” | “complete code intelligence” |
| Test bench | “structured test evidence” | “automatic verification of all changes” |
| Sandbox | “OS-level sandbox provider prototype” | “production sandbox” |
| MicroVM | “microVM preflight/doctor/proof harness” | “microVM execution” |
| macOS VM | “VM-isolated Linux execution on macOS” | “macOS microVM execution” |
| Memory | “retrieval/inspection memory” | “autonomous memory injection” |
| MCP HTTP | “local authenticated Streamable HTTP preview” | “remote MCP production server” |
| Plugins | “declarative extension packs” | “plugin marketplace” |
| Provider routing | “dry-run/provider policy routing” | “broad provider-backed runtime” |
| CI/team | “metadata-first team guardrails” | “raw trace sync by default” |
| SwarmGraph | “offline consensus differentiators” | “broad provider-backed swarm execution” |

## Follow-Up When More Reports Arrive

- Add report inventory entry.
- Mark duplicate vs unique by hash/title.
- Update convergence table.
- Re-rank backlog only if new reports add stronger evidence.
- Do not rewrite roadmap/phases unless implementation status actually changes.
