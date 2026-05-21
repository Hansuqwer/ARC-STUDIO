# Phase 1 — Polish (v0.2-v0.5) Task Breakdown

**Timeline:** ~12 weeks  
**Target:** End of Phase 1 review (using PATH_TO_1.0_REVIEW_PROMPT.md Phase 1 checks)  
**Related:** ADR-020 (desktop-first), ADR-021 (audit chain), docs/roadmap.md, docs/phases.md  
**Last Updated:** 2026-05-21

## Overview

Phase 1 transforms ARC Studio from "functional alpha" to "polished developer tool." The work spans documentation, error messages, empty/degraded states, performance, accessibility, test hygiene, schema stability, and EU AI Act audit chain foundation.

**Parallel tracks run throughout:**
- **Track A — Org/Legal** (Apple Developer enrollment, EV cert, privacy policy, ToS)
- **Track B — Documentation** (Diátaxis framework, CLI help audit, architecture overview)
- **Track C — UX & Error Handling** (error messages, empty states, performance budgets, accessibility)
- **Track D — Audit Chain** (HMAC-SHA256 implementation for EU AI Act compliance)
- **Track E — Test & Schema Hygiene** (taxonomy cleanup, schema stability sweep, deprecation policy ADR)

---

## Week 1-2: Foundation

### Track A — Org/Legal (Start NOW, runs in parallel for all 12 weeks)

| Task | Deliverable | Est. Time | Acceptance |
|------|-------------|-----------|------------|
| A.1 | Enroll in Apple Developer Program ($99/year) | 1-2 hours | Enrollment submitted; wait for approval |
| A.2 | Request D-U-N-S number (if organizational) | 1-2 hours | D-U-N-S number obtained (1-7 days) |
| A.3 | Choose Windows EV certificate vendor (DigiCert, Sectigo, ~$300-500/year) | 30 min | Vendor selected; business verification started (2-4 weeks) |
| A.4 | Draft privacy policy skeleton | 2 hours | First draft covers data collection, storage, sharing, retention |
| A.5 | Draft terms of service skeleton | 2 hours | First draft covers license, warranties, liability, termination |

**Note:** These tasks take weeks (certificates) or require external review (legal). Start them now even though they're "needed in Phase 4."

### Track B — Documentation Foundation

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| B.1 | **Audit CLI help text** | Inventory of all CLI commands; gap list | 3 hours | Every `arc <subcommand> --help` exits 0 and outputs non-empty help text. Logged gaps as GitHub issues. |
| B.2 | **Audit slash command help** | Inventory of all slash commands; gap list | 1 hour | Every slash command has `/command --help` equivalent. Logged gaps. |
| B.3 | **Write Getting Started guide** (Diátaxis Tutorial) | `docs/tutorials/getting-started.md` | 4 hours | Fresh user can go from install to first `/run` in under 5 minutes following the guide. |
| B.4 | **Architecture overview** (Diátaxis Explanation) | `docs/explanation/architecture.md` | 3 hours | Covers three-layer architecture (Python backend, TypeScript extension, Theia app). Diagrams welcome. |

### Track C — UX & Error Handling Foundation

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| C.1 | **Stable error code inventory** | Document all error codes in `docs/reference/error-codes.md` | 2 hours | Every error path has a unique `error_code` string. Documented in a reference page. |
| C.2 | **Empty state audit** | Inventory of all IDE tabs and list views; state documentation | 2 hours | Every IDE tab has a documented empty state, loading state, cancelled state. Logged gaps. |

### Track D — Audit Chain Foundation

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| D.1 | **Implement audit event schema** | `python/src/agent_runtime_cockpit/audit/schema.py` | 3 hours | All event types defined as Pydantic models. Event schema tests pass. |
| D.2 | **Implement HMAC signing/verification** | `python/src/agent_runtime_cockpit/audit/hmac.py` | 4 hours | HMAC-SHA256 signing and verification with hash chain linkage. Unit tests for tamper detection, boundary cases. |
| D.3 | **Implement audit chain storage** | `python/src/agent_runtime_cockpit/audit/storage.py` | 3 hours | Append-only JSONL storage at `~/.arc/audit/<run_id>.audit.jsonl`. Key generated at `~/.arc/secrets/audit_key` (mode 0600). |
| D.4 | **Implement for SwarmGraph adapter** | Integrate audit events into SwarmGraph run lifecycle | 4 hours | SwarmGraph runs emit audit events (run_started, llm_request/response, tool_call/result, run_completed). Integration tests. |

