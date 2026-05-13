# Phase 2 Execution Prompt: Telemetry & Health (PR8+)

## Context

**Date:** 2026-05-12  
**Phase 1 Status:** ✅ COMPLETE (PR1-PR7 delivered)  
**Current Branch:** `main` (PR1-PR6 merged) + `roadmap/pr7-virtualized-list` (PR7 ready)  
**Test Status:** 196/196 passing  

## Phase 1 Achievements

✅ **PR1-PR6:** Merged to main
- AG-UI Foundation (33 event types)
- SwarmGraph & LangGraph mappers
- OpenAI Agents adapter with dual gating
- Event Stream View with live SSE
- Universal AG-UI renderer

✅ **PR7:** Ready for merge (PR #4)
- Virtualized list for 1000+ events
- Performance tests passing
- react-window v2 integration

## Mission: Phase 2 - Telemetry & Health

Execute the next phase of the ARC Studio Roadmap focusing on observability, health monitoring, and event filtering.

### Objectives

1. **Event Filtering** - Add type-based filtering to Event Stream
2. **OTel Export** - Implement OpenTelemetry trace export
3. **Health Monitor** - Create daemon health monitoring view

---

## PR8: Event Filtering by Type

### Goal
Add dropdown/multi-select filtering by AG-UI event type to Event Stream widget.

### Tasks
- [ ] Add event type filter dropdown to Event Stream header
- [ ] Support multi-select (e.g., show only TOOL_CALL_* events)
- [ ] Add "Select All" / "Clear All" buttons
- [ ] Persist filter selection in widget state
- [ ] Update filtered event count display
- [ ] Add keyboard shortcuts (Cmd+F to focus filter)

### Acceptance Criteria
- [ ] Dropdown shows all 33 AG-UI event types
- [ ] Multi-select works (checkboxes)
- [ ] Filter updates list in real-time
- [ ] Virtualized list handles filtered results
- [ ] Filter state persists during run selection
- [ ] TypeScript compilation passes
- [ ] All tests pass (no regressions)

### Tests
- [ ] Filter by single type
- [ ] Filter by multiple types
- [ ] Clear filter shows all events
- [ ] Filter persists across run selection
- [ ] Virtualization works with filtered list

### Security
- No security concerns (UI-only feature)

### Deliverable
Event Stream widget with working event type filter

---

## PR9: OTel Trace Export

### Goal
Export run traces to OpenTelemetry collector (user opt-in, local only by default).

### Tasks
- [ ] Pin OTel GenAI semconv version in docs/TELEMETRY_SEMCONV.md
- [ ] Create Python trace exporter service
- [ ] Convert RunRecord to OTLP format
- [ ] Add PreferenceContribution for OTLP endpoint
- [ ] Add CommandContribution: "ARC: Export Trace"
- [ ] Default disabled (require explicit endpoint config)
- [ ] Add warning for non-local endpoints
- [ ] Implement span attribute mapping (gen_ai.agent.*, gen_ai.tool.*)

### Acceptance Criteria
- [ ] OTel semconv version pinned and documented
- [ ] Exporter converts RunRecord → OTLP spans
- [ ] Preference setting for OTLP endpoint (default: none)
- [ ] Command exports selected run to configured endpoint
- [ ] Warning shown for non-localhost endpoints
- [ ] No export without endpoint configured
- [ ] No secrets in span attributes
- [ ] Python tests pass

### Tests
- [ ] Local fake OTLP collector test
- [ ] No endpoint = no export test
- [ ] Endpoint validation test
- [ ] Span attribute validation
- [ ] Secret redaction in spans

### Security
- [ ] User opt-in required
- [ ] Endpoint validation (warn on non-local)
- [ ] No secrets in span attributes
- [ ] No automatic export

### Deliverable
Working OTLP trace exporter with user opt-in

---

## PR10: Python Daemon Health Monitor

### Goal
Create health monitoring view showing Python daemon status.

### Tasks
- [ ] Confirm Python daemon health endpoint exists (/health)
- [ ] Create health client service in Theia
- [ ] Implement health view widget (AbstractViewContribution)
- [ ] Add CommandContribution: "ARC: Show Health Monitor"
- [ ] Add CommandContribution: "ARC: Restart Daemon" (with confirmation)
- [ ] Poll health endpoint (loopback only, 5s interval)
- [ ] Display: daemon status, active runs, version, uptime
- [ ] Show degraded state if health check fails

### Acceptance Criteria
- [ ] Health view shows daemon reachable/degraded
- [ ] Displays active run count
- [ ] Shows daemon version
- [ ] Restart command works with confirmation dialog
- [ ] Health polling only on loopback
- [ ] No environment variable dump
- [ ] TypeScript compilation passes
- [ ] UI smoke test passes

### Tests
- [ ] Client unit tests with mocked HTTP
- [ ] Health view renders correctly
- [ ] Restart confirmation shown
- [ ] Polling interval correct

### Security
- [ ] Loopback only (127.0.0.1)
- [ ] Restart requires confirmation
- [ ] No env var exposure
- [ ] No sensitive data in health response

### Deliverable
Health monitor view with daemon status and restart capability

---

## Execution Guidelines

### Test-Green Discipline
1. Run full test suite before each commit
2. Fix all failures before proceeding
3. No commits with failing tests
4. Verify TypeScript compilation

### Security First
1. No secrets in traces, logs, or UI
2. User opt-in for network operations
3. Validate all endpoints
4. Loopback-only for daemon communication

### Branch Strategy
- Create feature branch for each PR: `roadmap/pr8-event-filtering`, etc.
- Base on `main` (after PR7 merge)
- Push regularly
- Create PR when complete

### Commit Messages
Follow conventional commits:
```
feat(event-stream): add event type filtering (PR8)
feat(telemetry): add OTLP trace exporter (PR9)
feat(health): add daemon health monitor (PR10)
```

---

## Current State

### Repository
- **Main Branch:** PR1-PR6 merged
- **PR7 Branch:** `roadmap/pr7-virtualized-list` (ready for merge)
- **Working Directory:** Clean
- **Tests:** 196/196 passing

### Dependencies
- Theia 1.71.0
- react-window 2.2.7
- Python 3.x with pytest
- All AG-UI mappers registered

### Documentation
- docs/VERIFICATION.md - API verification
- docs/AG_UI_MAPPING.md - Event mapping reference
- docs/SECURITY.md - Security patterns
- docs/TELEMETRY_SEMCONV.md - OTel conventions (to be updated in PR9)
- docs/PR_ACCEPTANCE.md - Acceptance criteria

---

## Success Criteria

### Phase 2 Complete When:
- [ ] PR8 merged: Event filtering working
- [ ] PR9 merged: OTLP export functional
- [ ] PR10 merged: Health monitor operational
- [ ] All tests passing (200+ tests)
- [ ] Documentation updated
- [ ] No security issues
- [ ] No regressions

### Quality Gates
- TypeScript compilation: ✅ Clean
- Test coverage: ✅ No regressions
- Security review: ✅ No secrets exposed
- Performance: ✅ No degradation

---

## Execution Command

To start Phase 2 execution:

```
Execute Phase 2: PR8 (Event Filtering), PR9 (OTel Export), PR10 (Health Monitor)

Follow AUTOMATION_PROMPT.md guidelines:
- Test-green discipline
- Security-first principles
- No commits with failing tests
- User opt-in for network operations

Start with PR8: Event type filtering in Event Stream widget.
```

---

## Reference

- **AUTOMATION_PROMPT.md** - Full roadmap and guidelines
- **docs/PR_ACCEPTANCE.md** - Acceptance criteria matrix
- **PR #3** - PR1-PR6 merged (reference implementation)
- **PR #4** - PR7 ready for merge

---

**Status:** Ready for Phase 2 Execution  
**Date:** 2026-05-12  
**Next Action:** Merge PR7, then start PR8
