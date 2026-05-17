# 08 — Run Receipt

## Summary

The RunReceipt is a signed local artifact generated for every completed or failed run. It is the human/export surface — not Trace UI. It supports support requests, PR attachments, evals, and audit verification.

**Spec:** `ARC_STUDIO_UX_SPEC.md:1166`
**Status:** [MISSING] — zero code, spec only

## Schema

**Create file:** `python/src/agent_runtime_cockpit/protocol/run_receipt.py`

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class FileChange(BaseModel):
    path: str
    added: int = 0
    removed: int = 0

class RunReceipt(BaseModel):
    receipt_version: Literal[1] = 1
    receipt_id: str
    session_id: str
    run_id: str
    contract_id: Optional[str] = None
    status: Literal['completed', 'failed', 'cancelled']
    summary: str
    cost_usd: Optional[float] = None
    files_changed: list[FileChange] = Field(default_factory=list)
    approvals: list[str] = Field(default_factory=list)
    evidence_refs: list[dict] = Field(default_factory=list)
    rollback_command: Optional[str] = None
    trust_boundaries_crossed: list[str] = Field(default_factory=list)
    unresolved_risks: list[str] = Field(default_factory=list)
    audit_chain_ref: str
    signature: str
```

## CLI Verbs

Add to CLI (`python/src/agent_runtime_cockpit/cli.py`):

```
arc-studio receipt show <run-id>     # Print receipt JSON
arc-studio receipt export <run-id>   # Save receipt to file
arc-studio receipt verify <file>     # Verify HMAC signature
```

**Handler scaffold:**
```python
@app.command()
def receipt_show(run_id: str):
    """Show run receipt for a completed/failed run."""
    receipt = load_receipt(run_id)
    print(receipt.model_dump_json(indent=2))

@app.command()
def receipt_verify(file: Path):
    """Verify receipt HMAC signature."""
    data = json.loads(file.read_text())
    if verify_hmac(data):
        print(f"✓ Receipt {data['receipt_id']} signature valid")
    else:
        print(f"✗ Receipt signature INVALID", file=sys.stderr)
        raise typer.Exit(1)
```

## Entry Points to Extend

| File | What to Change |
|------|----------------|
| `orchestration/supervisor.py` | On run completion/failure: generate receipt, sign with HMAC, store |
| `storage/jsonl.py` | Add `save_receipt()`, `load_receipt()` methods |
| `storage/sqlite.py` | Add `receipts` table or store receipt_id in runs table |
| `security/hmac_chain.py` | Use existing HMAC signing for receipt signature |
| `cli.py` | Add `arc receipt` subcommand group |
| `protocol/events.py` | Add `RECEIPT_GENERATED` event type |
| `cli/slash_commands.py` | Add `/receipt` command |

## Receipt Storage

Default location: `.arc/receipts/{run_id}.receipt.json`
Format: Single JSON file with receipt object.
Storage dir created on first receipt generation.

## Example Payload

```json
{
  "receiptVersion": 1,
  "receiptId": "rcpt_01JR6X7ABC123DEF456GHI789",
  "sessionId": "ses_01JX8YABC123DEF456GHI789JK",
  "runId": "run_01HQ3WNOPQR456STU789VWX012",
  "contractId": "ctr_01K...",
  "status": "completed",
  "summary": "Reviewer workflow: ran scan_workspace + search_codebase, 2 files modified, completed in 48.2s",
  "costUsd": 0.04,
  "filesChanged": [
    {"path": "src/workflow.py", "added": 5, "removed": 2},
    {"path": "README.md", "added": 1, "removed": 0}
  ],
  "approvals": ["paid_call_anthropic_claude_sonnet_approved_auto"],
  "evidenceRefs": [
    {"evidenceId": "ev_001", "kind": "tool_output", "target": "run_01.../events/3"}
  ],
  "rollbackCommand": "git revert --no-edit HEAD",
  "trustBoundariesCrossed": [],
  "unresolvedRisks": [],
  "auditChainRef": ".arc/audit/run_01H.../chain.jsonl",
  "signature": "hmac_sha256:a1b2c3d4e5f6..."
}
```

## Backend TypeScript Interface

Add to `packages/arc-extension/src/common/arc-protocol.ts`:

```typescript
interface RunReceipt {
  receiptVersion: 1;
  receiptId: string;
  sessionId: string;
  runId: string;
  contractId?: string;
  status: 'completed' | 'failed' | 'cancelled';
  summary: string;
  costUsd?: number;
  filesChanged: Array<{ path: string; added?: number; removed?: number }>;
  approvals: string[];
  evidenceRefs: EvidenceRef[];
  rollbackCommand?: string;
  trustBoundariesCrossed: string[];
  unresolvedRisks: string[];
  auditChainRef: string;
  signature: string;
}
```

Extend `ArcService`:
```typescript
getReceipt(runId: string): Promise<RunReceipt>;
exportReceipt(runId: string): Promise<string>;  // Returns file path
verifyReceipt(filePath: string): Promise<{ valid: boolean; receipt?: RunReceipt }>;
```

## Frontend Component

**Create file:** `packages/arc-extension/src/browser/components/RunReceiptCard.tsx`

```typescript
interface RunReceiptCardProps {
  receipt: RunReceipt;
  onExport?: () => void;
  onVerify?: () => void;
}
```

## Acceptance Criteria

- [ ] Receipt generated on every completed/failed run
- [ ] `arc-studio receipt show <run-id>` prints receipt JSON
- [ ] `arc-studio receipt export <run-id>` saves to `.arc/receipts/`
- [ ] `arc-studio receipt verify <file>` validates HMAC signature
- [ ] Receipt linked in RunList, RunContract, and EvidenceRefs
- [ ] `/receipt` CLI command works
- [ ] Default UI links to receipts before advanced trace
- [ ] All tests pass

## Likely Failure Modes

1. **HMAC signing without key** — provide default dev key, warn in production
2. **Receipt storage collision** — ensure unique receipt_id (ULID-based)
3. **Large files_changed array** — cap at 100 files, warn if exceeded
4. **Receipt for cancelled run** — still generate but mark status=cancelled

## Do Not Implement Yet

- RunReceipt for `cancelled` status — v0.1 includes it, but only `completed` and `failed` are primary
- Receipt diff (compare two receipts) — v0.2
- Receipt gallery UI — v0.2
