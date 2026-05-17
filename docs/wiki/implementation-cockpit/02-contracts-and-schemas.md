# 02 — Contracts and Schemas

**Status:** Implementation-ready schemas for all seven cockpit primitives.
**Version:** v0.1 (v0.2 reserved fields marked `Optional` / `?`)

---

## Stable ID Format

All cockpit IDs follow a uniform convention:

| ID | Prefix | Pattern | Example |
|----|--------|---------|---------|
| `contract_id` | `ctr_` | `^ctr_[a-zA-Z0-9]{20,30}$` | `ctr_01JABCDEFGHIJKLMNOPQ` |
| `receipt_id` | `rcpt_` | `^rcpt_[a-zA-Z0-9]{20,30}$` | `rcpt_01JKLMNOPQRSTUVWXYZ` |
| `message_id` | `msg_` | `^msg_[a-zA-Z0-9]{20,30}$` | `msg_01Jabcdef1234567890` |
| `decision_id` | `dec_` | `^dec_[a-zA-Z0-9]{20,30}$` | `dec_01J1234567890abcdef` |
| `approval_id` | `appr_` | `^appr_[a-zA-Z0-9]{20,30}$` | `appr_01J9876543210fedcba` |
| `policy_decision_id` | `pd_` | `^pd_[a-zA-Z0-9]{20,30}$` | `pd_01JABCDEF1234567890` |
| `node_id` | (runtime-native or `n_`) | runtime-dependent | `reviewer`, `n_01J...` |
| `evidence_id` | `ev_` | `^ev_[a-zA-Z0-9]{20,30}$` | `ev_01JDEADBEEF1234567890` |
| `diff_id` | `td_` | `^td_[a-zA-Z0-9]{20,30}$` | `td_01JCAFEBABE0987654321` |

**Generation:** `secrets.token_urlsafe(16)` → prefix + base64-url-safe string. Created server-side in the supervisor before run start.

**Validation rule** (shared Python + TS):
```
/^(ctr_|rcpt_|msg_|dec_|appr_|pd_|ev_|td_)[a-zA-Z0-9_-]{20,30}$/
```

---

## 1. RunContract

**File:** `python/src/agent_runtime_cockpit/protocol/run_contract.py` [MISSING]
**TS mirror:** `packages/arc-protocol-ts/src/arc-protocol-types.ts` — append to existing file

### Python

```python
class ContractStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    FULFILLED = "fulfilled"
    VIOLATED = "violated"

class RunContract(BaseModel):
    schema_version: int = 1
    contract_id: str
    run_id: Optional[str] = None        # Assigned after supervisor creates the run
    session_id: str
    objective: str
    runtime: str
    mode: str                           # "plan" | "build" | "auto"
    allowed_tools: list[str] = Field(default_factory=list)
    write_scope: list[str] = Field(default_factory=list)          # [RESERVED v0.2]
    cost_ceiling_usd: float | str = "unknown"                     # "unknown" or number
    approval_policy: str = "auto"                                  # "auto" | "manual" | "none"
    rollback_plan: str = "none"                                    # "git-revert" | "manual" | "none"
    evidence_expected: list[str] = Field(default_factory=list)     # kinds: "file_diff", "test_output", ...
    status: ContractStatus = ContractStatus.PROPOSED
    terms_digest: Optional[str] = None                             # SHA-256 of canonical terms JSON
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    accepted_at: Optional[str] = None
    fulfilled_at: Optional[str] = None
    metadata: dict[str, Any] = Field(default_factory=dict)        # [RESERVED v0.2] extensible payload

    def is_satisfied_by(self, receipt: "RunReceipt") -> bool:
        """Check whether a receipt fulfills this contract's terms."""
        if receipt.run_id != self.run_id:
            return False
        if receipt.status == "failed" or receipt.status == "cancelled":
            return False
        if isinstance(self.cost_ceiling_usd, (int, float)):
            actual = receipt.cost_usd if isinstance(receipt.cost_usd, (int, float)) else float("inf")
            if actual > self.cost_ceiling_usd:
                return False
        return True
```

### TypeScript

```typescript
export type ContractStatus = 'proposed' | 'accepted' | 'fulfilled' | 'violated';

export interface RunContract {
  schema_version: number;
  contract_id: string;
  run_id?: string;
  session_id: string;
  objective: string;
  runtime: string;
  mode: 'plan' | 'build' | 'auto';
  allowed_tools: string[];
  write_scope: string[];              // v0.2+
  cost_ceiling_usd: number | 'unknown';
  approval_policy: string;
  rollback_plan: string;
  evidence_expected: string[];
  status: ContractStatus;
  terms_digest?: string;
  created_at: string;
  accepted_at?: string;
  fulfilled_at?: string;
  metadata: Record<string, unknown>;  // v0.2+
}
```

### JSON Example

