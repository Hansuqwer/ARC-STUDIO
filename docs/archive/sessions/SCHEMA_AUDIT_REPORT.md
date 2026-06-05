# ARC Studio Schema Audit Report

**Date:** 2026-05-22  
**Scope:** Python ↔ TypeScript schema consistency audit  
**Related:** ADR-022 (Deprecation Policy), ADR-018 (Protocol Package), ADR-004 (Event Schema Versioning)

## Executive Summary

This audit identifies 15 major schema categories shared between Python and TypeScript, documents 6 breaking-change risks (including 1 CRITICAL naming collision), and catalogs 1 active deprecation shim. The most critical risk is the RUN_FINISHED vs RUN_COMPLETED event naming collision that prevents proper run lifecycle tracking between Python and TypeScript.

**Critical Actions Required:**
1. **URGENT:** Fix RUN_FINISHED/RUN_COMPLETED naming collision (Risk 0) - highest runtime risk
2. Sync error codes between Python and TypeScript (12 missing codes in TS)
3. Add RuntimeCapabilities v2 support to TypeScript
4. Remove envelope.py shim in v0.3.0 per ADR-022 timeline

---

## 1. Shared Schemas Inventory

### 1.1 Core Protocol Schemas

| Schema | Python Location | TypeScript Location | Status |
|--------|----------------|---------------------|--------|
| **ArcEnvelope** | `protocol/event_envelope.py:30` | `arc-protocol-ts/src/arc-protocol-types.ts:7` | ✅ Consistent |
| **ArcError** | `protocol/event_envelope.py:17` | `arc-protocol-ts/src/arc-protocol-types.ts:15` | ✅ Consistent |
| **ArcMeta** | `protocol/event_envelope.py:23` | `arc-protocol-ts/src/arc-protocol-types.ts:21` | ✅ Consistent |
| **WorkspaceInfo** | `protocol/schemas.py:33` | `arc-protocol-ts/src/arc-protocol-types.ts:28` | ✅ Consistent |
| **RuntimeInfo** | `protocol/schemas.py:24` | `arc-protocol-ts/src/arc-protocol-types.ts:35` | ✅ Consistent |

**Protocol Version:** Both use `ARC_PROTOCOL_VERSION = "1.0"`

### 1.2 Runtime Capabilities

| Schema | Python Location | TypeScript Location | Status |
|--------|----------------|---------------------|--------|
| **RuntimeCapabilities (v1)** | `protocol/capabilities.py:40` | `arc-protocol-ts/src/arc-protocol-types.ts:54` | ✅ Consistent |
| **RuntimeCapability (v2)** | `protocol/runtime_capability.py:12` | ❌ Not implemented | ⚠️ **BREAKING RISK** |

**Schema Versions:**
- Python v1: `SCHEMA_VERSION = 1` (capabilities.py:7)
- Python v2: `schema_version: Literal[2] = 2` (runtime_capability.py:17)
- TypeScript: Only v1 (`CAPABILITY_SCHEMA_VERSION = 1`)

**Migration Support:**
- Python has `migrate_v1_to_v2()` function (runtime_capability.py:40-69)
- TypeScript has no v2 migration support

### 1.3 Workflow Schemas

| Schema | Python Location | TypeScript Location | Status |
|--------|----------------|---------------------|--------|
| **WorkflowInfo** | `protocol/schemas.py:74` | `arc-protocol-ts/src/arc-protocol-types.ts:69` | ✅ Consistent |
| **WorkflowNode** | `protocol/schemas.py:57` | `arc-protocol-ts/src/arc-protocol-types.ts:80` | ⚠️ **Field mismatch** |
| **WorkflowEdge** | `protocol/schemas.py:65` | `arc-protocol-ts/src/arc-protocol-types.ts:87` | ✅ Consistent |
| **SchemaInfo** | `protocol/schemas.py:87` | `arc-protocol-ts/src/arc-protocol-types.ts:96` | ✅ Consistent |

**WorkflowNode Difference:**
- Python has `source_location: Optional[SourceLocation]` field (schemas.py:61)
- TypeScript missing this field
- **Impact:** Source location data (file/line/column) lost in cross-language serialization

### 1.4 Run Tracking Schemas

