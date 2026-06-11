# Protocol Fixtures

Cross-language test fixtures for Python ↔ TypeScript schema validation.

## Purpose

These JSON fixtures serve as the single source of truth for testing schema consistency between Python (Pydantic) and TypeScript implementations. Each fixture represents a valid instance of a protocol schema and is used by both language test suites.

## Structure

```
protocol/fixtures/
├── arc-envelope/       # ArcEnvelope, ArcError, ArcMeta
├── runtime-capabilities/ # RuntimeCapabilities v1 and v2
├── run-record/         # RunRecord with events
├── run-event/          # Individual RunEvent instances
├── error-codes/        # Error code examples
├── workflow/           # WorkflowInfo, WorkflowNode, WorkflowEdge
├── cockpit/            # RunContract, RunReceipt, FailureAutopsy
└── README.md           # This file
```

## Usage

### Python

```python
import json
from pathlib import Path

def load_fixture(category: str, name: str) -> dict:
    """Load a JSON fixture by category and name."""
    fixture_path = Path(__file__).parent.parent / "protocol" / "fixtures" / category / f"{name}.json"
    return json.loads(fixture_path.read_text())

# Example
envelope = load_fixture("arc-envelope", "success")
```

### TypeScript

```typescript
import * as fs from 'fs';
import * as path from 'path';

function loadFixture(category: string, name: string): unknown {
  const fixturePath = path.join(__dirname, '../../protocol/fixtures', category, `${name}.json`);
  return JSON.parse(fs.readFileSync(fixturePath, 'utf-8'));
}

// Example
const envelope = loadFixture('arc-envelope', 'success');
```

## Fixture Naming Convention

- Use kebab-case for filenames: `success.json`, `error-not-found.json`
- Use descriptive names that indicate the test case: `v1-basic.json`, `v2-with-paid-calls.json`
- Include version in name when testing migrations: `v1.json`, `v2.json`

## Adding New Fixtures

1. Create JSON file in appropriate category directory
2. Ensure JSON is valid and formatted (use `jq` or similar)
3. Add corresponding test in both Python and TypeScript
4. Document any special cases in comments (JSON5 format if needed)

## Validation Rules

Each fixture must:
- Be valid JSON
- Match the schema definition in both languages
- Include all required fields
- Use realistic values (not just "test" or "foo")
- Include edge cases where applicable (null, empty arrays, etc.)

## Version History

- 2026-05-22: Initial structure created for schema audit (Risk 0 fix)
- Future: Add fixtures as schemas are validated

## Related Documentation

- `docs/SCHEMA_AUDIT_REPORT.md` - Schema consistency audit
- `docs/adr/ADR-022-deprecation-policy.md` - Schema versioning policy
- `docs/adr/ADR-018-protocol-package-as-canonical-schema-home.md` - Protocol package structure

## run-event-seq/ (additive, arc-v2)

Ordered, gap-free event sequences for replay/scrubber testing, one scenario per
directory, files named `NNN-<TYPE>.json` (NNN = zero-padded `sequence`).
Unlike the per-instance fixtures above, these model a *coherent run*: contiguous
`sequence`, one `run_id`, lifecycle brackets (RUN_STARTED … RUN_COMPLETED).
Generated and registry-validated by `scripts/generate-priority-fixtures.py`
(refuses to overwrite; refuses invalid data). Consumed by
`rust/arc-daemon-client` replay tests and, from Sprint 7, the Event Stream
panel's row-for-row parity oracle.

Note: `run-record/`, `workflow/`, and `cockpit/` listed above are aspirational
(finding F2 in `docs/planning/arc-v2-sprint-1-execution-report.md`) — they do
not exist yet; tests must enumerate actual directories.
