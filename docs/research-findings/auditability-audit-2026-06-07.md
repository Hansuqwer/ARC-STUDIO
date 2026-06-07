# ARC Studio Auditability Architecture Audit — 2026-06-07

> **Scope:** RunContract, RunReceipt, EvidenceRef, FailureAutopsy, audit chains, keyed audit verification, effect-boundary journal, replay, fork, diff, undo/redo, review provenance  
> **Source:** Synthesized from prior sessions + direct reads of audit/schema.py, transactions.py, runner_integration.py, RunReceiptCard.tsx, FailureAutopsyCard.tsx, audit/session.py

---

## 1. Evidence Architecture Map

```
┌─────────────────────────────────────────────────────────────────────┐
│              ARC STUDIO EVIDENCE & AUDIT ARCHITECTURE                │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 1 — RUN ARTIFACTS (filesystem, per run_id)                   │
│                                                                      │
│  ~/.arc/traces/{run_id}.jsonl          ← Event trace (JSONL)         │
│  ~/.arc/traces/{run_id}.receipt.json   ← RunReceipt                 │
│  ~/.arc/traces/{run_id}.autopsy.json   ← FailureAutopsy             │
│  ~/.arc/traces/{run_id}.contract.json  ← RunContract                │
│                                                                      │
│  ~/.arc/audit/{run_id}.audit.jsonl     ← HMAC-signed audit chain    │
│  ~/.arc/audit/{run_id}.audit.checkpoint.json ← Sidecar (tamper)     │
│  ~/.arc/audit/sandbox.audit.jsonl      ← Sandbox decisions          │
│  ~/.arc/audit/mcp.events.jsonl         ← MCP tool call audit        │
│  <workspace>/.arc/mcp/decisions.jsonl  ← MCP risk decisions         │
│                                                                      │
│  <workspace>/.arc/transactions/{txn_id}.json ← ArcTransaction       │
│   (before_hash, after_hash, before_content, after_content per file)  │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 2 — AUDIT CHAIN (ADR-021, EU AI Act compliance framing)      │
│                                                                      │
│  audit/schema.py: 12 typed AuditEventType values:                   │
│   llm_request, llm_response, tool_call, tool_result,                 │
│   hitl_prompt, hitl_response, budget_decision,                       │
│   run_started, run_completed, run_failed, run_cancelled,             │
│   sandbox_command                                                    │
│                                                                      │
│  audit/session.py: AuditSession context manager                     │
│   ├── log_run_started(runtime, mode)                                 │
│   ├── log_llm_request(provider, model)                               │
│   ├── log_llm_response(provider, model, usage, cost)                 │
│   ├── log_tool_call(tool_name, tool_id, arguments, trust_level)     │
│   ├── log_tool_result(tool_name, tool_id, result, trust_level)      │
│   ├── log_run_completed/failed/cancelled()                           │
│   └── RedactionConfig.from_env() → optional field redaction         │
│                                                                      │
│  audit/hmac_chain.py: HmacAuditChainWriter                          │
│   ├── SHA-256 chain with HMAC signing when key available            │
│   ├── fsync on every append                                         │
│   ├── .checkpoint.json sidecar for truncation detection             │
│   └── Fail-closed: no extension of corrupt chains                   │
│                                                                      │
│  audit/runner_integration.py: log_agui_to_audit()                  │
│   ├── Maps AG-UI events → typed audit events inline                 │
│   └── Used by CrewAI, LangGraph, SwarmGraph adapters               │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 3 — EFFECT BOUNDARY JOURNAL (transactions.py)               │
│                                                                      │
│  ArcTransaction:                                                     │
│   ├── transaction_id: txn-{uuid12hex}                               │
│   ├── workspace_root, source, created_at, git_head, git_status      │
│   └── files[]: TransactionFile (path, before_*, after_*)            │
│                                                                      │
│  TransactionFile:                                                    │
│   ├── before_exists, before_hash (SHA-256), before_content          │
│   └── after_exists, after_hash, after_content                       │
│                                                                      │
│  Stored at: <workspace>/.arc/transactions/{txn_id}.json             │
│  Path escape check: resolved path must be is_relative_to(root)      │
│  Write path: write_text_atomic()                                    │
│  Used by: arc edit apply (arc edit undo/redo implemented in CLI)    │
├─────────────────────────────────────────────────────────────────────┤
│  LAYER 4 — PROTOCOL EVIDENCE TYPES (arc-protocol.ts)               │
│                                                                      │
│  EvidenceRef {                                                       │
│    schema_version: number;                                           │
│    evidence_id: string;  // stable ev_{ulid}                        │
│    kind: 'file'|'tool_output'|'run'|'node'|'ledger'|'receipt';     │
│    target: string;       // file path, run ID, etc.                 │
│    label?: string;                                                   │
│    range?: [number, number];  // line range for 'file' kind         │
│    redacted: boolean;                                                │
│    metadata: Record<string, unknown>;                                │
│  }                                                                   │
│                                                                      │
│  RunReceipt { run_id, workflow_id, runtime, status, started_at,     │
│    ended_at, duration_ms, cost_usd, provider, model, event_count,   │
│    tool_calls_count, hitl_count, files_changed[], trust_boundaries, │
│    unresolved_risks[], evidence_refs[], audit_path,                  │
│    signature_status, sandbox_policy }                                │
│                                                                      │
│  FailureAutopsy { run_id, probable_cause, confidence, error_category,│
│    failed_node, last_safe_state, retry_options[], knows[], guesses[],│
│    evidence_refs[] }                                                 │
│                                                                      │
│  RunContract { run_id, proposed_by, accepted_at, workflow_hash,     │
│    runtime_id, profile_id, tools[], services[], capabilities[],     │
│    status: ContractStatus }                                          │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Audit Coverage Matrix

### Which run paths write receipts?

| Path | Writes receipt? | Writes autopsy? | Writes contract? | HMAC chain? |
|---|---|---|---|---|
| `arc run` (fake/offline, SwarmGraph) | ✅ via AuditBridgeService | ✅ on failure | ✅ | ✅ |
| `arc run` (LangGraph local-real) | ✅ | ✅ on failure | ✅ | ✅ |
| `arc run` (CrewAI gated) | ✅ | ✅ on failure | ✅ | ✅ |
| `arc studio chat` (provider-backed) | ✅ via ChatSession | ⚠️ best-effort | ⚠️ | ✅ |
| MCP tool calls | ✅ per-call audit event | ❌ | ❌ | ⚠️ (mcp.events.jsonl only) |
| Sandbox commands | ❌ (only sandbox.audit.jsonl) | ❌ | ❌ | ✅ (sandbox chain) |
| `arc runs fork` | ❌ | ❌ | ❌ | ❌ (new run, no artifact) |

### Audit is conditional, not universal

| Condition | Behavior |
|---|---|
| No HMAC key available | Falls through to SHA-256 only chain (not keyed) |
| Audit write failure | Best-effort — `_persist_audit_safely` logs but never fail-opens |
| Run completes before audit session ends | `log_run_completed()` called in finally block |
| `ARC_AUDIT_REDACT_MESSAGES=1` | LLM messages replaced with `<redacted>` before signing |
| `ARC_AUDIT_REDACT_TOOL_ARGS=1` | Tool arguments redacted before signing |
| `ARC_AUDIT_REDACT_TOOL_RESULTS=1` | Tool results redacted before signing |

Note: **Redaction is applied before HMAC signing.** A redacted chain and an unredacted chain will have different signatures. The chain verifies what was logged, not what was executed.

### Which run paths verify keyed audit?

`arc audit verify <run_id> --mode auto|sha256|hmac`:
- `auto`: tries HMAC first, falls back to SHA-256
- `hmac`: loads key from keychain; fails if no key
- `sha256`: verifies chain without key

**Keyed audit is only claimed where the key was available at write time.** If the key was not installed when the run executed, the chain is SHA-256 only. `arc audit verify` will report `mode: sha256` and a `WARNING: No HMAC key available for this chain`.

---

## 3. Replay / Fork / Diff Flow Map

```
arc runs replay <run_id>
  → reads {run_id}.jsonl from JsonlTraceStore
  → re-emits events WITHOUT re-executing any runtime
  → output: ReplayResult { run_id, events[], totalEvents, annotations }
  → AssuranceTab replay stepper: prev/next button, category filter
  → NOT deterministic re-execution — it is event stream replay only