| Schema | Python Location | TypeScript Location | Status |
|--------|----------------|---------------------|--------|
| **RunRecord** | `protocol/schemas.py:145` | `arc-protocol-ts/src/arc-protocol-types.ts:104` | ⚠️ **Field mismatch** |
| **RunEvent** | `protocol/schemas.py:111` | `arc-protocol-ts/src/arc-protocol-types.ts:118` | ✅ Consistent |
| **RunStatus** | `protocol/schemas.py:103` | `arc-protocol-ts/src/arc-protocol-types.ts:108` | ✅ Consistent |
| **BudgetVector** | `protocol/schemas.py:139` | `arc-protocol-ts/src/arc-protocol-types.ts:616` | ✅ Consistent |

**RunRecord Differences:**
- Python has `audit_path: Optional[str]` field (schemas.py:154)
- Python has `budget: Optional[BudgetVector]` field (schemas.py:155)
- TypeScript arc-protocol-types.ts missing these fields
- **Impact:** Audit path and budget data not accessible from TypeScript protocol types package

**Event Schema Version:** Both use `EVENT_SCHEMA_VERSION = 2`

### 1.5 Event Type Registry

| Schema | Python Location | TypeScript Location | Status |
|--------|----------------|---------------------|--------|
| **Event Types** | `protocol/events.py:36` (40+ types) | `arc-ag-ui/src/event-types.ts:5` (34 types) | ⚠️ **Count mismatch** |

**Python Event Types (40+):**
- Run lifecycle: RUN_STARTED, RUN_COMPLETED, RUN_FAILED, RUN_CANCELLED
- Step lifecycle: STEP_STARTED, STEP_COMPLETED, STEP_FAILED
- Agent lifecycle: AGENT_START, AGENT_END
- Tool calls: TOOL_CALL, TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END, TOOL_CALL_RESULT, TOOL_CALL_ERROR, TOOL_END
- Handoffs: HANDOFF
- Node lifecycle: NODE_STARTED, NODE_UPDATE, NODE_FAILED
- Messages: MESSAGE, MESSAGE_CHUNK, TEXT_MESSAGE_START, TEXT_MESSAGE_CONTENT, TEXT_MESSAGE_END, TEXT_MESSAGE_CHUNK
- State: STATE_SNAPSHOT
- SwarmGraph: SWARMGRAPH_TOPOLOGY, SWARMGRAPH_CONSENSUS, SWARMGRAPH_COST
- HITL: HITL_PROMPT, HITL_RESPONSE, HITL_TIMEOUT
- Cockpit: CONTRACT_PROPOSED, CONTRACT_ACCEPTED, CONTRACT_FULFILLED, CONTRACT_VIOLATED, RECEIPT_GENERATED, FAILURE_AUTOPSY_GENERATED, EVIDENCE_REF_CREATED
- Fallback: RAW, CUSTOM

**TypeScript AG-UI Event Types (34):**
- TEXT_MESSAGE_START, TEXT_MESSAGE_CONTENT, TEXT_MESSAGE_END, TEXT_MESSAGE_CHUNK
- TOOL_CALL_START, TOOL_CALL_ARGS, TOOL_CALL_END, TOOL_CALL_CHUNK, TOOL_CALL_RESULT
- STATE_SNAPSHOT, STATE_DELTA, MESSAGES_SNAPSHOT
- ACTIVITY_SNAPSHOT, ACTIVITY_DELTA
- RAW, CUSTOM
- RUN_STARTED, RUN_FINISHED, RUN_ERROR
- STEP_STARTED, STEP_FINISHED
- REASONING_START, REASONING_MESSAGE_START, REASONING_MESSAGE_CONTENT, REASONING_MESSAGE_END, REASONING_MESSAGE_CHUNK, REASONING_END, REASONING_ENCRYPTED_VALUE

**Missing in TypeScript:**
- AGENT_START, AGENT_END
- HANDOFF
- NODE_STARTED, NODE_UPDATE, NODE_FAILED
- SWARMGRAPH_TOPOLOGY, SWARMGRAPH_CONSENSUS, SWARMGRAPH_COST
- HITL_PROMPT, HITL_RESPONSE, HITL_TIMEOUT
- All Cockpit contract/receipt/autopsy events

**Impact:** TypeScript UI may not recognize or render Python-emitted events for SwarmGraph insights, HITL, and Cockpit primitives.

### 1.6 Cockpit Protocol Schemas