### Track E — Test & Schema Hygiene

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| E.1 | **ADR-020 (Deprecation Policy)** | `docs/adr/020-deprecation-policy.md` (rename existing ADR-020? Or create separate ADR?) | 2 hours | Policy defines: how long shims live (one minor + one patch), how breaking changes announced (CHANGELOG + release notes + deprecation warnings), semver promises. |
| E.2 | **Paid test taxonomy setup** | Move paid-smoke tests to `@pytest.mark.paid` | 2 hours | Full `pytest` run requires no `--deselect` flags to pass. CI runs paid taxonomy on schedule. |

**Week 1-2 Total:** ~30-35 hours (5-6 sessions of 6-7 hours each)

---

## Week 3-4: Implementation

### Track B — Documentation

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| B.5 | **Write How-To guides** | `docs/how-to/configure-provider.md`, `docs/how-to/run-workflow.md`, `docs/how-to/inspect-trace.md`, `docs/how-to/respond-hitl.md` | 6 hours | Task-oriented guides with concrete steps. Each guide has a single clear goal. |
| B.6 | **Write Reference docs** | `docs/reference/cli-commands.md`, `docs/reference/slash-commands.md` | 3 hours | 100% CLI command coverage. Each command has: description, syntax, flags, examples, exit codes, error codes. |

### Track C — UX & Error Handling

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| C.3 | **Implement actionable error messages** | All error paths updated | 8 hours | Every error includes: human-readable message, stable error_code, concrete next action. Sensitive data never logged. |
| C.4 | **Implement empty/degraded/cancelled states** | All IDE tabs and list views updated | 8 hours | Every IDE tab has empty state with onboarding. Every list has zero-results state. Every operation has cancelled state. Every async operation has loading state. |

### Track D — Audit Chain

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| D.5 | **Add `arc audit verify` CLI command** | CLI command + tests | 4 hours | `arc audit verify <run_id>` recomputes HMACs, checks chain integrity. Reports pass/fail with details. |
| D.6 | **Add `arc audit export` CLI command** | CLI command + tests | 3 hours | `arc audit export <run_id>` produces signed audit bundle. Bundle can be verified separately. |
| D.7 | **Extend to LangGraph adapter** | Audit events for LangGraph runs | 3 hours | LangGraph runs emit all required audit events. Integration tests. |

### Track E — Test & Schema Hygiene

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| E.3 | **Cross-language schema audit** | Audit report + migration plan | 4 hours | Every cross-language schema (Python ↔ TypeScript) audited for breaking-change risk. Shims documented with removal dates. |
| E.4 | **Schema stability tests** | Migration tests for all cross-language schemas | 4 hours | Every schema version has a migration test proving forward/backward compatibility. |

**Week 3-4 Total:** ~40-45 hours (6-7 sessions of 6-7 hours each)

---

## Week 5-6: Hardening

### Track B — Documentation

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| B.7 | **Documentation review pass** | Edit all docs for consistency | 4 hours | Docs use consistent terminology. No placeholder text. All links resolve. |
| B.8 | **CLI help text fill** | Fill gaps identified in B.1/B.2 | 3 hours | 100% CLI help coverage. Every slash command has discoverable help with examples. |

### Track C — UX & Error Handling

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| C.5 | **Establish performance budgets** | Measured baselines + budget document | 4 hours | REPL <50ms, first-token <500ms, arc --help <200ms, IDE tab switch <100ms. Documented in `docs/reference/performance-budgets.md`. |
| C.6 | **Add performance regression tests** | CI performance test suite | 4 hours | Performance regression tests in CI. Budgets enforced (or warnings emitted). |
| C.7 | **Accessibility audit** | Keyboard navigation, ARIA labels, colorblind palette | 8 hours | Keyboard navigation works for all IDE flows. ARIA labels on interactive elements. Colorblind-friendly palette. |

### Track D — Audit Chain

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| D.8 | **Extend to CrewAI adapter** | Audit events for CrewAI runs | 2 hours | CrewAI runs emit audit events. Integration tests. |
| D.9 | **Extend to OpenAI Agents adapter** | Audit events for OpenAI Agents runs | 2 hours | OpenAI Agents runs emit audit events. Integration tests. |
| D.10 | **Add redaction configuration** | `ARC_AUDIT_REDACT_*` env vars | 2 hours | Users can configure message/tool-args/tool-results redaction. Redaction applied before HMAC. |
| D.11 | **Add OTel audit log exporter** | Optional OTel exporter for audit events | 4 hours | Users with `~/.arc/config.yaml` OTel config can export audit events to their SIEM. No default remote exporter. |

