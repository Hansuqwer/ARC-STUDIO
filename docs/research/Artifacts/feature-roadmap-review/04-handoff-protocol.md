# Handoff Protocol Review

## Current ARC Spec

### What Exists Today

**Reserved in v0.1 protocol** (§0.5, Appendix B of ARC_STUDIO_UX_SPEC.md):

| Reservation | Status |
|---|---|
| `handoff` event kind | Reserved. No v0.1 runtime emits it. |
| Payload shape | `handoff_version`, `from_runtime`, `to_runtime`, `goal_for_next_phase`, `state`, `constraints`, `references`, `prior_audit_links`, `created_at`, `session_id`, `run_id` |
| Versioning | `handoff_version: 1`. Unknown major is rejected. |
| Redaction | Payload is redacted before logging or SSE display. |
| Session inclusion | Included in session transcript but marked reserved. |

**UI reservations** (§7.17, §8.11, §9 HandoffCard, §10.7, §14.6):

- CLI: Phase boundary card with `[Continue] [Edit handoff] [Cancel]`
- IDE: Modal sheet by default; non-modal chat card when `planner.auto_advance=true`
- HandoffCard component: `fromRuntime`, `toRuntime`, `goal`, `stateKeysCarriedOver`, `constraints`, `references`, `priorAuditLinks`, `onConfirm`, `onEdit`, `onCancel`
- Microcopy: `Phase {n} done. Next: {title} on {runtime}. Carrying: {summary}. Continue?`
- Accessibility: Required focus stop; Esc cancels; Enter confirms; Edit Handoff reachable before Confirm

**What already uses the word "handoff" in the codebase:**

| File | What it does | Relation to spec |
|---|---|---|
| `adapters/swarmgraph/mapping.py:44` | Maps SwarmGraph native `kind: handoff` to AG-UI `STEP_STARTED` with `stepName: handoff:<agent>` | **Intra-runtime** agent-to-agent handoff within SwarmGraph. NOT the phase-boundary handoff from the spec. |
| `adapters/openai_agents/mapping/openai_agents.py:38` | Maps OpenAI Agents `kind: handoff` to AG-UI `STEP_STARTED` with `stepName: handoff:<from>-><to>` | **Intra-runtime** agent delegation within OpenAI Agents SDK. NOT phase-boundary. |
| `ag_ui/__init__.py:38` | `AGUIEventType.HANDOFF` enum value | Exists but no mapper emits it; SwarmGraph/OpenAI mappers emit `STEP_STARTED` instead. |
| `protocol/events.py:110` | `HANDOFF` event type with `from_agent`/`to_agent` required fields | Registry entry for intra-runtime handoff. No phase-boundary fields. |
| `packages/arc-ag-ui/src/mapping/swarmgraph.ts:27` | Same as Python: maps `kind: handoff` to `STEP_STARTED` | TypeScript parity with Python mapper. |

**Critical distinction:** The codebase has two different concepts both called "handoff":

1. **Intra-runtime handoff** (already implemented): Agent A delegates to Agent B within the same runtime (SwarmGraph queen→worker, OpenAI Agents agent→agent). Mapped to `STEP_STARTED` in AG-UI.
2. **Inter-runtime phase-boundary handoff** (reserved v0.2): Runtime A finishes a phase and transfers state to Runtime B (SwarmGraph→HotLoop, SwarmGraph→LangGraph). Reserved in spec Appendix B. No implementation exists.

### What Does NOT Exist

- No `Planner` component or multi-phase plan model
- No `Router` component or runtime-suggestion logic
- No `HotLoop` runtime or adapter
- No phase-boundary event type in the event registry (only intra-runtime `HANDOFF`)
- No `HandoffPayload` Pydantic model matching Appendix B
- No handoff persistence, editing, or confirmation flow
- No phase transition UI in CLI or IDE
- No `planner.auto_advance` config
- No Tasks panel Phase view or Loop trace view

### Summary

The spec reserves the handoff event and payload shape in v0.1, deferring all behavior to v0.2. The existing codebase implements intra-runtime agent handoff (a different concept) but has zero code for the phase-boundary handoff described in the spec. This is correct for v0.1 scope but creates naming ambiguity that must be resolved before v0.2.

---

## Comparable Products / Research

### Terminology Clarification

