# ARC Studio + SwarmGraph Unified Feature List

**Document Version:** 2.0  
**Date:** 2026-05-22  
**Status:** Approved — Merged with Architecture Review  
**Owner:** ARC Studio Core Team + SwarmGraph Core Team  
**Source Documents:**
- `SWARMGRAPH_FEATURE_LIST.md` v1.0 (2026-05-22, research-driven)
- `ARC_STUDIO_1.0_ARCHITECTURE_AND_FEATURE_REVIEW.md` (2026-05-22, senior staff review)

---

## Executive Summary

This document merges the SwarmGraph research-driven feature list with the ARC Studio 1.0 architecture review. The architecture review correctly identified that **foundation work (audit, protocol, trust, IDE resilience) must precede differentiators (MCP, Consensus Escrow, Adaptive Consensus)**. The feature list had the right differentiators but wrong sequencing.

**Merged Priorities:**
1. Fix audit integrity, typed protocols, and trust enforcement (P0)
2. Harden IDE performance, CLI maintainability, and replay accuracy (P1)
3. Add MCP local control plane as distribution channel (P1)
4. Add SwarmGraph differentiators (P2)
5. Research future capabilities (P3+)

**Key Corrections from Architecture Review:**
- 7 foundation items added (P0/P1) that the original feature list missed
- MCP demoted from P0 → P1 (fix foundations first)
- MCP scoped as ARC local control plane, not standalone SwarmGraph server
- Adaptive Consensus must use deterministic heuristics, not LLM-only
- All features must respect workspace trust enforcement

---

## Feature Overview

| Phase | Features | Duration | Strategic Value |
|---|---|---|---|
| Phase 0 | Protocol + Audit Foundations | 2-3 weeks | **Credibility** |
| Phase 1 | Safety + IDE + CLI Hardening | 3-4 weeks | **Stability** |
| Phase 2 | MCP Local Control Plane | 2 weeks | Ecosystem Access |
| Phase 3 | Replay + Adapter + Eval Accuracy | 2-3 weeks | **Trust** |
| Phase 4 | SwarmGraph Differentiators | 3-4 weeks | Competitive Moat |
| Phase 5 | Enterprise Features | 1-2 weeks | Enterprise Adoption |
| Phase 6 | Research & Future | 3+ months | Long-term Innovation |

**Total Estimated Effort (P0-P2):** 15-20 weeks  
**Critical Path:** Audit → Protocol → Trust → IDE → CLI → MCP → Replay → HITL/Eval → Escrow → Adaptive

---

## Phase 0: Protocol + Audit Foundations

> **Source:** Architecture Review P0-1, P0-2. These were completely missing from the original feature list and are the highest-priority items.

### F0.1: Streaming Audit Verification + Optional HMAC Signing

**Priority:** P0 (Critical — Foundation)  
**Status:** Not Started  
**Effort:** 5 engineer-days  
**Owner:** Core Team  
**Dependencies:** None  
**Source:** Architecture Review Section 5, P0-1

**Problem:**  
`audit/chain.py` materializes both audit and event files with `read_text().splitlines()`. Large traces spike memory. The chain is tamper-evident (SHA-256) but not strongly authenticated. HMAC/signing is modeled but not implemented.

**Technical Scope:**
- Add `StreamingAuditVerifier.verify_sha256(chain_path, events_path)` — line-by-line iteration
- Add `verify_hmac(...)` with explicit audit versioning and key availability status
- Add CLI: `arc audit verify <run-id> --mode sha256|hmac|auto --max-memory-mb 500`
- Preserve old SHA-256 default for existing traces
- Add signed `.audit.sig` or versioned record fields for new HMAC traces
- Integrate with SwarmGraph `swarmgraph_hmac` audit paths

**Files to Inspect/Change:**
- `python/src/agent_runtime_cockpit/audit/chain.py`
- `python/src/agent_runtime_cockpit/audit/key_manager.py` (new if needed)
- `python/src/agent_runtime_cockpit/cli.py` or new `cli/commands/audit.py`
- `python/src/agent_runtime_cockpit/protocol/schemas.py`
- `packages/arc-protocol-ts/src/arc-protocol-types.ts`
- `runtimes/swarmgraph/**/audit*` integration points
- `docs/adr/*audit*`, `docs/SECURITY.md`

**Success Criteria:**
- [ ] `arc audit verify` on synthetic 100 MB trace completes in <30s and <500 MB RSS
- [ ] Old SHA-256 traces verify without migration
- [ ] HMAC traces fail verification on content/chain/signature mutation
- [ ] CLI emits stable JSON: `{ ok, mode, records_checked, reason, duration_ms }`
- [ ] Key-unavailable `--mode hmac` returns typed error, not crash

**Testing Requirements:**
- Canonical JSON hash stability tests
- Large-trace benchmark fixture (100 MB JSONL)
- Tamper tests: event mutation, chain deletion, line reordering, signature mismatch
- Key-unavailable test in `--mode hmac`
- Memory profiling under load

**Backward Compatibility:**
- No forced migration. `audit_level = arc_sha256` remains valid
- New signed runs advertise `swarmgraph_hmac` or `arc_hmac` only when keys present

**Strategic Value:** ⭐⭐⭐⭐⭐  
Audit credibility is the foundation for everything else. Without streaming verification and HMAC, large-trace auditing is broken and audit claims are weakened.

---

### F0.2: Discriminated RunEvent Unions + Protocol Conformance

