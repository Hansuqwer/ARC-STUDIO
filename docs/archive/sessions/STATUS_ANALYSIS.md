# ARC Studio Status Analysis

**Date:** 2026-05-22  
**Current Commit:** `ac99bfe` - "refactor(arc-extension): complete P2 arc-backend-service delegation"  
**Release Target:** v0.1.0-alpha on 2026-06-01  

## Executive Summary

ARC Studio v0.1.0-alpha is **feature-complete and ready for release**. All core roadmap items (R1-R13) are at "Baseline Complete" or "Polished Complete" status. The codebase is stable with:

- ✅ **1,430 Python tests passing** (20 skipped)
- ✅ **TypeScript tests passing** (arc-extension build successful)
- ✅ **No banned claims** in release documentation
- ✅ **Green CI workflows** on main branch
- ✅ **`.env` history scrubbed** (completed 2026-05-18)

The green window completed on 2026-05-21. The project is in **release candidate** status.

---

## Current Status by Roadmap Item

### v0.1.0-alpha Roadmap (Complete)

| ID | Feature | Status | Evidence |
|----|---------|--------|----------|
| R1 | Live Run Streaming | ✅ Complete | Phase 1 vertical baseline + Phase 8 productization |
| R2 | IDE Runtime Setup + Config | ✅ Complete | ConfigTab with safe YAML-backed config, wizard, export helpers |
| R3 | Provider/Quota/Cost UI | ✅ Baseline Complete | Typed diagnostics, local quota reset, 3-layer gated provider action |
| R4 | HITL + Audit UX | ✅ Complete | Dedicated Assurance tab with auto-refresh, filtering, export |
| R5 | SwarmGraph Insight | ✅ Complete | Topology/consensus/cost panels with event-backed rendering |
| R6 | Real Adoption | ✅ Complete | Local-real hardening baseline for langgraph+swarmgraph |
| R7 | Release Operations | ✅ Complete | Evidence refreshed, green window complete, .env scrubbed |
| R8 | IDE Provider/Quota Completion | ✅ Baseline Complete | Phase 12 - hardened diagnostics/quota/pay-gate UX |
| R9 | IDE Live Stream Polish | ✅ Baseline Complete | Phase 13 - daemon URL auto-discovery, async warning tests |
| R10 | Doctor/Daemon Parity | ✅ Baseline Complete | Phase 14 - orphan routes labeled, `arc runs links` added |
| R11 | SwarmGraph Cost Producer | ✅ Baseline Complete | Phase 15 - measured cost/token events with full schema |
| R12 | Packaging/Optional Features | ✅ Baseline Complete | Phase 16 - ADR-008, electron-builder configs, signing preflight |
| R13 | SwarmGraph Native Runtime | ✅ P1-P4 Baseline Complete | Phase 17 - native runtime, adapter bridge, CLI REPL, IDE default |

### Additional Completed Phases

| Phase | Scope | Status | Evidence |
|-------|-------|--------|----------|
| Phase 18 | CLI Consolidation | ✅ Baseline Complete | Unified slash commands, session migration, bare `arc` TTY |
| Phase 19 | Provider-Backed Runtime | ✅ Baseline Complete | ProviderClient protocol, BudgetEnforcer, cost estimators |
| Phase 20 | Streaming/Tools/Multi-Turn | ✅ Baseline Complete | Streaming verified, ToolRegistry, TurnManager, ChatSession v4 |

---

## What Remains

### For v0.1.0-alpha Release (Target: 2026-06-01)

**Status:** Ready to tag and release. No blocking work remains.

**Pre-release checklist:**
1. ✅ All tests passing (1,430 Python, TypeScript suite green)
2. ✅ Banned claims check passing
3. ✅ Green window completed (2026-05-21)
4. ✅ `.env` history scrubbed
5. ⏳ **Final release tag** - needs to be created
6. ⏳ **Release notes** - needs to be written
7. ⏳ **GitHub release** - needs to be published

**Recommended next steps for v0.1 release:**
```bash
# 1. Verify all checks pass
bash scripts/check-pr.sh

# 2. Create release tag
git tag -a v0.1.0-alpha -m "Release v0.1.0-alpha"

# 3. Push tag
git push origin v0.1.0-alpha

# 4. Create GitHub release with release notes
gh release create v0.1.0-alpha --title "v0.1.0-alpha" --notes-file docs/release/v0.1.0-alpha-notes.md
```

---

### For v0.2-v0.5 (Phase 1 Polish - 12 weeks)

**Status:** Not started. Planned work documented in `docs/PHASE_1_TASKS.md`.

**Timeline:** ~12 weeks (145-185 hours)  
**Target:** End of Phase 1 review using `PATH_TO_1.0_REVIEW_PROMPT.md`

#### Track A — Org/Legal (Parallel, 12 weeks)
- [ ] Enroll in Apple Developer Program ($99/year)
- [ ] Request D-U-N-S number (if organizational)
- [ ] Choose Windows EV certificate vendor (~$300-500/year)
- [ ] Draft privacy policy skeleton
- [ ] Draft terms of service skeleton

