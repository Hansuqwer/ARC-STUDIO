# ADR-004: Event Schema Versioning Contract

## Status
Proposed

## Context

ARC Studio has three overlapping event type systems:
1. **ARC internal events** (`RUN_STARTED`, `RUN_COMPLETED`, `NODE_STARTED`, etc.) — used by Python adapters
2. **AG-UI protocol events** (33 types: `RUN_STARTED`, `TEXT_MESSAGE_START`, `TOOL_CALL_START`, etc.) — used by frontend
3. **SwarmGraph internal events** — emitted by vendored runtime, mapped to ARC internal by adapter

Current problems:
- No schema version on events — breaking changes would silently corrupt old traces
- AG-UI bridge maps ARC internal → AG-UI types but has no version negotiation
- Adapters emit events directly without validation
- No compatibility guarantee between CLI, daemon, IDE, and adapters
- Trace parser handles multiple formats (single-line JSON, multi-line JSONL, LangGraph-style) but has no version awareness

## Decision

### Event Schema Versioning

All events carry a schema version:

```python
class RunEvent(BaseModel):
    schema_version: int = 1      # NEW: event schema version
    type: str                     # Event type string
    timestamp: str                # ISO 8601
    run_id: str                   # Parent run ID
    sequence: int                 # Ordering index (0-based)
    data: dict[str, Any]          # Event-specific payload
```

### Versioning Rules

1. **Version starts at 1** and increments on breaking changes
2. **Additive changes** (new event types, new optional fields in `data`) do NOT increment version
3. **Breaking changes** (renaming types, removing fields, changing required field semantics) DO increment version
4. **Readers must support at least the current and previous version** (N and N-1)
5. **Writers always emit the current version**
6. **Old traces retain their original version** — no migration needed

### Canonical Event Type Registry

Define a single registry of event types with versioned schemas:

```python
# Event type registry — single source of truth
EVENT_TYPES: dict[str, EventTypeDef] = {
    # Run lifecycle (v1)
    "RUN_STARTED": EventTypeDef(
        version=1,
        required_fields={"workflow_id", "runtime"},
        optional_fields={"profile_id", "isolation"},
    ),
    "RUN_COMPLETED": EventTypeDef(
        version=1,
        required_fields={"duration_ms"},
        optional_fields={"output"},
    ),
    "RUN_FAILED": EventTypeDef(
        version=1,
        required_fields={"error"},
        optional_fields={"error_detail"},
    ),
    "RUN_CANCELLED": EventTypeDef(
        version=1,
        required_fields={"cancel_reason"},
        optional_fields=set(),
    ),
    
    # Step lifecycle (v1)
    "STEP_STARTED": EventTypeDef(
        version=1,
        required_fields={"step_id", "step_name"},
        optional_fields={"step_type"},
    ),
    "STEP_COMPLETED": EventTypeDef(
        version=1,
        required_fields={"step_id"},
        optional_fields={"output", "duration_ms"},
    ),
    "STEP_FAILED": EventTypeDef(
        version=1,
        required_fields={"step_id", "error"},
        optional_fields=set(),
    ),
    
    # Text messages (v1)
    "TEXT_MESSAGE_START": EventTypeDef(
        version=1,
        required_fields={"message_id"},
        optional_fields={"role"},
    ),
    "TEXT_MESSAGE_CONTENT": EventTypeDef(
        version=1,
        required_fields={"message_id", "delta"},
        optional_fields=set(),
    ),
    "TEXT_MESSAGE_END": EventTypeDef(
        version=1,
        required_fields={"message_id"},
        optional_fields=set(),
    ),
    
    # Tool calls (v1)
    "TOOL_CALL_START": EventTypeDef(
        version=1,
        required_fields={"tool_call_id", "tool_name"},
        optional_fields=set(),
    ),
    "TOOL_CALL_ARGS": EventTypeDef(
        version=1,
        required_fields={"tool_call_id", "delta"},
        optional_fields=set(),
    ),
    "TOOL_CALL_END": EventTypeDef(
        version=1,
        required_fields={"tool_call_id"},
        optional_fields=set(),
    ),
    "TOOL_CALL_RESULT": EventTypeDef(
        version=1,
        required_fields={"tool_call_id", "result"},
        optional_fields=set(),
    ),
    
    # State (v1)
    "STATE_SNAPSHOT": EventTypeDef(
        version=1,
        required_fields={"state"},
        optional_fields={"redacted"},
    ),
    
    # Raw/fallback (v1)
    "RAW": EventTypeDef(
        version=1,
        required_fields={"raw"},
        optional_fields={"source"},
    ),
    "CUSTOM": EventTypeDef(
        version=1,
        required_fields={"custom_type"},
        optional_fields={"data"},
    ),
}
```