| Schema | Python Location | TypeScript Location | Status |
|--------|----------------|---------------------|--------|
| **RunContract** | `protocol/run_contract.py:24` | `arc-extension/src/common/arc-protocol.ts:590` | ✅ Consistent |
| **ContractStatus** | `protocol/run_contract.py:17` | `arc-extension/src/common/arc-protocol.ts:585` | ✅ Consistent |
| **RunReceipt** | `protocol/run_receipt.py:25` | `arc-extension/src/common/arc-protocol.ts:622` | ✅ Consistent |
| **FileChange** | `protocol/run_receipt.py:19` | `arc-extension/src/common/arc-protocol.ts:610` | ✅ Consistent |
| **FailureAutopsy** | `protocol/failure_autopsy.py:25` | `arc-extension/src/common/arc-protocol.ts:651` | ✅ Consistent |
| **RetryOption** | `protocol/failure_autopsy.py:12` | `arc-extension/src/common/arc-protocol.ts:645` | ✅ Consistent |

**Note:** These schemas are consistent in arc-extension/arc-protocol.ts but not present in arc-protocol-ts package.

### 1.7 Error Codes

| Schema | Python Location | TypeScript Location | Status |
|--------|----------------|---------------------|--------|
| **ArcErrorCode** | `protocol/errors.py:5` (14 codes) | `arc-extension/src/common/arc-protocol.ts:19` (8 codes) | ⚠️ **BREAKING RISK** |

**Python Error Codes (14):**
1. WORKSPACE_NOT_FOUND
2. NO_RUNTIME_DETECTED
3. ADAPTER_ERROR
4. ADAPTER_NOT_SUPPORTED
5. SCHEMA_EXPORT_FAILED
6. WORKFLOW_EXPORT_FAILED
7. RUN_FAILED
8. RUN_NOT_FOUND
9. CONTEXT_PROVIDER_ERROR
10. CONFORMANCE_FAILED
11. INVALID_INPUT
12. INTERNAL_ERROR
13. TIMEOUT
14. NOT_IMPLEMENTED

**TypeScript Error Codes (8):**
1. INVALID_INPUT
2. TRACE_NOT_FOUND
3. EXECUTION_FAILED
4. PARSE_ERROR
5. WORKFLOW_NOT_FOUND
6. PERMISSION_DENIED
7. TIMEOUT
8. UNKNOWN

**Missing in TypeScript (12 codes):**
- WORKSPACE_NOT_FOUND
- NO_RUNTIME_DETECTED
- ADAPTER_ERROR
- ADAPTER_NOT_SUPPORTED
- SCHEMA_EXPORT_FAILED
- WORKFLOW_EXPORT_FAILED
- RUN_FAILED
- RUN_NOT_FOUND
- CONTEXT_PROVIDER_ERROR
- CONFORMANCE_FAILED
- INTERNAL_ERROR
- NOT_IMPLEMENTED

**Extra in TypeScript (6 codes):**
- TRACE_NOT_FOUND
- EXECUTION_FAILED
- PARSE_ERROR
- WORKFLOW_NOT_FOUND
- PERMISSION_DENIED
- UNKNOWN

**Impact:** Python backend may emit error codes that TypeScript frontend cannot recognize or handle properly. 12 of 14 Python codes are missing in TypeScript (only TIMEOUT and INVALID_INPUT are shared).

### 1.8 Context Schemas

| Schema | Python Location | TypeScript Location | Status |
|--------|----------------|---------------------|--------|
| **ContextPackEntry** | `protocol/schemas.py:168` | `arc-protocol-ts/src/arc-protocol-types.ts:165` | ✅ Consistent |
| **SourceType** | `protocol/schemas.py:160` | `arc-protocol-ts/src/arc-protocol-types.ts:169` (as string) | ⚠️ Minor difference |

**SourceType Difference:**
- Python: Enum with LOCAL_REPO, CONTEXT7, VERCEL_GREP, GITHUB_SEARCH, WEB_SEARCH
- TypeScript: Plain string type
- **Impact:** Low - TypeScript accepts any string, Python validates against enum

---

## 2. Deprecation Shims

### 2.1 Active Shims

| Shim | Location | Target | Introduced | Removal Target | Status |
|------|----------|--------|------------|----------------|--------|
| **envelope.py** | `protocol/envelope.py` | `protocol/event_envelope.py` | v0.1.0-alpha (2026-05-11) | v0.3.0 | ✅ **Documented** |

**Shim Details:**

**File:** `python/src/agent_runtime_cockpit/protocol/envelope.py`

**Purpose:** Redirect imports from old `protocol.envelope` to new `protocol.event_envelope` location (per ADR-018)