"Handoff" means different things across products. This review distinguishes:

| Type | Meaning | ARC equivalent |
|---|---|---|
| Agent delegation | One agent transfers control to another within the same runtime | Intra-runtime handoff (already implemented) |
| Phase/state transfer | One runtime phase completes and transfers state to the next | **Inter-runtime handoff** (this review's scope) |
| Checkpoint/resume | Workflow state is saved and can be resumed from a point | Related but different; checkpoint is within a single runtime |
| Signal/message | External event injected into a running workflow | Related to HITL, not handoff |

### Product Comparison

| Product | Phase Handoff | Checkpoint/State Transfer | Agent Delegation | Audit Links | User-Editable State | Versioning | Redaction |
|---|---|---|---|---|---|---|---|
| **ARC Studio (spec)** | Reserved v0.2: explicit `handoff` event with typed payload between runtimes | JSONL traces + SQLite index; replay exists (P2); deterministic replay scoped behind runtime support | Intra-runtime: SwarmGraph queen→worker, OpenAI Agents agent→agent | `prior_audit_links` in handoff payload; HMAC audit chain (P2-P4) | `[Edit handoff]` action in UI (reserved) | `handoff_version` with major-version rejection | Redaction contract (§10.10) applies to handoff payload |
| **LangGraph Studio** | No explicit phase handoff. Graph nodes execute sequentially or conditionally. State passes through `StateGraph` channels. | Checkpoints via `BaseCheckpointSaver` (SQLite, Postgres, Redis). Time-travel replay from any checkpoint. State can be forked/edited before replay. | No native agent delegation. Multi-agent patterns are user-implemented via graph structure. | No built-in audit chain. Checkpoint ID provides traceability but no cryptographic signing. | State can be edited in Studio before replay. No explicit "handoff document" concept. | Graph/state schema versioning is user-managed. No built-in version field. | No built-in redaction. Secrets in state are visible in Studio. |
| **Temporal** | No phase handoff between different runtimes. Workflows are single-runtime. | Workflow state is durable by design. `ContinueAsNew` transfers state to a fresh workflow execution. Signals/queries provide external communication. | No agent concept. Child workflows provide delegation-like patterns. | Workflow execution history is immutable and auditable. No cryptographic signing. | Workflow state is not user-editable during execution. Signals can inject data. | Workflow type/version managed via `GetVersion()` API for backward-compatible changes. | No built-in redaction. Payloads visible in Temporal UI. |
| **MCP (Model Context Protocol)** | No phase handoff. MCP is a tool-calling protocol, not a workflow orchestrator. | No state persistence. Each tool call is stateless unless the tool implements its own state. | Agent-to-agent delegation is out of scope. MCP connects tools to agents, not agents to agents. | No audit. Tool call logging is implementation-specific. | N/A | Protocol versioning via `protocolVersion` negotiation. | Redaction is implementation-specific. MCP spec does not mandate it. |
| **ACP (Agent Client Protocol)** | Draft spec includes agent-to-agent message passing. Phase handoff not defined. | Session state managed per agent. Cross-agent state transfer is message-based. | Core concept: agents delegate tasks via structured messages. | Audit trail via message IDs and session correlation. No cryptographic signing. | Message content can be user-inspected but not typically edited mid-flow. | Protocol versioning. Message schema versioning is TBD. | Redaction is implementation-specific. |
| **Claude Code** | No phase handoff. Single-runtime (Claude) execution. | Session history persisted. Resume/continue/fork supported. No checkpoint-based replay. | Sub-agent delegation via "task" mode. Sub-agent results return to parent. | No audit chain. Conversation history provides traceability. | User can edit conversation context. No explicit handoff document. | No versioning. | Secrets in conversation are not redacted in history. |
| **CrewAI** | No phase handoff between runtimes. Tasks execute sequentially within a crew. | No checkpoint/replay. Task outputs are stored but not resumable. | Agent-to-agent task delegation is the core pattern. Crew = agents + tasks. | No audit chain. Task execution logs provide traceability. | Task inputs/outputs are not user-editable mid-run. | No versioning. | No built-in redaction. |
| **OpenAI Agents SDK** | No phase handoff. Single-runtime execution. | No checkpoint. Conversation history is the state. | Native `handoff()` API: agent delegates to another agent. This is what ARC's intra-runtime handoff maps. | No audit chain. Trace events provide observability. | No user-editable handoff. | SDK versioning, no handoff versioning. | No built-in redaction. |

### Key Observations

1. **No product implements inter-runtime phase handoff as a first-class concept.** ARC Studio's handoff protocol is novel in this space. LangGraph Studio's checkpoint+fork is the closest analog but is intra-runtime only.

2. **LangGraph Studio's checkpoint editing is the closest UX pattern.** Users can edit state at any checkpoint and replay forward. ARC's `[Edit handoff]` action is conceptually similar but operates at phase boundaries rather than arbitrary checkpoints.

3. **Temporal's `ContinueAsNew` is the closest architectural pattern.** It explicitly transfers state from one workflow execution to a new one, with versioning and backward compatibility. However, it's same-runtime, not cross-runtime.

4. **OpenAI Agents SDK's `handoff()` is what ARC already maps.** This is intra-runtime agent delegation, not the phase-boundary handoff ARC reserves. The naming collision must be addressed.

5. **No product has cryptographic audit links in state transfer.** ARC's `prior_audit_links` field is unique and aligns with the high-assurance positioning.

6. **No product has explicit redaction of handoff/state transfer data.** ARC's redaction contract is more rigorous than any competitor examined.

---

## Gaps

### Naming Ambiguity (Critical)

**Problem:** The codebase uses "handoff" for two different concepts:
- Intra-runtime: `kind: handoff` in SwarmGraph/OpenAI Agents mappers → `STEP_STARTED`
- Inter-runtime: Reserved `event_type: handoff` in Appendix B spec → phase boundary transfer

**Impact:** When v0.2 implementation begins, developers will confuse the two. The event registry already has `HANDOFF` with `from_agent`/`to_agent` fields, which describes intra-runtime delegation, not phase-boundary transfer.

**Severity:** High. Must resolve before v0.2 code is written.

### Missing Event Type for Phase-Boundary Handoff

**Problem:** The event registry (`protocol/events.py`) has `HANDOFF` for intra-runtime agent delegation. There is no event type for the phase-boundary handoff described in Appendix B.

**Impact:** The reserved payload shape has no corresponding event type definition. When v0.2 arrives, the event registry needs a new type (e.g., `PHASE_HANDOFF` or `HANDOFF_V2`).

**Severity:** High. Blocks v0.2 implementation.

### No HandoffPayload Pydantic Model

**Problem:** Appendix B defines a YAML payload shape but there is no corresponding Pydantic model in `protocol/schemas.py` or anywhere else.

**Impact:** No validation, no type safety, no JSON schema generation for the handoff payload.

**Severity:** Medium. Easy to add but must be done before v0.2.

### State Field Is Untyped

**Problem:** The `state` field in Appendix B is `object`. This is too loose. Different runtimes will produce different state shapes, and the next runtime needs to know what to expect.

**Impact:** Without a typed or at least schema-annotated state field, the receiving runtime must guess at structure. This is fragile and error-prone.

**Severity:** Medium. Needs design decision before v0.2.

### No Handoff Persistence Model

**Problem:** The spec says handoff events are "included in session transcript" but there is no dedicated persistence model for handoff documents. If a handoff is edited, where is the edited version stored?

**Impact:** Without persistence, edited handoffs are lost on session resume. The `[Edit handoff]` action has no backing store.

**Severity:** Medium. Needs design before v0.2.

### Missing Error Recovery Path

**Problem:** The spec shows `[Continue] [Edit handoff] [Cancel]` but does not define what happens when:
- The receiving runtime rejects the handoff payload
- The handoff payload is malformed or version-incompatible
- The receiving runtime is unavailable
- The handoff times out

**Impact:** No recovery strategy for failed handoffs. This is critical for multi-phase plans where a failed handoff blocks the entire pipeline.

**Severity:** High. Must be defined before v0.2.

### No Handoff Validation/Schema Negotiation

**Problem:** The spec does not define how the receiving runtime validates the incoming handoff payload. Does HotLoop declare what state keys it expects? Does SwarmGraph validate that its output matches HotLoop's input schema?

**Impact:** Without schema negotiation or validation, handoffs will fail silently or produce confusing runtime errors.

**Severity:** Medium-High.

### Redaction Scope Is Undefined for Handoff

**Problem:** §10.10 defines a general redaction contract but does not specify which handoff fields are redacted. `state` likely contains file paths and code snippets. `references` may contain URLs with tokens. `prior_audit_links` may contain file paths.

**Impact:** Redaction may be over-applied (making handoff unreadable) or under-applied (leaking secrets).

**Severity:** Medium.

### Auto-Advance Behavior Is Under-Specified

**Problem:** §7.17 says `planner.auto_advance=true` makes the phase boundary "non-modal but still visible" but does not define:
- What happens if auto-advance is on but the handoff is invalid?
- Does auto-advance skip the `[Edit handoff]` option?
- Can auto-advance be configured per-phase or is it global?

**Impact:** Ambiguous behavior for a safety-relevant feature.

**Severity:** Medium.

### No Handoff Metrics/Observability

**Problem:** No metrics for handoff success rate, duration, edit frequency, or failure reasons.

**Impact:** Cannot debug handoff issues or measure adoption of multi-phase plans.

**Severity:** Low for v0.2, Medium for v0.3.

### TypeScript Protocol Types Missing Handoff

**Problem:** `arc-protocol-types.ts` has no handoff-related types. The `RunEvent` type is generic and would accept a handoff event, but there is no typed `HandoffPayload` interface.

**Impact:** TypeScript frontend has no type safety for handoff rendering.

**Severity:** Medium. Easy to add but must be done before v0.2 UI work.

---

## Improvement Proposals

| Proposal | Why | v0.1/v0.2/v0.3 | Risk | Spec edits |
|---|---|---|---|---|
| **Rename intra-runtime handoff to `agent_delegation`** | Eliminates naming collision. `HANDOFF` event type becomes exclusively phase-boundary. Current mappers emit `STEP_STARTED` already, so the rename is internal to event registry and mapper comments. | v0.2 (before handoff implementation) | Low. Mappers already emit `STEP_STARTED`, not `HANDOFF`. Only the event registry entry and comments need updating. | §10.10: clarify that `agent_delegation` is intra-runtime, `handoff` is inter-runtime. |
| **Add `PHASE_HANDOFF` event type to registry** | Separate event type with phase-boundary fields: `from_runtime`, `to_runtime`, `goal_for_next_phase`, `state_schema`, `constraints`, `references`, `prior_audit_links`. Keeps `HANDOFF` for intra-runtime delegation. | v0.2 | Low. Additive change to event registry. | Appendix B: update to reference `PHASE_HANDOFF` event type. `protocol/events.py`: add new entry. |
| **Add `HandoffPayload` Pydantic model** | Type-safe payload with validation. Include `handoff_version`, `from_runtime`, `to_runtime`, `goal_for_next_phase`, `state` (with `state_schema` hint), `constraints`, `references`, `prior_audit_links`, `created_at`, `session_id`, `run_id`. | v0.2 | Low. Standard Pydantic model. | Appendix B: reference the Pydantic model as canonical definition. |
| **Add `state_schema` field to handoff payload** | Receiving runtime needs to know what shape `state` has. Add `state_schema: str` (a URI or schema name) or `state_schema: dict` (inline JSON Schema). Enables validation at phase boundary. | v0.2 | Medium. Requires each runtime to declare its output schema. Lowers handoff failure rate. | Appendix B: add `state_schema` field. §7.17: show schema validation in phase boundary card. |
| **Define handoff rejection/recovery flow** | When receiving runtime rejects handoff, the system needs a defined recovery path. Options: (a) retry with modified state, (b) fall back to previous runtime, (c) pause for user intervention, (d) abort plan. | v0.2 | Medium. Recovery flow adds complexity but is essential for reliability. | §7.17: add error state card with recovery options. §15: add handoff error states. |
| **Define handoff persistence in session store** | Store handoff documents in session directory (`~/.arc/sessions/<id>/handoffs/`). Each handoff is a JSON file with ULID name. Edited handoffs create new files with `original_handoff_id` reference. | v0.2 | Low. File-based persistence is simple and aligns with session architecture. | §7.14.1: add handoff storage path. Appendix B: add persistence note. |
| **Define redaction rules per handoff field** | `state`: redact secret-like values using existing redactor. `references`: redact URL tokens. `prior_audit_links`: no redaction (file paths are safe). `constraints`: no redaction. `goal_for_next_phase`: no redaction. | v0.2 | Low. Extends existing redaction contract. | §10.10: add handoff-specific redaction rules. |
| **Add handoff validation endpoint** | Python daemon exposes `POST /api/handoff/validate` that checks payload against receiving runtime's expected schema. Returns validation errors before phase advance. | v0.2 | Medium. Requires each runtime to declare input schema. | New section in spec for handoff API. |
| **Make auto_advance per-phase, not global** | `planner.auto_advance` as a boolean is too coarse. Make it `planner.auto_advance: "none" | "all" | "safe-only"`. `safe-only` auto-advances only when handoff validation passes. | v0.2 | Low. Config change is additive. | §7.17: update auto_advance copy. §8.6: add auto_advance config options. |
| **Add handoff observability events** | Emit `HANDOFF_STARTED`, `HANDOFF_COMPLETED`, `HANDOFF_FAILED`, `HANDOFF_EDITED` events. Include duration, validation result, edit count. | v0.3 | Low. Additive event types. | `protocol/events.py`: add handoff lifecycle events. |
| **Add handoff diff view** | When user edits handoff, show diff between original and edited payload. Similar to existing diff review flow. | v0.3 | Medium. Requires diff component reuse for JSON. | §9: add `HandoffDiff` component spec. |
| **Add handoff template library** | Pre-defined handoff templates for common phase transitions (SG→HL, SG→LG, LG→SG). Templates define expected state schema and constraints. | v0.3 | Medium. Template system adds maintenance burden. | New section for handoff templates. |

---

## Recommended Decisions

### Decision 1: Rename intra-runtime handoff to `agent_delegation` in event registry

**Rationale:** The naming collision between intra-runtime agent delegation (already implemented) and inter-runtime phase-boundary handoff (reserved v0.2) will cause implementation errors. The current mappers already emit `STEP_STARTED` for intra-runtime handoffs, so the `HANDOFF` event type in the registry is unused in practice. Rename it to `AGENT_DELEGATION` and reserve `HANDOFF` (or `PHASE_HANDOFF`) for the phase-boundary concept.

**Action:** Update `protocol/events.py` and `ag_ui/__init__.py` before v0.2.

### Decision 2: Use `PHASE_HANDOFF` as the event type name for phase-boundary handoff

**Rationale:** Explicit is better than implicit. `PHASE_HANDOFF` clearly distinguishes from `AGENT_DELEGATION` (intra-runtime) and matches the spec's phase-boundary concept. The Appendix B payload maps directly to this event type's data field.

**Action:** Add to `protocol/events.py` and `ag_ui/__init__.py` in v0.2.

### Decision 3: Add `state_schema` field to handoff payload

**Rationale:** Without a schema hint, the receiving runtime cannot validate incoming state. This is the single biggest reliability risk for multi-phase plans. The `state_schema` field can be a simple string identifier (e.g., `"hotloop:v1:react-ui-state"`) or an inline JSON Schema for complex cases. Start with string identifiers; add inline schema support in v0.3 if needed.

**Action:** Update Appendix B payload shape. Add to `HandoffPayload` Pydantic model.

### Decision 4: Handoff persistence in session directory

**Rationale:** The session architecture (§7.14.1) already defines a per-session directory structure. Handoff documents belong there. Each handoff is a JSON file. Edited handoffs create new files with back-references. This is simple, crash-safe, and aligns with the existing session lifecycle.

**Action:** Define in v0.2 session architecture. No spec edit needed beyond §7.14.1.

### Decision 5: Failed handoff recovery = pause for user intervention

**Rationale:** When a handoff fails (validation error, runtime unavailable, version mismatch), the safest default is to pause and show the user the failure with recovery options. Auto-retry is dangerous (may loop). Auto-abort is too aggressive. Pausing aligns with the spec's default modal behavior at phase boundaries.

Recovery options: `[Edit handoff] [Retry] [Skip phase] [Abort plan]`

**Action:** Define in §7.17 error states and §15 edge cases.

### Decision 6: Handoff is visible to users by default

**Rationale:** The spec already defines this correctly. Phase boundaries are trust-critical moments where state crosses runtime boundaries. Users must see what is being transferred and have the option to edit or cancel. Auto-advance is an opt-in convenience, not the default.

**Action:** No change needed. Spec is correct.

### Decision 7: Users CAN edit handoff documents, but with constraints

**Rationale:** `[Edit handoff]` is in the spec and should be kept. However, editing should be constrained:
- `goal_for_next_phase`: editable (user may refine the goal)
- `state`: partially editable (user can add/remove keys but cannot break schema)
- `constraints`: editable (user may add constraints)
- `references`: editable (user may add/remove references)
- `prior_audit_links`: **not editable** (audit chain integrity)
- `from_runtime`, `to_runtime`, `handoff_version`: **not editable** (structural fields)

**Action:** Define editable vs locked fields in HandoffCard spec (§9).

### Decision 8: Redaction applies to `state` and `references` only

**Rationale:** `state` may contain secret-like values (API keys in env vars, tokens in URLs). `references` may contain URLs with auth tokens. Other fields (`goal`, `constraints`, `audit_links`) are user-facing text and should not be redacted. Apply the existing redaction contract (§10.10) to `state` values and `references` URLs.

**Action:** Update §10.10 with handoff-specific redaction rules.

---

## Specific Spec Edits

### Appendix B: Reserved Handoff Event Payload

**Current:**
```yaml
event_type: handoff
handoff_version: 1
from_runtime: swarmgraph
to_runtime: hotloop
goal_for_next_phase: string
state: object
constraints: string[]
references: string[]
prior_audit_links: string[]
created_at: iso8601
session_id: ulid
run_id: ulid | null
```

**Edit to:**
```yaml
event_type: PHASE_HANDOFF
handoff_version: 1
from_runtime: string        # e.g., "swarmgraph"
to_runtime: string          # e.g., "hotloop"
goal_for_next_phase: string
state_schema: string        # schema identifier for state validation (e.g., "hotloop:v1:react-ui-state")
state: object               # validated against state_schema by receiving runtime
constraints: string[]
references: string[]
prior_audit_links: string[] # immutable; not user-editable
created_at: iso8601
session_id: ulid
run_id: ulid | null
handoff_id: ulid            # unique identifier for this handoff document
```

**Add note:**
> `prior_audit_links`, `from_runtime`, `to_runtime`, `handoff_version`, and `handoff_id` are immutable and not user-editable via `[Edit handoff]`. All other fields are editable. Redaction applies to `state` values and `references` URLs per §10.10.

### §7.17: Handoff Transition

**Add error state card:**
```text
┌ handoff failed ─────────────────────────────────────────────────────────────────────────────────┤
│ HotLoop rejected handoff: state_schema mismatch.                                                │
│ Expected keys: [files, device_target]. Found: [files, constraints].                              │
│                                                                                                  │
│ [Edit handoff] [Retry] [Skip phase 2] [Abort plan]                                               │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

**Add copy for auto_advance modes:**
> `planner.auto_advance` accepts `"none"` (default, pause at every boundary), `"safe-only"` (auto-advance when validation passes, pause on failure), or `"all"` (auto-advance always, log failures). `"all"` is not recommended for paid-call runtimes.

### §8.11: Phase Transition Flow

**Add:**
> Handoff documents are persisted in the session directory at `~/.arc/sessions/<session_id>/handoffs/<handoff_id>.json`. Edited handoffs create new files with `original_handoff_id` field pointing to the original. The session transcript references handoff files by `handoff_id`.

### §9: HandoffCard Component

**Edit `HandoffCardProps`:**
```ts
interface HandoffCardProps {
  fromRuntime: string;
  toRuntime: string;
  goal: string;
  stateSchema: string;           // NEW
  stateKeysCarriedOver: string[];
  constraints: string[];
  references: string[];
  priorAuditLinks: string[];
  editableFields: Array<'goal' | 'state' | 'constraints' | 'references'>;  // NEW
  onConfirm: () => void;
  onEdit: (field: string, value: unknown) => void;   // CHANGED: field-specific
  onCancel: () => void;
  onRetry?: () => void;          // NEW
  onSkipPhase?: () => void;      // NEW
  onAbortPlan?: () => void;      // NEW
  error?: HandoffError;          // NEW
}

interface HandoffError {
  code: 'schema_mismatch' | 'runtime_unavailable' | 'version_incompatible' | 'timeout' | 'unknown';
  message: string;
  detail?: string;
}
```

### §10.7: Planner, Router, Handoff Copy

**Add error copy:**

| Surface | Exact copy |
|---|---|
| Handoff schema mismatch | `{runtime} rejected handoff: expected keys [{expected}], found [{found}]. Edit handoff or skip phase.` |
| Handoff runtime unavailable | `{runtime} is not available. {reason}. Retry, skip phase, or abort plan.` |
| Handoff version incompatible | `Handoff version {version} is not supported by {runtime}. Supported: {supported_versions}.` |
| Handoff timeout | `Handoff to {runtime} timed out after {seconds}s. Retry or abort.` |

### §10.10: Redaction Contract

**Add:**
> Handoff payloads are redacted before logging, SSE display, or UI rendering. Redaction applies to:
> - `state` values: apply the standard redactor (API keys, tokens, passwords, bearer tokens, cloud credentials)
> - `references` URLs: redact query-string tokens and auth segments
> - `prior_audit_links`: not redacted (file paths are safe)
> - `goal_for_next_phase`, `constraints`: not redacted (user-facing text)
>
> Redaction never modifies the persisted handoff document. Redaction is applied at display time only.

### §15: States And Edge Cases

**Add handoff row detail:**

| Surface | Empty | Loading | Populated | Error | Offline | Awaiting approval | Applied/Rolled back |
|---|---|---|---|---|---|---|---|
| Handoff | pending (no active phase boundary) | preparing (runtime serializing state) | confirmed (handoff accepted by receiving runtime) | failed (schema mismatch, runtime unavailable, version incompatible, timeout) | unavailable (daemon offline, cannot validate) | awaiting confirm (modal sheet or chat card) | completed (phase N+1 started) |

### `protocol/events.py`

**Add:**
```python
# ── Phase handoff (inter-runtime) ────────────────────────────────────────
"PHASE_HANDOFF": EventTypeDef(
    required_fields={"from_runtime", "to_runtime", "goal_for_next_phase", "state", "handoff_id"},
    optional_fields={"state_schema", "constraints", "references", "prior_audit_links"},
),
"PHASE_HANDOFF_COMPLETED": EventTypeDef(
    required_fields={"handoff_id", "to_runtime"},
    optional_fields={"duration_ms"},
),
"PHASE_HANDOFF_FAILED": EventTypeDef(
    required_fields={"handoff_id", "error"},
    optional_fields={"error_type", "recovery_options"},
),
```

**Rename existing:**
```python
# Change "HANDOFF" to "AGENT_DELEGATION" with a deprecation alias
"AGENT_DELEGATION": EventTypeDef(
    required_fields={"from_agent", "to_agent"},
    optional_fields=set(),
),
```

---

## Acceptance Criteria

### v0.2 Handoff Protocol

- [ ] `PHASE_HANDOFF` event type exists in Python event registry with correct required/optional fields
- [ ] `PHASE_HANDOFF` event type exists in AG-UI event types (Python and TypeScript)
- [ ] `HandoffPayload` Pydantic model exists with all Appendix B fields including `state_schema` and `handoff_id`
- [ ] `HandoffPayload` validates on creation; invalid payloads raise `ValueError`
- [ ] Intra-runtime handoff renamed to `AGENT_DELEGATION` in event registry (backward-compatible alias for `HANDOFF` during transition)
- [ ] SwarmGraph and OpenAI Agents mappers updated to reference `AGENT_DELEGATION` in comments (behavior unchanged: still emit `STEP_STARTED`)
- [ ] Handoff persistence: handoff documents saved to session directory as JSON files
- [ ] Handoff validation: receiving runtime can validate incoming state against `state_schema`
- [ ] Handoff rejection: failed handoffs produce `PHASE_HANDOFF_FAILED` event with error code and recovery options
- [ ] Handoff recovery: UI shows `[Edit handoff] [Retry] [Skip phase] [Abort plan]` on failure
- [ ] Handoff redaction: `state` values and `references` URLs are redacted in display; persisted document is unmodified
- [ ] Handoff immutability: `prior_audit_links`, `from_runtime`, `to_runtime`, `handoff_version`, `handoff_id` are not user-editable
- [ ] `HandoffCard` component renders with error states and recovery actions
- [ ] CLI phase boundary card renders with error states and recovery actions
- [ ] Auto-advance supports `"none"`, `"safe-only"`, `"all"` modes
- [ ] Handoff events are included in session transcript
- [ ] TypeScript `HandoffPayload` interface exists in `arc-protocol-types.ts`
- [ ] All handoff-related tests pass (payload validation, redaction, persistence, rejection/recovery)

### v0.2 Planner Integration (prerequisite for handoff)

- [ ] Planner emits multi-phase plans with runtime annotations
- [ ] Phase boundary triggers handoff creation
- [ ] Handoff confirmation advances to next phase
- [ ] Handoff cancellation aborts or pauses the plan

### v0.2 Router Integration (optional for handoff)

- [ ] Router can suggest runtime switches that trigger handoff
- [ ] Router suggestion card renders in Chat
- [ ] Accepting router suggestion creates handoff document

---

## Reject / Do Not Build

### Rejected: Unified "handoff" event type for both intra-runtime and inter-runtime

**Considered:** Using a single `HANDOFF` event type with a `scope` field (`"intra_runtime"` vs `"inter_runtime"`).

**Rejected because:** The two concepts have fundamentally different payload shapes, different consumers, and different lifecycle semantics. A unified type would require many optional fields and conditional validation, making the schema harder to understand and implement. Separate types are cleaner and prevent accidental misuse.

### Rejected: Automatic handoff state inference

**Considered:** Having the system automatically infer what state to carry over based on the receiving runtime's needs, without explicit `state_schema`.

**Rejected because:** Automatic inference is fragile and opaque. When it fails, users cannot debug why. Explicit `state_schema` makes the contract visible and debuggable. The spec's `[Edit handoff]` action requires the user to understand what is being transferred; automatic inference undermines this.

### Rejected: Handoff as a first-class run (separate run_id)

**Considered:** Treating each handoff as its own mini-run with a separate `run_id`, events, and lifecycle.

**Rejected because:** Handoffs are transitions between phases of the same session, not independent runs. Giving them separate run_ids would fragment the session timeline and complicate the Runs panel. Handoffs should be events within the session transcript, not top-level runs.

### Rejected: Cryptographic signing of handoff documents

**Considered:** Signing handoff payloads with HMAC to ensure integrity across phase boundaries.

**Rejected for v0.2:** The SwarmGraph HMAC audit chain (P2-P4) already provides cryptographic integrity for audit records. Adding separate signing for handoff documents doubles the key management burden. For v0.2, handoff integrity is ensured by:
1. Session-local storage (not network-transmitted)
2. `prior_audit_links` connecting to the signed audit chain
3. Immutability of structural fields

Cryptographic signing of handoff documents can be added in v0.3 if multi-machine or multi-user handoff becomes a requirement.

### Rejected: Handoff rollback (undo a completed handoff)

**Considered:** Allowing users to "undo" a completed handoff and return to the previous phase.

**Rejected for v0.2:** Rollback requires the previous runtime to be able to resume from the handoff point, which is runtime-specific and not universally supported. SwarmGraph may support it via checkpoint; HotLoop may not. For v0.2, the recovery path for a bad handoff is `[Edit handoff] [Retry] [Skip phase] [Abort plan]`. Rollback can be added in v0.3 for runtimes that support checkpoint-based resume.

### Rejected: Handoff templates as v0.2 scope

**Considered:** Pre-defined handoff templates for common phase transitions.

**Rejected for v0.2:** Templates require understanding of real-world handoff patterns, which we don't have yet. v0.2 should ship with the raw handoff mechanism and learn from usage. Templates are a v0.3 feature after we have data on common transitions.

### Do Not Build: Handoff between parallel phases

**Deferred to v0.3+:** The spec explicitly defers parallel phase execution to v0.3+. Handoff between parallel phases requires a fundamentally different model (fan-out/fan-in, merge semantics, conflict resolution). Do not design for this in v0.2.

### Do Not Build: Cross-machine handoff

**Deferred indefinitely:** ARC Studio is local-first. Handoff between runtimes on different machines requires network transport, authentication, and serialization that is out of scope for the product's positioning. If multi-machine becomes a requirement, it should be a separate feature with its own spec.
