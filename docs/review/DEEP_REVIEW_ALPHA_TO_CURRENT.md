# Deep Review: ARC Studio — v0.1.0-alpha to Current

**Generated:** 2026-05-22  
**Review window:** `v0.1.0-alpha` tag → `HEAD`  
**Target:** GenSpark.ai analysis and patch suggestions  

---

## Executive Summary

ARC Studio has shipped 23 commits (83 files, +12,516 lines, -392 deletions) since the `v0.1.0-alpha` release tag. The work spans five parallel tracks: **Documentation (Phase 1, Track B)**, **Audit Chain (Phase 1, Track D)**, **Schema Audit Remediation**, **Cross-Language Test Infrastructure**, and **ADRs (Phase 1, Track E)**.

**Current health:** 1448 Python tests (1428 pass, 20 skip), 39 TypeScript tests, `pnpm check:pr` green. The codebase has grown from a functional alpha into a documented, schema-audited, audit-chain-equipped developer tool. Four of seven schema audit risks are closed.

---

## 1. Git History Summary (v0.1.0-alpha..HEAD)

| Category | Commits | Files Changed | Lines Added |
|----------|---------|---------------|-------------|
| Audit Chain (Phase 1, Track D) | 8 | 24 | ~2,300 |
| Documentation (Phase 1, Track B/C) | 11 | 17 | ~7,400 |
| Schema Audit & Fixes | 4 | 42 | ~2,680 |
| **Total** | **23** | **83** | **~12,516** |

### Tags
- `v0.1.0-alpha` — Initial release
- `v0.6.0-alpha` — (exists, not tagged in this history window)
- `v0.8.1` — Latest tag

---

## 2. Architecture & Package Structure

### Current Layout (4 packages, 26 Python modules, 18 TypeScript test files, 123 docs)

**TypeScript packages (`packages/`):**
- `arc-extension/` — Main Eclipse Theia extension (backend services + frontend widgets)
- `arc-protocol-ts/` — Standalone protocol types (no Theia dependency)
- `arc-ag-ui/` — AG-UI event mapping (swarmgraph, langgraph)
- `arc-test-fixtures/` — Test fixture projects

**Python backend (`python/src/agent_runtime_cockpit/`):**
- `protocol/` — Schema definitions (envelope, errors, run records, capability, cost records)
- `audit/` — EU AI Act audit chain (new in Phase 1)
- `adapters/` — Runtime adapters (swarmgraph, langgraph, crewai, llamaindex, openai_agents, ag2)
- `orchestration/` — Event broker, supervisor, runtime router
- `storage/` — SQLite, JSONL, indexed store
- `security/` — Trust, redaction, injection patterns, profiles
- `web/` — Aiohttp daemon (SSE, auth, routes)
- `cli_repl/` — Interactive slash commands
- `providers/` — LLM providers (anthropic, cost extraction)
- `budget/` — Budget enforcement, cost tracking
- `runtime/` — Mode enum, registry
- `isolation/` — Subprocess, Docker isolation
- `arena/` — Arena evaluation models

---

## 3. What Was Built Since Alpha

### 3.1 Audit Chain (Phase 1, Track D) — 8 Commits

**ADR-021** defines the audit chain architecture for EU AI Act compliance (433 lines).

**Implementation layers:**

| Layer | File | Lines | Description |
|-------|------|-------|-------------|
| Schema | `audit/schema.py` | 324 | 7 event types (RunStartedEvent, RunCompletedEvent, LlmRequestEvent, LlmResponseEvent, ToolCallEvent, ToolResultEvent, ErrorEvent), HMAC chain proof types |
| Storage | `audit/storage.py` | 136 | Append-only JSONL store at `~/.arc/audit/<run_id>.chain.jsonl`, key management at `~/.arc/secrets/audit_key` (mode 0600) |
| Session | `audit/session.py` | 301 | AuditSession with HMAC linkage, redaction config, cancellable writes |
| HMAC | `audit/hmac_chain.py` | (separate file) | SHA-256 chain linking, tamper detection |
| Redaction | `audit/__init__.py` | 49 | Config-based LLM payload redaction (Phase 1, D.10) |

