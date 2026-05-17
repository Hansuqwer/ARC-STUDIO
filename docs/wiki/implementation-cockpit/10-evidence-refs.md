# 10 — Evidence Refs

## Summary

EvidenceRefs are lightweight citations that attach to chat messages, failures, graph nodes, receipts, and ledger rows. They enable cross-surface linking: "this fact is backed by this tool output" or "this failure is linked to this graph node."

**Spec:** `ARC_STUDIO_UX_SPEC.md:1145`
**Status:** [MISSING] — zero code, spec only

## Schema

**Create file:** `python/src/agent_runtime_cockpit/protocol/evidence_refs.py`

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class EvidenceRef(BaseModel):
    evidence_id: str
    kind: Literal['file', 'tool_output', 'run', 'node', 'ledger', 'receipt', 'frame_receipt']
    target: str           # URI/path to the evidence
    range: Optional[list[int]] = None  # [start, end] line range for file/tool_output
    redacted: bool = False
```

## Where EvidenceRefs Attach

| Surface | Attached to |
|---------|-------------|
| Chat messages | `message.evidence_refs` |
| Run failures | `failure_autopsy.evidence_refs` |
| Graph nodes | `graph_node.evidence_refs` |
| Run receipts | `run_receipt.evidence_refs` |
| Ledger entries | `audit_record.evidence_refs` (v0.2) |
| Frame receipts | `frame_receipt.evidence_refs` (v0.2 HotLoop) |

## Validation Rules

1. Invalid evidence refs are **stripped server-side** before rendering
2. v0.1 renders only `file` and `tool_output` kinds
3. Unsupported-claim downgrading is reserved for v0.2
4. `frame_receipt` kind is recognized but not rendered in v0.1

## Entry Points to Extend

| File | What to Change |
|------|----------------|
| `protocol/schemas.py` | Add `evidence_refs: list[EvidenceRef]` to `RunEvent` |
| `protocol/events.py` | Add `EVIDENCE_REF_CREATED` event type |
| `protocol/run_receipt.py` | `RunReceipt.evidence_refs` field |
| `protocol/failure_autopsy.py` | `FailureAutopsy.evidence_refs` field |
| `web/routes.py` | Add `GET /api/evidence/{id}` endpoint |
| `adapters/base.py` | Adapters can optionally emit evidence refs |
| `security/redaction.py` | Redact evidence targets if they contain secrets |

## Example Payloads

**File evidence:**
```json
{
  "evidenceId": "ev_001",
  "kind": "file",
  "target": "src/workflow.py",
  "range": [42, 56]
}
```

**Tool output evidence:**
```json
{
  "evidenceId": "ev_002",
  "kind": "tool_output",
  "target": "run_01HQ3WN.../events/3",
  "range": [0, 100]
}
```

**Run evidence:**
```json
{
  "evidenceId": "ev_003",
  "kind": "run",
  "target": "run_01HQ3WNOPQR456STU789VWX012"
}
```

**Node evidence:**
```json
{
  "evidenceId": "ev_004",
  "kind": "node",
  "target": "reviewer_001"
}
```

## Frontend Component

**Create file:** `packages/arc-extension/src/browser/components/EvidenceChip.tsx`

```typescript
interface EvidenceChipProps {
  ref: EvidenceRef;
  onOpen: (ref: EvidenceRef) => void;
}
```

**Rendering:**
- File → filename icon + path (truncated)
- Tool output → terminal icon + event summary
- Run → `#` icon + run ID (truncated)
- Node → node icon + node name
- Ledger → ledger icon + audit entry ref
- Receipt → receipt icon + receipt ID

**Keyboard:** Enter/click opens the evidence target. File opens in Theia editor at line range. Tool output opens event detail.

## Cross-Highlighting (v0.1 baseline)

1. Selecting a graph node → highlight related evidence chips in Chat
2. Clicking an evidence chip → navigate to the target (file in editor, run in Runs tab)
3. Evidence Ref counter shown on graph node (`{N} evidence`)
4. Evidence chips in receipts are clickable

## Backend TypeScript Interface

Add to `packages/arc-extension/src/common/arc-protocol.ts`:

```typescript
interface EvidenceRef {
  evidenceId: string;
  kind: 'file' | 'tool_output' | 'run' | 'node' | 'ledger' | 'receipt' | 'frame_receipt';
  target: string;
  range?: [number, number];
  redacted?: boolean;
}
```

## Acceptance Criteria

- [ ] EvidenceRef can attach to chat messages
- [ ] EvidenceRef can attach to FailureAutopsy
- [ ] EvidenceRef can attach to RunReceipt
- [ ] Invalid refs stripped server-side
- [ ] `EvidenceChip` renders `file` and `tool_output` in v0.1
- [ ] Cross-highlighting: clicking evidence highlights target
- [ ] All tests pass

## Do Not Implement Yet

- Ledger evidence rendering — v0.2
- Unsupported-claim downgrading — v0.2
- `frame_receipt` rendering — v0.2 HotLoop [RESERVED]
- `@symbol` and `@url` mention evidence — v0.2/v0.3
