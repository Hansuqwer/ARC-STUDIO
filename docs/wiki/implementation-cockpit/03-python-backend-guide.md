# 03 — Python Backend Implementation Guide

**Goal:** Detailed implementation plan for 7 new backend capabilities — RunContract, RunReceipt, FailureAutopsy, EvidenceRef, RuntimeCapability validation, TrustDiff, and their CLI verbs.

**Status conventions used:**
- `[EXISTS]` — code present
- `[STUB]` — interface exists, body is `...` or `raise NotImplementedError`
- `[MISSING]` — no code at all

---

## 1. Generate RunContract Before Run Starts

### Purpose

A **RunContract** is a non-repudiable record of what the run *promises* to do: runtime ID, profile, workspace identity, timeout, input hash, and a commitment that the system can later compare against the actual RunReceipt. Generated synchronously before `asyncio.create_task()` in `JobSupervisor.start_run()`.

### Files to Edit

| File | Change |
|------|--------|
| `protocol/schemas.py` | Add `RunContract` model |
| `protocol/errors.py` | Add `CONTRACT_REJECTED`, `CONTRACT_EXPIRED` error codes |
| `orchestration/events.py` | Add `"RUN_CONTRACT_ISSUED"` event type to `EVENT_TYPES` |
| `orchestration/supervisor.py` | Generate and persist `RunContract` in `start_run()` |
| `storage/jsonl.py` | Add `save_contract()` / `load_contract()` methods |
| `storage/sqlite.py` | Add `contracts` table, `save_contract()` / `load_contract()` |
| `storage/indexed_store.py` | Add dual-write contract support, `backfill_contracts()` |
| `cli.py` | Add `arc contract show <run>` command (advanced/debug), optional accept flow |

### New Models in `protocol/schemas.py`

```python
class ContractStatus(str, Enum):
    ISSUED = "issued"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"

class RunContract(BaseModel):
    run_id: str
    workflow_id: str
    runtime: str
    profile_id: str
    workspace_path: str
    workspace_trust_hash: str  # SHA-256 of workspace trust DB entry
    input_hash: str            # SHA-256 of RunRequest.inputs
    timeout_seconds: int
    issued_at: str             # ISO-8601
    expires_at: str            # issued_at + timeout_seconds
    status: ContractStatus = ContractStatus.ISSUED
    accepted_at: Optional[str] = None
    accepted_by: Optional[str] = None  # operator ID if HITL accepted
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Sample Payload

```json
{
  "run_id": "run-a1b2c3d4e5f6",
  "workflow_id": "wf-my-agent",
  "runtime": "swarmgraph",
  "profile_id": "local-paid",
  "workspace_path": "/home/user/projects/my-agent",
  "workspace_trust_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "input_hash": "a7ffc6f8bf1ed76651c14756a061d662f580ff4de43b49fa82d80a4b80f8434a",
  "timeout_seconds": 300,
  "issued_at": "2026-05-16T10:00:00+00:00",
  "expires_at": "2026-05-16T10:05:00+00:00",
  "status": "issued",
  "accepted_at": null,
  "accepted_by": null,
  "metadata": {}
}
```

### Changes to `orchestration/supervisor.py`

```python
# In start_run(), BEFORE creating the asyncio task:
import hashlib

def _compute_input_hash(inputs: dict) -> str:
    return hashlib.sha256(
        json.dumps(inputs, sort_keys=True).encode()
    ).hexdigest()

# Inside start_run(), after RunRecord creation:
contract = RunContract(
    run_id=run.id,
    workflow_id=request.workflow_id,
    runtime=request.runtime or "unknown",
    profile_id=request.profile_id,
    workspace_path=str(Path(request.workspace_root).resolve())
        if request.workspace_root else "unknown",
    workspace_trust_hash=_compute_trust_hash(request.workspace_root, request.workspace_trust_db),
    input_hash=_compute_input_hash(request.inputs),
    timeout_seconds=request.timeout_seconds,
    issued_at=now,
    expires_at=(datetime.now(timezone.utc) + timedelta(seconds=request.timeout_seconds)).isoformat(),
)
self.store.save_contract(contract)
self._emit_event(run_id, "RUN_CONTRACT_ISSUED", {
    "contract": contract.model_dump(),
})
```

### New Tests (`tests/test_contract.py`)

1. `test_contract_generated_before_run` — mock executor, verify `RunContract` stored before run starts
2. `test_contract_fields_populated` — check input_hash, timeout, workspace_path
3. `test_contract_expiry` — contract.expires_at > issued_at
4. `test_contract_missing_workspace_root` — defaults to "unknown"
5. `test_contract_roundtrip_jsonl` — save + load via JsonlTraceStore
6. `test_contract_roundtrip_sqlite` — save + load via SqliteStore
7. `test_contract_cli_show` — `arc contract show <run>` returns contract JSON
8. `test_contract_backfill` — backfill contracts from existing JSONL to SQLite
9. `test_contract_input_hash_determinism` — same inputs produce same hash

### No-Go Boundaries

- **Do NOT** make run execution conditional on contract acceptance (speculative — deferred to v0.2 unless spec says otherwise)
- **Do NOT** store contracts in a separate directory from traces by default (keep `.arc/traces/<run>.contract.json` adjacent to `.arc/traces/<run>.jsonl`)
- **Do NOT** add WS/client push for contract issuance yet — SSE event is sufficient

### Edge Cases

- Run requested with empty inputs → input_hash = SHA-256("{}")
- Workspace root not set → workspace_path = "unknown", trust_hash = "untrusted"
- Timeout = 0 → contract expires immediately, status = "expired"
- Same run_id generated twice (UUID collision) → `RunContract` overwrites (same as RunRecord)

---

## 2. Emit RunReceipt After Completed/Failed/Cancelled Run

### Purpose

A **RunReceipt** is a signed attestation that a run completed (or failed/cancelled), containing the actual outcome, duration, event count, and a link back to the original contract. Signed with HMAC-SHA256 using the existing `AuditKeyManager` infrastructure.

### Files to Edit

| File | Change |
|------|--------|
| `protocol/schemas.py` | Add `RunReceipt`, `ReceiptStatus` models |
| `protocol/errors.py` | Add `RECEIPT_VERIFICATION_FAILED`, `RECEIPT_NOT_FOUND` |
| `orchestration/events.py` | Add `RUN_RECEIPT_ISSUED` event type |
| `orchestration/supervisor.py` | Generate and persist `RunReceipt` in `_execute_run()` finally block |
| `storage/jsonl.py` | Add `save_receipt()` / `load_receipt()` |
| `storage/sqlite.py` | Add `receipts` table |
| `storage/indexed_store.py` | Add dual-write receipt support |
| `audit/hmac_chain.py` | Ensure `sign_audit_record()` is importable for receipt signing |
| `cli.py` | Add `arc receipt show/export/verify` commands |

### New Models in `protocol/schemas.py`

```python
class ReceiptStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RunReceipt(BaseModel):
    run_id: str
    workflow_id: str
    runtime: str
    status: ReceiptStatus
    started_at: str
    ended_at: str
    duration_ms: int
    event_count: int
    contract_hash: str           # SHA-256 of the RunContract JSON
    input_hash: str              # echo from contract
    output_summary: str = ""     # first 500 chars of final output, or error msg
    error: Optional[str] = None  # if FAILED
    error_detail: Optional[str] = None  # exception type name
    signature: str = ""          # HMAC-SHA256 hex digest
    signing_key_id: str = ""     # "hmac-audit-key-v1" or "env-fallback"
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Sample Payload (Completed)