arc runs fork <run_id>
  → copies run record to new run_id with status=PENDING
  → copies only RUN_STARTED and STEP_STARTED events (first event if none match)
  → records forked_from, forked_at, original_status in metadata
  → writes forked_to list back to source run
  → DOES NOT copy: receipt, autopsy, contract, audit chain
  → DOES NOT use TransactionFile journal entries
  → New run starts fresh; fork is metadata only

arc runs diff <run_a> <run_b>
  → calls diff_run_records(a, b) via run_diff module
  → output: { types_only_in_a, types_only_in_b, types_common,
              tool_calls_a/b, error_events_a/b,
              duration_a/b_ms, final_output_a/b }
  → IDE: RunsTab shows diff section backed by diffRuns() RPC call
  → Gap: event hashing is on data_keys only (not values) — topology
    regressions invisible if same event type present with different content

arc edit apply <plan_id>
  → validates plan, requires --approve or --approval-token
  → calls write_text_atomic() for each file change
  → creates ArcTransaction record with before/after content + hashes
  → stored at <workspace>/.arc/transactions/{txn_id}.json

arc edit undo <transaction_id>
  → reads ArcTransaction from disk
  → validates path escape (is_relative_to(workspace))
  → restores before_content for each file using write_text_atomic()
  → Implemented: CLI arc edit undo / arc edit redo