**Adapter integration (3 adapters):**
- `adapters/swarmgraph/runner.py` — 86 lines of audit wiring
- `adapters/langgraph/runner.py` — 51 lines of audit wiring
- `adapters/crewai/runner.py` — 58 lines of audit wiring

**CLI commands (D.5-D.6):**
- `arc audit verify` — Verify HMAC chain integrity
- `arc audit export` — Export audit bundle (tarball)

**Tests:** 5 test files, 861 test lines covering schema validation, storage, session lifecycle, runner integration, redaction.

**Known gap:** LLM request/response events deferred to Phase 1.5 pending AG-UI schema extension (documented in ADR-021).

### 3.2 Documentation (Phase 1, Track B) — 11 Commits

**Diátaxis framework implementation (4 types):**

| Type | File | Lines | Status |
|------|------|-------|--------|
| Tutorial | `docs/tutorials/getting-started.md` | 104 | ✅ Complete |
| How-To | `docs/how-to/configure-provider.md` | 213 | ✅ Complete |
| How-To | `docs/how-to/inspect-trace.md` | 435 | ✅ Complete |
| How-To | `docs/how-to/respond-hitl.md` | 380 | ✅ Complete |
| How-To | `docs/how-to/run-workflow.md` | 334 | ✅ Complete |
| Explanation | `docs/explanation/architecture.md` | 400 | ✅ Complete |
| Reference | `docs/reference/cli-commands.md` | 1,410 | ✅ Complete |
| Reference | `docs/reference/error-codes.md` | 763 | ✅ Complete |
| Reference | `docs/reference/slash-commands.md` | 682 | ✅ Complete |

**Audits completed (Track C):**
- `docs/audit/empty-state-audit.md` — 552 lines (all UI tabs documented with empty/loading/error states)
- `docs/audit/slash-command-help-audit.md` — 236 lines (all slash commands inventoried)
- `scripts/audit-cli-help.py` — 140 lines (automated CLI help audit)

**ADR documentation (5 new ADRs):**

| ADR | Title | Lines | Phase |
|-----|-------|-------|-------|
| 020 | Product Path: Desktop-First, SaaS-Later | 117 | Phase 1 |
| 021 | Audit Chain Architecture (EU AI Act) | 433 | Phase 1 |
| 022 | Deprecation Policy | 164 | Phase 1 |
| 023 | Error Code Standardization | 400 | Phase 1 |

**Planning documents:**
- `docs/PHASE_1_TASKS.md` — 407 lines (detailed 12-week sprint plan)
- `docs/PATH_TO_1.0_REVIEW_PROMPT.md` — 457 lines (Phase 1-5 review criteria)

### 3.3 Schema Audit Remediation — 4 Commits

**`docs/SCHEMA_AUDIT_REPORT.md`** — 790 lines, surveying every Python ↔ TypeScript schema pair.

**Risk closure status:**

| Risk | Severity | Status | Effort | Resolution |
|------|----------|--------|--------|------------|
| **Risk 0:** Run lifecycle event naming collision | CRITICAL | ✅ Closed | ~2h | Standardized on Python vocabulary (RUN_COMPLETED/FAILED/CANCELLED). Added TS aliases. |
| **Risk 1:** Error code mismatch | MEDIUM-HIGH | ✅ Closed | ~1h | ADR-023 implemented. 16 canonical codes in Python + TypeScript. 29 TS callers migrated. |
| **Risk 2:** RuntimeCapability v2 not supported in TS | MEDIUM-HIGH | 🔄 Core done | ~1h | RuntimeMode enum, RuntimeCapabilityV2 interface, migrateV1ToV2(), 18 tests. Integration pending API exposure. |
| **Risk 3:** WorkflowNode missing source_location | MEDIUM | ✅ Closed | ~10m | SourceLocation interface added to TypeScript. |
| **Risk 4:** RunRecord missing audit_path/budget | MEDIUM | ✅ Closed | ~10m | BudgetVector + audit_path + budget fields added to RunRecord. |
| **Risk 5:** Event type registry mismatch | MEDIUM | ⏸️ Not started | 6-8h est. | 15+ event types missing in TypeScript AGUIEventType. |
| **Risk 6:** SourceType enum vs string | LOW | ⏸️ Not started | <1h | TypeScript uses string, Python uses enum. |

