# Handover: Track D (Audit Chain) - EU AI Act Compliance

**Date:** 2026-05-22  
**Session:** New session starting Track D implementation  
**Deadline:** August 2, 2026 (72 days remaining)  
**Priority:** CRITICAL - EU AI Act enforcement deadline

---

## Previous Session Summary

The previous session (2026-05-22) completed:
- ✅ **STATUS_ANALYSIS.md** - Comprehensive project status analysis
- ✅ **README.md** - Version fixes (v1.0.0-alpha → v0.1.0-alpha)
- ✅ **Phase 1 Task B.1** - CLI help text audit (111 commands, 100% coverage)
- ✅ **Phase 1 Task B.2** - Slash command audit (19 commands, gap documented)
- ✅ **Phase 1 Task E.1** - ADR-022 Deprecation Policy (reviewed and accepted)

**Commit:** `02f39f4` - "docs: complete Phase 1 tasks B.1, B.2, E.1 and update README version"  
**Branch:** `main` (ahead of origin by 1 commit - not yet pushed)

**Phase 1 Progress:** 3 of ~40 tasks complete (7.5%)

---

## Track D Overview: Audit Chain for EU AI Act Compliance

### Critical Context

**EU AI Act Enforcement:** August 2, 2026 (72 days from now)

ARC Studio must implement a tamper-evident audit chain to satisfy EU AI Act transparency and accountability obligations. Even as a "limited risk" desktop developer tool, ARC Studio needs:

1. **Transparency** - Users can inspect what the agent did and why
2. **Accountability** - Decisions are attributable to specific principals
3. **Tamper-evidence** - Audit records cannot be silently modified
4. **Completeness** - All material agent actions are logged

### Architecture Decision Records

**Primary ADRs:**
- **ADR-021** - Audit Chain Architecture for EU AI Act Compliance (Proposed, draft 2026-05-21)
  - Location: `docs/adr/021-audit-chain-architecture.md`
  - 433 lines, comprehensive design
  - HMAC-SHA256 signed audit chain
  - JSONL storage at `~/.arc/audit/<run_id>.audit.jsonl`
  - Event types: llm_request, llm_response, tool_call, tool_result, hitl_prompt, hitl_response, budget_decision, run lifecycle

- **ADR-005** - Audit HMAC Key Management and Rotation (Proposed)
  - Location: `docs/adr/005-audit-key-management.md`
  - 249 lines
  - Key generation, storage (keychain), rotation
  - CLI commands: `arc audit init`, `arc audit verify`, `arc audit export`

**Related ADRs:**
- **ADR-022** - Deprecation Policy (Accepted 2026-05-22)
- **ADR-020** - Desktop-First Product Path (Proposed)
- **ADR-014** - Security Architecture (referenced)
- **ADR-019** - Tool Trust Boundaries (referenced)

---

## Current Implementation Status

### ✅ Already Implemented

The audit module already exists with substantial implementation:

**Location:** `python/src/agent_runtime_cockpit/audit/`

**Files:**
- `schema.py` (322+ lines) - Audit event types and Pydantic models
- `storage.py` - Audit chain storage (JSONL backend)
- `session.py` - Audit session management and redaction
- `__init__.py` - Module exports

**Total lines:** ~1,396 lines in audit module

**Event Types Implemented:**
```python
class AuditEventType(str, Enum):
    llm_request = "llm_request"
    llm_response = "llm_response"
    tool_call = "tool_call"
    tool_result = "tool_result"
    hitl_prompt = "hitl_prompt"
    hitl_response = "hitl_response"
    budget_decision = "budget_decision"
    run_started = "run_started"
    run_completed = "run_completed"
    run_failed = "run_failed"
    run_cancelled = "run_cancelled"
```

**Event Models Implemented:**
- `LlmRequestEvent`
- `LlmResponseEvent`
- `ToolCallEvent`
- `ToolResultEvent`
- `BudgetDecisionEvent`
- `RunStartedEvent`
- `RunCompletedEvent`
- `RunFailedEvent`
- `RunCancelledEvent`

**Additional Schemas:**
- `python/src/agent_runtime_cockpit/schemas/audit_events.py` - Alternative audit schema location

### ⚠️ Status Unknown / Needs Verification

The following need to be checked:
1. **HMAC signing/verification** - Is it implemented in `storage.py`?
2. **Key management** - Is key generation/storage implemented?
3. **CLI commands** - Are `arc audit verify` and `arc audit export` implemented?
4. **Adapter integration** - Is SwarmGraph adapter wired to emit audit events?
5. **Tests** - What test coverage exists?