**Priority:** P0 (Critical — Foundation)  
**Status:** Not Started  
**Effort:** 6 engineer-days  
**Owner:** Protocol Team  
**Dependencies:** None  
**Source:** Architecture Review Section 5, P0-2

**Problem:**  
`RunEvent` is `type: string` with `data: Record<string, unknown>`. This forces unsafe consumers in widgets, adapters, AG-UI mappers, and tests. No exhaustive handling is possible.

**Technical Scope:**
- Introduce `KnownRunEvent` discriminated union in TypeScript
- Define typed payloads for at least: `RUN_STARTED`, `RUN_COMPLETED`, `RUN_FAILED`, `STEP_STARTED`, `STEP_COMPLETED`, `TOOL_CALL`, `TOOL_RESULT`, `HITL_PROMPT`, `HITL_DECISION`, `AUDIT_RECORD`, `TOKEN_USAGE`, `RUNTIME_WARNING`, `RAW`
- Add helpers: `isEventOfType(event, type)`, `assertNeverEvent(event)`, `parseEvent(raw)`
- Generate or mirror Python schemas to avoid cross-language drift
- Convert all widget and mapper consumers away from `any` and `Record<string, unknown>`
- Add shared protocol conformance fixtures (`protocol/fixtures/`)

**Files to Inspect/Change:**
- `packages/arc-protocol-ts/src/arc-protocol-types.ts`
- `packages/arc-extension/src/**`
- `packages/arc-ag-ui/src/**`
- `python/src/agent_runtime_cockpit/protocol/schemas.py`
- `protocol/fixtures/**`
- All test files consuming `RunEvent`

**Success Criteria:**
- [ ] `pnpm check:pr` and TypeScript strict typecheck pass with no unsafe `RunEvent.data` access
- [ ] Unknown future events represented as `RAW` without crashing UI
- [ ] All protocol fixtures round-trip through Python and TypeScript
- [ ] Widget and mapper consumers use typed narrowing, not `any`

**Testing Requirements:**
- Type-level tests for event narrowing
- Fixture compatibility tests for schema v1 → v2 migration
- UI tests for HITL, audit, token usage, and warning events
- Cross-language fixture round-trip tests

**Backward Compatibility:**
- Keep `EVENT_SCHEMA_VERSION = 2`
- Parse legacy events into typed schema v2 where possible
- Unknown future schemas become `RAW`

**Strategic Value:** ⭐⭐⭐⭐⭐  
Fixes the unsafe protocol boundary across the entire product. Every consumer benefits.

---

### F0.3: Enforced Workspace Trust + Paid-Call Gates + Runtime Safety

**Priority:** P0/P1 (Critical — Safety)  
**Status:** Not Started  
**Effort:** 7 engineer-days  
**Owner:** Security Team  
**Dependencies:** None  
**Source:** Architecture Review Section 5, P0-3

**Problem:**  
ARC names workspace trust and paid-call gating, but they are labels, not enforcement points. Untrusted workspaces can still trigger runtime execution, MCP server activation, shell commands, and provider-backed calls.

**Technical Scope:**
- Centralize `TrustState` and `PaidCallPolicy` in protocol package
- Require explicit trust for: runtime execution, provider-backed calls, MCP server start, workspace prompt loading, shell-command execution
- Add confirmation UI with command descriptions for shell/runtime actions
- Add CLI `--allow-paid`, `--trust-workspace`, and `--dry-run` semantics consistently
- Make all blocked actions return typed denial events, not silent no-ops
- Align with Theia 1.71 Workspace Trust patterns

**Files to Inspect/Change:**
- `packages/arc-extension/src/browser/**trust**`
- `packages/arc-extension/src/common/arc-protocol.ts`
- `python/src/agent_runtime_cockpit/security/**`
- `python/src/agent_runtime_cockpit/adapters/**`
- `python/src/agent_runtime_cockpit/isolation/**`
- `docs/SECURITY.md`

**Success Criteria:**
- [ ] Untrusted workspace: run, paid calls, MCP serve, workspace prompt load, shell commands are blocked with typed reasons
- [ ] Trusted workspace: actions proceed only after paid-call/shell approval when required
- [ ] UI shows trust and paid-call state before execution
- [ ] Denied actions produce typed events, not silent no-ops
- [ ] CLI `--allow-paid` and `--trust-workspace` work consistently

**Testing Requirements:**
- Workspace trust unit tests
- End-to-end UI tests for restricted mode
- CLI tests for `--allow-paid` and denial JSON
- Adapter contract tests: provider-backed runtimes blocked without gates

**Backward Compatibility:**
- Default to safe restricted behavior for new/unknown workspaces
- Migration notice for existing local workspaces

**Strategic Value:** ⭐⭐⭐⭐⭐  
Safety gates are enforcement points, not labels. This is non-negotiable for 1.0.

---

## Phase 1: IDE + CLI Hardening

> **Source:** Architecture Review P1-4, P1-5. Missing from original feature list.

### F1.1: Trace Viewer Virtualization + Daemon Resilience

**Priority:** P1 (Required)  
**Status:** Not Started  
**Effort:** 5 engineer-days  
**Owner:** Frontend Team  
**Dependencies:** None  
**Source:** Architecture Review Section 5, P1-4

**Problem:**  
Trace viewer performs eager `filteredTraces.map(...)` over all filtered traces — unacceptable for large stores. Daemon disconnect causes hung promises.

