# Phase 0 — IDE Tab Inventory

Status: DRAFT (Phase 0 inventory, non-destructive)
Scope: every tab in `packages/arc-extension/src/browser/tabs/`.
Output: list of Python APIs called per tab, env dependencies, and any hidden IDE-only execution paths.

## How to fill this file

1. Walk each `*Tab.tsx` file.
2. Record every backend call (Theia service or subprocess invocation).
3. Record every env var read.
4. Mark any code path that does NOT route through canonical CLI APIs as "Hidden execution path".

## ChatTab

| Aspect | Value |
|---|---|
| File | packages/arc-extension/src/browser/tabs/ChatTab.tsx |
| Backend services called | `preflightRun`, `startRun`, `listRuntimeCapabilities`, `getConfigStatus` (`ChatTab.tsx:74-112`, `114-137`) |
| Python CLI commands invoked | none directly from React; routes through Theia `ArcService` |
| Env vars read | none in React |
| Runtime default | swarmgraph |
| Profile default | local-safe |
| Isolation default | subprocess |
| Allow-paid-calls default | false |
| Run button text | "Run fake/offline" (hardcoded — drift) |
| Hidden execution path? | no direct React subprocess; possible semantic drift because UI hardcodes fallback runtimes and "Run fake/offline" (`ChatTab.tsx:12-17`, `235-240`) |
| Phase to fix | 5 (parity) |

## RunsTab

| Aspect | Value |
|---|---|
| File | packages/arc-extension/src/browser/tabs/RunsTab.tsx |
| Backend services called | `getTraces`, `getRunReceipt`, `getRunAutopsy`, `getRunContract`, `getAuditChainInfo`, `replayRun`, `listPendingHitlPrompts`, `respondHitlPrompt`, `diffRuns` (`RunsTab.tsx:80-189`) |
| Python CLI commands invoked | none directly from React |
| Env vars read | none in React |
| Hidden execution path? | no direct React subprocess; backend service path must be parity-audited |
| Phase to fix | 5 |

## WorkflowsTab

| Aspect | Value |
|---|---|
| File | packages/arc-extension/src/browser/tabs/WorkflowsTab.tsx |
| Backend services called | workflow detection/listing via `ArcService` (source-contract; exact methods in `WorkflowsTab.tsx`) |
| Python CLI commands invoked | none directly from React |
| Env vars read | none in React |
| Hidden execution path? | no direct React subprocess found in tab inventory |
| Phase to fix | 5 |

## ConfigTab

| Aspect | Value |
|---|---|
| File | packages/arc-extension/src/browser/tabs/ConfigTab.tsx |
| Backend services called | `getConfigStatus`, `getProviderCatalog`, `listProfiles`, `getIsolationStatus`, `listIsolationProviders`, `getProviderDiagnostics`, `getProviderQuota`, `listRuntimeCapabilities`, provider action/quota APIs (`ConfigTab.tsx:154-220`) |
| Python CLI commands invoked | none directly from React |
| Env vars read | none in React; provider env var names shown as refs only |
| Writes secrets directly? | must be NO |
| Writes env-var refs only? | must be YES |
| Hidden execution path? | no direct React subprocess; capability fallback display can drift from Python (`ConfigTab.tsx:40-47`, `207-216`) |
| Phase to fix | 5 |

## SwarmGraphInsightTab

| Aspect | Value |
|---|---|
| File | packages/arc-extension/src/browser/tabs/SwarmGraphInsightTab.tsx |
| Backend services called | `getTraces`, `readTrace`; optional active stream if live base URL supplied (`SwarmGraphInsightTab.tsx:221-260`, `262-416`) |
| Daemon URLs (3-tier fallback) | user-entered live base URL; stored trace via Theia service; no hardcoded provider URL |
| Trace source | stored traces by default; optional active stream attempt |
| Empty-state behavior | honest empty (no fabricated data) — verify |
| Hidden execution path? | no execution path; visualization only. Honest empty/degraded states are explicit (`SwarmGraphInsightTab.tsx:37-45`, `88-150`) |
| Phase to fix | 5 |

## AssuranceTab