### 3.4 Cross-Language Test Harness

**Fixture structure (`protocol/fixtures/`):**

| Category | Fixtures | Purpose |
|----------|----------|---------|
| `arc-envelope/` | 3 | Success, error-run-failed, error-workspace-not-found |
| `run-event/` | 4 | Run-started, completed, failed, cancelled |
| `runtime-capabilities/` | 3 | V1-basic, v2-gated-local, v2-provider-backed |
| `error-codes/` | 7 | All canonical error codes with details payloads |
| `cockpit/` | N | Cockpit protocol fixtures |
| `run-record/` | N | Run record fixtures |
| `workflow/` | N | Workflow fixtures |

**Test loader utilities:**
- Python: `python/tests/fixtures/loader.py` (130 lines) — `load_fixture()`, `load_and_validate()`, `validate_round_trip()`
- TypeScript: `packages/arc-protocol-ts/src/fixtures/loader.ts` (123 lines) — Same API

**Test counts:**
- Python fixture tests: 48 passing
- TypeScript fixture tests: 21 passing (now runs via Jest)
- RuntimeCapability v2 tests: 18 passing

---

## 4. Architecture Decisions & Patterns

### 4.1 Deprecation Policy (ADR-022)

- One minor version + one patch cycle notice period
- Aliases kept during deprecation
- Deprecation warnings emitted on legacy path usage
- Adopted by ADR-023 (error codes) and ADR-018 (envelope shim)

### 4.2 Error Code Standardization (ADR-023)

- Chose **Option B** (wire compatibility): legacy TS codes keep original string values, marked `@deprecated`
- Python `ArcErrorCode.from_legacy()` — read-path normalization for older traces
- TypeScript `canonicalErrorCode()` — same function for TypeScript read paths
- 16 canonical codes, 4 deprecated TS codes
- Removal target: v0.3.0 for deprecated codes

### 4.3 RuntimeCapability v2 Schema

- Python has migrated to v2 (mode, profile_id, isolation_id, allow_paid_calls, cost_source_default, supports_cancellation, supports_streaming)
- TypeScript port complete with `migrateV1ToV2()` function
- Paid-call invariant validation: `allow_paid_calls=true` requires `mode=provider_backed`
- Currently no API endpoint exposes v2 schema (CLI returns flattened RuntimeCapabilityReport)
- Integration work deferred until endpoints emit v2

### 4.4 Audit Chain (ADR-021)

- HMAC-SHA256 per-event signing with genesis root
- Append-only JSONL storage at `~/.arc/audit/`
- Key generated at `~/.arc/secrets/audit_key` (mode 0600)
- Dual scope: lifecycle events (run lifecycle) + tool events (tool calls/results)
- LLM request/response events deferred to Phase 1.5

---

## 5. Current Test Stats

| Suite | Count | Status |
|-------|-------|--------|
| Python full suite | 1448 collected | 1428 passed, 20 skipped |
| Python fixture tests | 48 | 48 passed |
| TypeScript (arc-protocol-ts) | 39 | 39 passed |
| pnpm check:pr (typecheck + hygiene) | — | Green |

---

## 6. Known Issues & Gaps

### 6.1 Critical Gaps (Blocking)

1. **Risk 5: Event type registry mismatch** — Python has 40+ event types, TypeScript AG-UI has 34. Missing: swarmgraph topology, consensus, cost events; HITL events; cockpit contract/receipt/autopsy events; agent/node lifecycle events. (6-8h, MEDIUM severity)