**Technical Scope:**
- Replace eager list rendering with virtualization (`react-window` or Theia virtual list)
- Add incremental trace pagination from daemon: `offset`, `limit`, `filter`, `sort`
- Add reconnect/backoff hook for event streams
- Add bounded client-side event queue and dropped-event warning
- Use ANSI-aware output rendering for agent logs

**Files to Inspect/Change:**
- `packages/arc-extension/src/browser/components/TraceViewerSection.tsx`
- `packages/arc-extension/src/browser/hooks/useResilientSSE.ts` (new)
- `packages/arc-extension/src/browser/services/**`
- Daemon endpoint/event streaming code

**Success Criteria:**
- [ ] 50k trace rows render without browser freeze
- [ ] Filtering stays interactive: <200ms p95 for local metadata
- [ ] Killing daemon shows reconnecting state within 2s, recovers without page reload
- [ ] No unresolved RPC promises after daemon disconnect

**Testing Requirements:**
- Component tests with 50k fake traces
- Playwright test for daemon kill/restart recovery
- Backpressure test for bursty events
- Accessibility checks for virtualized list navigation

**Strategic Value:** ⭐⭐⭐⭐  
Required for large trace stores and reliable IDE performance.

---

### F1.2: CLI Decomposition + Stable JSON Contracts + `arc doctor`

**Priority:** P1 (Required)  
**Status:** Not Started  
**Effort:** 6 engineer-days  
**Owner:** Backend Team  
**Dependencies:** None  
**Source:** Architecture Review Section 5, P1-5

**Problem:**  
CLI is too large for maintainability. No stable JSON output contracts. `arc doctor` is incomplete. Adding MCP, richer audit, eval, and isolation commands requires decomposition first.

**Technical Scope:**
- Create command modules: `serve.py`, `run.py`, `runs.py`, `audit.py`, `hitl.py`, `eval.py`, `runtimes.py`, `doctor.py`, `mcp.py`
- Keep existing Typer command names and options
- Add stable JSON schema snapshots for major CLI outputs
- Make `arc doctor --json` report: versions, daemon, adapters, trust, isolation, paid-call gates, MCP support, known blockers

**Files to Inspect/Change:**
- `python/src/agent_runtime_cockpit/cli.py`
- New `python/src/agent_runtime_cockpit/cli/commands/*.py`
- `python/tests/test_cli_*.py`
- `scripts/generate-runtime-table.sh`
- CLI docs

**Success Criteria:**
- [ ] Existing documented commands still work identically
- [ ] `arc --help` retains user-facing command structure
- [ ] `arc doctor --json` is deterministic and snapshot-tested
- [ ] CLI modules each stay below maintainability threshold, no circular imports
- [ ] JSON schema snapshots exist for major outputs

**Testing Requirements:**
- Typer CLI runner tests for each command group
- JSON schema snapshot tests
- Backward-compat command alias tests

**Backward Compatibility:**
- Preserve all public commands
- Deprecated aliases for one minor release with warnings

**Strategic Value:** ⭐⭐⭐⭐  
Required before adding MCP, richer audit, eval, and isolation commands.

---

## Phase 2: MCP Local Control Plane

> **Source:** Both documents. Architecture review narrows MCP scope: expose ARC as a local control plane, not a standalone SwarmGraph product surface. Start with stdio, not HTTP.

### F2.1: MCP Local Control Plane for ARC + Narrow SwarmGraph Wrapper

**Priority:** P1 (Important)  
**Status:** Not Started  
**Effort:** 8 engineer-days  
**Owner:** Backend Team  
**Dependencies:** F0.3 (Trust Enforcement), F1.2 (CLI Decomposition)  
**Source:** Architecture Review P1-6, merged with Feature List F1.1

**Description:**  
Expose ARC as a local MCP control plane over existing capabilities, with narrow SwarmGraph wrappers. MCP is a local control plane, not a cloud pivot. SwarmGraph tools are wrapped through ARC rather than making SwarmGraph the product control surface.

**Critical Design Decision (from review):**  
> "Expose ARC as a local MCP control plane first; wrap SwarmGraph tools/resources through ARC rather than making SwarmGraph the product control surface."

**Technical Scope:**
- New `python/src/agent_runtime_cockpit/mcp/server.py`
- New `python/src/agent_runtime_cockpit/cli/commands/mcp.py`
- **Start with `arc mcp serve --stdio` first**
- Add `arc mcp serve --http 127.0.0.1:<port>` later only after auth/trust policy defined
- **No HTTP binding beyond loopback without explicit auth decision**

**MCP Tools (ARC-level):**
- `arc_run` — start a run via any configured adapter
- `arc_run_status` — check run status
- `arc_trace_search` — search local trace store
- `arc_trace_read` — read specific trace
- `arc_audit_verify` — verify audit chain
- `arc_hitl_list` — list pending HITL prompts
- `arc_hitl_respond` — respond to HITL prompt
- `arc_runtime_capabilities` — list adapter capabilities
- `arc_doctor` — run diagnostic checks

**MCP Resources (ARC-level):**
- `arc://runs/{run_id}` — run metadata
- `arc://traces/{run_id}` — trace data
- `arc://audit/{run_id}` — audit chain
- `arc://runtimes/{runtime_id}/capabilities` — adapter capabilities

**SwarmGraph Wrappers (narrow):**
- `swarmgraph_run` — wraps SwarmGraph consensus execution
- `swarmgraph_status` — wraps SwarmGraph run status
- `swarmgraph_audit_verify` — wraps SwarmGraph audit chain verification

