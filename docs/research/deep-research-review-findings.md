# Deep Research Review Findings

**Date:** 2026-05-27
**Scope:** All current files matching `docs/research/deep-research-report*.md`, de-duplicated by title/hash.
**Status:** Research synthesis only. `docs/roadmap.md` and `docs/phases.md` remain the status sources of truth.

## Report Inventory

| File | Title | Status |
|---|---|---|
| `deep-research-report.md` | ARC Studio Global Feature Discovery | Unique |
| `deep-research-report-2.md` | ARC Studio as a better AI IDE | Unique |
| `deep-research-report-3.md` | ARC Studio packaging, distribution, and onboarding research | Unique |
| `deep-research-report-4.md` | ARC Studio plugin and extension ecosystem recommendations | Unique |
| `deep-research-report-5.md` | ARC Studio MCP roadmap | Unique |
| `deep-research-report-6.md` | Security and sandbox improvements for ARC Studio | Unique |
| `deep-research-report-7.md` | ARC Studio memory, context, and RAG roadmap | Unique |
| `deep-research-report-8.md` | ARC Studio CI and Team Workflow Research | Unique |
| `deep-research-report-9.md` | Research opportunities for ARC Studio SwarmGraph runtime | Unique |
| `deep-research-report copy.md` | ARC Studio Theia Architecture Research | Unique |
| `deep-research-report-3 copy.md` | ARC Studio Global Feature Discovery | Duplicate of `deep-research-report.md` |
| `deep-research-report-4 2.md` | ARC Studio packaging, distribution, and onboarding research | Duplicate of `deep-research-report-3.md` |
| `deep-research-report-5 2.md` | ARC Studio plugin and extension ecosystem recommendations | Duplicate of `deep-research-report-4.md` |
| `deep-research-report-6 2.md` | Security and sandbox improvements for ARC Studio | Duplicate of `deep-research-report-6.md` |
| `deep-research-report-7 2.md` | ARC Studio memory, context, and RAG roadmap | Duplicate of `deep-research-report-7.md` |

## Executive Verdict

The reports converge on a sharper product thesis: ARC should be a trace-native agent engineering cockpit, not another chat sidebar or generic agent framework. Its strongest existing assets are traces, audit/HITL, sandbox policy, SwarmGraph topology/consensus/cost state, MCP stdio, provider gates, local-first memory research, and a Theia-based workbench.

The main risk remains scope explosion. The new reports add important but large surfaces: trace-aware review, workspace intelligence, structured test bench, CI/team governance, consensus-native SwarmGraph, and Theia-native service decomposition. These are directionally strong but must become small, status-safe slices.

The highest-confidence near-term themes are:

| Theme | Verdict | Why |
|---|---|---|
| Trace-aware review / replay debugger | Strong fit | Converts ARC trace/audit data into user trust and debugging value. |
| Plan / Apply / Review loop | Strong fit | Matches market baseline and reuses existing policy/sandbox/HITL primitives. |
| Agent Command Centre / Approval Centre | Strong fit | Unifies sessions, runs, approvals, sandbox state, risk, and evidence. |
| MCP Panel / Workbench | Strong fit | ARC has stdio MCP; registry/inspector/client mode should be staged. |
| Workspace intelligence + test bench | Strong fit, but sizeable | Needed for AI IDE parity; should start as index/search/test evidence surfaces. |
| CI/team governance | Strong fit, gated | `arc ci` can package review/eval/policy/receipt work without syncing raw local state by default. |
| Consensus-native SwarmGraph | Strong differentiator | ARC can lead on selective debate, weighted quorum, verifier lanes, HITL quorums, and risk-based topology. |
| Theia-native architecture cleanup | Strong enabler | Backend façade split, typed JSON-RPC, multi-root and WidgetManager patterns reduce platform debt. |
| Layered sandbox providers | Strong fit, but claim-sensitive | Seatbelt/bubblewrap/Landlock before broad VM/microVM execution claims. |
| Memory SQLite/provenance subsystem | Strong fit, gated | Retrieval/inspection before any runtime injection. |
| Plugin system | Good strategic fit, defer executable marketplace | Start with declarative packs; executable plugins need signing/permissions/sandbox/audit. |

## Cross-Report Convergence