### Track E — Test & Schema Hygiene

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| E.5 | **Deprecation policy enforcement** | Deprecated features identified, shims added | 4 hours | All deprecated features have: CHANGELOG entry, deprecation warning in code, documented removal timeline. |

**Week 5-6 Total:** ~35-40 hours (5-6 sessions of 6-7 hours each)

---

## Week 7-8: Verification & Completion

### Track A — Org/Legal Check

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| A.6 | **Check certificate status** | Status review | 15 min | Apple Developer ID cert issued or in progress. Windows EV cert business verification complete or in progress. |

### Track C — UX & Error Handling

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| C.8 | **Degraded cost records** | "Estimated" badges for non-measured cost data | 2 hours | Degraded cost records render with explicit "estimated" badges. Measured cost records are unbadged. |
| C.9 | **Screen reader compatibility** | Test with NVDA or VoiceOver | 4 hours | All IDE flows navigable with at least one screen reader. Issues logged as followups. |
| C.10 | **`NO_COLOR` env var support** | CLI output respects `NO_COLOR` | 2 hours | `NO_COLOR=1 arc <command>` produces no ANSI escape codes. Tests cover colored and uncolored output. |
| C.11 | **`prefers-reduced-motion` support** | Animations disabled when OS preference set | 1 hour | No automatic animations in IDE when OS requests reduced motion. |

### Track D — Audit Chain Completion

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| D.12 | **Add retention policy** | `arc runs prune --audit-older-than` | 2 hours | Users can prune audit chains older than N days. Prune also deletes the audit key? (No — keep key until explicitly rotated.) |
| D.13 | **Audit chain documentation** | User guide + compliance posture doc | 3 hours | User guide covers: how audit chains work, how to verify, how to export, how to configure redaction. Compliance posture documents EU AI Act "limited risk" tier. |
| D.14 | **Final test pass** | Comprehensive audit chain tests | 4 hours | All adapters tested. Tamper detection tested. Redaction tested. Export/verify round-trip tested. |

### Track E — Test & Schema Hygiene

| # | Task | Deliverable | Est. Time | Acceptance |
|---|------|-------------|-----------|------------|
| E.6 | **Full pytest run verification** | `pytest -q` passes with no flags | 1 hour | `uv run pytest -q` exits 0. No `--deselect` required. Paid tests excluded by default. |
| E.7 | **Schema migration test pass** | All migration tests pass | 1 hour | `uv run pytest tests/contract/` — all migration tests pass. No schema version without a migration test. |

**Week 7-8 Total:** ~20-25 hours (3-4 sessions of 6-7 hours each)

---

## Week 9-12: Polish & Buffer

These weeks are buffer for tasks that took longer than estimated, plus additional polish discovered during implementation.

**Priority tasks if behind schedule:**

1. Audit chain completion (Aug 2 deadline)
2. Performance budgets meeting targets
3. Accessibility verification
4. Documentation completeness
5. Schema stability tests

**Polish tasks (if ahead of schedule):**

| # | Task | Est. Time | Notes |
|---|------|-----------|-------|
| P.1 | Documentation screenshots | 3 hours | Add screenshots to Getting Started guide and How-To guides |
| P.2 | CLI completion scripts | 2 hours | Shell completion for `arc` commands (bash, zsh, fish) |
| P.3 | First-run wizard | 4 hours | Welcome screen with configuration prompts |
| P.4 | Theme consistency pass | 3 hours | Consistent colors, fonts, spacing across all IDE surfaces |
| P.5 | `arc doctor` UX polish | 2 hours | Better formatting, recommendations, actionable next steps |

---

## Summary Table

| Week | Track B (Docs) | Track C (UX) | Track D (Audit) | Track E (Hygiene) | Hours |
|------|---------------|-------------|-----------------|-------------------|-------|
| 1-2 | B.1-B.4: CLI audit, Getting Started, architecture | C.1-C.2: Error codes, empty state audit | D.1-D.4: Schema, HMAC, storage, SwarmGraph POC | E.1-E.2: Deprecation ADR, paid taxonomy | 30-35 |
| 3-4 | B.5-B.6: How-Tos, Reference | C.3-C.4: Error messages, empty states | D.5-D.7: verify/export CLI, LangGraph | E.3-E.4: Schema audit, migration tests | 40-45 |
| 5-6 | B.7-B.8: Review, CLI fill | C.5-C.7: Performance, accessibility | D.8-D.11: CrewAI, OpenAI, redaction, OTel | E.5: Deprecation enforcement | 35-40 |
| 7-8 | — | C.8-C.11: Degraded costs, screen reader, NO_COLOR, reduced-motion | D.12-D.14: Retention, docs, final tests | E.6-E.7: Full pytest, migration pass | 20-25 |
| 9-12 | Polish + buffer | Polish + buffer | Polish + buffer | Polish + buffer | ~20 |

