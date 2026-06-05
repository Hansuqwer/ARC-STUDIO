# Policy: Protocol Changes Are Additive-Only

> **Status:** Authoritative for ARC Studio protocol evolution.
> **Owner:** Sprint planning + spec authors + protocol PR reviewers.
> **Last updated:** 2026-06-04
> **Companion to:** `docs/policy/cosai-llm-in-path.md`, `docs/policy/local-first.md`
> **Origin:** Lock the "3 Python sites + 1 TS site" rule + Pydantic
> `extra="ignore"` convention that's been repeated in every spec since
> v0.3.0-alpha. Future specs reference this policy by ID instead of
> restating the rule.

---

## The rule

**Protocol changes must be additive.** A new release MUST NOT:

- Remove an existing typed event from `KnownRunEvent` union
- Remove a field from an existing event payload
- Rename a field
- Change a field's type in a non-superset way (e.g., `int → str`)
- Tighten validation on an existing field (e.g., add a regex constraint that some prior payloads would fail)
- Reject payloads that contain unknown fields (`extra="forbid"`)
- Change `KNOWN_RUN_EVENT_TYPES` membership for an existing type
- Bump protocol schema version unless additive-only across all consumers

A new release MAY:

- Add a new typed event (in 3 Python sites + 1 TS site — see §"The 4-site rule")
- Add a new optional field to an existing event payload (`Field(default=None)` or `default=""`)
- Add a new enum variant (if downstream code handles unknown variants gracefully)
- Add a new convention for an opt-in interpretation of existing data
- Deprecate a field (still serialize it; log warning when consumed)

---

## Why

**Single-process, single-user** doesn't excuse non-additive changes. Two reasons:

1. **Cross-language pairs** — Python and TS evolve at different rates per CI; an additive Python change that breaks the TS schema lock-step causes flaky CI for nobody's benefit. Mandatory additive-only keeps the languages in safe drift.

2. **JSONL trace persistence** — ARC writes traces to disk. A trace written on v0.3.0-alpha must still parse on v0.5.0-alpha. Removing or renaming fields invalidates the user's history. `extra="ignore"` ensures *new* fields don't break *old* readers; this policy ensures *old* fields don't break *new* readers.

The combination of `extra="ignore"` (forward-compat) + additive-only (backward-compat) gives **bidirectional schema compatibility** within the alpha series.

---

## The 4-site rule

When adding a new typed event, **exactly 4 files must change**, in this order:

### Python sites (3)

1. **`python/src/agent_runtime_cockpit/events/types.py`** — Define the event dataclass.
   ```python
   @dataclass(frozen=True)
   class MyNewEvent:
       field_one: str
       field_two: int
       optional_thing: str | None = None  # always defaults required
   ```

2. **`python/src/agent_runtime_cockpit/protocol/typed_events.py`** — Three additions in this file:
   ```python
   # site 2a: KnownRunEvent union — add the new event class
   KnownRunEvent = (
       ...existing...
       | MyNewEvent
   )

   # site 2b: is_known_event set — add the event's `type` field value
   _KNOWN_EVENT_TYPES: set[str] = {
       ...existing...
       "my_new_event",  # MUST match the type discriminator
   }

   # site 2c: parse_typed_event type_map — register the parser
   _TYPE_MAP: dict[str, type] = {
       ...existing...
       "my_new_event": MyNewEvent,
   }
   ```

3. **`python/tests/events/test_my_new_event_roundtrip.py`** — Three test cases minimum:
   - `test_event_round_trips_through_typed_events`
   - `test_event_parses_with_extra_fields_ignored` (forward-compat proof)
   - `test_event_in_known_event_types_set`

### TypeScript site (1)