```json
{
  "schema_version": 1,
  "contract_id": "ctr_01JABCDEFGHIJKLMNOPQ",
  "run_id": "run_01HXYZ123456789",
  "session_id": "ses_01JZZYYXXWWVVUU",
  "objective": "Run reviewer workflow against PR #42",
  "runtime": "swarmgraph",
  "mode": "build",
  "allowed_tools": ["scan_workspace", "read_file", "search_code"],
  "write_scope": ["src/"],
  "cost_ceiling_usd": 0.08,
  "approval_policy": "auto",
  "rollback_plan": "git-revert",
  "evidence_expected": ["file_diff", "test_output"],
  "status": "accepted",
  "terms_digest": "sha256:a1b2c3d4e5f6...",
  "created_at": "2026-05-16T10:00:00Z",
  "accepted_at": "2026-05-16T10:00:01Z",
  "fulfilled_at": null,
  "metadata": {}
}
```

### Storage

- **Canonical:** JSONL as first record in `.arc/traces/{run_id}.jsonl` (appended after `RunRecord`)
- **SQLite:** `contract_id` column added to `runs` table (nullable TEXT)
- **Index:** `CREATE INDEX IF NOT EXISTS idx_runs_contract ON runs(contract_id);`
- **Migration (v0.1→v0.2):** Add `write_scope` and `metadata` columns — both default to empty, no backfill needed.

### Event Names

| Event | Direction | Payload |
|-------|-----------|---------|
| `CONTRACT_PROPOSED` | supervisor → broker | full `RunContract` |
| `CONTRACT_ACCEPTED` | frontend → supervisor | `contract_id`, `accepted_at` |
| `CONTRACT_FULFILLED` | supervisor → broker | `contract_id`, `receipt_id` |
| `CONTRACT_VIOLATED` | supervisor → broker | `contract_id`, `reason` |

### Redaction

- `objective` — `Redactor.redact_string()` (may contain API keys in prompts)
- `metadata` — `Redactor.redact_dict()` recursive
- `terms_digest` — never redacted (hash)

### Validation

```python
def validate_contract_id(cid: str) -> str:
    if not re.match(r'^ctr_[a-zA-Z0-9_-]{20,30}$', cid):
        raise ValueError(f"Invalid contract_id: {cid!r}")
    return cid

def validate_run_contract(c: RunContract) -> None:
    validate_contract_id(c.contract_id)
    if c.mode not in ("plan", "build", "auto"):
        raise ValueError(f"Invalid mode: {c.mode}")
    if isinstance(c.cost_ceiling_usd, (int, float)) and c.cost_ceiling_usd < 0:
        raise ValueError("cost_ceiling_usd must be non-negative")
```

### Backcompat

- `schema_version` defaults to 1. Old contracts (pre-v0.1) loaded with missing fields → default to `PROPOSED` and empty lists.
- `run_id` is `None` until the supervisor assigns it — frontend must handle `undefined`.
- v0.2 additions (`write_scope`, `metadata`) are `Optional`/`Field(default_factory=list)` so serialization is stable.

### Tests to Add

| Test | What |
|------|------|
| `test_contract_default_status` | Default status is `PROPOSED` |
| `test_contract_is_satisfied_by_ok` | Receipt with matching run_id, completed, under ceiling → true |
| `test_contract_is_satisfied_by_over_budget` | Receipt over ceiling → false |
| `test_contract_is_satisfied_by_failed` | Failed receipt → false |
| `test_contract_json_roundtrip` | `model_dump_json()` → `model_validate_json()` preserves fields |
| `test_contract_validation` | Bad contract_id raises ValueError |
| `test_contract_serialized_in_run_record` | `RunRecord` roundtrip includes contract |

---

## 2. RunReceipt

**File:** `python/src/agent_runtime_cockpit/protocol/run_receipt.py` [MISSING]
**TS mirror:** `packages/arc-protocol-ts/src/arc-protocol-types.ts`

### Python

```python
class FileChange(BaseModel):
    path: str
    added: int = 0
    removed: int = 0

class RunReceipt(BaseModel):
    schema_version: int = 1
    receipt_id: str
    run_id: str
    session_id: Optional[str] = None
    contract_id: Optional[str] = None        # Links back to the original contract
    status: str                               # "completed" | "failed" | "cancelled"
    summary: str
    cost_usd: float | str = "unknown"         # "unknown" or number
    duration_ms: int = 0
    files_changed: list[FileChange] = Field(default_factory=list)
    approvals: list[str] = Field(default_factory=list)              # approval_ids
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    rollback_command: Optional[str] = None                          # [RESERVED v0.2]
    trust_boundaries_crossed: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)       # [RESERVED v0.2]
    audit_chain_ref: Optional[str] = None                           # Path to audit chain
    signature: Optional[str] = None                                 # HMAC-SHA256 of canonical JSON
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def canonical_bytes(self) -> bytes:
        """Deterministic JSON for signing. Sorted keys, no whitespace."""
        d = self.model_dump(mode="json", exclude={"signature"})
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    def sign(self, key: str) -> None:
        import hmac, hashlib
        self.signature = hmac.new(key.encode(), self.canonical_bytes(), hashlib.sha256).hexdigest()

    def verify(self, key: str) -> bool:
        import hmac, hashlib
        if not self.signature:
            return False
        expected = hmac.new(key.encode(), self.canonical_bytes(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(expected, self.signature)
```

### TypeScript