arc edit redo <transaction_id>
  → same as undo but restores after_content
```

### Is replay deterministic?

**No.** `arc runs replay` is a trace playback — it reads stored events and re-emits them in order. It does **not** re-execute the runtime. The events reflect what happened; replaying them produces the same event sequence but never re-runs the agent or makes new provider calls. This is correctly labeled "replay" not "re-run" in all UI surfaces.

### Does fork use effect-boundary journal entries?

**No.** `arc runs fork` copies metadata and a subset of events. It creates a new PENDING run with inherited context but does not copy or reference the source run's `ArcTransaction` records. The fork starts from scratch — no workspace file state is inherited or rolled back.

### Are diffs linked to evidence?

**Partially.** `diff_run_records()` computes structural diffs (event type presence, error events, final output substring). It does **not** link diff results to `EvidenceRef` objects. `RunsTab` shows diff results inline but with no `EvidenceChip` linkage. `EvidenceRef` objects exist in `RunReceipt.evidence_refs` and `FailureAutopsy.evidence_refs` and are rendered via `EvidenceChip` with click events — but these are not connected to the diff view.

---

## 4. IDE Evidence UX Gaps

### RunsTab

| Feature | Status | Notes |
|---|---|---|
| Run list | ✅ | From `getTraces()` |
| RunReceiptCard | ⚠️ `.catch(() => null)` | Silently absent if CLI fails; no "receipt missing" indicator |
| FailureAutopsyCard | ⚠️ `.catch(() => null)` | Same silent failure |
| RunContractCard | ⚠️ `.catch(() => null)` | Same silent failure |
| EvidenceChip on receipt | ✅ | Clickable, emits `EvidenceSelectionEvent` |
| EvidenceChip on autopsy | ✅ | Same |
| Diff section | ✅ | `diffRuns()` backed; controls visible |
| Run-to-replay navigation | ❌ | No "Replay in Assurance" button in RunsTab |
| Audit path shown | ❌ | `receipt.audit_path` typed but not rendered in UI |
| Signature status shown | ❌ | `receipt.signature_status` typed but not rendered |
| Transaction journal link | ❌ | No link from run to transaction records |

### AssuranceTab

| Feature | Status | Notes |
|---|---|---|
| Replay stepper | ✅ | prev/next buttons, category filter, JSON export |
| Audit verify | ✅ | `getAuditChainInfo` shows present/missing/degraded |
| Audit path shown | ❌ | `audit_path` field exists in `AuditChainInfo` but not rendered |
| Audit signature mode (sha256 vs hmac) | ❌ | Not displayed; users cannot tell if chain is keyed |
| HITL inbox approve/reject | ✅ | Token-expiry blocking enforced |
| HITL age for real records | ❌ | `_age()` returns `""` for ISO strings (real records never show age) |
| Policy bypass warnings panel | ❌ | `POLICY_BYPASS_WARNING` events exist; no dedicated panel |
| Transaction journal viewer | ❌ | `arc edit list/show` CLI commands exist; no IDE surface |

### EditPlansTab

| Feature | Status | Notes |
|---|---|---|
| List/show/approve/diff/apply | ✅ | Full CRUD surface |
| `arc edit undo/redo` | ❌ | CLI commands exist; no IDE button |
| Link from edit plan to audit chain | ❌ | No connection between edit plan approval and HMAC audit entry |
| Transaction journal viewer | ❌ | `ArcTransaction` records not surfaced in any IDE tab |

### EvidenceRef system gaps

| Gap | Detail |
|---|---|
| `EvidenceRef` never emitted for context retrieval | Context pack entries (`LocalRepoProvider`) have no `EvidenceRef`; only run-time events produce refs |
| `EvidenceRef.range` (line range) — file navigation not wired | Has `range: [number, number]` for 'file' kind; no Theia `NavigationLocation` action is triggered when an EvidenceChip is clicked |
| Graph topology (`GraphNodeData.evidenceRefs`) | Present in protocol; `arc-workflow-graph-widget.tsx` uses `CrossLinkState` with `linkedEvidenceIds` — correct wiring |
| `RunLinksResponse.evidenceChains` | Exists but never displayed in any tab panel |

---

## 5. Tests Needed

### High priority (critical gaps)

| Test | Why needed |
|---|---|
| `test_run_receipt_missing_shows_indicator_not_silence` | `.catch(() => null)` means missing receipts are invisible; need contract test asserting placeholder text |
| `test_run_fork_does_not_copy_audit_chain` | Fork behavior; confirm new run starts fresh |
| `test_transaction_undo_restores_content` | `arc edit undo` correctness; before_content restored |
| `test_transaction_redo_restores_after_content` | `arc edit redo` correctness |
| `test_audit_session_redaction_before_signing` | Redaction applied pre-HMAC; redacted and unredacted chains have different sigs |
| `test_audit_verify_reports_sha256_vs_hmac` | Mode distinction should be surfaced in output |
| `test_replay_does_not_re_execute_runtime` | Verify replay is read-only event playback |
| `test_diff_run_hashes_event_values_not_just_keys` | Current hash on `data_keys` only; topology regressions are invisible |

### Medium priority

| Test | Why needed |
|---|---|
| `test_evidence_chip_click_emits_selection_event` | EvidenceChip wiring to RunsTab |
| `test_failure_autopsy_retry_options_are_actionable` | onRetry callback wired |
| `test_run_contract_status_reflects_compliance` | ContractStatus enum values |
| `test_audit_path_shown_in_receipt_card` | Currently not rendered |
| `test_signature_status_shown_in_receipt_card` | Currently not rendered |
| `test_hitl_age_shown_for_iso_timestamp` | Real records show `""` for age |
| `test_transaction_path_escape_rejected` | `is_relative_to(workspace)` check |

### Existing test coverage (confirmed from prior sessions)

| Test | Status | What it covers |
|---|---|---|
| `tests/audit/test_session.py` | ✅ | AuditSession context manager, redaction, log_* methods |
| `tests/audit/test_hmac_chain.py` | ✅ | HMAC chain append, verify, checkpoint, truncation detection |
| `tests/web/test_cli_runs.py` | ✅ (minimal) | Basic runs list; fork/diff/budget/autopsy untested |
| `tests/cli/test_audit_query.py` | ✅ | audit query filter_isolation, composition |
| `tests/security/test_workspace_escape.py` | ✅ | `is_path_within_root()` including transactions path |
| `studio-tabs.contract.test.ts` | ✅ | RunsTab: replay-only label, .catch(() => null) pattern |
| `studio-tabs.contract.test.ts` | ✅ | AssuranceTab: audit state machine, replay stepper |
| `studio-tabs.contract.test.ts` | ✅ | EditPlansTab: sandbox/transaction gate copy |

---

## 6. Improved Implementation Prompt

**Target:** Three slices that improve evidence visibility without breaking changes.

```
# Auditability Next Slice: Receipt Display + Audit Path + Replay Navigation