2. **Risk 2 Integration** — RuntimeCapability v2 schema exists in TypeScript but no API endpoint emits v2 data yet. Integration needed when Python APIs expose v2 schema.

### 6.2 Moderate Gaps

3. **Pre-existing ruff lint issues** — 9 lint errors in audit/history files (outside recent commit scope). Tracked separately.

4. **Python CI gap** (#20): 52 web/daemon tests return HTTP 500 on Python 3.12 (all pass on Python 3.11/macOS). Suspect asyncio event loop compatibility.

5. **Node/E2E CI gap** (#19): webpack `Aborted (core dump)` on Ubuntu CI runner. Workaround: `NODE_OPTIONS=--max-old-space-size=8192`.

### 6.3 Documentation Gaps

6. **No migration guide for audit chain** — How users migrate from pre-audit to post-audit runs is undocumented.

7. **No diagram files** — Architecture overview mentions diagrams but none exist.

8. **SECURITY_AUDIT_REPORT.md** references resolved issues (U-1) but marks them stale.

### 6.4 Test Gaps

9. **Test coverage** — Branch coverage at ~67% for arc-extension. No coverage data for Python.

10. **No end-to-end audit chain test** — Tests cover individual components but no full run → audit → verify flow.

11. **TypeScript Jest coverage** — No coverage thresholds or CI enforcement for arc-protocol-ts tests.

---

## 7. Phase 1 Completion Status (from PHASE_1_TASKS.md)

### Track B — Documentation: ~90% Complete
- [x] B.1: CLI help audit
- [x] B.2: Slash command help audit
- [x] B.3: Getting Started tutorial
- [x] B.4: Architecture overview
- [x] B.5: How-To guides
- [x] B.6: Reference docs
- [ ] B.7: **Missing:** Changelog governance ADR, documentation style guide

### Track C — UX & Error Handling: ~40% Complete
- [x] C.1: Error code inventory
- [x] C.2: Empty state audit
- [ ] C.3: **Missing:** Performance budgets
- [ ] C.4: **Missing:** Accessibility audit
- [ ] C.5: **Missing:** Keyboard navigation audit

### Track D — Audit Chain: ~75% Complete
- [x] D.1: Event schema
- [x] D.2: HMAC signing/verification
- [x] D.3: Storage layer
- [x] D.4: SwarmGraph integration
- [x] D.5-D.6: CLI verify/export
- [x] D.10: Redaction config
- [ ] D.7: **Deferred:** LLM request/response events (Phase 1.5)
- [ ] D.8: **Deferred:** HITL audit events (Phase 2)
- [ ] D.9: **Deferred:** Cost audit events (Phase 2)

### Track E — Test & Schema Hygiene: ~40% Complete
- [x] ADR-022: Deprecation policy
- [x] Schema audit report
- [x] 4 of 7 schema risks closed
- [ ] Risk 5 (event type mismatch): Not started

---

## 8. Files Changed Since Alpha (Most Impactful)

| File | Δ Lines | Why It Matters |
|------|---------|----------------|
| `docs/reference/cli-commands.md` | +1,410 | Every CLI command documented |
| `docs/reference/error-codes.md` | +763 | Error code inventory |
| `docs/SCHEMA_AUDIT_REPORT.md` | +790 | Every schema gap documented |
| `docs/PHASE_1_TASKS.md` | +407 | 12-week sprint plan |
| `docs/adr/023-error-code-standardization.md` | +400 | Error code sync blueprint |
| `docs/explanation/architecture.md` | +400 | Three-layer architecture |
| `docs/adr/021-audit-chain-architecture.md` | +433 | Audit chain design |
| `python/src/agent_runtime_cockpit/audit/schema.py` | +324 | Audit event types |
| `python/src/agent_runtime_cockpit/audit/session.py` | +301 | Audit session integration |
| `packages/arc-protocol-ts/src/fixtures/loader.test.ts` | +259 | Cross-language TS tests |
| `python/tests/fixtures/test_cross_language.py` | +285 | Cross-language Python tests |

---

## 9. Specific Areas Needing GenSpark Review

### 9.1 Architecture Decisions to Validate

1. **Option B vs Option A for error code migration** — We chose wire-compatible Option B (legacy strings preserved). Is there a better migration strategy?

2. **Audit chain HMAC strategy** — SHA-256 per-event with genesis root. Is this sufficient for EU AI Act Article 16 compliance? Should we use a different chaining strategy?

3. **RuntimeCapability v2 integration** — Should we push v2 into API responses now, or wait for an adapter that needs it?

4. **Cross-language test strategy** — JSON fixtures validated independently by Python and TypeScript. Should we add a CI step that cross-validates both against each other?

### 9.2 Code Quality Concerns

5. **`arc-backend-service.ts`** — 1,769 lines, still too large despite prior refactoring. Needs further splitting.

6. **Audit adapter integration duplication** — SwarmGraph, LangGraph, and CrewAI have very similar audit wiring (~50-86 lines each). Should be unified.

7. **No audit session lifecycle management** — Sessions are created per-run but there's no global audit session registry or cleanup mechanism.

8. **Error code migration completeness** — We migrated 29 call sites. Are there edge cases where string comparison (not enum) is used that we missed?

### 9.3 Documentation Gaps

9. **No test documentation** — How to write tests, how to add fixtures, how to run specific test categories.

10. **No contribution guide** — PR workflow, commit message conventions, code review checklist.

11. **No API reference** — Auto-generated from Pydantic models? Manual?

### 9.4 Infrastructure Gaps

12. **No pre-commit hooks** — lint/format/typecheck should run before every commit.

13. **No CI for TypeScript tests** — arc-protocol-ts tests are not in CI workflow (only `pnpm test` at root includes them).

14. **`pnpm-lock.yaml` stale warning** — "Lockfile only installation will make it out-of-date" warning present.

---

## 10. Patch Suggestions Needed

### High Priority

1. **Risk 5: Event type registry sync** — Port 15+ missing event types from Python to TypeScript AGUIEventType. Add rendering for swarmgraph topology, HITL, cockpit events.

2. **arc-backend-service.ts refactoring** — Split into config-service + run-lifecycle-service (~500 lines each).

3. **Audit adapter unification** — Extract common audit pattern from 3 adapters into a mixin or decorator.

4. **TypeScript CI integration** — Add arc-protocol-ts Jest tests to CI workflow.

### Medium Priority

5. **Documentation diagrams** — Architecture diagram for `docs/explanation/architecture.md`.

6. **Contribution guide** — `docs/CONTRIBUTING.md` with PR workflow, commit conventions.

7. **Performance budgets** — Track page load time, build time, test execution time.

8. **Accessibility audit** — WCAG compliance check for Theia widgets.

### Lower Priority

9. **Pre-commit hooks** — Husky + lint-staged for lint/format/typecheck.

10. **Coverage thresholds** — Enforce minimum branch coverage.

11. **pnpm-lock.yaml cleanup** — Resolve stale lockfile warning.

---

## 11. Appendix: Key Metrics

| Metric | Value |
|--------|-------|
| Python modules | 26 packages |
| Python tests | 1448 (1428 pass) |
| TypeScript packages | 4 |
| TypeScript tests | 39 (arc-protocol-ts) + 581 (arc-extension) = 620 total |
| ADRs | 23 (1-23) |
| Doc files | ~123 |
| Audit chain event types | 7 |
| Canonical error codes | 16 |
| Deprecated error codes | 4 |
| Open schema risks | 3 (Risk 2 integration, Risk 5, Risk 6) |
| Commits since alpha | 23 |
| Lines added since alpha | +12,516 |
| Lines removed since alpha | -392 |
| Total fixture categories | 7 |
| Total fixture files | 20+ |
| Working days since alpha | ~14 |

---

*This document was generated for GenSpark.ai review. All data is current as of 2026-05-22 10:15 UTC.*