```typescript
export interface FileChange {
  path: string;
  added: number;
  removed: number;
}

export interface RunReceipt {
  schema_version: number;
  receipt_id: string;
  run_id: string;
  session_id?: string;
  contract_id?: string;
  status: 'completed' | 'failed' | 'cancelled';
  summary: string;
  cost_usd: number | 'unknown';
  duration_ms: number;
  files_changed: FileChange[];
  approvals: string[];
  evidence_refs: EvidenceRef[];
  rollback_command?: string;              // v0.2+
  trust_boundaries_crossed: string[];
  unresolved_risks: string[];            // v0.2+
  audit_chain_ref?: string;
  signature?: string;
  created_at: string;
}
```

### JSON Example

```json
{
  "schema_version": 1,
  "receipt_id": "rcpt_01JKLMNOPQRSTUVWXYZ",
  "run_id": "run_01HXYZ123456789",
  "session_id": "ses_01JZZYYXXWWVVUU",
  "contract_id": "ctr_01JABCDEFGHIJKLMNOPQ",
  "status": "completed",
  "summary": "Reviewer workflow completed in 48.2s. Found 3 lint issues.",
  "cost_usd": 0.04,
  "duration_ms": 48200,
  "files_changed": [
    {"path": "src/workflow.py", "added": 5, "removed": 2}
  ],
  "approvals": ["appr_01J9876543210fedcba"],
  "evidence_refs": [
    {"evidence_id": "ev_01JDEADBEEF1234567890", "kind": "file_diff", "target": "src/workflow.py"}
  ],
  "trust_boundaries_crossed": ["network_allowed"],
  "audit_chain_ref": "audit/run_01HXYZ123456789/chain.jsonl",
  "signature": "a1b2c3d4e5f67890abcdef1234567890abcdef1234567890abcdef1234567890",
  "created_at": "2026-05-16T10:01:30Z"
}
```

### Storage

- **Canonical:** Appended as the last JSONL record in `.arc/traces/{run_id}.jsonl`
- **SQLite:** `receipt_id` column in `runs` table (nullable TEXT). Receipt JSON stored in `runs.metadata` under key `"receipt"`.
- **Export:** `arc-studio receipt export <run>` writes standalone receipt JSON to stdout/file.

### Event Names

| Event | Direction | Payload |
|-------|-----------|---------|
| `RUN_COMPLETED` | supervisor → broker | carries `receipt_id` in `data` |
| `RUN_FAILED` | supervisor → broker | carries `receipt_id` + `error_detail` in `data` |
| `RUN_CANCELLED` | supervisor → broker | carries `receipt_id` + `cancel_reason` in `data` |

### Redaction

- `summary` — `Redactor.redact_string()` (may contain leaked secrets)
- `files_changed[].path` — no redaction (paths are not secrets)
- `signature` — never redacted

### Validation

```python
def validate_receipt_id(rid: str) -> str:
    if not re.match(r'^rcpt_[a-zA-Z0-9_-]{20,30}$', rid):
        raise ValueError(f"Invalid receipt_id: {rid!r}")
    return rid

def validate_run_receipt(r: RunReceipt) -> None:
    validate_receipt_id(r.receipt_id)
    if r.status not in ("completed", "failed", "cancelled"):
        raise ValueError(f"Invalid receipt status: {r.status}")
    if len(r.summary) > 2000:
        raise ValueError("Summary exceeds 2000 chars")
```

### Backcompat

- `signature` is `None` for receipts generated before audit is configured — no crash, just unverifiable.
- `contract_id` is `None` for runs started without a contract — frontend hides contract link.
- v0.2 fields (`rollback_command`, `unresolved_risks`) are `Optional`/empty.

### Tests to Add

| Test | What |
|------|------|
| `test_receipt_defaults` | Default fields are empty/sensible |
| `test_receipt_sign_verify` | Roundtrip sign + verify with correct key |
| `test_receipt_sign_verify_wrong_key` | Verify fails with wrong key |
| `test_receipt_tampered` | Modify after sign → verify returns false |
| `test_receipt_canonical_deterministic` | Same data → same canonical_bytes |
| `test_receipt_json_roundtrip` | Serialization roundtrip preserves all fields |
| `test_receipt_validation` | Bad receipt_id raises |
| `test_receipt_export_cli` | CLI outputs valid receipt JSON [e2e] |

---

## 3. FailureAutopsy

**File:** `python/src/agent_runtime_cockpit/protocol/failure_autopsy.py` [MISSING]
**TS mirror:** `packages/arc-protocol-ts/src/arc-protocol-types.ts`

### Python

```python
class RetryOption(BaseModel):
    label: str
    command: Optional[str] = None
    risk: str = "medium"                    # "low" | "medium" | "high"

class FailureAutopsy(BaseModel):
    schema_version: int = 1
    run_id: str
    probable_cause: str = "unknown"
    confidence: str = "unknown"             # "high" | "medium" | "low" | "unknown"
    failed_node: Optional[str] = None
    last_safe_state: Optional[str] = None
    retry_options: list[RetryOption] = Field(default_factory=list)
    related_issues: list[str] = Field(default_factory=list)
    knows: list[str] = Field(default_factory=list)
    guesses: list[str] = Field(default_factory=list)
    evidence_refs: list[EvidenceRef] = Field(default_factory=list)
    error_category: Optional[str] = None    # "tool_timeout" | "provider_error" | "validation" | "internal" | "unknown"
    stack_summary: Optional[str] = None     # Truncated stack trace, redacted
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict)        # [RESERVED v0.2]
```

