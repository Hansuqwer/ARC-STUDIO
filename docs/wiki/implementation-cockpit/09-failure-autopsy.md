# 09 — Failure Autopsy

## Summary

The FailureAutopsy is a structured diagnosis for failed runs. It replaces the raw trace-first UX with a bounded "knows vs guesses" summary, making failures actionable without requiring the user to read raw event JSON.

**Spec:** `ARC_STUDIO_UX_SPEC.md:1392`
**Status:** [MISSING] — zero code, spec only

## Schema

**Create file:** `python/src/agent_runtime_cockpit/protocol/failure_autopsy.py`

```python
from pydantic import BaseModel, Field
from typing import Literal, Optional

class RetryOption(BaseModel):
    label: str
    command: Optional[str] = None
    risk: Literal['low', 'medium', 'high']

class FailureAutopsy(BaseModel):
    run_id: str
    probable_cause: str = 'unknown'       # Best guess at root cause
    confidence: Literal['high', 'medium', 'low', 'unknown'] = 'unknown'
    failed_node: Optional[str] = None      # Which graph node failed
    last_safe_state: Optional[str] = None  # Last known good state
    retry_options: list[RetryOption] = Field(default_factory=list)
    related_issues: list[str] = Field(default_factory=list)
    knows: list[str] = Field(default_factory=list)    # Facts with evidence
    guesses: list[str] = Field(default_factory=list)  # Hypotheses
    evidence_refs: list[dict] = Field(default_factory=list)
```

## Generation Strategy

FailureAutopsy is generated in `JobSupervisor._execute_run()` when the run transitions to `FAILED`:

```python
# In supervisor.py, _execute_run catch block:
except Exception as e:
    run.supervisor_phase = "failing"
    autopsy = self._generate_autopsy(run, e)
    run.metadata['failure_autopsy'] = autopsy.model_dump()
```

The generation method analyzes:
1. **Last events** — Check the last 5-20 events for error signals
2. **Node state** — Find the last RUNNING/Waiting node before failure
3. **Error message** — Parse redacted error for known patterns
4. **Tool results** — Check if a tool call returned an error
5. **Knows vs Guesses** — Direct evidence goes in `knows`, inferences go in `guesses`

```python
def _generate_autopsy(self, run: RunRecord, error: Exception) -> FailureAutopsy:
    # 1. Get events from supervisor.store
    # 2. Scan backwards for failed node
    # 3. Check error_detail, last few events, tool outputs
    # 4. Build knows (from direct evidence) and guesses (from inference)
    # 5. Generate retry options
    return FailureAutopsy(...)
```

## Entry Points to Extend

| File | What to Change |
|------|----------------|
| `orchestration/supervisor.py` | Add `_generate_autopsy()` method; call on FAILED transition |
| `protocol/events.py` | Add `FAILURE_AUTOPSY_GENERATED` event type |
| `web/routes.py` | Add `GET /api/runs/{id}/autopsy` endpoint |
| `storage/jsonl.py` | Autopsy stored in `run.metadata['failure_autopsy']` |
| `cli/slash_commands.py` | Show autopsy on `/runs` with failed runs |
| `cli/chat_repl.py` | Render `FailureCard` on run failure |

## Example Payload

```json
{
  "runId": "run_01HQ3WNOPQR456STU789VWX012",
  "probableCause": "Tool execution timeout at node 'reviewer'",
  "confidence": "high",
  "failedNode": "reviewer",
  "lastSafeState": "worker 'writer' completed at T+12.4s",
  "retryOptions": [
    {"label": "Retry with same input", "risk": "low"},
    {"label": "Retry with timeout=600s", "command": "arc run --timeout 600", "risk": "low"},
    {"label": "Open in diagnostic mode", "risk": "medium"}
  ],
  "knows": [
    "Node 'reviewer' was active for 45.2s before failure",
    "Event 'TOOL_CALL_SEARCH' started at T+15.3s, never completed",
    "No network policy blocks detected"
  ],
  "guesses": [
    "Search tool may be rate-limited by external API",
    "Search query may match too many results (>10K)",
    "Reviewer node may have infinite loop in consensus logic"
  ],
  "evidenceRefs": [
    {"evidenceId": "ev_002", "kind": "tool_output", "target": "run_01.../events/3"},
    {"evidenceId": "ev_003", "kind": "node", "target": "reviewer"}
  ]
}
```

## Frontend Component

**Create or reuse** from `ARC_STUDIO_UX_SPEC.md:1378`:

```typescript
interface FailureCardProps {
  runSummary: RunSummary;
  autopsy?: FailureAutopsy;
  lastEvents: Array<{ type: string; timestamp: string; summary: string }>;
  maxEvents?: number;  // Default: 5, configurable: 3-20
  costUsd?: number | 'unknown';
  onRetry: () => void;
  onOpenDoctor: () => void;
  onOpenAdvancedTrace: () => void;
}
```

**Rendering:**
- Show `probableCause` in state.danger card header
- Show `confidence` badge
- Knows section with checkmarks
- Guesses section with question marks
- Retry options as buttons
- EvidenceRefs as clickable chips
- Expandable "Show me what happened" with last N redacted events

**Copy:** `Run failed at {failureNode}: {failureReason}. Retry, run diagnostics, open receipt, or open the advanced trace.`

## Acceptance Criteria

- [ ] Autopsy generated on every failed run
- [ ] `knows` vs `guesses` distinction is preserved and rendered
- [ ] Rendered in `FailureCard` in Chat and Runs panel
- [ ] Links to EvidenceRefs
- [ ] Retry options include at least "Retry with same input"
- [ ] Last N events are redacted before display
- [ ] Low-confidence causes render as `unknown` plus evidence links
- [ ] All tests pass

## Do Not Implement Yet

- Autopsy for `cancelled` runs (by definition not a failure) — not needed
- Autopsy comparison (compare two failures) — v0.2
- LLM-based autopsy (try harder to explain) — v0.2
- Auto-retry based on autopsy recommendations — v0.2