```json
{
  "run_id": "run-a1b2c3d4e5f6",
  "workflow_id": "wf-my-agent",
  "runtime": "swarmgraph",
  "status": "completed",
  "started_at": "2026-05-16T10:00:00+00:00",
  "ended_at": "2026-05-16T10:00:45+00:00",
  "duration_ms": 45123,
  "event_count": 87,
  "contract_hash": "abc123...",
  "input_hash": "a7ffc6f8...",
  "output_summary": "Task completed successfully. Final output: {\"result\": \"all checks passed\"}",
  "error": null,
  "error_detail": null,
  "signature": "a1b2c3d4e5f6...",
  "signing_key_id": "hmac-audit-key-v1",
  "metadata": {}
}
```

### Sample Payload (Failed)

```json
{
  "run_id": "run-deadbeef1234",
  "workflow_id": "wf-broken",
  "runtime": "langgraph",
  "status": "failed",
  "started_at": "2026-05-16T10:00:00+00:00",
  "ended_at": "2026-05-16T10:00:12+00:00",
  "duration_ms": 12340,
  "event_count": 5,
  "contract_hash": "def456...",
  "input_hash": "b7ffc6f8...",
  "output_summary": "RuntimeError: Connection refused",
  "error": "Connection refused",
  "error_detail": "RuntimeError",
  "signature": "deadbeef...",
  "signing_key_id": "env-fallback",
  "metadata": {}
}
```

### Changes to `orchestration/supervisor.py`

In `_execute_run()`, in the `finally` block, after updating the run status:

```python
# After end_run and cleanup in _execute_run():
from ..audit.key_manager import AuditKeyManager
from ..audit.hmac_chain import sign_audit_record

# Generate receipt
contract = self.store.load_contract(run_id)
contract_hash = hashlib.sha256(
    contract.model_dump_json().encode()
).hexdigest() if contract else "no-contract"

# Build output summary
output_summary = ""
error = None
error_detail = None
for ev in run.events if run else []:
    if ev.type in ("RUN_COMPLETED", "RUN_FAILED", "RUN_CANCELLED"):
        output_summary = json.dumps(ev.data, default=str)[:500]
    if ev.type == "RUN_FAILED":
        error = ev.data.get("error")
        error_detail = ev.data.get("error_detail")

receipt = RunReceipt(
    run_id=run_id,
    workflow_id=request.workflow_id,
    runtime=request.runtime or "unknown",
    status=...,  # derived from final run.status
    started_at=...,
    ended_at=...,
    duration_ms=duration,
    event_count=len(run.events) if run else 0,
    contract_hash=contract_hash,
    input_hash=contract.input_hash if contract else "no-contract",
    output_summary=output_summary,
    error=error,
    error_detail=error_detail,
)

# Sign receipt
km = AuditKeyManager()
key, status = km.get_key()
if key:
    receipt.signing_key_id = status.key_id
    _, receipt.signature = sign_audit_record(
        receipt.model_dump(exclude={"signature", "signing_key_id"}),
        key,
    )

self.store.save_receipt(receipt)
```

### New Tests (`tests/test_receipt.py`)

1. `test_receipt_generated_on_complete` — mock executor succeeds, verify receipt exists
2. `test_receipt_generated_on_failure` — executor raises, receipt.status == "failed"
3. `test_receipt_generated_on_cancel` — cancel run, receipt.status == "cancelled"
4. `test_receipt_signed` — signature field is non-empty when key available
5. `test_receipt_signed_deterministic` — same inputs produce same signature (with same key)
6. `test_receipt_no_key_no_signature` — when no key, signature = ""
7. `test_receipt_contract_hash_matches` — verify contract_hash is correct
8. `test_receipt_roundtrip_jsonl` — save + load
9. `test_receipt_roundtrip_sqlite` — save + load
10. `test_receipt_cli_show` — `arc receipt show <run>` output
11. `test_receipt_cli_export` — `arc receipt export <run>` writes file

### Expected CLI Output