4. **`packages/arc-protocol-ts/src/run-events.ts`** — Two additions in this file:
   ```typescript
   // site 4a: KnownRunEvent union — add interface
   export interface MyNewEventData {
     field_one: string;
     field_two: number;
     optional_thing?: string;  // optional fields use `?`, never required
   }

   export interface MyNewEvent {
     type: 'my_new_event';
     data: MyNewEventData;
   }

   export type KnownRunEvent =
     | ...existing...
     | MyNewEvent;

   // site 4b: KNOWN_RUN_EVENT_TYPES set
   export const KNOWN_RUN_EVENT_TYPES = new Set<string>([
     ...existing,
     'my_new_event',
   ]);
   ```

   And in `packages/arc-protocol-ts/src/run-events.test.ts`:
   - `parseRunEvent recognizes my_new_event`
   - `isKnownEvent('my_new_event') === true`

---

## Pydantic / dataclass conventions

For Python event models that use Pydantic (some legacy paths still do):

```python
class SomeEventModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)
    # OR for legacy V1:
    # class Config:
    #     extra = "ignore"
    #     allow_mutation = False

    field_one: str
    field_two: int
    optional_thing: str | None = None
```

For Python dataclasses (preferred for new code):

```python
@dataclass(frozen=True)
class SomeEventModel:
    field_one: str
    field_two: int
    optional_thing: str | None = None  # defaults required for all optional fields
```

**Never** use `extra="forbid"` or `extra="allow"`:
- `forbid` breaks forward-compat — downstream emits a new field, ARC crashes
- `allow` admits arbitrary garbage; loses type safety

Always `extra="ignore"`.

---

## Field addition rules

When adding a field to an existing event:

| Field type | Required? | Default | Rationale |
|---|---|---|---|
| Optional metadata | No | `None` (Python) / `undefined` (TS) | Existing producers don't emit; existing consumers don't expect |
| Numeric counter / total | No | `0` | Safe additive identity |
| List of new items | No | `[]` (Python) / `[]` (TS) | Safe additive identity |
| String label | No | `""` or `None` | Either; pick consistently |
| Boolean flag | No | `False` | Conservative default |
| Required by downstream | **STOP** | n/a | Adding a required field is non-additive. Re-design to make it optional with a default. |

If a new field would semantically need to be required, the correct migration is:

1. v0.X-alpha: Add as optional with default. Document "providers SHOULD populate this; consumers MUST handle absence."
2. v0.X+1-alpha (after one release cycle minimum): Producers start populating universally.
3. v0.X+2-alpha (after two release cycles): Consumers MAY assume present. Field stays formally optional in schema forever.

The field schema stays optional even when adoption is universal. This is the additive-only price.

---

## Deprecation procedure

To deprecate a field (still serialize, but new code should ignore):

1. Update CHANGELOG under `### Deprecated`:
   ```
   - **Protocol**: `EventX.fieldY` deprecated. Producers may still emit;
     consumers should prefer `EventX.fieldZ`. Removal not planned within
     the v0.x alpha series.
   ```
2. Update field docstring with `# DEPRECATED: see CHANGELOG <tag>`.
3. Add a runtime warning when a consumer reads the field — log once per process per field.
4. **Do NOT remove the field** in any v0.x-alpha tag. The alpha series promises backward-compat; field removal requires a major version bump (v1.0+).

To deprecate an entire event:

1. Add `# DEPRECATED in v0.X-alpha` comment at the event class definition.
2. Keep parsing it (additive-only — old traces must still load).
3. Stop emitting it from new code paths; document that emission is grandfathered.
4. Removal: same as field removal — major version bump required.

---

## How to check compliance

### Code review checklist

For any PR touching `protocol/`, `events/`, or `packages/arc-protocol-ts/src/run-events.ts`:

- [ ] If a new event was added, are all 4 sites updated? (Run `scripts/protocol_audit.py` to verify — see §"Tooling")
- [ ] If a field was added, is it optional with a default?
- [ ] If a field was removed/renamed, **STOP** — this is a policy violation. Refactor as additive + deprecation.
- [ ] Is `extra="ignore"` (or equivalent) the configured behavior?
- [ ] Does the CHANGELOG entry note the additive nature?
- [ ] Are TS round-trip tests + Python round-trip tests both updated?