### TypeScript

```typescript
export interface RetryOption {
  label: string;
  command?: string;
  risk: 'low' | 'medium' | 'high';
}

export interface FailureAutopsy {
  schema_version: number;
  run_id: string;
  probable_cause: string;
  confidence: 'high' | 'medium' | 'low' | 'unknown';
  failed_node?: string;
  last_safe_state?: string;
  retry_options: RetryOption[];
  related_issues: string[];
  knows: string[];
  guesses: string[];
  evidence_refs: EvidenceRef[];
  error_category?: 'tool_timeout' | 'provider_error' | 'validation' | 'internal' | 'unknown';
  stack_summary?: string;
  created_at: string;
  metadata: Record<string, unknown>;  // v0.2+
}
```

### JSON Example

```json
{
  "schema_version": 1,
  "run_id": "run_01HXYZ123456789",
  "probable_cause": "Tool execution timeout at node 'reviewer'",
  "confidence": "high",
  "failed_node": "reviewer",
  "last_safe_state": "writer completed, reviewer started",
  "retry_options": [
    {"label": "Retry with longer timeout", "command": "arc run wf-review --timeout 600", "risk": "low"},
    {"label": "Skip reviewer node", "risk": "medium"}
  ],
  "related_issues": [],
  "knows": [
    "Node reviewer called search_tool with input 'find PR #42'",
    "search_tool exceeded 120s timeout"
  ],
  "guesses": [
    "Search tool may have hung on external API rate limit",
    "Workspace index may be stale"
  ],
  "evidence_refs": [
    {"evidence_id": "ev_01JDEADBEEF1234567890", "kind": "tool_output", "target": "search_tool"}
  ],
  "error_category": "tool_timeout",
  "stack_summary": "Traceback (most recent call last):\n  ...\nconcurrent.futures.TimeoutError: 120s",
  "created_at": "2026-05-16T10:01:35Z",
  "metadata": {}
}
```

### Storage

- **Canonical:** Stored in `RunRecord.metadata["autopsy"]` as a dict, serialized in the JSONL trace
- **SQLite:** `runs.error_detail` column captures `probable_cause` + `error_category` (flat text, not full model)
- **Retrieval:** Populated by supervisor on `RUNNING → FAILED` transition

### Event Names

| Event | Direction | Payload |
|-------|-----------|---------|
| `RUN_FAILED` | supervisor → broker | carries full `FailureAutopsy` in `data.autopsy` |

### Redaction

- `stack_summary` — `Redactor.redact_string()` (may contain paths, keys in tracebacks)
- `knows[]`, `guesses[]` — each string passed through `Redactor.redact_string()`
- `probable_cause` — `Redactor.redact_string()`

### Validation

```python
def validate_failure_autopsy(a: FailureAutopsy) -> None:
    if a.confidence not in ("high", "medium", "low", "unknown"):
        raise ValueError(f"Invalid confidence: {a.confidence}")
    if a.error_category and a.error_category not in (
        "tool_timeout", "provider_error", "validation", "internal", "unknown"
    ):
        raise ValueError(f"Invalid error_category: {a.error_category}")
    if len(a.knows) + len(a.guesses) > 50:
        raise ValueError("Too many knows/guesses (max 50 total)")
```

### Backcompat

- `schema_version` defaults to 1. v0.2 may add `root_cause_analysis` — currently in `metadata`.
- `error_category` is `None` for pre-v0.2 autopsies — frontend renders as "unknown".
- `retry_options` is always a list (possibly empty) — never `None`.

### Tests to Add

| Test | What |
|------|------|
| `test_autopsy_defaults` | Default confidence is "unknown" |
| `test_autopsy_knows_guesses_distinct` | knows and guesses are separate arrays |
| `test_autopsy_json_roundtrip` | Full roundtrip |
| `test_autopsy_validation_confidence` | Bad confidence raises |
| `test_autopsy_validation_too_many` | >50 total knows+guesses raises |
| `test_autopsy_stored_in_run_metadata` | Autopsy is accessible via RunRecord.metadata |
| `test_autopsy_redaction` | API keys in stack_summary are [REDACTED] |

---

## 4. EvidenceRef

**File:** `python/src/agent_runtime_cockpit/protocol/evidence_refs.py` [MISSING]
**TS mirror:** `packages/arc-protocol-ts/src/arc-protocol-types.ts`

### Python