```
$ arc receipt show run-a1b2c3d4e5f6
Run Receipt: run-a1b2c3d4e5f6
  Status:      completed
  Runtime:     swarmgraph
  Duration:    45.123s
  Events:      87
  Signed:      yes (hmac-audit-key-v1)

$ arc receipt export run-a1b2c3d4e5f6
Receipt exported to: /home/user/projects/my-agent/.arc/receipts/run-a1b2c3d4e5f6.receipt.json

$ arc receipt verify /home/user/projects/my-agent/.arc/receipts/run-a1b2c3d4e5f6.receipt.json
✓ Receipt signature valid (key: hmac-audit-key-v1)
  Run:     run-a1b2c3d4e5f6
  Status:  completed
  Tamper:  none detected
```

### No-Go Boundaries

- **Do NOT** embed the full `RunRecord` inside the receipt — just the summary and hash
- **Do NOT** block the run completion on receipt signing failure (best-effort)
- **Do NOT** store receipts in the trace file — separate `.arc/receipts/` directory
- **Do NOT** implement receipt revocation (v0.2 feature)

### Edge Cases

- No audit key available → signature = "", signing_key_id = "none", CLI shows "unsigned"
- RunRecord has 0 events → event_count = 0, output_summary = ""
- Contract not found → contract_hash = "no-contract", input_hash = "no-contract"
- Very long output → truncated at 500 chars
- Empty workspace path → workspace_path = "unknown" in receipt metadata

---

## 3. Build FailureAutopsy from Run Metadata/Events

### Purpose

A **FailureAutopsy** is a structured diagnosis of why a run failed — not just the error message, but a breakdown of *what was known* at each failure point and *what we can guess* about the root cause. Consumed by the CLI `arc runs autopsy` command and the Theia autopsy panel.

### Files to Edit

| File | Change |
|------|--------|
| `protocol/schemas.py` | Add `FailureAutopsy`, `AutopsyFinding`, `AutopsyKnowsGuesses` models |
| `orchestration/events.py` | Add `AUTOPSY_GENERATED` event type |
| `orchestration/supervisor.py` | Generate `FailureAutopsy` in the `except` branch of `_execute_run()` |
| `storage/jsonl.py` | Add `save_autopsy()` / `load_autopsy()` |
| `storage/sqlite.py` | Add `autopsies` table |
| `cli.py` | Add `arc runs autopsy <run>` command (advanced) |

### New Models in `protocol/schemas.py`

```python
class FindingCategory(str, Enum):
    RUNTIME_ERROR = "runtime_error"
    TOOL_FAILURE = "tool_failure"
    TIMEOUT = "timeout"
    PROVIDER_ERROR = "provider_error"
    POLICY_BLOCK = "policy_block"
    INPUT_ERROR = "input_error"
    UNKNOWN = "unknown"

class AutopsyFinding(BaseModel):
    category: FindingCategory
    message: str
    source_event_type: Optional[str] = None  # e.g. "TOOL_CALL_ERROR"
    source_sequence: Optional[int] = None    # event sequence number
    knows: str        # what we definitively know
    guesses: list[str] = Field(default_factory=list)  # possible root causes

class FailureAutopsy(BaseModel):
    run_id: str
    status: str  # "failed" or "cancelled"
    error: str
    error_detail: str
    findings: list[AutopsyFinding] = Field(default_factory=list)
    event_timeline: list[dict] = Field(default_factory=list)
    # event_timeline = truncated last-N events before failure
    generated_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Sample Payload

```json
{
  "run_id": "run-deadbeef1234",
  "status": "failed",
  "error": "Connection refused",
  "error_detail": "RuntimeError",
  "findings": [
    {
      "category": "provider_error",
      "message": "OpenAI API connection failed after 3 retries",
      "source_event_type": "TOOL_CALL_ERROR",
      "source_sequence": 42,
      "knows": "The tool call to 'web_search' on sequence 42 received a connection refused error from api.openai.com",
      "guesses": [
        "Network proxy is blocking outbound HTTPS to api.openai.com",
        "API endpoint changed or is temporarily down",
        "VPN or corporate firewall is interfering"
      ]
    },
    {
      "category": "timeout",
      "message": "Run exceeded 300s timeout",
      "source_event_type": "RUN_FAILED",
      "source_sequence": null,
      "knows": "The run was terminated by the supervisor after reaching the configured timeout of 300 seconds",
      "guesses": [
        "A tool call entered an infinite retry loop",
        "The runtime adapter hung on a subprocess call"
      ]
    }
  ],
  "event_timeline": [
    {"sequence": 40, "type": "TOOL_CALL", "data": {"tool_name": "web_search", "tool_call_id": "call_abc"}},
    {"sequence": 41, "type": "TOOL_CALL_RESULT", "data": {"tool_call_id": "call_abc", "result": "..."}},
    {"sequence": 42, "type": "TOOL_CALL_ERROR", "data": {"tool_call_id": "call_abc", "error": "Connection refused"}}
  ],
  "generated_at": "2026-05-16T10:00:13+00:00",
  "metadata": {}
}
```

### Autopsy Generation Logic

Heuristics for building `findings` from events:

| Event Pattern | Finding Category | knows template |
|--------------|------------------|----------------|
| `TOOL_CALL_ERROR` | `tool_failure` | Tool `{tool_name}` failed with `{error}` |
| `RUN_FAILED` + prior `TOOL_CALL_ERROR` | `tool_failure` | Run failed due to tool error |
| `RUN_FAILED` with `error_detail = "TimeoutError"` | `timeout` | Run hit timeout at `{duration_ms}`ms |
| `RUN_FAILED` with `error_detail = "GatingError"` | `policy_block` | Profile `{profile_id}` blocked the call |
| `RUN_FAILED` with `error_detail = "ProviderError"` | `provider_error` | Provider `{provider}` returned `{status_code}` |
| No events before RUN_FAILED | `runtime_error` | Runtime adapter threw during init: `{error}` |

Guesses are static strings based on category (no ML — simple pattern matching).

### Changes to `orchestration/supervisor.py`

In the `except Exception as e:` branch of `_execute_run()`, after saving the failed RunRecord:

```python
# Build autopsy
from ..protocol.schemas import FailureAutopsy, AutopsyFinding, FindingCategory