**Implementation:**
```python
from warnings import warn
from agent_runtime_cockpit.protocol.event_envelope import (
    ARC_PROTOCOL_VERSION, ArcEnvelope, ArcError, ArcMeta, err, ok
)

warn(
    "agent_runtime_cockpit.protocol.envelope is deprecated; import "
    "agent_runtime_cockpit.protocol.event_envelope instead",
    DeprecationWarning,
    stacklevel=2,
)
```

**Removal Timeline (per ADR-022):**
- **Notice Period:** One minor version + one patch cycle
- **Introduced:** v0.1.0-alpha (2026-05-11, commit 0ab9b7d)
- **Removal Version:** v0.3.0
- **Status:** ✅ Documented in shim file and this audit
- **Action Required:** Add CHANGELOG entry in v0.2.0 announcing removal in v0.3.0

### 2.2 Schema Version Migrations

These are not shims but migration functions that must be maintained per ADR-022:

| Migration | Location | Versions | Support Duration |
|-----------|----------|----------|------------------|
| **CostRecord** | `protocol/cost_record.py` | v1→v2→v3 | One version cycle |
| **RuntimeCapability** | `protocol/runtime_capability.py:40` | v1→v2 | One version cycle |
| **RunEvent** | `protocol/schemas.py:119` | v1→v2 | One version cycle |

**Per ADR-022:** Schema readers must support current and previous version. Writers must always write latest version.

---

## 3. Breaking Change Risks

### 3.0 CRITICAL Risk (Immediate Action Required)

#### Risk 0: Run Lifecycle Event Naming Collision
**Severity:** CRITICAL  
**Impact:** Run lifecycle tracking completely broken between Python and TypeScript

**Details:**
- Python uses: RUN_COMPLETED, RUN_FAILED, RUN_CANCELLED
- TypeScript uses: RUN_FINISHED, RUN_ERROR
- Both sides think they're handling run lifecycle but use different vocabularies
- This is a **naming collision**, not just a missing event

**Failure Scenario:**
1. Python backend completes a run successfully
2. Emits `RunEvent(type="RUN_COMPLETED", ...)`
3. TypeScript frontend listens for "RUN_FINISHED"
4. Event never matches, UI never updates
5. User sees perpetual "running" state despite completion

**Why This Is CRITICAL:**
- Affects core functionality (run status tracking)
- Silent failure - no error thrown, just wrong behavior
- Both sides believe they're correct
- Impacts every run execution in the UI

**Migration Path:**
1. **Immediate:** Standardize on Python's vocabulary (more precise: COMPLETED/FAILED/CANCELLED vs FINISHED/ERROR)
2. Add TypeScript aliases for backwards compatibility
3. Update all TypeScript event handlers to use new names
4. Deprecate old names with warnings
5. Remove old names in v0.3.0

**Concrete Patch:**
```typescript
// packages/arc-ag-ui/src/event-types.ts
export enum AGUIEventType {
  // Standardize on Python's vocabulary (more precise)
  RUN_STARTED = 'RUN_STARTED',
  RUN_COMPLETED = 'RUN_COMPLETED',
  RUN_FAILED = 'RUN_FAILED',
  RUN_CANCELLED = 'RUN_CANCELLED',
  
  /** @deprecated Use RUN_COMPLETED - kept for backwards compat until v0.3.0 */
  RUN_FINISHED = 'RUN_COMPLETED',
  /** @deprecated Use RUN_FAILED - kept for backwards compat until v0.3.0 */
  RUN_ERROR = 'RUN_FAILED',
  
  // ... rest of events
}

// Update RUN_LIFECYCLE_EVENTS set
export const RUN_LIFECYCLE_EVENTS = new Set<AGUIEventType>([
  AGUIEventType.RUN_STARTED,
  AGUIEventType.RUN_COMPLETED,
  AGUIEventType.RUN_FAILED,
  AGUIEventType.RUN_CANCELLED,
]);
```

**Estimated Effort:** 2 hours (high priority, must be done this week)

**Testing Required:**
- Verify Python emits RUN_COMPLETED/RUN_FAILED/RUN_CANCELLED
- Verify TypeScript handlers recognize all three events
- Test run lifecycle UI updates correctly
- Add integration test for event name matching

---

### 3.1 High Priority Risks

#### Risk 1: Error Code Mismatch
**Severity:** MEDIUM-HIGH  
**Impact:** Degraded error handling when Python emits unrecognized error codes