## Context

ARC Studio v0.8-r-ux2. Three auditability gaps discovered:

1. RunReceiptCard, FailureAutopsyCard, and RunContractCard are fetched
   with `.catch(() => null)`. When the CLI fails or artifacts are missing,
   these cards are silently absent — the user sees a placeholder that is
   identical for "loading", "missing artifact", and "CLI error". There is
   no honest "Receipt not found" state.

2. RunReceipt has `audit_path` and `signature_status` fields (typed in
   arc-protocol.ts) but these are never rendered in RunReceiptCard.tsx.
   Users cannot see where their audit chain is stored or whether it is
   SHA-256 or HMAC-keyed.

3. AssuranceTab's replay stepper exists, but RunsTab has no "Replay in
   Assurance" button. After viewing a failed run in RunsTab, there is no
   direct navigation to the AssuranceTab replay for that specific run.

## Scope

### Slice A: Honest receipt missing/error state in RunsTab

File: packages/arc-extension/src/browser/tabs/RunsTab.tsx

Replace the silent `.catch(() => null)` pattern with explicit state:

```typescript
// Replace:
const receipt = await arcService.getRunReceipt(runId).catch(() => null);

// With:
let receipt: RunReceipt | null = null;
let receiptError: string | null = null;
try {
    receipt = await arcService.getRunReceipt(runId);
} catch (error) {
    receiptError = error instanceof Error ? error.message : 'Failed to load receipt';
}
```