findings = self._build_autopsy_findings(run_id, e)
autopsy = FailureAutopsy(
    run_id=run_id,
    status="failed",
    error=str(e),
    error_detail=type(e).__name__,
    findings=findings,
    event_timeline=self._build_event_timeline(run_id, tail=5),
    generated_at=datetime.now(timezone.utc).isoformat(),
)
self.store.save_autopsy(autopsy)
self._emit_event(run_id, "AUTOPSY_GENERATED", {"autopsy": autopsy.model_dump()})
```

### New Tests (`tests/test_autopsy.py`)

1. `test_autopsy_generated_on_failure` — executor raises, autopsy exists
2. `test_autopsy_not_generated_on_success` — no autopsy for completed runs
3. `test_autopsy_tool_error_finding` — inject TOOL_CALL_ERROR events, verify finding
4. `test_autopsy_timeout_finding` — simulate timeout
5. `test_autopsy_policy_block_finding` — simulate GatingError
6. `test_autopsy_timeline_limited` — timeline capped at last N events
7. `test_autopsy_roundtrip` — save + load
8. `test_autopsy_cli_show` — `arc runs autopsy <run>` output
9. `test_autopsy_cancelled_has_autopsy` — cancelled runs also get autopsy

### Expected CLI Output

```
$ arc runs autopsy run-deadbeef1234
═══ FailureAutopsy: run-deadbeef1234 ═══
Status: failed
Error: Connection refused (RuntimeError)

Findings:
  [1] provider_error: OpenAI API connection failed after 3 retries
      → knows: The tool call to 'web_search' on sequence 42 received a
        connection refused error from api.openai.com
      → guesses: Network proxy, API endpoint changed, VPN interference

  [2] timeout: Run exceeded 300s timeout
      → knows: The run was terminated by the supervisor after reaching
        the configured timeout of 300 seconds
      → guesses: Infinite retry loop, hung subprocess

Last 5 events: seq:40 TOOL_CALL | seq:41 TOOL_CALL_RESULT | seq:42 TOOL_CALL_ERROR
```

### No-Go Boundaries

- **Do NOT** use any ML/LLM for guess generation — static templates only
- **Do NOT** compute autopsy synchronously in the hot path — it blocks until all events are saved
- **Do NOT** store autopsy for completed or cancelled runs by default (cancelled only if spec requires)
- **Do NOT** attempt to parse error strings from provider SDK internals

### Edge Cases

- Zero events before failure → empty timeline, single `runtime_error` finding
- Non-standard exception types → error_detail = `type(e).__name__`
- Cancelled run with exception → cancelled status preferred, error still recorded
- Multiple TOOL_CALL_ERROR events → one finding per unique tool_name

---

## 4. Attach EvidenceRef to Messages/Tool Outputs/Runs

### Purpose

**EvidenceRef** is a lightweight cross-reference that links a message, tool output, or run event back to supporting evidence — a source file, a web search result, a code snippet, or a prior run. This enables the graph/chat/evidence cross-highlighting described in the UX spec.

### Files to Edit

| File | Change |
|------|--------|
| `protocol/schemas.py` | Add `EvidenceRef`, `EvidenceSource` models |
| `orchestration/events.py` | Add optional `evidence_refs` field to `MESSAGE`, `TOOL_CALL_RESULT`, `TOOL_CALL_ERROR`, `RUN_COMPLETED` event type defs |
| `adapters/base.py` | Add `collect_evidence()` method to `RuntimeAdapter` (optional, returns `list[EvidenceRef]`) |
| `cli.py` | Add `arc runs evidence <run>` command (list all evidence refs for a run) |

### New Models in `protocol/schemas.py`

```python
class EvidenceSource(str, Enum):
    SOURCE_FILE = "source_file"
    WEB_SEARCH = "web_search"
    TOOL_OUTPUT = "tool_output"
    PRIOR_RUN = "prior_run"
    CONTEXT_PACK = "context_pack"

class EvidenceRef(BaseModel):
    id: str            # unique within the run
    source: EvidenceSource
    label: str         # human-readable short label
    uri: str           # stable URI for cross-surface linking
                       # e.g. "file:///path/to/file.py#L42"
                       #      "run://run-abc123/event/15"
                       #      "web://example.com/doc"
    content_summary: str = ""  # first 300 chars of evidence content
    attached_to_event_type: Optional[str] = None  # "MESSAGE", "TOOL_CALL_RESULT"
    attached_to_sequence: Optional[int] = None
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Sample Payloads

Embedded in event data:

```json
{
  "type": "TOOL_CALL_RESULT",
  "data": {
    "tool_call_id": "call_abc",
    "result": "42 users found",
    "evidence_refs": [
      {
        "id": "ev-001",
        "source": "web_search",
        "label": "User count from API",
        "uri": "web://api.example.com/users?count=42",
        "content_summary": "API returned: {\"total\": 42}",
        "attached_to_event_type": "TOOL_CALL_RESULT",
        "attached_to_sequence": 23
      },
      {
        "id": "ev-002",
        "source": "source_file",
        "label": "Query definition in users.py",
        "uri": "file:///home/user/project/src/users.py#L15",
        "content_summary": "def get_user_count(): return len(db.users)",
        "attached_to_event_type": "TOOL_CALL_RESULT",
        "attached_to_sequence": 23
      }
    ]
  }
}
```

### Changes to Event Registry

In `protocol/events.py`, add `evidence_refs` as optional field to relevant event types:

```python
"TOOL_CALL_RESULT": EventTypeDef(
    required_fields={"tool_call_id", "result"},
    optional_fields={"evidence_refs"},
),
"MESSAGE": EventTypeDef(
    required_fields={"text"},
    optional_fields={"source", "coalesced", "evidence_refs"},
),
"RUN_COMPLETED": EventTypeDef(
    required_fields={"duration_ms"},
    optional_fields={"output", "evidence_refs"},
),
```

### Changes to `adapters/base.py`

```python
def collect_evidence(self, workspace: Path) -> list[EvidenceRef]:
    """Collect evidence references from the workspace for this runtime.
    
    Default implementation returns empty list. Adapters may override
    to surface source files, config references, etc.
    """
    return []
```

### New Tests (`tests/test_evidence.py`)

1. `test_evidence_ref_validates_schema` — valid EvidenceRef passes model_validate
2. `test_evidence_ref_missing_id_fails` — id is required
3. `test_evidence_ref_uri_stability` — same data produces same uri format
4. `test_evidence_ref_in_event_data` — create TOOL_CALL_RESULT event with evidence_refs
5. `test_evidence_ref_missing_optional_ok` — content_summary defaults to ""
6. `test_evidence_cli_list` — `arc runs evidence <run>` returns list
7. `test_evidence_adapter_collect` — adapter.collect_evidence() returns list
8. `test_evidence_adapter_default_empty` — default implementation returns []
9. `test_evidence_uri_formats` — file://, run://, web:// all parse correctly

### Expected CLI Output

```
$ arc runs evidence run-a1b2c3d4e5f6
Evidence Refs for run-a1b2c3d4e5f6 (12 total):
  ev-001  web_search    User count from API                    TOOL_CALL_RESULT seq:23
  ev-002  source_file   Query definition in users.py            TOOL_CALL_RESULT seq:23
  ev-003  prior_run     Previous run run-xyz789                 RUN_COMPLETED
  ev-004  web_search    Documentation for pandas.DataFrame      MESSAGE seq:45
```

### No-Go Boundaries

- **Do NOT** automatically scrape evidence from tool outputs — evidence_refs must be explicitly provided (by adapter or user)
- **Do NOT** store evidence separately — they live inside event data
- **Do NOT** implement cross-surface linking behavior in this PR — just the data model and CLI
- **Do NOT** `EvidenceRef.uri` resolution — dereferencing the URI is a Theia-side concern

### Edge Cases

- Empty evidence list → `evidence_refs` field absent or `[]`
- Truncated content → content_summary capped at 300 chars
- URI with missing scheme → accept any string, no validation
- Same evidence attached to multiple events → separate `EvidenceRef` objects (each has unique id)

---

## 5. Extend Runtime Manifest / Capability Validation

### Purpose

The existing `RuntimeCapabilities` model and `CapabilityReport` are single-adapter. This extension adds:
1. **Manifest validation** — ensure an adapter's `capabilities()` return matches what was registered
2. **Cross-adapter capability negotiation** — when combo routing is used, the effective capability is the intersection of all members
3. **Guardrail enforcement** — before a run starts, verify the chosen runtime can *honestly* do what's being asked

### Files to Edit

| File | Change |
|------|--------|
| `adapters/base.py` | Add `validate_manifest()` method to `RuntimeAdapter` |
| `adapters/registry.py` | Add manifest validation at registration time |
| `protocol/capabilities.py` | Add `ManifestValidationResult`, `CapabilityConstraint` models |
| `orchestration/runtime_router.py` | Add capability intersection for combo routing, guardrail check in `resolve()` |
| `orchestration/supervisor.py` | Add capability check before `start_run()` when runtime is set |
| `cli.py` | Add `arc adapter validate <adapter>` command |

### New Models in `protocol/capabilities.py`

```python
class CapabilityConstraint(BaseModel):
    """A constraint that a runtime must satisfy."""
    field: str       # e.g. "can_trace", "audit_level"
    operator: str    # "eq", "ne", "gte", "has" (for enum/list fields)
    value: Any

class ManifestValidationResult(BaseModel):
    adapter_id: str
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
```

### Sample Validation Output

```json
{
  "adapter_id": "swarmgraph",
  "valid": true,
  "errors": [],
  "warnings": [
    "capability 'can_eval' is false but registry claims 'swarmgraph' supports eval"
  ]
}
```

### Changes to `adapters/registry.py`

```python
class AdapterRegistry:
    def register(self, adapter: RuntimeAdapter) -> ManifestValidationResult:
        # ...existing registration logic...
        validation = adapter.validate_manifest()
        if not validation.valid:
            log.warning(f"Adapter {adapter.adapter_id} manifest invalid: {validation.errors}")
        return validation

    def validate_all(self) -> list[ManifestValidationResult]:
        return [adapter.validate_manifest() for adapter in self._adapters.values()]
```

### Changes to `orchestration/runtime_router.py`

```python
def intersect_capabilities(adapters: list[RuntimeAdapter]) -> RuntimeCapabilities:
    """Intersection of capabilities for combo routing."""
    caps = [a.capabilities() for a in adapters]
    return RuntimeCapabilities(
        can_run=all(c.can_run for c in caps),
        can_trace=all(c.can_trace for c in caps),
        can_replay=all(c.can_replay for c in caps),
        can_audit=all(c.can_audit for c in caps),
        # ...boolean fields: AND
        execution_modes=list(set.intersection(
            *(set(c.execution_modes) for c in caps)
        )) if caps else [],
        audit_level=... , # lowest common = most restrictive
        hitl_level=... ,  # lowest common = most restrictive
    )
```

### New Tests (`tests/test_capability_validation.py`)