| Aspect | Value |
|---|---|
| File | packages/arc-extension/src/browser/tabs/AssuranceTab.tsx |
| Backend services called | run/receipt/audit/HITL service calls; needs source-contract fill in Phase 5 |
| Auto-refresh interval | current value to verify in `AssuranceTab.tsx` during Phase 5 |
| LIVE badge source | current value to verify; target must come from live transport status, not optimistic UI |
| Hidden execution path? | unknown until `AssuranceTab.tsx` line audit; no execution claim in Phase 0 |
| Phase to fix | 5 |

## Transport parity audit

| Concern | Status | Evidence | Phase to fix |
|---|---|---|---|
| Theia backend env allowlist for ARC_* | needs backend audit | backend service not fully audited in Phase 0 | 5 |
| Theia backend uses subprocess to `arc`, not in-process duplication | mixed/needs audit | React routes through `ArcService`; backend implementation must be checked | 5 |
| Any IDE-only Python module imported directly (bypassing CLI) | no React direct import | tab files import TS protocol/service only | 5 |
| Capability report consumed from Python, not redefined in TS | partial | `ChatTab.tsx:96-112`, `139-142`; `ConfigTab.tsx:207-216` consume `listRuntimeCapabilities`, but fallback options exist | 3 |
| Event envelope consumed from Python, not redefined in TS | partial | SwarmGraphInsightTab consumes trace event types; contract tests still needed | 3 |

## Acceptance for this file

- Every tab has all Aspect rows filled.
- Every "Hidden execution path?" cell is yes/no with code citation.
- Transport parity table has no Unknown rows.
- Every drift item has a target phase.

## AssuranceTab Two-Mode Lock (per ADR-015)

The AssuranceTab inventory row above needs expansion. The locked design is two-mode (Developer + Compliance) with a Both option. Phase 0 inventory should record the current state of AssuranceTab and the gap to the locked design.

| Aspect | Current state | Target (ADR-015) | Gap |
|---|---|---|---|
| Mode selector | absent | Developer / Compliance / Both | new |
| Timeline replay | <fill> | required (Developer) | <fill> |
| Trace tree | <fill> | required (Developer) | <fill> |
| Run summary card | <fill> | required (Compliance) | <fill> |
| Policy attribution | <fill> | required (Compliance) | <fill> |
| Evidence panel | <fill> | required (Compliance) | <fill> |
| Audit chain integrity | <fill> | required (Compliance) | <fill> |
| HITL decisions view | partial | required (both modes) | <fill> |
| Injection events view | absent | required (Compliance) | <fill> |
| Trust changes view | absent | required (Compliance) | <fill> |
| Regulator export button | absent | required (Compliance) | <fill> |
| Side-by-side Both mode | absent | required | <fill> |

## Transport Parity Audit (additions per ADR-014)

| Concern | Status | Evidence | Phase to fix |
|---|---|---|---|
| Untrusted-input tagging in Theia → Python flow | absent/unknown | not visible in React tabs | 4 |
| L2 classifier in Theia backend pipeline | absent/unknown | no React evidence | 4 |
| CaMeL boundary respected by IDE (no direct privileged actions) | partial | React calls service APIs; backend authorization still required | 4 |
| MCP allowlist enforced by Theia backend | absent/unknown | no React evidence | 5.6 |
| Receipt v2 schema rendered by IDE | absent | current RunsTab renders receipt/contract cards; v2 compliance mode pending | 5 |

## Runtime Dropdown / Capability Source Contract

- Runtime dropdowns in ChatTab and ConfigTab must use `ArcService.listRuntimeCapabilities()` as authoritative source.
- Fallback runtime lists are display-only/degraded and must be labelled unknown when backend capability reports fail.
- `swarmgraph` remains default selected runtime only when config/capability state does not supply another explicit default.
- Disabled state follows `cap.can_run`; TS cannot override Python blockers except to keep current fake/offline fallback visibly degraded.
- Profile/isolation/paid controls must be included in every start/preflight request; current ChatTab sends runtime/profile/allowPaid but does not pass isolation in `startRun` (`ChatTab.tsx:118-124`).