---

## Phase 1 Tasks: Track D (Audit Chain)

### Task D.1: Implement Audit Event Schema (3 hours)

**Status:** ⚠️ PARTIALLY COMPLETE - Schema exists, needs verification and completion

**What's Already Done:**
- ✅ Event type enum (`AuditEventType`)
- ✅ Pydantic models for all event types
- ✅ Base `AuditEvent` class with `to_audit_event()` method
- ✅ Supporting enums (`TrustLevel`, `StopReason`, `RuntimeMode`)

**What Needs to be Done:**
1. **Verify schema completeness** against ADR-021 specification
2. **Add missing fields** if any (compare with ADR-021 section "Audit Event Schema")
3. **Add schema version field** (`version: "1"`) to all events
4. **Add principal field** (default `"local"` for desktop 1.0)
5. **Add sequence field** for event ordering
6. **Write schema tests** - Unit tests for all event types
7. **Add schema migration tests** - Forward/backward compatibility

**Acceptance Criteria:**
- [ ] All event types from ADR-021 are implemented as Pydantic models
- [ ] Each event has: version, event_type, timestamp, principal, run_id, session_id, sequence, payload
- [ ] Schema tests cover all event types with valid/invalid inputs
- [ ] Schema migration tests prove forward/backward compatibility
- [ ] Documentation: Each event type has docstring with example

**Files to Check/Modify:**
- `python/src/agent_runtime_cockpit/audit/schema.py`
- `python/src/agent_runtime_cockpit/schemas/audit_events.py` (consolidate if duplicate)
- `python/tests/audit/test_schema.py` (create if missing)

**Verification Commands:**
```bash
cd python

# Run schema tests
uv run pytest tests/audit/test_schema.py -v

# Check schema coverage
uv run pytest tests/audit/ --cov=agent_runtime_cockpit.audit.schema --cov-report=term-missing

# Verify all event types can serialize
uv run python -c "
from agent_runtime_cockpit.audit.schema import *
events = [
    LlmRequestEvent(run_id='test', provider='anthropic', model='claude-3-5-sonnet-20241022'),
    LlmResponseEvent(run_id='test', provider='anthropic', model='claude-3-5-sonnet-20241022', response_id='msg_123', stop_reason=StopReason.end_turn, usage={'input_tokens': 100, 'output_tokens': 50}, content=[]),
    # ... test all event types
]
for e in events:
    print(f'{e.event_type}: {e.to_audit_event()}')
"
```

---

### Task D.2: Implement HMAC Signing/Verification (4 hours)

**Status:** ⚠️ UNKNOWN - Needs investigation