1. `test_manifest_valid` — adapter returns honest capabilities, validation passes
2. `test_manifest_invalid_runtime` — adapter lies about can_run, validation fails
3. `test_capability_intersection` — combo of 2 adapters produces correct intersection
4. `test_capability_intersection_empty` — no common execution_modes → empty list
5. `test_guardrail_check_before_run` — supervisor checks capability before run
6. `test_guardrail_blocks_unsupported` — run with unsupported feature raises
7. `test_registry_validates_on_register` — `register()` returns validation result
8. `test_validate_all` — validates all registered adapters
9. `test_cli_adapter_validate` — `arc adapter validate swarmgraph` output

### Expected CLI Output

```
$ arc adapter validate swarmgraph
✓ swarmgraph manifest valid
  can_run:       true  (matches registry)
  can_trace:     true  (matches registry)
  can_audit:     true  (matches registry)
  ⚠ can_eval:    false (registry claims eval support)

$ arc adapter validate langgraph
✓ langgraph manifest valid
  All capabilities match registry claims
```

### No-Go Boundaries

- **Do NOT** use contract/smart-contract languages (e.g., WASM, Solidity) for manifests — plain Pydantic model validation is sufficient
- **Do NOT** enforce manifests at runtime by default — only when `ARC_STRICT_MANIFEST=true` or profile requires it
- **Do NOT** build a full Prolog/Datalog rule engine for capability constraints — simple operator matching is enough

### Edge Cases

- Adapter returns `RuntimeCapabilities()` with all defaults → all bools are False, validation passes trivially
- Intersection of empty adapter list → returns all-False RuntimeCapabilities
- `audit_level` enum comparison: "none" < "arc_sha256" < "swarmgraph_hmac"
- Adapter registered twice → duplicate registration produces warning, not error

---

## 6. Add TrustDiff Model for Trust/Policy/Provider Changes

### Purpose

**TrustDiff** captures the delta between the trust/policy/provider state *before* and *after* a run. This allows the system to detect if a workspace's trust status, a run's policy profile, or a provider's routing changed between runs — critical for audit and non-repudiation.

### Files to Edit

| File | Change |
|------|--------|
| `protocol/schemas.py` | Add `TrustDiff`, `TrustChange`, `PolicyChange`, `ProviderChange` models |
| `security/trust.py` | Add `compute_trust_diff()` function |
| `security/profiles.py` | Add `compute_policy_diff()` function |
| `providers.py` | Add `compute_provider_diff()` function |
| `orchestration/supervisor.py` | Compute and store TrustDiff in `start_run()` alongside RunContract |
| `storage/jsonl.py` | Add `save_trust_diff()` / `load_trust_diff()` |
| `cli.py` | Add `arc workspace trust-diff` command, `arc runs trust-diff <run>` command |

### New Models in `protocol/schemas.py`

```python
class TrustChange(BaseModel):
    field: str                    # "trust_level", "workspace_path"
    before: Optional[str] = None
    after: Optional[str] = None

class PolicyChange(BaseModel):
    profile_id: str
    changes: list[TrustChange] = Field(default_factory=list)

class ProviderChange(BaseModel):
    provider_id: str
    changes: list[TrustChange] = Field(default_factory=list)

class TrustDiff(BaseModel):
    run_id: str
    workspace_path: str
    trust: TrustResolution         # current state
    trust_changes: list[TrustChange] = Field(default_factory=list)
    policy: RunProfile             # current profile
    policy_changes: list[PolicyChange] = Field(default_factory=list)
    provider_changes: list[ProviderChange] = Field(default_factory=list)
    computed_at: str
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### Sample Payload

```json
{
  "run_id": "run-a1b2c3d4e5f6",
  "workspace_path": "/home/user/projects/my-agent",
  "trust": {
    "level": "trusted",
    "reason": "Workspace trusted in external trust database",
    "marker_path": "/home/user/.arc/trusted-workspaces.json",
    "warning": null
  },
  "trust_changes": [
    {
      "field": "trust_level",
      "before": "untrusted",
      "after": "trusted"
    }
  ],
  "policy": {
    "id": "local-paid",
    "name": "Local Paid",
    "allow_paid_calls": true,
    "allow_network": true,
    "allow_shell": false,
    "allow_secrets": false,
    "env_allowlist": [],
    "backend": "local"
  },
  "policy_changes": [
    {
      "profile_id": "local-paid",
      "changes": [
        {
          "field": "allow_paid_calls",
          "before": "false",
          "after": "true"
        }
      ]
    }
  ],
  "provider_changes": [
    {
      "provider_id": "openai",
      "changes": [
        {
          "field": "default_model",
          "before": "gpt-4.1-mini",
          "after": "gpt-4.1"
        }
      ]
    }
  ],
  "computed_at": "2026-05-16T10:00:00+00:00",
  "metadata": {}
}
```

### Changes to `security/trust.py`

```python
from ..protocol.schemas import TrustChange

def compute_trust_diff(
    workspace: Path,
    previous_trust: Optional[TrustResolution] = None,
    trust_db: Path = TRUST_DB,
) -> list[TrustChange]:
    """Compute changes in workspace trust state since previous_trust."""
    current = resolve_trust(workspace, trust_db=trust_db)
    changes: list[TrustChange] = []
    
    if previous_trust and previous_trust.level != current.level:
        changes.append(TrustChange(
            field="trust_level",
            before=previous_trust.level.value,
            after=current.level.value,
        ))
    
    return changes
```

### Changes to `security/profiles.py`

```python
from ..protocol.schemas import TrustChange, PolicyChange

def compute_policy_diff(
    current_profile: RunProfile,
    previous_profile: Optional[RunProfile] = None,
) -> list[PolicyChange]:
    if previous_profile is None or previous_profile == current_profile:
        return []
    changes = []
    for field in ("allow_paid_calls", "allow_network", "allow_shell", "allow_secrets", "backend"):
        before = getattr(previous_profile, field)
        after = getattr(current_profile, field)
        if str(before) != str(after):
            changes.append(TrustChange(
                field=field,
                before=str(before),
                after=str(after),
            ))
    return [PolicyChange(profile_id=current_profile.id, changes=changes)]