```python
class EvidenceKind(str, Enum):
    FILE = "file"
    TOOL_OUTPUT = "tool_output"
    RUN = "run"
    NODE = "node"
    LEDGER = "ledger"
    RECEIPT = "receipt"
    FRAME_RECEIPT = "frame_receipt"     # [RESERVED v0.2 — HotLoop frames]

class EvidenceRef(BaseModel):
    schema_version: int = 1
    evidence_id: str
    kind: EvidenceKind
    target: str                             # File path, run_id, node_id, receipt_id, etc.
    label: Optional[str] = None             # Human-readable label for rendering
    range_: Optional[tuple[int, int]] = Field(default=None, alias="range")
                                            # [start_line, end_line] for FILE kind
    redacted: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)        # [RESERVED v0.2]

    model_config = {"populate_by_name": True}

    def resolve(self, workspace_root: Path) -> Optional[Path]:
        """Resolve target to an absolute path for FILE kind evidence."""
        if self.kind == EvidenceKind.FILE:
            resolved = (workspace_root / self.target).resolve()
            if resolved.is_file():
                return resolved
        return None
```

### TypeScript

```typescript
export type EvidenceKind =
  | 'file'
  | 'tool_output'
  | 'run'
  | 'node'
  | 'ledger'
  | 'receipt'
  | 'frame_receipt';  // v0.2+

export interface EvidenceRef {
  schema_version: number;
  evidence_id: string;
  kind: EvidenceKind;
  target: string;
  label?: string;
  range?: [number, number];
  redacted: boolean;
  metadata: Record<string, unknown>;  // v0.2+
}
```

### JSON Example

```json
{
  "schema_version": 1,
  "evidence_id": "ev_01JDEADBEEF1234567890",
  "kind": "file",
  "target": "src/workflow.py",
  "label": "Changed lines in reviewer node",
  "range": [42, 58],
  "redacted": false,
  "metadata": {}
}
```

### Storage

- **Not stored standalone.** EvidenceRefs are embedded in parent objects:
  - `RunReceipt.evidence_refs[]`
  - `FailureAutopsy.evidence_refs[]`
  - `RunEvent.data.evidence_refs[]` (for `TOOL_CALL`, `MESSAGE` events)
- **No dedicated SQLite table.** Queries filter via parent run_id.

### Event Names

EvidenceRefs are **not emitted as standalone events**. They piggyback on parent events:
- `TOOL_CALL_RESULT` — `data.evidence_refs` contains ref to tool output
- `MESSAGE` — `data.evidence_refs` contains ref to source files
- `RUN_COMPLETED` — receipt carries aggregated evidence_refs

### Redaction

- `metadata` — `Redactor.redact_dict()` if populated
- `target` — not redacted (is a file path or identifier)

### Validation

```python
def validate_evidence_id(eid: str) -> str:
    if not re.match(r'^ev_[a-zA-Z0-9_-]{20,30}$', eid):
        raise ValueError(f"Invalid evidence_id: {eid!r}")
    return eid

def validate_evidence_ref(ref: EvidenceRef) -> None:
    validate_evidence_id(ref.evidence_id)
    if not ref.target:
        raise ValueError("EvidenceRef target must not be empty")
    if ref.range_:
        start, end = ref.range_
        if start < 0 or end < 0 or start > end:
            raise ValueError(f"Invalid range: ({start}, {end})")
```

### Backcompat

- `schema_version` defaults to 1. Old evidence refs (v0.0) missing `evidence_id` → generate on load.
- `FRAME_RECEIPT` kind is reserved — rejected by validation in v0.1.
- `range_` uses alias `"range"` for JSON compatibility (`model_config.populate_by_name = True`).

### Tests to Add

| Test | What |
|------|------|
| `test_evidence_ref_defaults` | Default redacted=False |
| `test_evidence_ref_range_alias` | JSON key "range" maps to range_ field |
| `test_evidence_ref_resolve_file` | resolve() returns valid Path for existing file |
| `test_evidence_ref_resolve_missing` | resolve() returns None for non-existent |
| `test_evidence_ref_validation_eid` | Bad evidence_id raises |
| `test_evidence_ref_validation_range` | Negative range raises |
| `test_evidence_ref_kind_enum` | Only valid kinds accepted |
| `test_evidence_ref_frame_receipt_rejected` | frame_receipt kind raises in v0.1 |

---

## 5. TrustDiff

**File:** `python/src/agent_runtime_cockpit/protocol/trust_diff.py` [MISSING]
**TS mirror:** `packages/arc-protocol-ts/src/arc-protocol-types.ts`

### Python

```python
class TrustDiff(BaseModel):
    schema_version: int = 1
    diff_id: str
    workspace_path: str
    before: list[str] = Field(default_factory=list)        # Capability tokens before
    after: list[str] = Field(default_factory=list)         # Capability tokens after
    added_capabilities: list[str] = Field(default_factory=list)
    removed_restrictions: list[str] = Field(default_factory=list)
    affected_runtimes: list[str] = Field(default_factory=list)
    reason: str = "unknown"                                 # "workspace_first_trust" | "profile_switch" | "runtime_added"
    requires_confirmation: bool = False
    confirmed_at: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict[str, Any] = Field(default_factory=dict) # [RESERVED v0.2]

    @staticmethod
    def compute(
        before_caps: set[str],
        after_caps: set[str],
        workspace_path: str,
        reason: str = "workspace_first_trust",
    ) -> "TrustDiff":
        added = after_caps - before_caps
        removed = before_caps - after_caps
        return TrustDiff(
            diff_id="td_" + secrets.token_urlsafe(16),
            workspace_path=workspace_path,
            before=sorted(before_caps),
            after=sorted(after_caps),
            added_capabilities=sorted(added),
            removed_restrictions=sorted(removed),
            requires_confirmation=len(added) > 0,
            reason=reason,
        )
```