**What Needs to be Done:**
1. **Implement HMAC-SHA256 signing** per ADR-021 specification
2. **Implement hash chain linkage** (each event's HMAC includes previous HMAC)
3. **Implement key generation** (256-bit random key)
4. **Implement key storage** (filesystem at `~/.arc/secrets/audit_key`, mode 0600)
5. **Implement key loading** with fallback to `ARC_AUDIT_SECRET` env var
6. **Implement verification** (recompute HMACs and check chain integrity)
7. **Write HMAC tests** - Unit tests for signing, verification, tampering detection

**HMAC Computation (from ADR-021):**
```python
def compute_hmac(event: dict, prev_hmac: str, key: bytes) -> str:
    # Canonical JSON serialization (sorted keys, no whitespace)
    event_json = json.dumps(event, sort_keys=True, separators=(',', ':'))
    
    # Concatenate event JSON + previous HMAC
    message = event_json.encode('utf-8') + prev_hmac.encode('utf-8')
    
    # Compute HMAC-SHA256
    h = hmac.new(key, message, hashlib.sha256)
    return h.hexdigest()
```

**Key Storage:**
```
~/.arc/secrets/audit_key (mode 0600, owner-only read/write)
```

**Acceptance Criteria:**
- [ ] HMAC signing function matches ADR-021 specification
- [ ] Hash chain linkage works (each event depends on previous)
- [ ] Key generation creates 256-bit random key
- [ ] Key storage uses mode 0600 (owner-only)
- [ ] Key loading tries filesystem first, then env var
- [ ] Verification detects tampering (modified events fail verification)
- [ ] Tests cover: signing, verification, tampering detection, missing key, invalid key

**Files to Create/Modify:**
- `python/src/agent_runtime_cockpit/audit/hmac.py` (create)
- `python/src/agent_runtime_cockpit/audit/keys.py` (create)
- `python/tests/audit/test_hmac.py` (create)
- `python/tests/audit/test_keys.py` (create)

**Verification Commands:**
```bash
cd python

# Run HMAC tests
uv run pytest tests/audit/test_hmac.py -v

# Test key generation and storage
uv run python -c "
from agent_runtime_cockpit.audit.keys import generate_key, store_key, load_key
key = generate_key()
print(f'Generated key: {key[:16]}...')
store_key(key)
loaded = load_key()
assert loaded == key, 'Key mismatch!'
print('✓ Key generation and storage working')
"

# Test HMAC signing and verification
uv run python -c "
from agent_runtime_cockpit.audit.hmac import compute_hmac, verify_chain
from agent_runtime_cockpit.audit.schema import LlmRequestEvent

event = LlmRequestEvent(run_id='test', provider='anthropic', model='claude-3-5-sonnet-20241022')
event_dict = event.to_audit_event()

key = b'test_key_32_bytes_long_exactly!!'
hmac1 = compute_hmac(event_dict, '', key)
print(f'HMAC: {hmac1}')

# Verify tampering detection
event_dict['model'] = 'tampered'
hmac2 = compute_hmac(event_dict, '', key)
assert hmac1 != hmac2, 'Tampering not detected!'
print('✓ HMAC signing and tampering detection working')
"
```

---

### Task D.3: Implement Audit Chain Storage (3 hours)

**Status:** ⚠️ PARTIALLY COMPLETE - `storage.py` exists, needs verification

**What's Already Done:**
- ✅ `audit/storage.py` exists (needs review)

**What Needs to be Done:**
1. **Review existing storage implementation** in `audit/storage.py`
2. **Implement JSONL append-only storage** at `~/.arc/audit/<run_id>.audit.jsonl`
3. **Integrate HMAC signing** into storage (sign events before writing)
4. **Implement chain verification** (read chain, verify all HMACs)
5. **Implement atomic writes** (write to temp file, then rename)
6. **Handle concurrent writes** (file locking if needed)
7. **Write storage tests** - Unit tests for append, read, verify

**Storage Format (JSONL):**
```jsonl
{"version":"1","event_type":"run_started","timestamp":"2026-05-22T15:00:00.000Z","principal":"local","run_id":"run_abc123","session_id":"session_xyz","sequence":0,"payload":{...},"hmac":"abc123...","prev_hmac":null}
{"version":"1","event_type":"llm_request","timestamp":"2026-05-22T15:00:01.000Z","principal":"local","run_id":"run_abc123","session_id":"session_xyz","sequence":1,"payload":{...},"hmac":"def456...","prev_hmac":"abc123..."}
```

**Acceptance Criteria:**
- [ ] Audit chains stored at `~/.arc/audit/<run_id>.audit.jsonl`
- [ ] Each line is a valid JSON object (JSONL format)
- [ ] Events are appended atomically (no partial writes)
- [ ] HMAC signatures are computed and stored with each event
- [ ] Chain verification reads entire file and checks all HMACs
- [ ] Tests cover: append, read, verify, tampering detection, concurrent writes

**Files to Check/Modify:**
- `python/src/agent_runtime_cockpit/audit/storage.py` (review and complete)
- `python/tests/audit/test_storage.py` (create if missing)

**Verification Commands:**
```bash
cd python

# Run storage tests
uv run pytest tests/audit/test_storage.py -v

# Test audit chain creation and verification
uv run python -c "
from pathlib import Path
from agent_runtime_cockpit.audit.storage import AuditChainWriter, AuditChainReader
from agent_runtime_cockpit.audit.schema import RunStartedEvent, LlmRequestEvent
from agent_runtime_cockpit.audit.keys import generate_key

# Create test audit chain
audit_dir = Path('/tmp/arc_audit_test')
audit_dir.mkdir(exist_ok=True)
run_id = 'test_run_123'

key = generate_key()
writer = AuditChainWriter(audit_dir, run_id, key)

# Append events
event1 = RunStartedEvent(run_id=run_id, runtime='swarmgraph', mode='fake', profile='default', isolation='subprocess')
writer.append(event1)

event2 = LlmRequestEvent(run_id=run_id, provider='anthropic', model='claude-3-5-sonnet-20241022')
writer.append(event2)

writer.close()

# Verify chain
reader = AuditChainReader(audit_dir, run_id, key)
result = reader.verify()
print(f'Verification: {result}')
assert result.verified, 'Chain verification failed!'
print('✓ Audit chain storage and verification working')
"
```

---

### Task D.4: Implement for SwarmGraph Adapter (4 hours)

**Status:** NOT STARTED (depends on D.1, D.2, D.3)

**What Needs to be Done:**
1. **Wire SwarmGraph adapter** to emit audit events
2. **Emit run lifecycle events** (run_started, run_completed, run_failed, run_cancelled)
3. **Emit LLM events** (llm_request, llm_response) - if SwarmGraph exposes them
4. **Emit tool events** (tool_call, tool_result) - if SwarmGraph exposes them
5. **Configure audit via environment** (`ARC_AUDIT_ENABLED=true`)
6. **Write integration tests** - End-to-end test with SwarmGraph run

**Note:** This task is listed in PHASE_1_TASKS.md but is part of Week 1-2. It may be deferred to Week 3-4 depending on D.1-D.3 completion time.

**Acceptance Criteria:**
- [ ] SwarmGraph runs emit audit events when `ARC_AUDIT_ENABLED=true`
- [ ] Audit chain is created at `~/.arc/audit/<run_id>.audit.jsonl`
- [ ] Chain includes run lifecycle events at minimum
- [ ] Chain verifies successfully after run completes
- [ ] Integration test proves end-to-end audit chain creation

**Files to Modify:**
- `python/src/agent_runtime_cockpit/adapters/swarmgraph/adapter.py`
- `python/tests/adapters/test_swarmgraph_audit.py` (create)

---

## Implementation Strategy

### Recommended Approach

**Phase 1: Verify and Complete Schema (D.1)**
1. Read `audit/schema.py` thoroughly
2. Compare with ADR-021 specification
3. Add missing fields (version, principal, sequence, hmac, prev_hmac)
4. Write comprehensive schema tests
5. Verify: `uv run pytest tests/audit/test_schema.py -v`

**Phase 2: Implement HMAC (D.2)**
1. Create `audit/hmac.py` with `compute_hmac()` and `verify_hmac()` functions
2. Create `audit/keys.py` with key generation, storage, loading
3. Write HMAC tests with tampering detection
4. Verify: `uv run pytest tests/audit/test_hmac.py tests/audit/test_keys.py -v`

**Phase 3: Complete Storage (D.3)**
1. Review existing `audit/storage.py`
2. Integrate HMAC signing into storage writer
3. Implement chain verification in storage reader
4. Write storage tests
5. Verify: `uv run pytest tests/audit/test_storage.py -v`

**Phase 4: Integration (D.4 - Optional for Week 1-2)**
1. Wire SwarmGraph adapter to emit events
2. Write integration test
3. Verify: `uv run pytest tests/adapters/test_swarmgraph_audit.py -v`

### Time Estimates

| Task | Estimated | Notes |
|------|-----------|-------|
| D.1 | 2-3 hours | Schema mostly done, needs completion and tests |
| D.2 | 4-5 hours | New implementation, critical for security |
| D.3 | 2-3 hours | Storage exists, needs HMAC integration |
| D.4 | 4-5 hours | Adapter wiring, integration tests |
| **Total** | **12-16 hours** | ~2-3 work sessions |

---

## Key References

### Documentation
- `docs/adr/021-audit-chain-architecture.md` - Primary design document (433 lines)
- `docs/adr/005-audit-key-management.md` - Key management design (249 lines)
- `docs/PHASE_1_TASKS.md` - Task breakdown and acceptance criteria
- `docs/STATUS_ANALYSIS.md` - Current project status

### Code Locations
- `python/src/agent_runtime_cockpit/audit/` - Audit module (1,396 lines)
  - `schema.py` - Event types and models (322+ lines)
  - `storage.py` - JSONL storage backend
  - `session.py` - Audit session and redaction
  - `__init__.py` - Module exports
- `python/src/agent_runtime_cockpit/schemas/audit_events.py` - Alternative schema location (may need consolidation)

### Tests
- `python/tests/audit/` - Audit tests (create if missing)
  - `test_schema.py` - Schema tests
  - `test_hmac.py` - HMAC signing/verification tests
  - `test_keys.py` - Key management tests
  - `test_storage.py` - Storage tests
  - `test_integration.py` - End-to-end tests

---

## Success Criteria

### Week 1-2 Completion (D.1, D.2, D.3)

**Must Have:**
- ✅ Audit event schema complete with all fields from ADR-021
- ✅ HMAC-SHA256 signing and verification implemented
- ✅ Audit chain storage (JSONL) with HMAC integration
- ✅ Key generation and storage (filesystem, mode 0600)
- ✅ Comprehensive tests (schema, HMAC, storage)
- ✅ All tests passing: `uv run pytest tests/audit/ -v`

**Nice to Have:**
- ✅ D.4 SwarmGraph adapter integration (may defer to Week 3-4)
- ✅ CLI commands (`arc audit verify`, `arc audit export`) - may defer to Week 3-4

### Verification Checklist

Before marking Track D complete:

```bash
# 1. All audit tests pass
cd python && uv run pytest tests/audit/ -v

# 2. Schema coverage
uv run pytest tests/audit/test_schema.py --cov=agent_runtime_cockpit.audit.schema --cov-report=term-missing

# 3. HMAC coverage
uv run pytest tests/audit/test_hmac.py --cov=agent_runtime_cockpit.audit.hmac --cov-report=term-missing

# 4. Storage coverage
uv run pytest tests/audit/test_storage.py --cov=agent_runtime_cockpit.audit.storage --cov-report=term-missing

# 5. Full test suite still passes
uv run pytest -q

# 6. Type checking passes
uv run mypy src/agent_runtime_cockpit/audit/

# 7. Linting passes
uv run ruff check src/agent_runtime_cockpit/audit/
```

---

## Risk Mitigation

### Critical Risks

1. **Deadline Pressure (Aug 2, 2026 - 72 days)**
   - Mitigation: Prioritize D.1-D.3 over D.4-D.14
   - Mitigation: Focus on SwarmGraph adapter first (most mature)
   - Mitigation: Defer other adapters to Phase 1 completion

2. **HMAC Implementation Security**
   - Mitigation: Follow ADR-021 specification exactly
   - Mitigation: Use timing-safe comparison for HMAC verification
   - Mitigation: External security review in Phase 3 (v0.9)

3. **Key Management Complexity**
   - Mitigation: Start with simple filesystem storage (mode 0600)
   - Mitigation: Defer keychain integration to Phase 1 completion
   - Mitigation: Document backup requirements clearly

4. **Test Coverage Gaps**
   - Mitigation: Write tests alongside implementation (TDD)
   - Mitigation: Require 80%+ coverage for audit module
   - Mitigation: Include tampering detection tests

---

## Next Steps

### Immediate Actions (This Session)

1. **Read existing audit code**
   ```bash
   cd python
   cat src/agent_runtime_cockpit/audit/schema.py
   cat src/agent_runtime_cockpit/audit/storage.py
   cat src/agent_runtime_cockpit/audit/session.py
   ```

2. **Check for existing tests**
   ```bash
   find tests/ -name "*audit*" -type f
   uv run pytest tests/ -k audit --collect-only
   ```

3. **Start with D.1 (Schema Completion)**
   - Compare `audit/schema.py` with ADR-021 specification
   - Add missing fields (version, principal, sequence, hmac, prev_hmac)
   - Write schema tests
   - Verify: `uv run pytest tests/audit/test_schema.py -v`

4. **Continue to D.2 (HMAC Implementation)**
   - Create `audit/hmac.py`
   - Create `audit/keys.py`
   - Write HMAC tests
   - Verify: `uv run pytest tests/audit/test_hmac.py -v`

5. **Complete D.3 (Storage Integration)**
   - Review `audit/storage.py`
   - Integrate HMAC signing
   - Write storage tests
   - Verify: `uv run pytest tests/audit/test_storage.py -v`

### Session Goals

**Minimum:** Complete D.1 (Schema) and D.2 (HMAC)  
**Target:** Complete D.1, D.2, and D.3 (Storage)  
**Stretch:** Start D.4 (SwarmGraph integration)

---

## Contact & Escalation

**Deadline:** August 2, 2026 (72 days)  
**Priority:** CRITICAL  
**Escalation:** If blocked for >4 hours, document blocker and move to next task

**Questions to Resolve:**
1. Should we consolidate `audit/schema.py` and `schemas/audit_events.py`?
2. Should we use keychain storage or filesystem for keys in v0.1?
3. Should we implement key rotation in Phase 1 or defer to Phase 3?

---

**Handover created:** 2026-05-22  
**For session starting:** Track D (Audit Chain) implementation  
**Estimated duration:** 12-16 hours (2-3 work sessions)  
**Success metric:** D.1, D.2, D.3 complete with passing tests
