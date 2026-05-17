# 11 — Runtime Capabilities

## Existing Implementation

**Capabilities model:** `python/src/agent_runtime_cockpit/protocol/capabilities.py` (83 lines) [EXISTS]

```python
class RuntimeCapabilities(BaseModel):
    schema_version: int = 1
    support_level: SupportLevel
    execution_modes: list[ExecutionMode]
    adoption_modes: list[str]
    audit_level: AuditLevel
    hitl_level: HitlLevel
    can_inspect: bool = False
    can_run: bool = False
    can_export_schema: bool = False
    can_export_workflow: bool = False
    can_trace: bool = False
    can_replay: bool = False
    can_stream_events: bool = False
    can_audit: bool = False
    can_checkpoint: bool = False
    can_resume: bool = False
    can_fork: bool = False
    can_diff: bool = False
    can_eval: bool = False
    requires_paid_calls: bool = False
    requires_network: bool = False
    requires_shell: bool = False
    requires_secrets: bool = False
```

**Runtime endpoint:** `GET /api/runtimes` → `runtime_capabilities()` in `web/routes.py`
**TypeScript interface:** `RuntimeCapabilityReport` in `packages/arc-extension/src/common/arc-protocol.ts`
**Adapter interface:** `RuntimeAdapter.capabilities()` returns `RuntimeCapabilities`

## What To Add

### Capability Negotiation

Add a negotiation layer that answers: "Can runtime X execute workflow Y with constraints Z?"

**Create file:** `python/src/agent_runtime_cockpit/orchestration/capability_negotiation.py`

```python
class CapabilityNegotiation:
    """
    Negotiates whether a runtime can execute a workflow given constraints.
    Returns a resolution with required actions (install, configure, approve).
    """

    def resolve(
        self,
        workflow: WorkflowInfo,
        runtime_caps: RuntimeCapabilities,
        constraints: list[str],
    ) -> NegotiationResult:
        ...

class NegotiationResult(BaseModel):
    can_run: bool
    missing_capabilities: list[str]
    required_actions: list[str]  # "Set env var X", "Approve paid calls"
    cost_estimate: str | None
```

### Capability Report with Status

Extend `CapabilityReport` (already in `adapters/base.py:35`) to add:

```python
class CapabilityReport(BaseModel):
    runtime_id: str
    detected: bool
    can_run: bool
    availability: RuntimeAvailability
    reason: str
    detected_artifacts: list[str]
    required_env: list[str]
    version: str | None
    requires_paid_calls: bool
    doctor_actions: list[DoctorAction]
    # NEW:
    can_emit_contract: bool = False
    can_emit_receipt: bool = False
    can_emit_autopsy: bool = False
    can_emit_evidence: bool = False
```

### Capability Snapshots at Runtime Switch

When a user switches runtime (via `/runtime` or Config tab), the system should:

1. Get capabilities of new runtime
2. Compare with capabilities of old runtime
3. Show a diff: "SwarmGraph can do X, Y, Z; LangGraph adds A but lacks B"
4. If new runtime lacks required capabilities, warn before switching

### TrustDiff Integration

When capabilities change (runtime switch, policy change, trust change), generate a `TrustDiff`:

```typescript
interface TrustDiff {
  diffId: string;
  before: string[];   // Previous capabilities
  after: string[];    // New capabilities
  addedCapabilities: string[];
  removedRestrictions: string[];
  affectedRuntimes: string[];
  requiresConfirmation: boolean;
}
```

### Entry Points to Extend

| File | What to Change |
|------|----------------|
| `protocol/capabilities.py` | Add negotiation fields (can_emit_* flags) |
| `orchestration/runtime_router.py` | Add capability diff on runtime switch |
| `security/trust.py` | Compute TrustDiff from capability changes |
| `adapters/base.py` | Extend `CapabilityReport` with negotiation fields |
| `adapters/swarmgraph.py` | SwarmGraph claims contract/receipt/autopsy/evidence support |
| `cli/slash_commands.py` | Show capability diff on `/runtime` switch |
| `web/routes.py` | Add `GET /api/runtimes/{id}/resolve` endpoint |

## Example: SwarmGraph Capability Report

```json
{
  "runtimeId": "swarmgraph",
  "supportLevel": "stable",
  "executionModes": ["direct", "background"],
  "canRun": true,
  "canInspect": true,
  "canTrace": true,
  "canCheckpoint": true,
  "canEmitContract": true,
  "canEmitReceipt": true,
  "canEmitAutopsy": true,
  "canEmitEvidence": true,
  "requiresPaidCalls": false,
  "doctorActions": [{"id": "check_cli", "label": "Check swarmgraph CLI"}]
}
```

## Acceptance Criteria

- [ ] `GET /api/runtimes` returns capabilities for all runtimes
- [ ] Capability report includes v0.1 cockpit primitive flags (`can_emit_*`)
- [ ] Runtime switch shows capability diff
- [ ] TrustDiff generated when capabilities change
- [ ] Frontend renders capability status per runtime
- [ ] All tests pass

## Do Not Implement Yet

- Suggestion-based runtime switching (router) — v0.2 [RESERVED]
- Runtime conformance tests — v0.2
- Runtime marketplace — v0.3+
- Manifest format per runtime — v0.2 [RESERVED]