```

### Integration in `orchestration/supervisor.py`

In `start_run()`, alongside contract generation:

```python
from ..protocol.schemas import TrustDiff
from ..security.trust import compute_trust_diff, resolve_trust
from ..security.profiles import compute_policy_diff, resolve_profile

trust_diff = TrustDiff(
    run_id=run.id,
    workspace_path=str(Path(request.workspace_root).resolve()) if request.workspace_root else "unknown",
    trust=resolve_trust(Path(request.workspace_root)) if request.workspace_root else ...,
    trust_changes=compute_trust_diff(Path(request.workspace_root)) if request.workspace_root else [],
    policy=resolve_profile(request.profile_id),
    policy_changes=compute_policy_diff(resolve_profile(request.profile_id)),
    provider_changes=[],  # populated by runtime router
    computed_at=now,
)
self.store.save_trust_diff(trust_diff)
```

### New Tests (`tests/test_trust_diff.py`)

1. `test_trust_diff_no_changes` — trust state unchanged → empty changes
2. `test_trust_diff_trust_level_changed` — untrusted → trusted produces change
3. `test_trust_diff_policy_changed` — profile fields differ
4. `test_trust_diff_provider_changed` — provider config differs
5. `test_trust_diff_saved_on_start` — trust diff saved alongside contract
6. `test_trust_diff_cli_workspace` — `arc workspace trust-diff` output
7. `test_trust_diff_cli_runs` — `arc runs trust-diff <run>` output
8. `test_trust_diff_empty_workspace` — no workspace root → empty diff
9. `test_trust_diff_roundtrip` — save + load

### Expected CLI Output

```
$ arc workspace trust-diff
═══ TrustDiff for /home/user/projects/my-agent ═══
Trust Level: trusted (was untrusted)
  → Workspace was recently added to trust database

Profile: local-paid (unchanged)

Providers:
  openai: default_model changed gpt-4.1-mini → gpt-4.1

$ arc runs trust-diff run-a1b2c3d4e5f6
═══ TrustDiff for run-a1b2c3d4e5f6 ═══
Workspace: /home/user/projects/my-agent
Trust Level: trusted (no change from contract time)
Profile: local-paid (no change)
Providers: no changes
```

### No-Go Boundaries

- **Do NOT** store the full previous state — only the diff
- **Do NOT** compute TrustDiff retroactively for run history — only for new runs
- **Do NOT** implement TrustDiff rollback/undo — observed status only
- **Do NOT** snapshot provider quotas — only routing/config changes

### Edge Cases

- First run ever → no previous trust state → all changes = current state with before=null
- Workspace never trusted → trust_changes = []
- Profile not found → `resolve_profile` falls back to "stub"
- Provider not configured → provider_changes = []
- workspace_root = None → workspace_path = "unknown", trust = default untrusted

---

## 7. CLI Commands

### Overview

All new commands follow the existing CLI pattern: Typer sub-app, `_workspace()`, `_out(ok(...))`, `--json` flag.

### New Sub-Apps and Commands

#### 7.1 `arc receipt` Sub-App

```python
receipt_app = typer.Typer(name="receipt", help="Run receipt management")
app.add_typer(receipt_app)
```

| Command | Signature | Behavior |
|---------|-----------|----------|
| `show` | `<run_id>` | Load and display receipt for a run |
| `export` | `<run_id>` | Export receipt JSON to `.arc/receipts/<run>.receipt.json` |
| `verify` | `<file>` | Load receipt from file, verify HMAC signature |

##### `arc receipt show <run>`

```
$ arc receipt show run-a1b2c3d4e5f6
Run Receipt: run-a1b2c3d4e5f6
  Status:      completed
  Runtime:     swarmgraph
  Duration:    45.123s
  Events:      87
  Signed:      yes (hmac-audit-key-v1)

$ arc receipt show run-deadbeef1234 --json
{
  "ok": true,
  "data": {
    "run_id": "run-deadbeef1234",
    "status": "failed",
    "error": "Connection refused",
    "signature": "abc...",
    "signing_key_id": "hmac-audit-key-v1"
  }
}

$ arc receipt show nonexistent
Error [RUN_NOT_FOUND]: Run not found: nonexistent
```

##### `arc receipt export <run>`

```
$ arc receipt export run-a1b2c3d4e5f6
Receipt exported to: /home/user/projects/my-agent/.arc/receipts/run-a1b2c3d4e5f6.receipt.json

$ arc receipt export nonexistent
Error [RUN_NOT_FOUND]: Run not found: nonexistent
```

##### `arc receipt verify <file>`

```
$ arc receipt verify /path/to/receipt.json
✓ Receipt signature valid (key: hmac-audit-key-v1)
  Run ID:    run-a1b2c3d4e5f6
  Status:    completed
  Duration:  45.123s
  Tamper:    none detected

$ arc receipt verify /path/to/tampered.json
✗ Receipt signature INVALID
  Run ID:    run-a1b2c3d4e5f6
  Status:    completed (claim)
  Expected:   abcdef123456...
  Got:        000000000000...
  Tamper:     DETECTED — receipt has been modified after signing
```

#### 7.2 Advanced/Debug Commands

```python
# Add to `runs_app`
@runs_app.command("autopsy")
def runs_autopsy(
    run_id: str = typer.Argument(..., help="Run ID to autopsy"),
    ...
): ...

@runs_app.command("trust-diff")
def runs_trust_diff(
    run_id: str = typer.Argument(..., help="Run ID"),
    ...
): ...

# New `contract_app`
contract_app = typer.Typer(name="contract", help="Run contract inspection (advanced)")
app.add_typer(contract_app)