### Event Validation

Events are validated at emission time:

```python
def create_event(run_id: str, sequence: int, event_type: str, data: dict) -> RunEvent:
    """Create a validated event with current schema version."""
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type: {event_type}")
    
    typedef = EVENT_TYPES[event_type]
    
    # Validate required fields
    missing = typedef.required_fields - data.keys()
    if missing:
        raise ValueError(f"Event {event_type} missing required fields: {missing}")
    
    return RunEvent(
        schema_version=typedef.version,
        type=event_type,
        timestamp=now(),
        run_id=run_id,
        sequence=sequence,
        data=data,
    )
```

### Backward Compatibility

**Reading old traces:**
- Trace parser reads `schema_version` from each event (defaults to 1 if missing)
- Known versions are parsed normally
- Unknown future versions: event is preserved as `RAW` type with original data
- This ensures forward compatibility — new traces can be read by old readers (with degraded fidelity)

**Reading new traces with old readers:**
- Old reader sees `schema_version: 2` → treats unknown types as `RAW`
- Known types with new optional fields → ignores unknown fields
- This is safe because all breaking changes increment version

### AG-UI Bridge Versioning

The AG-UI bridge maps versioned ARC events to AG-UI protocol:

```python
def arc_to_agui(event: RunEvent) -> dict:
    """Map ARC event to AG-UI protocol format."""
    if event.schema_version > CURRENT_SCHEMA_VERSION:
        # Unknown future version — pass through as RAW
        return {
            "type": "RAW",
            "timestamp": event.timestamp,
            "runId": event.run_id,
            "sequence": event.sequence,
            "data": {"raw": event.model_dump()},
        }
    
    mapping = ARC_TO_AGUI_MAPPING.get(event.type)
    if mapping:
        return mapping(event)
    
    return {
        "type": "CUSTOM",
        "timestamp": event.timestamp,
        "runId": event.run_id,
        "sequence": event.sequence,
        "data": {"custom_type": event.type, "data": event.data},
    }
```

### TypeScript Mirror

The TypeScript side mirrors the versioned event model:

```typescript
interface RunEvent {
    schema_version: number;  // Event schema version
    type: string;
    timestamp: string;
    run_id: string;
    sequence: number;
    data: Record<string, unknown>;
}

// Trace parser validates schema_version
function parseEvent(raw: string): RunEvent {
    const event = JSON.parse(raw);
    if (!event.schema_version) {
        event.schema_version = 1; // Default for old traces
    }
    if (event.schema_version > CURRENT_SCHEMA_VERSION) {
        // Unknown version — treat as RAW
        return {
            ...event,
            type: 'RAW',
            data: { raw: event },
        };
    }
    return event;
}
```

### Breaking Change Process

When a breaking change is needed:
1. Increment `CURRENT_SCHEMA_VERSION`
2. Add new event type definitions to registry
3. Update `create_event()` validation
4. Update AG-UI bridge mapping
5. Update TypeScript mirror types
6. Document migration notes in CHANGELOG
7. Ensure readers support N-1 version

## Consequences

### Positive
- Breaking changes are explicit and versioned
- Old traces remain readable forever
- New readers can handle old traces (backward compatible)
- Old readers can handle new traces (forward compatible, degraded)
- Single registry prevents event type drift
- Validation catches adapter bugs at emission time

### Negative
- Adds `schema_version` field to every event (minor storage overhead)
- Breaking changes require coordinated Python + TypeScript updates
- Registry must be maintained as event types evolve

### Neutral
- AG-UI protocol versioning is separate (AG-UI has its own version)
- SwarmGraph internal events are mapped at adapter boundary (not versioned by ARC)
- Event validation is cheap (dict key checks, no deep validation)

## References
- Current RunEvent: `python/src/agent_runtime_cockpit/protocol/schemas.py:109-114`
- AG-UI event types (Python): `python/src/agent_runtime_cockpit/ag_ui/__init__.py:21-41`
- AG-UI event types (TypeScript): `packages/arc-ag-ui/src/event-types.ts:5-34`
- AG-UI bridge: `python/src/agent_runtime_cockpit/web/agui_bridge.py:22-32`
- Event creation helper: `python/src/agent_runtime_cockpit/orchestration/events.py:18-19`
- Trace parser: `packages/arc-extension/src/node/services/trace-parser.ts`
