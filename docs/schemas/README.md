# Generated Schema Snapshots

Files in this directory are generated JSON Schema snapshots for compatibility checks and documentation. They are not the canonical source for typed RunEvent unions.

Canonical RunEvent sources:
- Python legacy wire model: `python/src/agent_runtime_cockpit/protocol/schemas.py`
- Python typed/core registry: `python/src/agent_runtime_cockpit/protocol/events.py` and `python/src/agent_runtime_cockpit/protocol/typed_events.py`
- TypeScript typed union: `packages/arc-protocol-ts/src/run-events.ts`
- Cross-language registry fixture: `protocol/fixtures/run-event-registry.json`

`RunEvent.json` remains intentionally broad because legacy traces and extension consumers still use `{ type, data }` compatibility. Typed coverage is enforced by source-level parity tests, not by this snapshot alone.