### TypeScript

```typescript
export interface TrustDiff {
  schema_version: number;
  diff_id: string;
  workspace_path: string;
  before: string[];
  after: string[];
  added_capabilities: string[];
  removed_restrictions: string[];
  affected_runtimes: string[];
  reason: 'workspace_first_trust' | 'profile_switch' | 'runtime_added' | 'unknown';
  requires_confirmation: boolean;
  confirmed_at?: string;
  created_at: string;
  metadata: Record<string, unknown>;  // v0.2+
}
```

### JSON Example

```json
{
  "schema_version": 1,
  "diff_id": "td_01JCAFEBABE0987654321",
  "workspace_path": "/home/user/projects/my-agent",
  "before": ["read_only", "no_network", "no_paid_calls"],
  "after": ["read_only", "no_paid_calls"],
  "added_capabilities": [],
  "removed_restrictions": ["no_network"],
  "affected_runtimes": ["swarmgraph"],
  "reason": "profile_switch",
  "requires_confirmation": false,
  "created_at": "2026-05-16T10:00:00Z"
}
```

### Storage

- **Not stored long-term.** TrustDiff is computed in-memory by `ensure_trusted()` and returned to the caller.
- **Audit trail:** `policy_decision_id` is logged to `audit_log` table in SQLite when user confirms.
- **No JSONL persistence.** Re-computed on next trust check if needed.

### Event Names

| Event | Direction | Payload |
|-------|-----------|---------|
| `TRUST_DIFF_COMPUTED` | security → broker | full `TrustDiff` |
| `TRUST_DIFF_CONFIRMED` | frontend → supervisor | `diff_id`, `confirmed_at` |
| `TRUST_DIFF_REJECTED` | frontend → supervisor | `diff_id`, `reason` |

### Redaction

- `workspace_path` — no redaction (local path, not secret)
- `metadata` — `Redactor.redact_dict()` if populated

### Validation

```python
def validate_diff_id(did: str) -> str:
    if not re.match(r'^td_[a-zA-Z0-9_-]{20,30}$', did):
        raise ValueError(f"Invalid diff_id: {did!r}")
    return did

def validate_trust_diff(d: TrustDiff) -> None:
    validate_diff_id(d.diff_id)
    if d.reason not in ("workspace_first_trust", "profile_switch", "runtime_added", "unknown"):
        raise ValueError(f"Invalid reason: {d.reason}")
```

### Backcompat

- `schema_version` defaults to 1. v0.2 may add `provider_key_changes` in metadata.
- `reason` field allows forward-compat: frontend falls back to "unknown" for new reasons.

### Tests to Add

| Test | What |
|------|------|
| `test_trust_diff_compute_added` | Single capability added → requires_confirmation=True |
| `test_trust_diff_compute_removed` | Restriction removed → added_capabilities includes its inverse |
| `test_trust_diff_compute_no_change` | Identical before/after → empty diffs, no confirm |
| `test_trust_diff_json_roundtrip` | Roundtrip |
| `test_trust_diff_validation_did` | Bad diff_id raises |
| `test_trust_diff_reason_validation` | Bad reason raises |
| `test_trust_diff_confirmed_at` | Set confirmed_at after confirm |
| `test_trust_diff_integration_ensure_trusted` | ensure_trusted() returns TrustDiff [integration] |

---

## 6. CapabilitySnapshot

**File:** `python/src/agent_runtime_cockpit/protocol/capabilities.py` — extend existing `RuntimeCapabilities` [MISSING: snapshot wrapper]
**TS mirror:** `packages/arc-protocol-ts/src/arc-protocol-types.ts`

### Python

```python
class CapabilitySnapshot(BaseModel):
    schema_version: int = 1
    snapshot_id: str
    workspace_path: str
    runtime_snapshots: dict[str, RuntimeCapabilities] = Field(default_factory=dict)
                                                    # runtime_id → capabilities
    combined_capabilities: RuntimeCapabilities = Field(default_factory=RuntimeCapabilities)
                                                    # Union of all runtime caps
    computed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None                # [RESERVED v0.2] TTL for caching
    metadata: dict[str, Any] = Field(default_factory=dict)
```

### TypeScript

```typescript
export interface CapabilitySnapshot {
  schema_version: number;
  snapshot_id: string;
  workspace_path: string;
  runtime_snapshots: Record<string, RuntimeCapabilities>;
  combined_capabilities: RuntimeCapabilities;
  computed_at: string;
  expires_at?: string;             // v0.2+
  metadata: Record<string, unknown>;
}
```

### JSON Example