**Success Criteria:**
- [ ] `arc mcp serve --stdio` works from Claude Desktop / Codex-style local MCP clients
- [ ] Tools are **disabled in untrusted workspaces**
- [ ] MCP resource reads are local-only and redacted where configured
- [ ] No HTTP binding beyond loopback without explicit auth decision
- [ ] SwarmGraph tools wrap CLI/adapter behavior, not replace it

**Testing Requirements:**
- MCP stdio integration test
- Tool schema validation tests
- Trust denial test for MCP activation in untrusted workspace
- Resource path traversal tests (security)

**Backward Compatibility:**
- Additive feature; no existing CLI behavior changes
- MCP server disabled unless explicitly invoked

**Strategic Value:** ⭐⭐⭐⭐⭐  
Opens ARC to entire MCP ecosystem while maintaining local-first, trust-gated posture.

---

### F2.2: MCP Tasks for Async Execution

**Priority:** P1 (Important)  
**Status:** Not Started  
**Effort:** 5 engineer-days  
**Owner:** Backend Team  
**Dependencies:** F2.1 (MCP Server)  
**Source:** Feature List F1.2, narrowed by Architecture Review

**Description:**  
Implement ARC async task registry for long-running operations. Do not claim specific MCP SEP-1686 compliance until the exact public spec is pinned.

**Architecture Review Correction:**
> "Implement ARC async task registry now; do not claim specific SEP compliance until the exact public spec is pinned."

**Technical Scope:**
- ARC-level task registry (not MCP-specific initially)
- Task state machine: `pending` → `running` → `completed`/`failed`/`cancelled`
- Task result storage (SQLite)
- Configurable task expiry (default 24 hours)
- Retry policy support (exponential backoff, max 3 retries)
- SSE notifications for task state changes
- Surface via MCP tools when MCP server is active

**Success Criteria:**
- [ ] Client creates task and receives task ID immediately
- [ ] Client polls task status
- [ ] Task results include run outcome, audit chain, cost breakdown
- [ ] Failed tasks retry with exponential backoff
- [ ] Expired tasks return typed error
- [ ] Works via CLI, MCP, and daemon API

**Strategic Value:** ⭐⭐⭐⭐  
Essential for long-running SwarmGraph consensus and HITL workflows.

---

## Phase 3: Replay + Adapter + Eval Accuracy

> **Source:** Architecture Review P1-7, P1/P2-8. Missing from original feature list.

### F3.1: LangGraph Durable Execution + Replay Contract Update

**Priority:** P1 (Required)  
**Status:** Not Started  
**Effort:** 7 engineer-days  
**Owner:** Core Team  
**Dependencies:** F0.2 (RunEvent Unions)  
**Source:** Architecture Review Section 5, P1-7

**Problem:**  
LangGraph durable execution depends on persistence/checkpointers, thread IDs, and wrapping side effects. ARC must not claim exact replay/resume if those conditions are not met.

**Technical Scope:**
- Add `ReplayCapability` fields: `can_replay_trace`, `can_resume_checkpoint`, `requires_thread_id`, `side_effects_wrapped`, `determinism_level`
- Detect LangGraph checkpointer/thread configuration where possible
- Emit warnings when adapter can inspect but not safely resume
- Add replay report: what was replayed, simulated, skipped, and why
- Distinguish: "replay trace" / "resume workflow" / "simulate from trace" / "rerun from checkpoint"

**Files to Inspect/Change:**
- `python/src/agent_runtime_cockpit/adapters/langgraph*.py`
- `python/src/agent_runtime_cockpit/replay/**`
- `python/src/agent_runtime_cockpit/protocol/schemas.py`
- `packages/arc-protocol-ts/src/arc-protocol-types.ts`
- `runtimes/swarmgraph/**` adapter boundary docs

**Success Criteria:**
- [ ] LangGraph projects with checkpointer + thread ID report resumable
- [ ] Projects without durable config report inspect-only or simulated replay
- [ ] Side-effecting steps flagged unless wrapped/declared idempotent
- [ ] Replay report clearly states what is exact, simulated, skipped, unsafe

**Testing Requirements:**
- Fixture LangGraph projects: no checkpointer, checkpointer only, checkpointer + thread ID, side-effecting node
- Replay determinism tests
- UI tests for replay capability warnings

**Strategic Value:** ⭐⭐⭐⭐  
Prevents overclaiming replay capabilities. Builds trust with users.

---

### F3.2: Persistent HITL + Inspect-Style Eval Artifacts

**Priority:** P1/P2 (Required)  
**Status:** Not Started  
**Effort:** 8 engineer-days  
**Owner:** Backend + Frontend Team  
**Dependencies:** F0.1 (Streaming Audit), F0.2 (RunEvent Unions)  
**Source:** Architecture Review Section 5, P1/P2-8

**Problem:**  
HITL state is transient (lost on daemon restart). Eval artifacts are not repeatable or comparable. Both need to become persistent, audit-linked evidence.

**Technical Scope:**
- Store HITL prompts and decisions in SQLite with run IDs, timestamps, actor, decision, reason, audit hash
- Add `arc hitl pending --json`, `arc hitl respond <id> --approve|--reject --reason`
- Define ARC eval artifact schema:
  - `eval_spec`, `dataset_ref`, `runtime_adapter`, `solver_or_workflow`
  - `scorer`, `samples`, `scores`, `trace_refs`, `audit_refs`
