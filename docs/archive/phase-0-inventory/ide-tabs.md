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
| Lines of code | 53 (pure presentational component) |
| Backend services called | none directly — receives `workflows: WorkflowInfo[]`, `isScanning: boolean`, `onScanWorkspace: () => void` as props from parent (`WorkflowsTab.tsx:10-14`) |
| Python CLI commands invoked | none directly from React |
| Env vars read | none in React |
| Hidden execution path? | **no** — purely presentational; no subprocess, no Theia service calls |
| Empty state | "No workflows detected." with hint "Click Scan to detect SwarmGraph or LangGraph workflows" (`WorkflowsTab.tsx:32-39`) |
| Card rendering | workflow name + type badge + file path, keyed by index (`WorkflowsTab.tsx:41-49`) |
| Phase to fix | 5 (parity: parent integration audit) |

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
| Lines of code | 460 |
| Backend services called | `listPendingHitlPrompts()` (line 136), `respondHitlPrompt()` (line 153), `getAuditChainInfo()` (line 177), `replayRun()` (line 197) (`AssuranceTab.tsx:110-205`) |
| Python CLI commands invoked | none directly from React |
| Env vars read | none in React |
| Auto-refresh interval | `AUTO_REFRESH_INTERVAL_MS = 10_000` (10s, line 15); togglable via `autoRefreshEnabled` state (line 128) |
| LIVE badge source | from `autoRefreshEnabled` boolean state (line 252-254); shows `<span>LIVE</span>` when auto-refresh is on; **not** from live transport status — target must come from live transport, not optimistic UI (`AssuranceTab.tsx:252-254`) |
| Replay categories | `['lifecycle', 'message', 'tool', 'error', 'hitl', 'audit', 'unknown']` (line 16); all 7 categories selectable via checkboxes, "Clear filters" button, filtered-count display (`AssuranceTab.tsx:390-425`) |
| Audit state | `present` / `missing` / `degraded` via `auditState()` (lines 51-56); state banner shows icon + title + detail copy (`AssuranceTab.tsx:350-356`) |
| Audit disclaimer | "No adapter-wide keyed audit/HMAC claim. This view reports available run audit material only." (line 348) |
| Export buttons | HITL JSON download (line 265), audit JSON download (line 330), replay events JSON download (line 376); buttons visible/disabled based on data existence |
| HITL decisions | approve/reject/modify with token expiry/blocked checks (`AssuranceTab.tsx:47-49`, `287-319`) |
| Mode selector | **absent** — no Developer/Compliance/Both mode selector (gap vs ADR-015 two-mode target) |
| Timeline replay | present as ReplayStepper section (lines 369-457); step + total display, prev/next nav, annotations (HITL/AUDIT/APPROVAL/REPLAY), event data as JSON |
| Compliance mode features | **absent**: no policy attribution, evidence panel, injection events, trust changes, regulator export, compliance bundle (`AssuranceTab.tsx` line audit — compliance features not implemented) |
| Write secrets directly? | **no** — data flows through `ArcService` only |
| Hidden execution path? | **no** — purely visualization/UI layer; no subprocess, no direct Python execution |
| Phase to fix | 5 (parity: add mode selector; compliance features per ADR-015; LIVE badge from transport) |

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
| Mode selector | absent (lines 246-458 — no mode selector rendered) | Developer / Compliance / Both | new |
| Timeline replay | present as ReplayStepper (lines 369-457), step/filter/export, category checkboxes | required (Developer) | Add annotations from audit events |
| Trace tree | absent (no hierarchy/span detail view) | required (Developer) | new |
| Run summary card | absent (no dedicated summary card) | required (Compliance) | new |
| Policy attribution | absent (no policy/remediation summary) | required (Compliance) | new |
| Evidence panel | absent (no evidence drill-down) | required (Compliance) | new |
| Audit chain integrity | present: `present`/`missing`/`degraded` states, verify button, detail dl (lines 323-367) | required (Compliance) | Add timestamps per record |
| HITL decisions view | present: approve/reject/modify with token/expiry, inline cards (lines 248-321) | required (both modes) | Moderate gap |
| Injection events view | absent | required (Compliance) | new |
| Trust changes view | absent | required (Compliance) | new |
| Regulator export button | absent | required (Compliance) | new |
| Side-by-side Both mode | absent | required | new |

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