```json
{
  "schema_version": 1,
  "snapshot_id": "cs_01JAAAAABBBBBCCCCCD",
  "workspace_path": "/home/user/projects/my-agent",
  "runtime_snapshots": {
    "swarmgraph": {
      "schema_version": 1,
      "support_level": "beta",
      "execution_modes": ["standalone", "sequence"],
      "adoption_modes": [],
      "audit_level": "arc_sha256",
      "hitl_level": "advisory",
      "can_inspect": true,
      "can_run": true,
      "can_trace": true,
      "can_export_schema": true,
      "can_export_workflow": true,
      "can_replay": false,
      "requires_paid_calls": false,
      "requires_network": true
    }
  },
  "combined_capabilities": {
    "schema_version": 1,
    "support_level": "beta",
    "execution_modes": ["standalone", "sequence"],
    "adoption_modes": [],
    "audit_level": "arc_sha256",
    "hitl_level": "advisory",
    "can_inspect": true,
    "can_run": true,
    "can_trace": true,
    "can_export_schema": true,
    "can_export_workflow": true,
    "can_replay": false,
    "requires_paid_calls": false,
    "requires_network": true
  },
  "computed_at": "2026-05-16T10:00:00Z",
  "metadata": {}
}
```

### Storage

- **Not stored.** Computed on-demand by `RuntimeRouter.capability_snapshot()`.
- **Caching:** In-memory only (v0.1). v0.2 may cache to `.arc/capability-snapshot.json`.
- **Frontend:** Cached in React state, refetched on workspace switch.

### Event Names

No dedicated events. CapabilitySnapshot is a query response, not a streamed event.

### Redaction

- `metadata` — `Redactor.redact_dict()` if populated
- `runtime_snapshots` values — `Redactor.redact_dict()` applied to each snapshot's `model_dump()`

### Validation

```python
def validate_capability_snapshot(cs: CapabilitySnapshot) -> None:
    if not cs.runtime_snapshots:
        raise ValueError("At least one runtime snapshot required")
    for rid, caps in cs.runtime_snapshots.items():
        if not isinstance(caps, RuntimeCapabilities):
            raise ValueError(f"Invalid capabilities for runtime {rid}")
```

### Backcompat

- New fields added to `RuntimeCapabilities` in the future will automatically propagate via `model_dump()`.
- `expires_at` is `None` in v0.1 — frontend treats missing expiry as "stale after session".

### Tests to Add

| Test | What |
|------|------|
| `test_capability_snapshot_combined` | Combined caps merge flags correctly (OR logic) |
| `test_capability_snapshot_empty_runtimes` | Empty runtime_snapshots raises |
| `test_capability_snapshot_roundtrip` | Serialization roundtrip |
| `test_capability_snapshot_updates_on_change` | Re-compute after profile switch |
| `test_runtime_capabilities_requires_flags` | requires_paid_calls, requires_network, requires_shell serialize |

---

## 7. RuntimeManifest Extensions

**File:** `python/src/agent_runtime_cockpit/protocol/schemas.py` — extend `RuntimeInfo` [MISSING: manifest fields]
**TS mirror:** `packages/arc-protocol-ts/src/arc-protocol-types.ts` — extend `RuntimeInfo`

### Changes

Extend `RuntimeInfo` to carry a rich manifest alongside the existing capability model.

### Python (extend existing `RuntimeInfo` in `protocol/schemas.py`)

```python
class RuntimeManifest(BaseModel):
    schema_version: int = 1
    runtime_id: str
    version: str = "0.0.0"
    homepage: Optional[str] = None
    docs_url: Optional[str] = None
    license_: Optional[str] = Field(default=None, alias="license")
    supported_languages: list[str] = Field(default_factory=list)
    min_arc_version: str = "0.1.0"
    extra: dict[str, Any] = Field(default_factory=dict)         # [RESERVED v0.2]

    model_config = {"populate_by_name": True}


# Extended RuntimeInfo (add manifest field)
class RuntimeInfo(BaseModel):
    id: str
    name: str
    adapter: str
    confidence: ConfidenceLevel
    evidence: list[str] = Field(default_factory=list)
    capabilities: RuntimeCapabilities = Field(default_factory=RuntimeCapabilities)
    manifest: Optional[RuntimeManifest] = None                  # NEW
```

### TypeScript (extend existing `RuntimeInfo`)

```typescript
export interface RuntimeManifest {
  schema_version: number;
  runtime_id: string;
  version: string;
  homepage?: string;
  docs_url?: string;
  license?: string;
  supported_languages: string[];
  min_arc_version: string;
  extra: Record<string, unknown>;  // v0.2+
}

// Extended RuntimeInfo
export interface RuntimeInfo {
  id: string;
  name: string;
  adapter: string;
  confidence: 'high' | 'medium' | 'low';
  evidence: string[];
  capabilities: RuntimeCapabilities;
  manifest?: RuntimeManifest;  // NEW
}
```

### JSON Example

```json
{
  "id": "sg-001",
  "name": "SwarmGraph",
  "adapter": "swarmgraph",
  "confidence": "high",
  "evidence": ["swarmgraph.yaml found", "pyproject.toml references hive-swarm"],
  "capabilities": { "...": "..." },
  "manifest": {
    "schema_version": 1,
    "runtime_id": "swarmgraph",
    "version": "0.4.2",
    "homepage": "https://github.com/example/swarmgraph",
    "docs_url": "https://swarmgraph.dev/docs",
    "license": "MIT",
    "supported_languages": ["python"],
    "min_arc_version": "0.1.0",
    "extra": {}
  }
}
```

### Storage