Render explicit states:
```tsx
{receiptError ? (
    <div className="arc-studio-assurance__state-banner arc-studio-assurance__state-banner--warning">
        <span className="arc-studio-assurance__state-icon">⚠</span>
        <div className="arc-studio-assurance__state-body">
            <div className="arc-studio-assurance__state-title">Receipt unavailable</div>
            <div className="arc-studio-assurance__state-detail">{receiptError}</div>
            <div className="arc-studio-assurance__state-detail">
                CLI: <code>arc runs budget {runId}</code>
            </div>
        </div>
    </div>
) : receipt ? (
    <RunReceiptCard receipt={receipt} onVerify={...} onExport={...} />
) : null}
```

Apply same pattern to FailureAutopsyCard and RunContractCard.

### Slice B: Show audit path and signature status in RunReceiptCard

File: packages/arc-extension/src/browser/components/RunReceiptCard.tsx

Add audit_path and signature_status rendering:

```tsx
{receipt.audit_path && (
    <div className="arc-receipt-audit-row">
        <span className="arc-receipt-label">Audit chain:</span>
        <code className="arc-receipt-audit-path" title={receipt.audit_path}>
            {receipt.audit_path.replace(/.*\.arc\//, '~/.arc/')}
        </code>
        <span
            className={`arc-receipt-sig-badge arc-receipt-sig-badge--${receipt.signature_status ?? 'unknown'}`}
            aria-label={`Signature status: ${receipt.signature_status ?? 'unknown'}`}
        >
            {receipt.signature_status === 'hmac' ? '🔑 HMAC' :
             receipt.signature_status === 'sha256' ? '🔒 SHA-256' :
             receipt.signature_status === 'missing' ? '⚠ No chain' :
             '? Unknown'}
        </span>
        <button onClick={onVerify} aria-label="Verify audit chain">
            Verify
        </button>
    </div>
)}
```

Add to CSS (arc-studio-widget.css):
```css
.arc-receipt-audit-row {
    display: flex; gap: 8px; align-items: center;
    font-size: 11px; margin-top: 8px; flex-wrap: wrap;
}
.arc-receipt-audit-path {
    font-family: var(--arc-font-family-mono); opacity: 0.8;
    max-width: 280px; overflow: hidden; text-overflow: ellipsis;
}
.arc-receipt-sig-badge--hmac { color: var(--arc-color-success); }
.arc-receipt-sig-badge--sha256 { color: var(--arc-color-primary); }
.arc-receipt-sig-badge--missing { color: var(--arc-color-warning); }
```

Contract test addition in studio-tabs.contract.test.ts:
- Assert `receipt.audit_path` reference exists in RunReceiptCard source
- Assert `receipt.signature_status` reference exists
- Assert `aria-label="Signature status"` exists

### Slice C: "Replay in Assurance" navigation from RunsTab

File: packages/arc-extension/src/browser/tabs/RunsTab.tsx

Add a navigation button to the run detail section that switches to the
Assurance tab with the selected run ID:

```tsx
{selectedRunId && (
    <button
        className="arc-studio-assurance__button"
        onClick={() => props.onOpenInAssurance?.(selectedRunId)}
        aria-label={`Open run ${selectedRunId} replay in Assurance tab`}
    >
        Replay in Assurance →
    </button>
)}
```

File: packages/arc-extension/src/browser/arc-studio-widget.tsx

Add `onOpenInAssurance` callback to RunsTab prop:
```tsx
<RunsTab
    arcService={this.arcService}
    initialRunId={this.state.selectedRunId}
    onOpenInAssurance={(runId) => {
        this.setState({ activeTab: 'assurance', selectedRunId: runId });
    }}
/>
```

AssuranceTab already accepts `initialRunId` — wire it to auto-open replay
for the provided run ID on mount.

### Slice D: Show undo/redo in EditPlansTab

File: packages/arc-extension/src/browser/tabs/EditPlansTab.tsx

Add Undo and Redo buttons to each applied plan row that calls the CLI:

```tsx
{plan.transaction_id && (
    <>
        <button
            onClick={() => arcService.applyEditPlan({
                type: 'undo', transactionId: plan.transaction_id
            })}
            aria-label={`Undo transaction ${plan.transaction_id}`}
        >
            Undo
        </button>
        <button
            onClick={() => arcService.applyEditPlan({
                type: 'redo', transactionId: plan.transaction_id
            })}
            aria-label={`Redo transaction ${plan.transaction_id}`}
        >
            Redo
        </button>
    </>
)}
```

This requires `arcService.applyEditPlan()` to accept `type: 'undo'|'redo'`.
Add to arc-protocol.ts and backend service.

Alternatively, simpler first-pass: add CLI hint text:
```tsx
{plan.transaction_id && (
    <div className="arc-edit-plans__undo-hint">
        <code>arc edit undo {plan.transaction_id}</code> /
        <code>arc edit redo {plan.transaction_id}</code>
    </div>
)}
```

## Do NOT do in this slice

- EvidenceRef line-range navigation (Theia NavigationLocation wiring)
- Full evidence provenance graph
- `RunLinksResponse.evidenceChains` viewer
- Diff event-value hashing (separate diff slice)
- HITL age fix (requires Python schema change)
- Audit chain HMAC signing for decisions.jsonl

## Contract test additions required

```typescript
// In studio-tabs.contract.test.ts, RunsTab section:
it('shows honest receipt missing state', () => {
    // Assert source contains "Receipt unavailable" copy
    // Assert source references receiptError state
});

it('shows audit_path in RunReceiptCard', () => {
    // Assert receipt.audit_path rendered
    // Assert receipt.signature_status rendered
    // Assert aria-label for sig status
});

it('has replay navigation to AssuranceTab', () => {
    // Assert onOpenInAssurance prop exists
    // Assert "Replay in Assurance" button copy
});
```

## Verification

```bash
pnpm typecheck && pnpm build
pnpm test packages/arc-extension
```

---

## Appendix: Answered research questions

| Question | Answer |
|---|---|
| Which run paths write receipts? | `arc run` (all runtimes) via AuditBridgeService. MCP tool calls only to mcp.events.jsonl. Sandbox commands only to sandbox.audit.jsonl. |
| Which run paths verify keyed audit? | `arc audit verify --mode hmac` requires key in keychain. Key availability at write time determines chain type. Reported in verify output. |
| Is audit conditional or universal? | Conditional. No key → SHA-256 only. Write failure → best-effort, non-fatal. Redaction → optional per env var. |
| Are missing audit materials rendered honestly? | **No.** Currently `.catch(() => null)` on all 3 artifact fetches; user sees placeholder for loading/missing/error. |
| Does fork use effect-boundary journal entries? | **No.** `arc runs fork` is metadata+events copy only; no TransactionFile records. |
| Is replay deterministic? | Deterministic read-only playback of stored events. No runtime re-execution. |
| Are diffs linked to evidence? | Partially. `EvidenceChip` on receipt/autopsy. Diff section has no EvidenceRef linkage. |
| Are failure autopsies actionable? | `FailureAutopsyCard` shows `retry_options[]` with risk levels. `onRetry` callback exists but is not wired to `startRun()` in RunsTab. |
| Is undo/redo implemented or deferred? | **Implemented at CLI level** (`arc edit undo/redo`). **IDE level**: no buttons — only CLI hint text planned as follow-on. |
