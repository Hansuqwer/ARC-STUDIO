# Follow-up: arc-extension consumes new typed events

**Status:** queued (post-merge of `feat/post-merge-and-ux-p0`)
**Branch to open:** `feat/arc-extension/typed-event-consumers`

## Context

Python now emits `CAPABILITY_CARD_DECISION` and `MCP_CALL_DECISION` typed
events at adapter, MCP server, and SwarmGraph boundaries (landed in the
8-PR sprint + D-01/D-02 wiring from `feat/post-merge-and-ux-p0`).

The Theia extension does not yet render them:

```
grep -rn "CAPABILITY_CARD_DECISION\|MCP_CALL_DECISION" packages/arc-extension/src/
# → 0 hits
```

Both event types are already present in the TypeScript discriminated union:
```
grep -n "CAPABILITY_CARD_DECISION\|MCP_CALL_DECISION" packages/arc-protocol-ts/src/run-events.ts
# → 2 hits (KnownRunEvent union + KNOWN_RUN_EVENT_TYPES array)
```

## Acceptance criteria

- [ ] `packages/arc-extension/src/browser/tabs/AssuranceTab.tsx` renders a
  capability card decision banner per `CAPABILITY_CARD_DECISION` event
  (mirror the Python `CapabilityCardBanner` widget: green/amber/red strip)
- [ ] `packages/arc-extension/src/browser/tabs/McpWorkbenchTab.tsx` renders
  a "Recent MCP Decisions" stream per `MCP_CALL_DECISION` event
  (allow=green, warn=amber, deny=red rows with server/tool/risk)
- [ ] `packages/arc-protocol-ts/src/run-events.ts` — no change needed
  (already typed)
- [ ] New contract tests in `packages/arc-extension/src/browser/__tests__/`
  covering both tab renders with mock event payloads
- [ ] No Theia API drift (do not downgrade Theia; open a separate fix PR if
  a Theia API surface has changed)

## Files likely touched

```
packages/arc-extension/src/browser/tabs/AssuranceTab.tsx
packages/arc-extension/src/browser/tabs/McpWorkbenchTab.tsx
packages/arc-extension/src/common/arc-protocol.ts
packages/arc-extension/src/node/arc-backend-service.ts
```

## Event payload shapes (from Python protocol)

```typescript
// CAPABILITY_CARD_DECISION (packages/arc-protocol-ts/src/run-events.ts)
data: {
  action: string;
  decision: 'allow' | 'deny' | 'warn';
  reason: string;
  card_id?: string;
  card_hash?: string;
  entity_type?: string;
  mode: 'off' | 'warn' | 'strict';
  remediation?: string;
  correlation_id?: string;
}

// MCP_CALL_DECISION
data: {
  server_id: string;
  tool_name: string;
  decision: 'allow' | 'deny' | 'warn';
  risk_score: 'low' | 'medium' | 'high' | 'critical';
  policy: 'auto_low' | 'auto_medium' | 'strict';
  reason: string;
  injection_severity?: string;
  drift?: string;
  manifest_risk?: string;
  correlation_id?: string;
}
```

## Estimate

1 day (AssuranceTab + McpWorkbenchTab + 4 contract tests).