**Total estimated hours:** 145-185 (across 12 weeks)  
**Average weekly hours:** 12-15  

---

## Week-by-Week Sprint Plan

### Sprint 1 (Week 1-2)

**Focus:** Foundation — get the architectural decisions right before building.

**Day 1-2:**
- [ ] Enroll in Apple Developer Program (A.1)
- [ ] Request D-U-N-S number (A.2)
- [ ] Choose EV certificate vendor (A.3)
- [ ] Start privacy policy draft (A.4)
- [ ] Start terms of service draft (A.5)
- [ ] Draft ADR-020 (Deprecation Policy) (E.1)

**Day 3-4:**
- [ ] Implement audit event schema (D.1)
- [ ] Implement HMAC signing/verification (D.2)
- [ ] CLI help text audit (B.1)
- [ ] Slash command help audit (B.2)

**Day 5-6:**
- [ ] Implement audit chain storage (D.3)
- [ ] Implement audit chain for SwarmGraph (D.4)
- [ ] Stable error code inventory (C.1)
- [ ] Empty state audit (C.2)
- [ ] Set up `@pytest.mark.paid` taxonomy (E.2)

**End of Sprint 1 deliverables:**
- Audit chain works for SwarmGraph (proof of concept)
- CLI help gaps documented
- Error codes documented
- Empty state gaps documented
- Deprecation policy ADR drafted
- Org/legal track started

### Sprint 2 (Week 3-4)

**Focus:** Build — implement the core changes.

**Day 1-2:**
- [ ] Write Getting Started guide (B.3)
- [ ] Write architecture overview (B.4)
- [ ] Implement actionable error messages (C.3)

**Day 3-4:**
- [ ] Implement empty/degraded/cancelled states (C.4)
- [ ] Write How-To guides (B.5)
- [ ] Write Reference docs (B.6)

**Day 5-6:**
- [ ] Add `arc audit verify` CLI (D.5)
- [ ] Add `arc audit export` CLI (D.6)
- [ ] Extend audit chain to LangGraph (D.7)
- [ ] Cross-language schema audit (E.3)
- [ ] Schema stability tests (E.4)

**End of Sprint 2 deliverables:**
- All core documentation written
- Error messages actionable + empty states implemented
- Audit chain for SwarmGraph + LangGraph
- Schema stability baseline established

### Sprint 3 (Week 5-6)

**Focus:** Harden — polish, performance, accessibility.

**Day 1-2:**
- [ ] Documentation review pass (B.7)
- [ ] Fill CLI help gaps (B.8)
- [ ] Establish performance budgets (C.5)

**Day 3-4:**
- [ ] Add performance regression tests (C.6)
- [ ] Accessibility audit (C.7)
- [ ] Deprecation policy enforcement (E.5)

**Day 5-6:**
- [ ] Extend audit chain to CrewAI (D.8)
- [ ] Extend audit chain to OpenAI Agents (D.9)
- [ ] Add redaction configuration (D.10)
- [ ] Add OTel audit log exporter (D.11)

**End of Sprint 3 deliverables:**
- All docs reviewed and consistent
- Performance baselines established
- Accessibility audit complete
- All adapters have audit chains
- OTel export working

### Sprint 4 (Week 7-8)

**Focus:** Verification — test, verify, document.

**Day 1-2:**
- [ ] Check certificate status (A.6)
- [ ] Degraded cost records with badges (C.8)
- [ ] Screen reader compatibility (C.9)
- [ ] `NO_COLOR` env var support (C.10)
- [ ] `prefers-reduced-motion` support (C.11)

**Day 3-4:**
- [ ] Add audit chain retention policy (D.12)
- [ ] Write audit chain documentation (D.13)
- [ ] Audit chain final test pass (D.14)

