# ADR-0004: Mock and Fallback Policy

**Status:** Accepted  
**Date:** 2025

## Policy

Every mock MUST include:

### TypeScript
```ts
/**
 * MOCK_REASON: <why this is mocked>
 * REAL_IMPLEMENTATION_PATH: <where the real implementation goes>
 * LOCAL_FIX_STEPS: <exact steps to replace this mock>
 * OWNER: <team or agent responsible>
 * REMOVE_BEFORE: <milestone or date>
 */
```

### Python
```python
MOCK_REASON = ""
REAL_IMPLEMENTATION_PATH = ""
LOCAL_FIX_STEPS = ""
OWNER = ""
REMOVE_BEFORE = ""
```

## Allowed Mocks

- SwarmGraph sample output (if real repo unavailable)
- LangGraph fixture (if install fails)
- Context7 provider (if API key absent)
- Vercel Grep provider (if network blocked)
- AG-UI event stream (if no runtime executes)
- A2UI renderer placeholder
- Electron signing placeholder
- Open VSX download placeholder

## Not Allowed

- Fake tests that pass without asserting behavior
- Fake runtime detection reporting success for every repo
- Fake context retrieval returning stale hardcoded docs as current
- Fake security redaction

## Exit Criteria for a Mock

1. It is behind the real interface
2. It is documented with the metadata above
3. It has test coverage
4. It does NOT claim production status
5. It has a clear replacement path