# New `evidence_app`
evidence_app = typer.Typer(name="evidence", help="Evidence reference inspection (advanced)")
app.add_typer(evidence_app)
```

##### `arc runs autopsy <run>` (already described above)

##### `arc contract show <run>`

```
$ arc contract show run-a1b2c3d4e5f6
═══ RunContract: run-a1b2c3d4e5f6 ═══
  Workflow:    wf-my-agent
  Runtime:     swarmgraph
  Profile:     local-paid
  Workspace:   /home/user/projects/my-agent
  Timeout:     300s (expires 2026-05-16T10:05:00+00:00)
  Status:      issued
  Input Hash:  a7ffc6f8...8434a
  Trust Hash:  e3b0c442...2b855
```

##### `arc runs evidence <run>` (already described above)

#### 7.3 Implementation Notes for CLI

Each command follows the same pattern as `runs_get`:

```python
@receipt_app.command("show")
def receipt_show(
    run_id: str = typer.Argument(..., help="Run ID"),
    workspace: Optional[str] = WORKSPACE_FLAG,
    json_output: bool = JSON_FLAG,
    debug: bool = DEBUG_FLAG,
) -> None:
    _setup_logging(debug)
    from .storage.indexed_store import IndexedTraceStore
    ws = _workspace(workspace)
    store = IndexedTraceStore(
        trace_dir=ws / ".arc" / "traces",
        db_path=ws / ".arc" / "arc.db",
    )
    receipt = store.load_receipt(run_id)
    if receipt is None:
        _out(err(ArcErrorCode.RECEIPT_NOT_FOUND, f"Receipt not found: {run_id}"), json_output)
        raise typer.Exit(1)
    _out(ok(receipt.model_dump(), workspace=str(ws)), json_output)
```

### CLI Test Locations

| Test File | Tests For |
|-----------|-----------|
| `tests/cli/test_cli_receipt.py` | receipt show/export/verify (10+ tests) |
| `tests/cli/test_cli_contract.py` | contract show (3-5 tests) |
| `tests/cli/test_cli_evidence.py` | evidence list (3-5 tests) |
| `tests/cli/test_cli_autopsy.py` | runs autopsy (3-5 tests) |
| `tests/cli/test_cli_trust_diff.py` | runs trust-diff, workspace trust-diff (3-5 tests) |

Tests follow the pattern from `tests/cli/test_cli_runs.py`: `@pytest.mark.needs("receipt")`, `run_cli` fixture, `workspace` fixture, skip cleanly if command absent.

---

## Test File Summary

| New Test File | Tests | Priority |
|--------------|-------|----------|
| `tests/test_contract.py` | 9 | P0 — core contract model |
| `tests/test_receipt.py` | 11 | P0 — core receipt model + signing |
| `tests/test_autopsy.py` | 9 | P1 — diagnosis generation |
| `tests/test_evidence.py` | 9 | P1 — evidence ref model |
| `tests/test_capability_validation.py` | 9 | P0 — guardrail enforcement |
| `tests/test_trust_diff.py` | 9 | P1 — trust diff model |
| `tests/cli/test_cli_receipt.py` | 10 | P0 — CLI verbs |
| `tests/cli/test_cli_contract.py` | 5 | P2 — advanced CLI |
| `tests/cli/test_cli_evidence.py` | 5 | P2 — advanced CLI |
| `tests/cli/test_cli_autopsy.py` | 5 | P2 — advanced CLI |
| `tests/cli/test_cli_trust_diff.py` | 5 | P2 — advanced CLI |

### Modified Test Files

| File | New Tests |
|------|-----------|
| `tests/test_storage.py` | Contract/receipt/autopsy/trust_diff JSONL + SQLite roundtrips (add to existing classes) |
| `tests/test_protocol.py` | Schema validation for new models |
| `tests/test_event_schema.py` | New event types (RUN_CONTRACT_ISSUED, RUN_RECEIPT_ISSUED, AUTOPSY_GENERATED) |

---

## Implementation Order (PR Dependencies)

```
PR 1: Schema contracts + storage
   ├── protocol/schemas.py (RunContract, RunReceipt, FailureAutopsy, EvidenceRef, TrustDiff)
   ├── protocol/errors.py (new error codes)
   ├── protocol/events.py (new event types)
   ├── storage/jsonl.py (+contract/receipt/autopsy/evidence/trust_diff methods)
   ├── storage/sqlite.py (+tables)
   ├── storage/indexed_store.py (+dual-write)
   ├── tests/test_contract.py
   └── tests/test_storage.py (extend)

PR 2: Supervisor integration (contract + receipt + autopsy + trust diff)
   ├── orchestration/supervisor.py (contract generation, receipt signing, autopsy)
   ├── orchestration/events.py (event registration)
   ├── tests/test_receipt.py
   ├── tests/test_autopsy.py
   └── tests/test_trust_diff.py

PR 3: Trust diff + policy diff
   ├── security/trust.py (compute_trust_diff)
   ├── security/profiles.py (compute_policy_diff)
   └── tests/test_trust_diff.py (extend)

PR 4: Capability validation
   ├── adapters/base.py (validate_manifest)
   ├── adapters/registry.py (register-time validation)
   ├── protocol/capabilities.py (ManifestValidationResult)
   ├── orchestration/runtime_router.py (intersection + guardrail)
   └── tests/test_capability_validation.py

PR 5: Evidence refs
   ├── protocol/schemas.py (EvidenceRef — already in PR 1)
   ├── adapters/base.py (collect_evidence)
   └── tests/test_evidence.py

PR 6: CLI commands
   ├── cli.py (receipt, contract, evidence, autopsy, trust-diff commands)
   ├── tests/cli/test_cli_receipt.py
   ├── tests/cli/test_cli_contract.py
   ├── tests/cli/test_cli_evidence.py
   ├── tests/cli/test_cli_autopsy.py
   └── tests/cli/test_cli_trust_diff.py
```