- Optional export to Inspect AI-compatible directory/log shape
- HITL prompts survive daemon restart

**Success Criteria:**
- [ ] HITL prompt survives daemon restart and is answerable by CLI or IDE
- [ ] HITL decisions are audit-linked
- [ ] `arc eval run --batch --json` produces repeatable artifact paths
- [ ] Eval reports can compare two runs on same dataset

**Testing Requirements:**
- SQLite persistence tests
- Daemon restart + pending HITL test
- Eval artifact schema snapshot tests
- Golden trace comparison tests

**Backward Compatibility:**
- Existing transient HITL remains for one release, new runs use persistent store
- Eval exports are additive

**Strategic Value:** ⭐⭐⭐⭐  
Converts HITL and eval from ad hoc UI state into repeatable evidence.

---

## Phase 4: SwarmGraph Differentiators

> **Source:** Both documents agree on these features. Architecture review says "apply after foundations." Consensus Escrow and Adaptive Consensus are unique differentiators no other framework has.

### F4.1: Consensus Escrow (Commit-Reveal Voting)

**Priority:** P2 (Differentiator — after foundations)  
**Status:** Not Started  
**Effort:** 4 engineer-days  
**Owner:** SwarmGraph Core Team  
**Dependencies:** F0.1 (Streaming Audit — must be solid first)  
**Source:** Feature List F2.1, confirmed by Architecture Review P2-9

**Description:**  
Cryptographic commit-reveal voting protocol to prevent vote manipulation and ensure provably honest consensus. **Unique feature — no other agent framework has this.**

**Architecture Review Correction:**
> "Use `hash(canonical_vote || nonce)` — canonical serialization matters, not just SHA-256 of raw bytes."

**Technical Scope:**
- New module: `swarm-shared/consensus_escrow.py`
- `CommitRevealVote` Pydantic model (frozen=True)
- `ConsensusEscrow` class: commit / reveal / verify / tally
- Commit: `hash(canonical_json(vote) || nonce)` — canonical serialization
- Reveal: vote + nonce → recompute hash → compare
- Opt-in via `--consensus-escrow` flag or adaptive high-risk selection
- Audit chain records commit and reveal events
- Existing consensus protocols unchanged when escrow disabled

**Implementation:**
```python
class CommitRevealVote(BaseModel, frozen=True):
    worker_id: str
    commit_hash: str  # SHA-256(canonical_json(vote) || nonce)
    commit_timestamp: datetime
    revealed_vote: Optional[ConsensusVote] = None
    revealed_nonce: Optional[str] = None
    reveal_timestamp: Optional[datetime] = None
    phase: Literal["committed", "revealed", "verified", "invalid"]

class ConsensusEscrow:
    def commit(self, worker_id: str, vote: ConsensusVote, nonce: str) -> CommitRevealVote
    def reveal(self, worker_id: str, vote: ConsensusVote, nonce: str) -> CommitRevealVote
    def verify(self, worker_id: str) -> bool
    def tally(self) -> ConsensusResult
    def get_audit_records(self) -> list[AuditEvent]
```

**Success Criteria:**
- [ ] Worker cannot change vote after commit without verification failure
- [ ] Audit chain records commit and reveal timestamps
- [ ] Existing protocols run unchanged when escrow disabled
- [ ] Adversarial tests: 5 scenarios all pass
- [ ] Performance overhead <10% vs standard consensus

**Testing Requirements:**
- Unit tests: commit, reveal, verify, tally (20 tests)
- Adversarial tests: vote manipulation attempts (5 scenarios)
- Integration with Raft, BFT, simple-majority
- Performance benchmarks: 2-10 workers
- Canonical JSON hash stability tests

**Strategic Value:** ⭐⭐⭐⭐⭐  
**Killer feature for regulated environments.** Provable vote integrity is unique in agent space. Quick win (4 days) with massive differentiation.

---

### F4.2: Adaptive Consensus Protocol (Conservative Version)

**Priority:** P2 (Differentiator — after escrow)  
**Status:** Not Started  
**Effort:** 10 engineer-days  
**Owner:** SwarmGraph Core Team  
**Dependencies:** F4.1 (Consensus Escrow)  
**Source:** Feature List F2.2, corrected by Architecture Review P2-10

**Description:**  
Dynamic consensus protocol selection based on task risk. **No other framework does automatic protocol selection.**

**Architecture Review Corrections:**
> 1. "Add deterministic heuristic risk assessor first, not LLM-only risk scoring."
> 2. "Require user confirmation for high/critical risk."
> 3. "User can override protocol with audit record."

**Technical Scope:**
- **Deterministic heuristic risk assessor** (not LLM-based):
  - Inputs: task text, workspace trust, file types, target runtime, paid-call status, production/deploy/security/finance keywords
  - Outputs: risk level, recommended protocol, worker count, HITL requirement, anti-drift setting, cost estimate, rationale
- Protocol selection matrix
- User confirmation for high/critical risk
- User override with audit record
- Cost estimate before run
- Dynamic escalation on consensus failure

**Protocol Selection Matrix:**
| Risk Level | Protocol | Min Workers | HITL | Anti-Drift | Cost Multiplier |
|---|---|---|---|---|---|
| Low | Simple Majority | 2 | No | Off | 1.0x |
| Medium | Raft | 3 | Optional | Keyword | 1.5x |
| High | BFT | 4 | Required | Embedding | 2.0x |
| Critical | BFT + Escrow | 5 | Required | Embedding | 2.5x |

