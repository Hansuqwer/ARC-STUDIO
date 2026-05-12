# PR Acceptance Matrix (machine-readable)

| PR  | Acceptance test command(s)                                                          | Must-green | Status |
| --- | ----------------------------------------------------------------------------------- | ---------- | ------ |
| PR1 | grep -q "AG-UI" docs/VERIFICATION.md                                                | yes        | ✅ PASS |
| PR2 | cd packages/arc-ag-ui && pnpm test                                                  | yes        | ✅ PASS |
| PR3 | cd packages/arc-ag-ui && pnpm test  (golden fixtures included)                     | yes        | ✅ PASS |
| PR4 | uv run pytest python/arc_daemon/adapters/test_openai_agents.py                     | yes        | PENDING |
| PR5 | pnpm test --workspace theia-extensions/arc-event-stream                             | yes        | PENDING |
| ... | ...                                                                                 |            |        |

The roadmap agent reads this file row-by-row. If a row's command exits 0 the PR
is accepted, otherwise the agent halts.

## PR1-PR3 Completion Summary (2026-05-12)

### Completed Items
✅ **PR1: API Verification** - docs/VERIFICATION.md created with all Theia 1.71 APIs, protocol versions pinned
✅ **PR2: AG-UI Schema & Fixtures** - packages/arc-ag-ui created with event types, mappers, redaction, fixtures
✅ **PR3: Mapping Implementation** - SwarmGraph and LangGraph mappers implemented with golden tests

### Test Results
```
✔ swarmgraph mapping matches golden (1.805917ms)
✔ langgraph mapping matches golden (0.767084ms)
✔ unknown runtime falls through to RAW (0.084291ms)
✔ mapper exception becomes RUN_ERROR (0.105125ms)
✔ redacts OpenAI-style keys in strings (0.647459ms)
✔ redacts by key name (0.065167ms)
✔ safeEvent caps oversized payloads (0.395ms)
✔ no-live-provider invariant: secrets in nested tool args redacted (0.05175ms)

ℹ tests 8
ℹ pass 8
ℹ fail 0
```

### Files Created
- `docs/VERIFICATION.md` - API verification results
- `docs/AG_UI_MAPPING.md` - Mapping reference documentation
- `docs/TELEMETRY_SEMCONV.md` - OpenTelemetry semantic conventions
- `packages/arc-ag-ui/package.json` - Package configuration
- `packages/arc-ag-ui/tsconfig.json` - TypeScript configuration
- `packages/arc-ag-ui/src/event-types.ts` - AG-UI event type enum (33 variants)
- `packages/arc-ag-ui/src/redaction.ts` - Secret redaction utilities
- `packages/arc-ag-ui/src/mapper.ts` - Core mapping infrastructure
- `packages/arc-ag-ui/src/mapping/swarmgraph.ts` - SwarmGraph mapper
- `packages/arc-ag-ui/src/mapping/langgraph.ts` - LangGraph mapper
- `packages/arc-ag-ui/src/index.ts` - Package exports
- `packages/arc-ag-ui/test/fixtures/swarmgraph.input.jsonl` - SwarmGraph test input
- `packages/arc-ag-ui/test/fixtures/swarmgraph.expected.jsonl` - SwarmGraph golden output
- `packages/arc-ag-ui/test/fixtures/langgraph.input.jsonl` - LangGraph test input
- `packages/arc-ag-ui/test/fixtures/langgraph.expected.jsonl` - LangGraph golden output
- `packages/arc-ag-ui/test/mapping.test.js` - Mapping tests
- `packages/arc-ag-ui/test/redaction.test.js` - Redaction tests
- `.github/workflows/arc-roadmap-gate.yml` - CI gate workflow

### Next Steps
Ready for PR4: OpenAI Agents SDK Adapter Skeleton

### Security Checklist ✅
- [x] No API keys, tokens, or credentials in code
- [x] No secrets in test fixtures (using fake/redacted values)
- [x] Redaction applied to all mapped events
- [x] Secret patterns cover OpenAI, GitHub, Slack, AWS
- [x] Event payload size capped at 64 KiB
- [x] No HTML injection risk (JSON only)

### Acceptance Criteria Met ✅
- [x] Canonical AG-UI event types defined (33 variants)
- [x] SwarmGraph → AG-UI mapping implemented
- [x] LangGraph → AG-UI mapping implemented
- [x] Unknown events map to RAW/CUSTOM
- [x] Errors preserve code/message
- [x] Secrets redacted in all events
- [x] Golden fixture tests pass
- [x] Schema validation works
- [x] Documentation complete