| Area | Reports | Shared finding | Review verdict |
|---|---|---|---|
| Agent supervision | Global, AI IDE | Market has moved from chat to supervisory multi-agent/session operation. | Accurate; make Command Centre an aggregator MVP first. |
| Plan/review/checkpoint loop | Global, AI IDE, security, Theia | Safe autonomy requires explicit plan, apply, review, approval, rollback, and evidence. | High-confidence P0/P1 direction. |
| Trace-native review | AI IDE, CI/team, SwarmGraph, Theia | ARC should expose trace/audit/test/provenance as review evidence. | Strongest differentiator beyond chat parity. |
| MCP | Global, plugin, MCP | MCP is a host/workbench/ecosystem surface, not only stdio server plumbing. | Accurate; stdio panel before HTTP/hub. |
| Sandbox | Global, security, plugin, CI/team | Sandbox policy must be visible, audited, and policy-checkable locally and in CI. | Accurate; preserve subprocess/OS/microVM truth boundaries. |
| Memory | Global, memory, SwarmGraph | Memory needs scope/provenance/deletion/eval gates; no blind auto-injection. | Accurate and aligned with current constraints. |
| CI/team | CI/team | AI review explains; eval, policy, receipts, provenance decide. | Strong; local-first/private-by-default posture is essential. |
| SwarmGraph | SwarmGraph | ARC should differentiate on consensus economics, verifiers, risk-conditioned orchestration. | Strong; avoid broad provider-backed execution claims. |
| Theia architecture | AI IDE, Theia | Product code should be Theia-native: DI, typed RPC, multi-root, stateful widgets. | Strong enabler; validate against actual source before large refactor. |
| Packaging/onboarding | Packaging, AI IDE | Browser + local daemon first; desktop shell follows; setup wizard needed. | Strong and realistic. |
| Plugin ecosystem | Plugin, MCP, CI/team | Manifest, permissions, signing, registry metadata, audit before executable ecosystem. | Strong long-term direction; marketplace deferred. |

## High-Confidence Findings

### 1. ARC Should Own Trace-Native Review

- **Source reports:** `deep-research-report-2.md`, `deep-research-report-8.md`, `deep-research-report-9.md`, `deep-research-report copy.md`
- **Finding:** Leading IDEs have review/checkpoint UX, but ARC can uniquely link diffs to prompts, tools, approvals, tests, SwarmGraph nodes, policy decisions, and audit material.
- **Verdict:** Highest-confidence product differentiator.
- **Implementation consequence:** Build review mode as an evidence surface over existing traces first. Every missing producer must render unknown/absent, not fabricated evidence.
- **Risk:** Requires trace schema completeness; do not imply every hunk has provenance until producers exist.

### 2. Agent Command Centre Is The Best Product Unifier

- **Source reports:** `deep-research-report.md`, `deep-research-report-2.md`
- **Finding:** Competitors expose parallel agents, worktrees, background sessions, checkpoints, and supervisory dashboards. ARC already has many primitives but distributes them across tabs and CLI surfaces.
- **Verdict:** Accurate. Build as an aggregator, not a runtime rewrite.
- **Implementation consequence:** List sessions/runs/tasks/approvals/risk/sandbox/provider/worktree links from existing producers.
- **Risk:** Large rewrite if it replaces existing tabs too early.

### 3. Reviewable Plan Mode Should Be A First-Class Safety Gate

- **Source reports:** `deep-research-report.md`, `deep-research-report-2.md`, `deep-research-report-6.md`
- **Finding:** Plan-before-execute is now expected and maps to ARC's sandbox/policy strengths.
- **Verdict:** Accurate and feasible.
- **Implementation consequence:** Start with deterministic policy explain, file-intent preview, command classification, provider/cost/risk if present, approval audit record.
- **Risk:** Overbuilding a planning agent before deterministic preview exists.

### 4. Workspace Intelligence And Test Bench Are AI IDE Parity Blockers

- **Source report:** `deep-research-report-2.md`
- **Finding:** ARC needs codebase intelligence and structured verification, not terminal output alone.
- **Verdict:** Strong, but should be staged.
- **Implementation consequence:** Start with symbols/files/git/traces/MCP resources in a local index and a test-command evidence pane. Keep model-backed retrieval optional/gated.
- **Risk:** Indexing and test auto-detection can be expensive/noisy; require degraded states.

### 5. MCP Workbench Is A Major Opportunity

- **Source reports:** `deep-research-report.md`, `deep-research-report-4.md`, `deep-research-report-5.md`
- **Finding:** ARC should evolve from stdio-only MCP server to MCP workbench: registry discovery, inspector, panel, external server management, prompts/resources, roots, Streamable HTTP, auth, audit.
- **Verdict:** Directionally accurate.
- **Implementation consequence:** Start with MCP panel + local stdio inventory + inspector-like diagnostics before remote HTTP/hub mode.
- **Risk:** HTTP transport and OAuth are security-sensitive; remote surface needs explicit auth/origin/SSRF gates.