**Success Criteria:**
- [ ] 100 labeled prompt fixtures classify at 90%+ agreement with expected risk
- [ ] User can override protocol with audit record
- [ ] Cost estimate appears before run
- [ ] Deterministic heuristics (no LLM dependency for risk assessment)
- [ ] Audit chain records risk assessment, selection, and any override

**Testing Requirements:**
- 100-prompt validation dataset with manual labels
- Deterministic heuristic tests (no randomness)
- Cost accuracy tests (estimated vs actual)
- Override + audit record tests
- Escalation scenario tests

**Strategic Value:** ⭐⭐⭐⭐⭐  
**Major differentiator.** "Right tool for the job" automatically. Aligns with audit-first positioning.

---

## Phase 5: Enterprise Features

### F5.1: Event-Driven Audit/HITL Notifications (Local-First)

**Priority:** P2 (Enterprise Value)  
**Status:** Not Started  
**Effort:** 5 engineer-days  
**Owner:** Backend Team  
**Dependencies:** F3.2 (Persistent HITL)  
**Source:** Feature List F3.1, narrowed by Architecture Review P2-11

**Architecture Review Correction:**
> "Use local event hooks and optional signed webhooks for teams, but not turn into a SaaS notification platform."

**Technical Scope:**
- Local event bus for: `hitl_required`, `hitl_decided`, `audit_verified`, `run_completed`, `run_failed`, `quota_warning`
- IDE badges and CLI watch mode (`arc events watch`)
- Optional signed webhook endpoints configured per workspace
- Retry with bounded exponential backoff and local dead-letter log
- HMAC-signed payloads for webhook verification

**Success Criteria:**
- [ ] HITL badge updates without manual refresh
- [ ] `arc events watch` streams typed events
- [ ] Webhook payloads are HMAC-signed if configured
- [ ] Dead letter queue captures permanent failures
- [ ] Rate limiting prevents webhook spam

**Testing Requirements:**
- Event bus unit tests
- IDE badge update tests
- Webhook delivery + retry tests
- HMAC verification tests

**Strategic Value:** ⭐⭐⭐⭐  
Enables enterprise compliance integration without SaaS sprawl.

---

## Phase 6: Research & Future

### F6.1: Swarm Memory Graph

**Priority:** P3 (Research)  
**Status:** Research Phase  
**Effort:** 4-6 weeks (after validation)  
**Owner:** Research Team  
**Dependencies:** None  
**Source:** Both documents. Both agree: research only, high risk.

**Architecture Review Concern:**
> "High risk of memory pollution, privacy leakage, and unverifiable 'learning.' Next step: design doc + prototype on 10 sanitized runs only."

**Research Questions:**
- What constitutes a "useful" memory?
- How to prevent memory pollution?
- How to isolate tenants/workspaces?
- How to redact sensitive content in memories?
- How to prove retrieved memory improves outcomes rather than biasing consensus?

**Next Steps:**
1. Design document with memory schema (1 week)
2. Prototype on 10 sanitized runs (2 weeks)
3. Evaluate: do memories improve outcomes? (1 week)
4. Decision point: proceed or pivot

---

### F6.2: Skill-Based Agent Capabilities

**Priority:** P4 (Deferred)  
**Status:** Monitoring  
**Effort:** 3-4 weeks (after spec stabilizes)  
**Owner:** TBD  
**Dependencies:** MCP Skills WG specification

**Architecture Review Concern:**
> "Dynamic skill loading needs a stable spec, sandboxing, trust levels, version constraints, and permission boundaries. It also increases attack surface."

**Action:** Monitor MCP Skills WG. Revisit after trust/isolation gates are fully enforced.

---

### F6.3: Stateless Session Support

**Priority:** P5 (Deferred)  
**Status:** Deferred  
**Effort:** 4-6 weeks  
**Owner:** TBD  
**Dependencies:** Scale requirement

**Architecture Review Concern:**
> "ARC is local-first single-user loopback; distributed state is premature."

**Action:** Revisit if multi-user/server deployment becomes a product goal.

---

### F6.4: Deep Agents-Style Planning Layer

**Priority:** Rejected for 1.0  
**Status:** Rejected  
**Source:** Architecture Review Section 6

**Architecture Review Decision:**
> "A planning layer would pull SwarmGraph toward generic agent orchestration. SwarmGraph's best differentiation is provable consensus, not broad autonomous planning. Keep planning outside SwarmGraph unless a user's own workflow explicitly composes it."

---

## Implementation Order (Minimizes Breakage)

This order comes from the Architecture Review Section 7 and is the correct implementation sequence:

```
Step 1: Protocol + Audit Foundations                    [F0.1, F0.2]
        Streaming audit verifier, HMAC signing,
        discriminated RunEvent unions, protocol fixtures

Step 2: Safety Gates + Trust Enforcement                [F0.3]
        Workspace Trust, paid-call gating,
        MCP/runtime/shell blocking in restricted mode

Step 3: IDE Scale + Daemon Resilience                   [F1.1]
        Trace virtualization, event pagination,
        reconnect/backpressure handling

Step 4: CLI Maintainability                             [F1.2]
        Split command modules, stable JSON schemas,
        arc doctor --json

Step 5: MCP Local Control Plane                         [F2.1, F2.2]
        arc mcp serve --stdio, ARC tools/resources,
        narrow SwarmGraph wrapper, async task registry

Step 6: Replay + Adapter Accuracy                       [F3.1]
        LangGraph durable execution detection,
        replay report, adapter conformance suite

Step 7: HITL/Eval Evidence Layer                        [F3.2]
        Persistent HITL store, eval artifacts,
        eval comparison reports

Step 8: SwarmGraph Differentiators                      [F4.1, F4.2]
        Consensus Escrow, Adaptive Consensus

Step 9: Enterprise Notifications                        [F5.1]
        Event-driven audit/HITL, local-first webhooks

Step 10: Research / Future                              [F6.1-F6.4]
         Memory Graph prototype, Skills monitoring
```