**Details:**
- Python has 14 error codes, TypeScript has 8
- 12 of 14 Python codes missing in TypeScript (only TIMEOUT and INVALID_INPUT are shared)
- TypeScript has 6 codes Python doesn't use: TRACE_NOT_FOUND, EXECUTION_FAILED, PARSE_ERROR, WORKFLOW_NOT_FOUND, PERMISSION_DENIED, UNKNOWN

**Failure Scenario:**
1. Python backend detects no runtime in workspace
2. Emits `ArcError(code="NO_RUNTIME_DETECTED", ...)`
3. TypeScript frontend receives error
4. Cannot match code to enum
5. Falls back to generic error handling or throws if using strict enum matching
6. User sees unhelpful error message or UI breaks

**Severity Rationale:**
- Rated MEDIUM-HIGH (not HIGH) because impact depends on TypeScript implementation
- If TypeScript uses tolerant string matching: degraded UX (generic errors)
- If TypeScript uses strict enum matching with no default: runtime failure
- Need to verify: Does TypeScript code use `switch(code)` without default branch?

**Migration Path:**
1. **First:** Write canonical error code list as ADR amendment (prerequisite)
2. Add missing codes to TypeScript enum
3. Add PERMISSION_DENIED to Python (TypeScript has it, Python doesn't)
4. Mark deprecated codes with @deprecated JSDoc
5. Follow ADR-022 deprecation timeline for removals

**Estimated Effort:** 7 hours total (4 hours ADR + 3 hours implementation)

---

#### Risk 2: RuntimeCapabilities v2 Not Supported in TypeScript
**Severity:** MEDIUM-HIGH (conditional on UI gating behavior)  
**Impact:** TypeScript cannot correctly parse v2 capability reports from Python

**Details:**
- Python has RuntimeCapability v2 schema with migration from v1
- TypeScript only has RuntimeCapabilities v1
- Python may emit v2 capability reports
- TypeScript will fail to parse or fall back to v1 incorrectly

**Failure Scenario:**
1. Python adapter reports capabilities using v2 schema
2. TypeScript receives capability report with `schema_version: 2`
3. If TypeScript has tolerant parsing: accepts v2, ignores unknown fields → degradation
4. If TypeScript has strict validation: rejects v2 → runtime failure
5. UI shows incorrect capability information or fails to load

**Severity Rationale:**
- Rated MEDIUM-HIGH because actual impact depends on TypeScript parsing behavior
- If Pydantic serialization includes `schema_version: 2` and TypeScript ignores extra fields: degradation, not crash
- Upgrade to HIGH if v2-only fields (`allow_paid_calls`, `cost_source_default`) gate UI behavior
- Example HIGH scenario: UI needs to show paid-call warnings but can't read `allow_paid_calls` field

**Critical v2 Fields:**
- `allow_paid_calls`: Gates whether runtime can make paid API calls
- `cost_source_default`: Indicates whether costs are estimated or measured
- `mode`: RuntimeMode enum (fake, gated_local, provider_backed)
- `profile_id`, `isolation_id`: Runtime isolation configuration

**v2 Schema Differences:**
- v2 uses `RuntimeMode` enum (fake, gated_local, provider_backed)
- v2 has `profile_id`, `isolation_id` fields
- v2 has `allow_paid_calls`, `cost_source_default` fields
- v2 has `supports_cancellation`, `supports_streaming` fields
- v2 validates paid call invariants

**Migration Path:**
1. Port RuntimeCapability v2 schema to TypeScript
2. Port `migrate_v1_to_v2()` function to TypeScript
3. **Critical:** Mirror Python's paid-call invariant validation (if `allow_paid_calls=true`, `mode` must be `provider_backed`)
4. Update TypeScript parsers to handle both v1 and v2 with schema version detection
5. Add `normalizeCapability()` function that auto-migrates v1→v2
6. Test round-trip serialization with fixtures

**Estimated Effort:** 6 hours (includes invariant validation testing)

---

### 3.2 Medium Risks

#### Risk 3: WorkflowNode Missing source_location Field
**Severity:** MEDIUM  
**Impact:** Source location data lost in cross-language serialization

**Details:**
- Python WorkflowNode has `source_location: Optional[SourceLocation]` field
- TypeScript WorkflowNode missing this field
- When Python serializes node with source location, TypeScript ignores it

**Impact:**
- Cannot jump to source code from graph visualization
- Debugging harder without file/line/column info
- Feature gap vs Python capabilities

**Migration Path:**
1. Add `source_location?: SourceLocation` to TypeScript WorkflowNode
2. Add SourceLocation interface to TypeScript
3. Update graph visualization to use source location if present
4. Test with Python-generated workflows

**Estimated Effort:** 2-3 hours

---

#### Risk 4: RunRecord Missing audit_path and budget Fields
**Severity:** MEDIUM  
**Impact:** Audit path and budget data not accessible from TypeScript protocol types package

**Details:**
- Python RunRecord has `audit_path: Optional[str]` field (schemas.py:154)
- Python RunRecord has `budget: Optional[BudgetVector]` field (schemas.py:155)
- TypeScript arc-protocol-types.ts missing these fields
- Note: arc-extension/arc-protocol.ts may have these fields

**Impact:**
- TypeScript code using arc-protocol-ts package cannot access audit path
- Budget information not available in protocol types
- May cause issues for audit chain features (ADR-021)

**Migration Path:**
1. Verify if arc-extension/arc-protocol.ts has these fields
2. If yes: Document that arc-protocol-ts is subset, arc-extension has full schema
3. If no: Add fields to both TypeScript locations
4. Update TypeScript consumers to use audit_path and budget

**Estimated Effort:** 1-2 hours

---

#### Risk 5: Event Type Registry Mismatch
**Severity:** MEDIUM  
**Impact:** TypeScript UI may not recognize Python-emitted events

**Details:**
- Python has 40+ event types in EVENT_TYPES registry
- TypeScript AG-UI has 34 event types
- Missing in TypeScript: SwarmGraph events, HITL events, Cockpit events, Agent/Node lifecycle events

**Missing Event Categories:**
- **SwarmGraph:** SWARMGRAPH_TOPOLOGY, SWARMGRAPH_CONSENSUS, SWARMGRAPH_COST
- **HITL:** HITL_PROMPT, HITL_RESPONSE, HITL_TIMEOUT
- **Cockpit:** CONTRACT_PROPOSED, CONTRACT_ACCEPTED, CONTRACT_FULFILLED, CONTRACT_VIOLATED, RECEIPT_GENERATED, FAILURE_AUTOPSY_GENERATED, EVIDENCE_REF_CREATED
- **Agent:** AGENT_START, AGENT_END
- **Node:** NODE_STARTED, NODE_UPDATE, NODE_FAILED
- **Handoff:** HANDOFF

**Impact:**
- SwarmGraph topology/consensus/cost events not rendered in UI
- HITL prompts not displayed
- Cockpit contract/receipt/autopsy events ignored
- Agent and node lifecycle not visualized

**Migration Path:**
1. Add missing event types to TypeScript AGUIEventType enum
2. Update event handlers in UI components
3. Add rendering logic for new event types
4. Test with Python-generated event streams

**Estimated Effort:** 6-8 hours (includes UI work)

---

### 3.3 Low Risks

#### Risk 6: SourceType Enum vs String
**Severity:** LOW  
**Impact:** TypeScript accepts invalid source types, Python validates

**Details:**
- Python SourceType is enum: LOCAL_REPO, CONTEXT7, VERCEL_GREP, GITHUB_SEARCH, WEB_SEARCH
- TypeScript source_type is plain string
- TypeScript can accept any string, Python will reject invalid values

**Migration Path:**
- Add SourceType enum to TypeScript
- Update ContextPackEntry to use enum
- Low priority - current behavior is permissive, not breaking

**Estimated Effort:** 1 hour

---

## 4. Revised Migration Plan

**Total Estimated Effort:** 60-80 hours (revised from initial 30-40 hour estimate)

**Rationale for Revision:**
- Initial estimate underestimated event type UI work
- Missed architectural work (version negotiation, CI enforcement)
- Didn't account for prerequisite work (canonical error list ADR)
- Testing should be in Phase 1, not Phase 4

### Week 1: Critical Path (Priority 0-1)

**Focus:** Fix runtime-breaking issues and establish test infrastructure

**Day 1-2:**
1. ✅ **Fix audit miscounts** (1 hour) - COMPLETED
2. ✅ **Update envelope.py with removal date** (1 hour) - COMPLETED
3. **Resolve RUN_FINISHED collision** (Risk 0, 2 hours) - **CRITICAL, must complete this week**
4. **Build cross-language test harness** (4 hours) - prerequisite for all validation
5. **Write canonical error code ADR amendment** (4 hours) - prerequisite for error code sync

**Day 3-4:**
6. **Apply Patch A: Error codes** (3 hours) - with test harness validation
7. **Wire format validation tests** (4 hours) - catch Pydantic serialization issues
8. **Decide version negotiation policy** (4 hours) - architectural decision for ADR-022/023

**Week 1 Deliverables:**
- RUN_FINISHED collision fixed (Risk 0)
- Cross-language test harness operational
- Canonical error code list in ADR
- Error codes synced between Python and TypeScript
- Version negotiation policy documented

**Week 1 Total:** ~23 hours

---

### Week 2: High Priority (Priority 2-3)

**Focus:** Complete schema parity and policy documentation

**Day 1-2:**
9. **Apply Patch B: RuntimeCapabilities v2** (6 hours) - with paid-call invariant validation
10. **Apply Patches C, D, F: Small schema additions** (5 hours) - batch into one PR
    - WorkflowNode.source_location
    - RunRecord.audit_path and budget
    - SourceType enum

**Day 3-4:**
11. **Apply Patch E2: Event type additions** (4 hours) - type-only, defer UI rendering
12. **Document forward compatibility policy** (2 hours) - ADR work for unknown events/codes
13. **Add field naming convention enforcement** (2 hours) - snake_case linting rule

**Week 2 Deliverables:**
- RuntimeCapabilities v2 support in TypeScript
- All schema fields synced
- Event types added (type-level)
- Forward compatibility policy documented
- Field naming conventions enforced

**Week 2 Total:** ~19 hours

---

### Week 3: Infrastructure (Medium Priority)

**Focus:** Prevent future schema drift

**Day 1-3:**
14. **Add JSON Schema export + CI drift check** (16 hours) - **prevents need for future audits**
    - Emit JSON Schema from Pydantic on every build
    - Check into repo
    - TypeScript CI validates against JSON Schema
    - Fail build on mismatch
15. **Create protocol/fixtures/ directory** (2 hours) - cross-language test fixtures
16. **Port schema documentation to TypeScript** (4 hours) - JSDoc parity with Python docstrings

**Week 3 Deliverables:**
- Automated schema drift detection in CI
- Cross-language fixture library
- Documentation parity between Python and TypeScript

**Week 3 Total:** ~22 hours

---

### Week 4: Validation & Cleanup

**Focus:** End-to-end validation and documentation

**Day 1-2:**
17. **Implement version negotiation** (6 hours) - based on Week 1 policy decision
18. **Implement forward compatibility policy** (4 hours) - based on Week 2 policy
19. **Integration testing** (6 hours) - end-to-end with real Python backend + TypeScript frontend
20. **Update CHANGELOG for v0.2.0** (2 hours) - document all changes and deprecations

**Week 4 Deliverables:**
- Version negotiation implemented
- Forward compatibility implemented
- Full integration test coverage
- CHANGELOG updated for v0.2.0 release

**Week 4 Total:** ~18 hours

---

**Grand Total:** 82 hours (~2 engineer-weeks of focused work)

**Critical Path Items (Must Complete Week 1):**
1. **RUN_FINISHED collision fix** (Risk 0) - blocks run lifecycle tracking
2. **Cross-language test harness** - blocks all other validation
3. **Canonical error code list** - blocks error code sync
4. **Error code sync** (Risk 1) - blocks proper error handling

**Dependency Chain:**
- Week 1 Day 1-2 → Week 1 Day 3-4 (test harness needed for validation)
- Week 1 → Week 2 (policies needed before implementation)
- Week 2 → Week 3 (schemas must be synced before CI enforcement)
- Week 1-3 → Week 4 (all changes must land before integration testing)

---

## 5. Recommendations

### 5.1 Immediate Actions

1. **Create Schema Sync Process**
   - Establish single source of truth for shared schemas
   - Consider generating TypeScript from Python (or vice versa)
   - Add CI check to detect schema drift

2. **Document Schema Ownership**
   - Clarify which package owns each schema
   - Document relationship between arc-protocol-ts and arc-extension/arc-protocol.ts
   - Explain when to use each package

3. **Add Schema Version Tests**
   - Test all migration functions
   - Verify readers support N and N-1 versions
   - Ensure writers always write latest version

### 5.2 Long-Term Improvements

1. **Schema Generation**
   - Consider using Pydantic → TypeScript code generation
   - Or JSON Schema as intermediate format
   - Reduces manual sync burden

2. **Deprecation Tracking**
   - Create deprecation registry document
   - Track all active shims and removal dates
   - Automate removal reminders

3. **Breaking Change Policy**
   - Enforce ADR-022 in code review
   - Require CHANGELOG entry for every deprecation
   - Require migration path documentation

---

## 6. Appendix

### 6.1 Schema File Locations

**Python:**
- Core: `python/src/agent_runtime_cockpit/protocol/`
- Events: `python/src/agent_runtime_cockpit/protocol/events.py`
- Capabilities: `python/src/agent_runtime_cockpit/protocol/capabilities.py`, `runtime_capability.py`
- Cockpit: `python/src/agent_runtime_cockpit/protocol/run_contract.py`, `run_receipt.py`, `failure_autopsy.py`

**TypeScript:**
- Protocol Types: `packages/arc-protocol-ts/src/arc-protocol-types.ts`
- Extension Protocol: `packages/arc-extension/src/common/arc-protocol.ts`
- Event Types: `packages/arc-ag-ui/src/event-types.ts`

### 6.2 Related ADRs

- **ADR-004:** Event schema versioning
- **ADR-018:** Protocol package as canonical schema home
- **ADR-021:** Audit chain architecture (requires audit_path field)
- **ADR-022:** Deprecation policy (defines shim lifetime)

### 6.3 Audit Methodology

1. Used Task tool to explore codebase and identify schema files
2. Read Python schema files in `protocol/` directory
3. Read TypeScript schema files in `arc-protocol-ts` and `arc-extension`
4. Compared field-by-field for consistency
5. Searched for deprecation shims and removal dates
6. Analyzed ADR-022 for deprecation policy
7. Identified breaking change risks based on schema mismatches

---

## 7. Architectural Gaps Not Covered by Initial Audit

The initial audit focused on type-level schema consistency but missed several architectural concerns that affect schema reliability and maintainability.

### 7.1 Wire Format Validation

**Gap:** Audit compares type definitions but doesn't verify actual JSON payloads over the wire.

**Risk:** Pydantic serialization behavior can introduce drift that type-level audits miss:
- `model_dump()` defaults and options
- `alias_generator` field name transformations  
- `exclude_none` behavior
- Custom JSON encoders

**Action Required:** Capture real JSON payloads from both sides and diff. Add wire-format fixture tests.

**Estimated Effort:** 4 hours

### 7.2 Version Negotiation Protocol

**Gap:** No handshake where client advertises supported schema versions.

**Risk:** Producer has no way to know whether to emit v1 or v2 schemas.

**Action Required:** Add version negotiation design to ADR-022 or create ADR-023. Decide: negotiate vs. always-migrate vs. always-downgrade.

**Estimated Effort:** 4 hours (ADR) + 6 hours (implementation)

### 7.3 CI Schema Drift Detection

**Gap:** No automated enforcement of schema consistency.

**Risk:** Every fix in this audit will decay within months without CI enforcement.

**Recommended Solution:** Emit JSON Schema from Pydantic on every build, check into repo, fail TypeScript CI on mismatch.

**Estimated Effort:** 16 hours

### 7.4 Forward Compatibility Policy

**Gap:** Undefined behavior for unknown event types, error codes, or schema versions.

**Action Required:** Document in ADR-022 whether TypeScript should throw (strict) or warn+ignore (lenient) for unknown values.

**Estimated Effort:** 2 hours (policy) + 4 hours (implementation)

### 7.5 Field Naming Convention Enforcement

**Gap:** No documented policy on snake_case vs camelCase.

**Action Required:** Document that wire format uses snake_case. Add linting rule to enforce snake_case in TypeScript protocol types.

**Estimated Effort:** 2 hours

### 7.6 Cross-Language Test Fixtures

**Gap:** No shared fixture directory for cross-language tests.

**Action Required:** Create `protocol/fixtures/` directory with JSON fixtures for each schema type. Load in both Python and TypeScript tests.

**Estimated Effort:** 2 hours

### 7.7 Schema Documentation Parity

**Gap:** Python Pydantic models have docstrings and `Field(description=...)`, TypeScript interfaces don't.

**Action Required:** Port descriptions to TypeScript as JSDoc comments.

**Estimated Effort:** 4 hours

---

**Report Status:** Revised (v2)  
**Revision Date:** 2026-05-22  
**Changes in v2:**
- Fixed miscounts (13→14 error codes, 5→12 missing codes)
- Added CRITICAL Risk 0 (RUN_FINISHED collision)
- Updated envelope.py with v0.3.0 removal date
- Added architectural gaps section (7 gaps identified)
- Revised effort estimate to 60-80 hours
- Reordered migration plan (critical path first, tests in Week 1)

**Next Review:** After Week 1 critical path completion  
**Owner:** Engineering team  
**Approver:** Technical lead