#### Track B — Documentation (Weeks 1-6)
- [ ] Audit CLI help text (all commands)
- [ ] Audit slash command help
- [ ] Write Getting Started guide (Diátaxis Tutorial)
- [ ] Write Architecture overview (Diátaxis Explanation)
- [ ] Write How-To guides (configure provider, run workflow, inspect trace, respond HITL)
- [ ] Write Reference docs (CLI commands, slash commands, error codes)
- [ ] Documentation review pass

#### Track C — UX & Error Handling (Weeks 1-8)
- [ ] Stable error code inventory
- [ ] Empty state audit
- [ ] Implement actionable error messages
- [ ] Implement empty/degraded/cancelled states
- [ ] Establish performance budgets
- [ ] Add performance regression tests
- [ ] Accessibility audit (keyboard navigation, ARIA labels, colorblind palette)
- [ ] Screen reader compatibility
- [ ] `NO_COLOR` env var support
- [ ] `prefers-reduced-motion` support

#### Track D — Audit Chain (Weeks 1-8, EU AI Act Compliance)
- [ ] Implement audit event schema
- [ ] Implement HMAC-SHA256 signing/verification
- [ ] Implement audit chain storage
- [ ] Implement for SwarmGraph adapter
- [ ] Add `arc audit verify` CLI command
- [ ] Add `arc audit export` CLI command
- [ ] Extend to LangGraph adapter
- [ ] Extend to CrewAI adapter
- [ ] Extend to OpenAI Agents adapter
- [ ] Add redaction configuration
- [ ] Add OTel audit log exporter
- [ ] Add retention policy
- [ ] Audit chain documentation

#### Track E — Test & Schema Hygiene (Weeks 1-8)
- [ ] ADR-020 (Deprecation Policy)
- [ ] Paid test taxonomy setup
- [ ] Cross-language schema audit
- [ ] Schema stability tests
- [ ] Deprecation policy enforcement
- [ ] Full pytest run verification
- [ ] Schema migration test pass

**Priority for Phase 1:**
1. **Audit chain completion** (Aug 2 deadline for EU AI Act compliance)
2. **Performance budgets** meeting targets
3. **Accessibility verification**
4. **Documentation completeness**
5. **Schema stability tests**

---

## Technical Debt & Known Issues

### Non-Blocking Issues
1. **Jest open-handle notice** - Tests pass but Jest reports open handles after completion
2. **Theia async contribution warnings** - Captured and fingerprinted in Phase 13; harmless
3. **Provider-backed adoption** - Narrow gated path exists; broad adoption deferred
4. **LM Arena** - Stub-default with gated live path; live productization deferred

### Deferred Features (Post-v0.1)
- Live LM Arena implementation
- Broad provider-backed adoption
- Real-time BudgetVector pressure/exhaustion interrupts at effect boundaries
- Electron release packaging (spike complete, full packaging deferred)

---

## Verification Commands

### Full verification suite:
```bash
# Python tests
cd python && uv run pytest -q

# TypeScript tests
pnpm --filter arc-extension test

# Build verification
pnpm --filter @arc-studio/protocol build
pnpm --filter arc-extension build
pnpm --filter @arc-studio/browser build

# PR hygiene
bash scripts/check-pr.sh

# Banned claims
bash scripts/check-banned-claims.sh docs/agents.md README.md docs/roadmap.md docs/phases.md docs/release/checklist.md
```

### Current test counts:
- **Python:** 1,430 passed, 20 skipped
- **TypeScript:** 762 tests (arc-extension)
- **E2E:** 11 passed, 4 skipped

---

## Release Scope Boundaries

### ✅ Included in v0.1.0-alpha
- Browser app (`applications/browser`)
- Python CLI/wheel (`python/`)
- SwarmGraph native runtime (P1-P4)
- CLI consolidation (unified slash commands)
- Provider-backed runtime foundations
- Streaming, tool use, multi-turn sessions

### ❌ Not Included in v0.1.0-alpha
- Electron release artifacts (spike complete, packaging deferred)
- LM Arena product feature (stub-default only)
- Broad SwarmGraph adoption claim (narrow gated path only)
- Adapter-wide HMAC-keyed audit trails (conditional per run path)
- Production/concurrent-user/tenant isolation

---

## Recommendations

### Immediate (This Week)
1. **Create v0.1.0-alpha release tag** and publish GitHub release
2. **Write release notes** highlighting features, limitations, and known issues
3. **Update README** to reflect v0.1.0-alpha status (if needed)

### Short-term (Next 2 Weeks)
1. **Start Track A (Org/Legal)** - Apple Developer enrollment, EV cert vendor selection
2. **Start Track B (Documentation)** - CLI help audit, Getting Started guide
3. **Start Track D (Audit Chain)** - Implement audit event schema and HMAC signing

### Medium-term (Next 12 Weeks)
1. **Complete Phase 1 polish work** following `docs/PHASE_1_TASKS.md`
2. **EU AI Act compliance** - Audit chain implementation by Aug 2 deadline
3. **Performance budgets** - Establish and enforce performance regression tests
4. **Accessibility** - Keyboard navigation, screen reader compatibility

---

## Conclusion

ARC Studio v0.1.0-alpha is **production-ready for local development use**. The codebase is stable, well-tested, and documented. All core features are implemented and verified.

The next phase focuses on **polish, documentation, and compliance** rather than new features. This positions ARC Studio for broader adoption and enterprise use cases.

**Recommended action:** Tag and release v0.1.0-alpha, then begin Phase 1 polish work.