---

## Implementation Timeline

### Weeks 1-2: Protocol + Audit Foundations (P0)
- **Week 1:** F0.1 Streaming Audit + HMAC (5 days)
- **Week 2:** F0.2 Discriminated RunEvent Unions (6 days, overlapping)

### Week 3: Safety Gates (P0/P1)
- **Week 3:** F0.3 Trust Enforcement + Paid-Call Gates (7 days)

### Weeks 4-5: IDE + CLI Hardening (P1)
- **Week 4:** F1.1 Trace Virtualization + Daemon Resilience (5 days)
- **Week 5:** F1.2 CLI Decomposition + `arc doctor` (6 days)

### Weeks 6-7: MCP Local Control Plane (P1)
- **Week 6:** F2.1 MCP Server (stdio + tools) (5 days)
- **Week 7:** F2.1 MCP Server (resources + SwarmGraph wrapper) + F2.2 Tasks (5 days)

### Weeks 8-9: Replay + HITL/Eval (P1/P2)
- **Week 8:** F3.1 LangGraph Replay Contract (7 days)
- **Week 9:** F3.2 Persistent HITL + Eval Artifacts (8 days, overlapping)

### Weeks 10-12: SwarmGraph Differentiators (P2)
- **Week 10:** F4.1 Consensus Escrow (4 days)
- **Weeks 11-12:** F4.2 Adaptive Consensus (10 days)

### Week 13: Enterprise Notifications (P2)
- **Week 13:** F5.1 Event-Driven Notifications (5 days)

### Weeks 14+: Research (P3+)
- F6.1 Swarm Memory Graph (prototype + evaluation)
- Ongoing: F6.2 Skills monitoring, F6.3/F6.4 deferred

---

## Feature Summary Table

| ID | Feature | Priority | Effort | Phase | Status | Source |
|---|---|---|---|---|---|---|
| F0.1 | Streaming Audit + HMAC | P0 | 5d | 0 | Not Started | Review P0-1 |
| F0.2 | Discriminated RunEvent Unions | P0 | 6d | 0 | Not Started | Review P0-2 |
| F0.3 | Trust + Paid-Call Enforcement | P0/P1 | 7d | 0 | Not Started | Review P0-3 |
| F1.1 | Trace Virtualization + Daemon | P1 | 5d | 1 | Not Started | Review P1-4 |
| F1.2 | CLI Decomposition + Doctor | P1 | 6d | 1 | Not Started | Review P1-5 |
| F2.1 | MCP Local Control Plane | P1 | 8d | 2 | Not Started | Both (merged) |
| F2.2 | MCP Async Task Registry | P1 | 5d | 2 | Not Started | Both (narrowed) |
| F3.1 | LangGraph Replay Contract | P1 | 7d | 3 | Not Started | Review P1-7 |
| F3.2 | Persistent HITL + Eval | P1/P2 | 8d | 3 | Not Started | Review P1/P2-8 |
| F4.1 | Consensus Escrow | P2 | 4d | 4 | Not Started | Both (confirmed) |
| F4.2 | Adaptive Consensus | P2 | 10d | 4 | Not Started | Both (corrected) |
| F5.1 | Event-Driven Notifications | P2 | 5d | 5 | Not Started | Both (narrowed) |
| F6.1 | Swarm Memory Graph | P3 | 4-6w | 6 | Research | Both (deferred) |
| F6.2 | Skill-Based Capabilities | P4 | 3-4w | 6 | Monitoring | Both (deferred) |
| F6.3 | Stateless Sessions | P5 | 4-6w | 6 | Deferred | Both (deferred) |
| F6.4 | Deep Agents Planning | Rejected | — | — | Rejected | Review (rejected) |

**Total P0-P2 Effort:** ~76 engineer-days (~15 weeks)

---

## Open Questions (from Architecture Review)

These must be resolved during implementation:

1. **Audit reconciliation:** Should ARC wrap SwarmGraph audit chains, ingest them as nested evidence, or verify independently and link by hash?
2. **Replay semantics:** What user-facing language distinguishes "replay trace," "resume workflow," "simulate from trace," and "rerun from checkpoint"?
3. **Electron strategy:** Is Electron a supported 1.0 target or an experimental packaging path?
4. **MCP HTTP auth:** Should Streamable HTTP be limited to `127.0.0.1`, or support remote binding with bearer/OAuth and explicit workspace trust?
5. **SwarmGraph task ownership:** Should async swarm state live in ARC's task registry, SwarmGraph's gateway, or both with clear ownership boundaries?
6. **Redaction policy:** What secret corpus and false-positive budget should define acceptable redaction behavior?
7. **Cost model:** What provider price source and refresh cadence should ARC use for pre-run estimates?
8. **Protocol generation:** Should Python Pydantic schemas generate TypeScript types, or should TypeScript remain source-of-truth with fixture conformance?

---

## Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Audit streaming breaks existing SHA-256 traces | Medium | High | Preserve old default, no forced migration |
| RunEvent union migration breaks consumers | High | High | Phased rollout, `RAW` fallback for unknowns |
| Trust enforcement frustrates users | Medium | Medium | Clear UX, migration notice, explicit elevation |
| Trace virtualization breaks accessibility | Low | Medium | Accessibility checks in tests |
| CLI split breaks existing scripts | Medium | High | Preserve commands, alias deprecated for 1 release |
| MCP exposes too much in untrusted workspace | Medium | High | Tools disabled in untrusted mode |
| Consensus Escrow performance overhead | Low | Medium | Benchmark early, parallel verification |
| Adaptive Consensus risk misclassification | Medium | High | Conservative rules, user override, audit trail |
| Memory Graph quality/privacy | High | High | Prototype-only, sanitized runs, decision gate |
| MCP SDK breaking changes | Medium | Medium | Pin versions, monitor changelog |

---

## Success Metrics

### Phase 0-1 (Foundations)
- `arc audit verify` handles 100 MB traces in <30s, <500 MB RSS
- Zero `any`/`Record<string, unknown>` in RunEvent consumers
- Untrusted workspace blocks all runtime/MCP/shell actions with typed reasons
- 50k trace rows render without browser freeze

### Phase 2-3 (Platform)
- MCP stdio server works from Claude Desktop + 2 other MCP clients
- LangGraph replay claims match actual capability with test fixtures
- HITL prompts survive daemon restart
- Eval artifacts are repeatable and comparable

### Phase 4-5 (Differentiators)
- Consensus Escrow: 100% adversarial test pass rate
- Adaptive Consensus: 90%+ prompt classification accuracy on 100-label dataset
- Event-driven HITL badges update without manual refresh
- User feedback: "This is unique, no other framework has this"

### Overall
- ARC Studio positioned as credible, audit-first agent cockpit
- SwarmGraph positioned as provably-honest consensus framework
- No overclaims about replay, adoption, or provider-backed execution
- 1.0 release passes architecture review without critical findings

---

## Change Log

| Date | Version | Changes |
|---|---|---|
| 2026-05-22 | 1.0 | Initial feature list (research-driven) |
| 2026-05-22 | 2.0 | Merged with Architecture Review: added 7 foundation items (F0.1-F0.3, F1.1-F1.2, F3.1-F3.2), corrected MCP priority P0→P1, narrowed MCP scope to local control plane, added open questions, corrected Adaptive Consensus to deterministic heuristics, rejected Deep Agents planning layer |

---

**Document Status:** APPROVED — Ready for implementation  
**Next Review:** 2026-05-29  
**Implementation Start:** Phase 0, Week 1

---

## Runtime Pack SDK (Phase RP-1)

**Status:** Implemented (patch series 0001–0008)  
**Priority:** P1  
**Constraint:** Local-first MVP; no network, no code execution, no dynamic import.

### Feature Summary

The Runtime Pack SDK adds a static, fail-closed discovery layer for runtime adapters. A runtime pack is a version-pinned JSON file (`arc-runtime-pack.json`) that fully describes a runtime's identity, permissions, capabilities, entrypoints, MCP/IR/policy claims, and security surface — without ARC having to hard-code any runtime-specific knowledge into the core codebase.

### Core Components

| Component | Location | Purpose |
|---|---|---|
| `models.py` | `runtime_packs/` | Typed Pydantic models for all manifest sub-structures |
| `hashing.py` | `runtime_packs/` | Deterministic sha256 over canonical JSON (volatile keys excluded) |
| `redaction.py` | `runtime_packs/` | Secret pattern detection; manifest redaction before registry write |
| `validation.py` | `runtime_packs/` | 12 static rules (R1–R12); fail-closed, no I/O |
| `loader.py` | `runtime_packs/` | JSON load, schema check, typed model, inspection summary |
| `registry.py` | `runtime_packs/` | Workspace registry: install (metadata only), list, drift, uninstall |
| `scaffold.py` | `runtime_packs/` | Scaffold minimal valid pack; hash-pinned at creation |
| `exporters.py` | `runtime_packs/` | Optional integrations: CapabilityCard, PolicyIssue, IR compat, MCP verify |
| `cli/runtime_pack.py` | `cli/` | 7 CLI commands: init/validate/inspect/list/install/uninstall/doctor |

### Validation Rules

R1 schema_version · R2 id safety · R3 semver · R4 entrypoint safety · R5 unknown permission (fail-closed) · R6 dangerous permission reason · R7 capability→permission backing · R8 dangerous default-allow warning · R9 MCP hash pin · R10 IR version + opaque policy · R11 no secrets · R12 hash integrity

### Design Properties

- All risk flags default `false` (missing data is safe)
- Unknown permission kinds are **errors** (fail-closed, not warnings)
- Dangerous permissions (network/paid/secrets/shell/outside_workspace) require an explicit `reason`
- Install refuses any manifest that fails validation
- No `subprocess`, no `importlib.import_module`, no network, no server start
- Manifests are deterministic and hash-addressable; `created_at` and similar volatile fields excluded from hash

### TypeScript Mirror

`packages/arc-protocol-ts/src/runtime-pack.ts` provides typed interfaces matching the Python models for UI and tooling consumption.

### Documentation

- `docs/RUNTIME_PACK_SDK.md` — full developer guide
- `docs/schemas/runtime-pack.schema.json` — JSON Schema (draft-07)
- `docs/RUNTIMES.md` — updated with Runtime Pack section