### 6. CI/Team Workflow Should Separate Advice From Gates

- **Source report:** `deep-research-report-8.md`
- **Finding:** AI review should explain; eval, policy, provenance, and signed receipts should decide.
- **Verdict:** Strong and compatible with local-first ARC.
- **Implementation consequence:** Stage `arc ci review`, `arc ci eval run`, `arc ci gate`, `arc ci policy check`, `arc ci receipt sign`, and minimal GitHub Action integration.
- **Risk:** Upload/sync must remain opt-in and metadata-first; no surprise trace exfiltration.

### 7. Security Research Correctly Avoids MicroVM Overclaiming

- **Source report:** `deep-research-report-6.md`
- **Finding:** macOS high isolation should be described as VM-isolated Linux execution, not microVM execution. Linux Firecracker is the honest microVM target. Seatbelt/bubblewrap/Landlock/seccomp are practical next sandbox layers.
- **Verdict:** Excellent claim discipline.
- **Implementation consequence:** Provider abstractions, doctor/preflight, Seatbelt/bubblewrap/Landlock before broad microVM execution claims.
- **Risk:** Seatbelt is deprecated; docs must present it as practical/current, not future-proof Apple API.

### 8. Memory Report Correctly Keeps Injection Blocked

- **Source report:** `deep-research-report-7.md`
- **Finding:** Memory should move from JSON prototype to SQLite/provenance/retrieval first. Runtime injection remains blocked until evals prove quality/cost lift and privacy safety.
- **Verdict:** Accurate and aligned with roadmap truth.
- **Implementation consequence:** Build memory inspect/query/index/deletion/evidence-pack foundations before prompt injection.
- **Risk:** SQLite FTS/WAL/temp deletion guarantees are subtle; distinguish logical vs physical deletion.

### 9. SwarmGraph Differentiation Should Be Consensus-Native

- **Source report:** `deep-research-report-9.md`
- **Finding:** ARC can differentiate on selective debate, confidence-weighted quorum, critic/verifier lanes, diversity-aware juries, human sign-off quorums, causal trace root-cause analysis, and battle replay.
- **Verdict:** Strong strategic direction.
- **Implementation consequence:** Add verifier/weighted-quorum/debate escalation under offline/eval harnesses before real provider-backed broad execution.
- **Risk:** Multi-agent debate may add cost without quality gain; require cost/quality evals.

### 10. Theia-Native Architecture Cleanup Is A Foundation Multiplier

- **Source report:** `deep-research-report copy.md`
- **Finding:** ARC should align with Theia DI, `common/browser/node` split, typed JSON-RPC, multi-root workspace services, WidgetManager lifecycle, preference scopes, command/menu/keybinding contributions, and backend-owned stream lifecycle.
- **Verdict:** Strong, but validate against current code before large refactor.
- **Implementation consequence:** Split broad backend façade into domain services incrementally; make session bridge typed/singleton; add multi-root root-qualified model.
- **Risk:** Refactor can destabilize working surfaces if not sliced behind tests.

### 11. Plugin Architecture Is Strong But Too Large For Near Term

- **Source report:** `deep-research-report-4.md`
- **Finding:** One manifest with multiple runtime classes and explicit permissions is the right long-term architecture.
- **Verdict:** Strong strategy, not immediate executable-plugin work.
- **Implementation consequence:** Begin with declarative packs only: prompts, workflows, slash aliases, eval recipes.
- **Risk:** Third-party executable plugins before sandbox/signing increase attack surface.

### 12. Packaging Direction Is Practical

- **Source report:** `deep-research-report-3.md`
- **Finding:** Browser app + local daemon is lowest-risk default; Electron shell with bundled daemon is convenience layer; Docker/devcontainer remains developer/support path.
- **Verdict:** Strong and realistic.
- **Implementation consequence:** Productize daemon bootstrap and first-run wizard before broad desktop claims.
- **Risk:** Packaging should not outrun trust/sandbox/provider credential hardening.

## Claims Needing Caution