**Day 5-6:**
- [ ] Full pytest run verification (E.6)
- [ ] Schema migration test pass (E.7)
- [ ] Phase 1 review (using PATH_TO_1.0_REVIEW_PROMPT.md)
- [ ] Document review outcome in docs/phases.md

**End of Sprint 4 deliverables:**
- Phase 1 review complete
- All acceptance criteria met (or documented followups)
- Ready to proceed to Phase 2

### Sprint 5 (Week 9-12) — Buffer

- [ ] Catch up on delayed tasks
- [ ] Polish tasks (screenshots, completion scripts, first-run wizard, theme, arc doctor UX)
- [ ] Re-review Phase 1 checklist
- [ ] Phase 1 review
- [ ] Update docs/roadmap.md and docs/phases.md with Phase 1 status

---

## Acceptance Criteria (from PATH_TO_1.0_REVIEW_PROMPT.md Phase 1 checks)

### Must pass for APPROVE:

| Check | Criterion | Evidence |
|-------|-----------|----------|
| Documentation | Getting Started guide exists, <5min first `/run` | `docs/tutorials/getting-started.md` |
| Documentation | 100% CLI command coverage in --help | `arc <subcommand> --help` audit log |
| Error messages | Every error has error_code + actionable message | `docs/reference/error-codes.md` |
| Error messages | No sensitive data logged in error output | Audit pass |
| Empty states | No fabricated data; every tab has empty state | IDE visual inspection |
| Performance | Budgets measured and documented | `docs/reference/performance-budgets.md` |
| Test taxonomy | Full `pytest` passes with no `--deselect` | CI run |
| EU AI Act | ADR-021 accepted, HMAC implementation started | `docs/adr/021-audit-chain-architecture.md` |
| EU AI Act | Audit chain schema includes `principal` field | Code review |
| Schema stability | All cross-language schemas have migration tests | `uv run pytest tests/contract/` |

### Must have started for APPROVE (can be APPROVE_WITH_FOLLOWUPS):

| Check | Criterion | Fallback |
|-------|-----------|----------|
| Performance | Regression tests in CI | Document as Phase 1 followup |
| Accessibility | Screen reader compatibility | Document as Phase 1 followup |
| Org/legal | Apple enrollment + EV cert started | Verify status, document as Phase 1 followup |
| KB navigation | All IDE flows navigable | Document gaps as Phase 1 followup |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| EU AI Act enforcement outpaces audit chain implementation | Low (12 weeks to implement, 72 days to deadline) | Critical | Start audit chain in Sprint 1. Prioritize SwarmGraph POC first. |
| Performance budgets require significant refactoring | Medium | High | Set budgets based on measured baseline, not aspirational targets. Document known violations. |
| Apple Developer enrollment delayed | Medium | Medium (Phase 4 impact) | Start in Sprint 1. Document as non-blocking for Phase 1-3. |
| Accessibility audit reveals major gaps | Medium | High | Document gaps as followups for v0.6+. Blockers only for critical navigation. |
| Schema audit reveals breaking changes | Medium | High | Implement shims with deprecation warnings. Document migration timeline per ADR-020. |
| Documentation takes longer than estimated | High | Medium | Pad with Sprint 5 buffer. Prioritize Getting Started guide + CLI help. |

---

## Dependencies

### Blocking dependencies (must complete before dependent task starts):
- ADR-020 (Deprecation Policy) ← E.5 (Deprecation enforcement)
- D.1 (Audit schema) ← D.2 (HMAC), D.3 (Storage), D.4 (SwarmGraph integration)
- D.4 (SwarmGraph POC) ← D.5-D.7 (Other adapters)
- E.3 (Schema audit) ← E.4 (Stability tests)

### Non-blocking parallel work:
- A.1-A.5 (Org/legal) — independent of all technical work
- B.1-B.8 (Documentation) — independent of audit chain work
- C.1-C.11 (UX) — independent of audit chain work
- E.1-E.2 (Test taxonomy) — independent of audit chain work

---

## Notes

- **Weekly cadence:** 12-15 hours per week (5-6 hours split Wed/Thu/Fri for ~3-4 months). This assumes the user is working alone on Phase 1 in their available time.
- **Timeline:** 12 weeks → mid-August 2026 completion. Audit chain completes in week 7-8, well before Aug 2 deadline.
- **Next steps after Phase 1 review:**
  - Phase 1 review → APPROVE/APPROVE_WITH_FOLLOWUPS/REJECT
  - Update docs/roadmap.md and docs/phases.md
  - Proceed to Phase 2 (Provider Expansion) planning