### Automated checks

Two test patterns enforce this policy:

#### Pattern A — KNOWN_RUN_EVENT_TYPES parity

`python/tests/protocol/test_typed_event_coverage.py`:

```python
def test_python_known_event_types_match_typescript():
    """Python _KNOWN_EVENT_TYPES set must equal TS KNOWN_RUN_EVENT_TYPES set."""
    from agent_runtime_cockpit.protocol.typed_events import _KNOWN_EVENT_TYPES
    py_types = set(_KNOWN_EVENT_TYPES)

    # Load TS file and parse the Set<string> literal
    ts_file = Path("packages/arc-protocol-ts/src/run-events.ts").read_text()
    ts_types = _parse_ts_set_literal(ts_file, "KNOWN_RUN_EVENT_TYPES")

    only_py = py_types - ts_types
    only_ts = ts_types - py_types
    assert not only_py, f"Python knows but TS doesn't: {only_py}"
    assert not only_ts, f"TS knows but Python doesn't: {only_ts}"
```

#### Pattern B — Forward-compat parse test

For every event model, a test asserting it ignores extra fields:

```python
def test_my_new_event_ignores_extra_fields():
    payload = {"type": "my_new_event", "field_one": "x", "field_two": 1,
               "extra_unknown_field": "anything"}
    event = parse_typed_event(payload)
    assert isinstance(event, MyNewEvent)
    # extra_unknown_field doesn't appear in the parsed event; doesn't raise
```

### Tooling

A grep audit (~30 LOC) you can run before any protocol PR:

```bash
# scripts/protocol_audit.sh
#!/usr/bin/env bash
set -e

echo "=== Python typed events coverage ==="
python3 -c "
from agent_runtime_cockpit.protocol.typed_events import _KNOWN_EVENT_TYPES, _TYPE_MAP, KnownRunEvent
import typing
union_types = {a.__name__ for a in typing.get_args(KnownRunEvent)}
type_map_types = set(_TYPE_MAP.values())
known_strings = set(_KNOWN_EVENT_TYPES)
print(f'KnownRunEvent classes: {len(union_types)}')
print(f'parse_typed_event _TYPE_MAP entries: {len(type_map_types)}')
print(f'_KNOWN_EVENT_TYPES strings: {len(known_strings)}')
# Sanity: all three must have same cardinality
assert len(union_types) == len(type_map_types) == len(known_strings), 'protocol sites drifted'
print('OK: Python sites in sync')
"

echo "=== TS typed events coverage ==="
grep -c "^export interface .*Event " packages/arc-protocol-ts/src/run-events.ts
grep -c "'.*':" packages/arc-protocol-ts/src/run-events.ts | head -1
```

---

## Resolution procedure for non-additive proposals

If a sprint genuinely needs a non-additive change (e.g., a field's type really is wrong and breaks user trust):

1. **STOP.** Don't do it in an alpha tag.
2. Open a ticket / issue tagged `breaking-change-candidate`.
3. Hold for the next major version bump (v1.0+).
4. In the meantime, add a *new* parallel field with the corrected type. Deprecate the old one per §"Deprecation procedure".
5. Both fields coexist in the v0.x series. v1.0 may remove the deprecated one.

There is no exception. Every alpha-series tag is bidirectionally compatible with every other alpha-series tag's traces. This is the trust we're building.

---

## Cross-references

- Companion policy: `docs/policy/cosai-llm-in-path.md` (decision-time LLM rule)
- Companion policy: `docs/policy/local-first.md` (deployment topology rule)
- First enforcement: every typed event added since v0.3.0-alpha follows this pattern
- Code: `python/src/agent_runtime_cockpit/protocol/typed_events.py` (the 3 Python sites)
- Code: `packages/arc-protocol-ts/src/run-events.ts` (the 1 TS site)
- Spec template reference: `docs/spec/TEMPLATE.md` (constraints block references this policy)
- Project rules: `AGENTS.md`