- **Not stored separately.** Manifest is reported by the adapter at detection time.
- **Cached in:** `WorkspaceInfo.runtimes[].manifest` — serialized in JSONL if workspace info is persisted.
- **SQLite:** Manifest is not indexed. Available via daemon RPC.

### Event Names

| Event | Direction | Payload |
|-------|-----------|---------|
| `WORKFLOW_DETECTED` | detector → broker | carries full `RuntimeInfo` including manifest |

### Redaction

- `manifest.extra` — `Redactor.redact_dict()` if populated
- `manifest.homepage`, `manifest.docs_url` — no redaction (public URLs)

### Validation

```python
def validate_runtime_manifest(m: RuntimeManifest) -> None:
    if not m.runtime_id:
        raise ValueError("runtime_id is required")
    if not re.match(r'^\d+\.\d+\.\d+$', m.version):
        raise ValueError(f"Invalid semver: {m.version}")
    if m.license_ and len(m.license_) > 100:
        raise ValueError("License string too long")
```

### Backcompat

- `manifest` is `None` for adapters that don't report it — frontend hides manifest section.
- `min_arc_version` defaults to `"0.1.0"` for manifests without the field.
- `license_` uses `alias="license"` for JSON compatibility.

### Tests to Add

| Test | What |
|------|------|
| `test_runtime_manifest_defaults` | Default version is "0.0.0" |
| `test_runtime_manifest_roundtrip` | Serialization preserves license alias |
| `test_runtime_manifest_validation_version` | Non-semver raises |
| `test_runtime_info_with_manifest` | Extended RuntimeInfo serializes manifest |
| `test_runtime_info_without_manifest` | None manifest doesn't crash |
| `test_workspace_info_manifests` | WorkspaceInfo roundtrip includes manifests |

---

## SQLite Schema Changes (v0.1)

Add to `runs` table in `storage/sqlite.py`:

```sql
ALTER TABLE runs ADD COLUMN contract_id TEXT;
ALTER TABLE runs ADD COLUMN receipt_id TEXT;
CREATE INDEX IF NOT EXISTS idx_runs_contract ON runs(contract_id);
CREATE INDEX IF NOT EXISTS idx_runs_receipt ON runs(receipt_id);
```

New table for policy decisions (used by TrustDiff confirmation):

```sql
CREATE TABLE IF NOT EXISTS policy_decisions (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    diff_id TEXT,
    action TEXT NOT NULL,         -- "confirm" | "reject" | "escalate"
    reason TEXT,
    decision_id TEXT UNIQUE,
    decided_at TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES runs(id)
);
```

---

## File Creation Summary

| File | Content | Status |
|------|---------|--------|
| `python/src/agent_runtime_cockpit/protocol/run_contract.py` | RunContract, ContractStatus, validation | [MISSING] |
| `python/src/agent_runtime_cockpit/protocol/run_receipt.py` | RunReceipt, FileChange, signing, validation | [MISSING] |
| `python/src/agent_runtime_cockpit/protocol/failure_autopsy.py` | FailureAutopsy, RetryOption, validation | [MISSING] |
| `python/src/agent_runtime_cockpit/protocol/evidence_refs.py` | EvidenceRef, EvidenceKind, validation | [MISSING] |
| `python/src/agent_runtime_cockpit/protocol/trust_diff.py` | TrustDiff, TrustDiff.compute(), validation | [MISSING] |
| `python/src/agent_runtime_cockpit/protocol/capabilities.py` | CapabilitySnapshot (extend) | [MISSING] |
| `python/src/agent_runtime_cockpit/protocol/schemas.py` | RuntimeManifest, extend RuntimeInfo | [MISSING] |
| `packages/arc-protocol-ts/src/arc-protocol-types.ts` | Append all TS interfaces | [EXISTS: extend] |
| `python/src/agent_runtime_cockpit/security/validation.py` | Add: validate_contract_id, validate_receipt_id, validate_evidence_id, validate_diff_id | [MISSING] |
| `python/src/agent_runtime_cockpit/storage/sqlite.py` | Add contract_id, receipt_id columns, policy_decisions table | [MISSING] |

---

## Test File Inventory

| Test File | New Tests |
|-----------|-----------|
| `python/tests/test_protocol.py` | ~25 tests for contract, receipt, autopsy, evidence, trust_diff, snapshot, manifest |

New file: `python/tests/test_receipt_signing.py` for the HMAC sign/verify tests (6 tests).

---

## Implementation Order (Dependency-Aware)

```
1. EvidenceRef        ← no deps (pure model)
2. RunContract        ← depends on EvidenceRef (evidence_expected is string list, not refs)
3. RunReceipt         ← depends on EvidenceRef (evidence_refs field)
4. FailureAutopsy     ← depends on EvidenceRef (evidence_refs field)
5. TrustDiff          ← no deps (pure model, uses set math)
6. CapabilitySnapshot ← depends on RuntimeCapabilities (already exists)
7. RuntimeManifest    ← depends on RuntimeInfo (already exists)
8. SQLite schema      ← depends on 1-7 (add columns + policy_decisions table)
9. Validation fns     ← depends on 1-7 (add to security/validation.py)
```
