# Cross-Language Test Harness - Setup Status

**Created:** 2026-05-22  
**Status:** Python tests operational, TypeScript tests need Jest config

## What's Complete

### ✅ Directory Structure
```
protocol/fixtures/
├── arc-envelope/           (3 fixtures)
├── runtime-capabilities/   (3 fixtures)
├── run-event/             (4 fixtures)
├── run-record/            (empty, ready for fixtures)
├── error-codes/           (empty, ready for fixtures)
├── workflow/              (empty, ready for fixtures)
├── cockpit/               (empty, ready for fixtures)
└── README.md              (comprehensive documentation)
```

### ✅ JSON Fixtures (10 total)

**ArcEnvelope (3):**
- `success.json` - Successful operation response
- `error-run-failed.json` - Run execution failure
- `error-workspace-not-found.json` - Workspace not found error

**RunEvent (4):**
- `run-started.json` - RUN_STARTED event (schema v2)
- `run-completed.json` - RUN_COMPLETED event (schema v2)
- `run-failed.json` - RUN_FAILED event (schema v2)
- `run-cancelled.json` - RUN_CANCELLED event (schema v2)

**RuntimeCapabilities (3):**
- `v1-basic.json` - RuntimeCapabilities v1 basic configuration
- `v2-gated-local.json` - RuntimeCapability v2 gated_local mode
- `v2-provider-backed.json` - RuntimeCapability v2 provider_backed mode

### ✅ Python Test Infrastructure

**Files:**
- `python/tests/fixtures/loader.py` - Fixture loader utility
- `python/tests/fixtures/test_cross_language.py` - Validation tests

**Test Results:**
```
21 tests PASSED in 0.04s
- 4 loader utility tests
- 4 ArcEnvelope validation tests
- 5 RunEvent validation tests
- 5 RuntimeCapabilities validation tests
- 3 cross-language consistency tests
```

**Features:**
- `load_fixture()` - Load raw JSON
- `load_and_validate()` - Load and validate against Pydantic model
- `validate_round_trip()` - Test serialization stability
- `list_fixtures()` / `list_categories()` - Discovery utilities

### ✅ TypeScript Test Infrastructure (Code Ready)

**Files:**
- `packages/arc-protocol-ts/src/fixtures/loader.ts` - Fixture loader utility
- `packages/arc-protocol-ts/src/fixtures/loader.test.ts` - Validation tests

**Status:** Code written but needs Jest + TypeScript configuration to run

## What Needs Setup

### TypeScript Jest Configuration

The TypeScript tests are written but can't run because Jest isn't configured for TypeScript.

**Required Steps:**

1. **Install dependencies:**
```bash
cd packages/arc-protocol-ts
npm install --save-dev jest ts-jest @types/jest @types/node
```

2. **Create jest.config.js:**
```javascript
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  roots: ['<rootDir>/src'],
  testMatch: ['**/*.test.ts'],
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json'],
  collectCoverageFrom: [
    'src/**/*.ts',
    '!src/**/*.test.ts',
    '!src/**/*.d.ts',
  ],
};
```

3. **Update package.json scripts:**
```json
{
  "scripts": {
    "test": "jest",
    "test:watch": "jest --watch",
    "test:coverage": "jest --coverage"
  }
}
```

4. **Run tests:**
```bash
npm test
```

**Expected Result:** 15+ tests should pass, matching Python test coverage

## Usage Examples

### Python

```python
from tests.fixtures.loader import load_fixture, load_and_validate
from agent_runtime_cockpit.protocol.event_envelope import ArcEnvelope

# Load raw JSON
data = load_fixture("arc-envelope", "success")

# Load and validate
envelope = load_and_validate("arc-envelope", "success", ArcEnvelope)
assert envelope.ok is True

# Round-trip test
from tests.fixtures.loader import validate_round_trip
original, serialized, instance = validate_round_trip(
    "arc-envelope", "success", ArcEnvelope
)
```

### TypeScript (after Jest setup)

```typescript
import { loadFixture, loadAndValidate } from './fixtures/loader';
import { ArcEnvelope, validateEnvelope } from './arc-protocol-types';

// Load raw JSON
const data = loadFixture('arc-envelope', 'success');

// Load and validate
const envelope = loadAndValidate('arc-envelope', 'success', validateArcEnvelope);
expect(envelope.ok).toBe(true);
```

## Next Steps

### Immediate (to complete test harness)
1. Configure Jest for TypeScript in arc-protocol-ts package (~30 minutes)
2. Verify all TypeScript tests pass (~15 minutes)
3. Add fixtures for remaining schemas (~1 hour):
   - Workflow (WorkflowInfo, WorkflowNode, WorkflowEdge)
   - Cockpit (RunContract, RunReceipt, FailureAutopsy)
   - Error codes (examples of each error code)

### Week 1 Remaining Tasks
After test harness is complete:
1. Write canonical error code ADR amendment (4 hours)
2. Sync error codes (Risk 1, 3 hours)
3. Wire format validation tests (4 hours)
4. Decide version negotiation policy (4 hours)

## Test Coverage

### Current Coverage
- ✅ ArcEnvelope (success and error cases)
- ✅ RunEvent (all 4 lifecycle events with schema v2)
- ✅ RuntimeCapabilities (v1 and v2 with different modes)
- ✅ Round-trip serialization validation
- ✅ Schema version consistency checks

### Missing Coverage (to add)
- ⏳ WorkflowInfo, WorkflowNode, WorkflowEdge
- ⏳ RunContract, RunReceipt, FailureAutopsy
- ⏳ Error code examples
- ⏳ RunRecord with full event history
- ⏳ EvidenceRef examples

## Benefits Delivered

Even with TypeScript tests pending Jest config, the test harness provides:

1. **Single Source of Truth:** JSON fixtures are language-neutral
2. **Python Validation:** 21 tests ensure Python schemas are correct
3. **Documentation:** Comprehensive README and examples
4. **Foundation:** Infrastructure ready for all future schema additions
5. **Round-Trip Testing:** Validates serialization stability
6. **Discovery:** Utilities to list all fixtures and categories

## Time Spent

- Directory structure and documentation: 30 minutes
- JSON fixture creation: 45 minutes
- Python loader and tests: 1 hour
- TypeScript loader and tests: 45 minutes
- **Total: ~3 hours** (of 4-hour estimate)

Remaining ~1 hour for Jest config + additional fixtures aligns with original estimate.

## Related Documentation

- `protocol/fixtures/README.md` - Fixture usage guide
- `docs/SCHEMA_AUDIT_REPORT.md` - Schema audit that motivated this work
- `docs/adr/ADR-022-deprecation-policy.md` - Schema versioning policy