| Claim / recommendation | Concern | Correction |
|---|---|---|
| “Trace-aware review can explain every diff” | Existing producers may not link every hunk to evidence | Render unknown/manual provenance explicitly. |
| “Agent Command Centre P0” | Too broad as written | P0 = aggregator MVP only; no new runtime. |
| “Workspace intelligence” | Can become large RAG/indexing project | Start with deterministic files/symbols/git/traces, then optional semantic layer. |
| “MCP HTTP / OAuth” | Adds remote attack surface | Do stdio panel/registry/inspector first; HTTP behind local-only/auth gate. |
| “CI team mode” | Can violate local-first promise | Private mode default; team upload metadata-only and opt-in. |
| “Plugin marketplace” | Requires signing, review, sandbox, permission broker | Start with local declarative packs only. |
| “Seatbelt primary macOS sandbox” | `sandbox-exec` deprecated | Current practical provider with replacement caveat and doctor warning. |
| “SQLite physical deletion” | FTS/WAL/temp-file caveats | Promise logical deletion first; physical scrub only when verified. |
| “uv installer / curl pipe” | Supply-chain implications | Prefer signed/checksummed installer plus Homebrew/pipx/uv alternatives. |
| “Provider gateway with fallbacks” | Can trigger paid/network calls | Keep dry-run/default-off; enforce provider trust/paid-call/cost gates. |
| “Consensus-native swarm runtime” | Cost and complexity can rise quickly | Require offline eval and cost/quality gates before broad adoption. |

## Missing Synthesis Points

| Missing point | Why it matters | Suggested addition |
|---|---|---|
| Explicit relation to existing sandbox hardening | Prevent duplicate systems | Tie Seatbelt/bubblewrap/Landlock to `IsolationProvider`. |
| IDE vs CLI ownership | Avoid implementation sprawl | Every feature needs CLI-first, service-first, or IDE-first owner. |
| Trace schema gap analysis | Review/replay depends on producers | Audit which run events include diffs, tests, approvals, tool I/O, checkpoints. |
| Migration from current memory JSON | Needed for rollout | Add import/export/backfill from `.arc/memory/graph.json` to SQLite. |
| MCP spec/version compatibility | Report uses latest spec claims | Implement version negotiation and document supported MCP version. |
| Enterprise/offline mode | Mentioned but unstructured | Add offline profile: local models only, no telemetry, no remote MCP, strict sandbox. |
| Adapter registry/certification link | Plugin/adapters overlap | Adapter certification should become plugin conformance later. |
| Theia multi-root model | Needed for trust/sandbox correctness | Use root-qualified paths in approvals, sessions, providers, and context. |
| CI artifact redaction | Prevent trace leakage | Define safe PR summary vs full local/private bundle. |

## Priority Review

### Keep Near-Term

- Trace-aware Review Mode MVP.
- Plan / Apply / Review deterministic loop.
- Agent Command Centre / Approval Centre aggregator MVP.
- MCP Panel with stdio server inventory, health, logs, tools/resources/prompts view.
- Provider/trust onboarding wizard.
- Workspace intelligence deterministic index + context explanation.
- Structured Test Bench MVP.
- Seatbelt/bubblewrap/Landlock research-to-provider slices.
- Memory SQLite/provenance/retrieval without auto-injection.
- Theia backend façade split and typed session bridge migration.
- `arc ci` advisory review + eval/policy/receipt gate design.

### Defer Until Foundations Exist

- Public plugin marketplace.
- Executable plugin runtime.
- Remote MCP HTTP server exposed beyond loopback.
- Public microVM execution claim.
- Cross-workspace memory sync.
- Broad provider-backed SwarmGraph execution.
- Automatic runtime memory injection.
- Full desktop-first distribution claim.
- Team/shared-server sync of raw traces by default.

### Needs Explicit Blockers

- macOS nested Firecracker: blocked by hardware/OS/nested virtualization complexity.
- Physical memory deletion: blocked by FTS/WAL/temp-file proof tests.
- Signed plugin ecosystem: blocked by manifest schema, signing/provenance, review flow, sandbox.
- MCP OAuth: blocked by auth model, token storage, SSRF/origin protections, integration tests.
- Provider-backed consensus execution: blocked by trust/paid/sandbox/approval/audit gates and eval proof.
- Trace-aware hunk provenance: blocked where producers do not emit diff/test/tool links.

## Recommended Review Actions

1. Treat these reports as feature discovery input, not implementation status truth.
2. Keep all roadmap/phase additions as Not Started/Deferred until code and tests land.
3. Use `docs/research/deep-research-improvements.md` as candidate backlog, not a replacement roadmap.
4. For every accepted feature, require claim wording and evidence producers before implementation starts.
5. Re-run synthesis if additional unique reports arrive.
