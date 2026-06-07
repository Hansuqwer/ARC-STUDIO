# ARC Studio Theia IDE Architecture Audit — 2026-06-07

> **Scope:** Widget registration, frontend/backend modules, JSON-RPC protocol, services, commands, keybindings, status bar, layout, extension boundaries, backend safety  
> **Agent count:** 12 parallel sub-agents  
> **IDE phases:** R1-R51, R62, R71, R79, R-AUDIT12/16/21/23 all Baseline Complete

---

## 1. Theia Architecture Map

```
┌─────────────────────────────────────────────────────────────────┐
│               ARC Studio Theia IDE                               │
│                                                                  │
│  Browser Process (Theia frontend)                                │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ArcStudioWidget (rank 90, area:left)  ← PRIMARY SHELL     │ │
│  │  12 React tabs: Chat / Runs / Workflows / Assurance /       │ │
│  │  SwarmGraphInsight / Battle / CommandCentre / MCP           │ │
│  │  Workbench / TestBench / EditPlans / CIGuardrails / Config  │ │
│  │                                                             │ │
│  │  ArcWidget (rank 100, area:left)       ← LEGACY (keep)     │ │
│  │                                                             │ │
│  │  Standalone widgets (area:main, URL-param/cmd only):        │ │
│  │  ArcEventStreamWidget  ArcWorkflowGraphWidget               │ │
│  │  ArcAdaptersWidget     ArcSimulationWidget                  │ │
│  │  ArcHealthWidget       ArcMobileWidget                      │ │
│  │  ArcWelcomeWidget      ArcContextDrawer (UNREACHABLE ⚠️)    │ │
│  │  ArcRunTimelineWidget  (DEAD CODE — no contribution ⚠️)     │ │
│  │                                                             │ │
│  │  ArcService (WebSocket JSON-RPC proxy)                      │ │
│  │  ← 72 methods via /services/arc channel                     │ │
│  │  NotificationService (polling) ← /services/arc/notifications│ │
│  └─────────────────────────┬───────────────────────────────────┘ │
│                             │ WebSocket JSON-RPC                  │
│  Node Process (Theia backend)                                    │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  ArcBackendService (facade, nearly all @deprecated)        │ │
│  │  ↓ delegates to 14 sub-services                            │ │
│  │  WorkflowExecutor    TraceParser       WorkflowDetector     │ │
│  │  FileManager         ConfigService     RunLifecycleService  │ │
│  │  AuditBridgeService  BattleService     DaemonDiscovery      │ │
│  │  SessionBridge       LocalTelemetry    EditPlanBridge       │ │
│  │  NotificationBackend WorkspaceRoot                          │ │
│  │                                                             │ │
│  │  GET /api/health  GET /api/metrics                          │ │
│  └─────────────────────────┬───────────────────────────────────┘ │
│                             │ HTTP + CLI subprocess               │
└─────────────────────────────┼───────────────────────────────────┘
                              │
              Python Daemon (127.0.0.1:7777)
              arc CLI subprocess (execFileSync with env allowlist)
```

### InversifyJS binding summary

| Layer | Bindings | Key facts |
|---|---|---|
| Frontend module | 53 bindings | 11 `FrontendApplicationContribution` impls; `arena-frontend-module.ts` is dead code (inlined) |
| Backend module | 15 services | 2 JSON-RPC channels; health/metrics not in ContainerModule |
| ArcService | 1 proxy token | `ArcStatusBarContribution` bypasses DI (creates own proxy) |

---

## 2. Protocol Method Inventory

**Total methods: 72** — significantly oversized; `notification-protocol.ts` (1 method) is the correct model.

### Method groups

| Group | Methods | Count |
|---|---|---|
| Core execution | executeWorkflow, cancelWorkflow, preflightRun, startRun, runGatedProviderAction | 5 |
| Traces | getTraces, readTrace, streamTrace*, streamActiveTrace*, readActiveTraceStream, cancelActiveTraceStream, validateTrace | 7 |
| Workflows/runtimes | detectWorkflows, listRuntimeCapabilities, getCapabilityDiff | 3 |
| Provider/config | getProviderStatus, getConfigStatus, saveConfig, listProfiles, getIsolationStatus, listIsolationProviders, getProviderCatalog, getProviderDiagnostics, getProviderQuota, resetProviderQuota, setProviderKeyRef, unsetProviderKeyRef, testProvider, listProviderModels, getProviderAccount, updateProviderAccount | 16 |
| Workspace/telemetry | getWorkspaceStatus, getMcpWorkbenchStatus, getWorkspaceInventory, detectTestbench, getCiCheckStatus | 5 |
| Run cockpit cards | getRunLinks, getRunReceipt, getRunAutopsy, getRunContract, getCapabilityCardSummary | 5 |
| HITL + audit | listPendingHitlPrompts, respondHitlPrompt, getAuditChainInfo, getMcpDecisions | 4 |
| Replay/diff | replayRun, diffRuns | 2 |
| Daemon | getPythonDaemonUrl, discoverPythonDaemonUrl | 2 |
| Battle | listBattles, getBattleDetails, getLeaderboard | 3 |
| Sessions | listChatSessions, getChatSession, importSession, deleteSession, updateSessionField | 5 |
| Edit plans | listEditPlans, showEditPlan, approveEditPlan, diffEditPlan, applyEditPlan | 5 |
| Security/sandbox | sandboxInspect, getMobileStatus | 2 |

`*` `streamTrace`/`streamActiveTrace` return `AsyncIterable` — **not JSON-RPC serializable** over the standard Theia channel.

### Recommended protocol split

| New service | Method count | Rationale |
|---|---|---|
| `WorkflowService` | 8 | Execution + runtime detection cohesion |
| `TraceService` | 9 | All trace I/O + replay |
| `ConfigService` (protocol) | 16 | Provider/config cohesion (backend service already exists) |
| `RunDetailsService` | 5 | Cockpit cards |
| `HitlAuditService` | 4 | HITL + audit decisions |
| `SessionService` | 5 | Sessions |
| `EditPlanService` | 5 | Edit plans |
| `BattleService` | 3 | Types already split to battle-protocol.ts |
| `TelemetryService` | 5 | Read-only telemetry/workspace |
| Keep on `ArcService` | 5 | Daemon discovery + workspace status glue |

Proxy test currently covers only 34/72 methods — 38 methods are untested at the contract level.

---

## 3. Widget / Page Inventory

### ArcStudioWidget — primary shell (12 tabs)

| # | Tab ID | Component | Notes |
|---|---|---|---|
| 1 | `chat` | ChatTab | `onNavigateToRuns` cross-tab callback |
| 2 | `runs` | RunsTab | `initialRunId` from ChatTab navigation |
| 3 | `workflows` | WorkflowsTab | Scan + display |
| 4 | `assurance` | AssuranceTab | HITL + audit + replay |
| 5 | `swarmgraph-insight` | SwarmGraphInsightTab | Trace-backed or live stream |
| 6 | `battle` | BattleTab | LM Arena (stub-gated) |
| 7 | `command-centre` | CommandCentreTab | 12 ArcService aggregate calls |
| 8 | `mcp-workbench` | McpWorkbenchTab | MCP server status |
| 9 | `testbench` | TestBenchTab | Detect-only; **no Run button** |
| 10 | `edit-plans` | EditPlansTab | Edit plan review/approve |
| 11 | `ci-guardrails` | CiGuardrailsTab | CI check results |
| 12 | `config` | ConfigTab | Provider/config management |

**StudioTabId union type is incomplete** — lists 8 IDs but 12 exist.  
**No dynamic tab extension point** — tabs are a static hardcoded array.

### Standalone widgets

| Widget | Area | Access | Status |
|---|---|---|---|
| ArcEventStreamWidget | main | `?arc-view=event-stream` or command | Keep — advanced trace tool, unique capabilities |
| ArcWorkflowGraphWidget | main | command only | Keep |
| ArcAdaptersWidget | main | command only | Soft deprecation candidate — unique: CapabilityDiffViewer |
| ArcSimulationWidget | main | `?arc-view=simulation-panel` | Keep |
| ArcHealthWidget | main | `?arc-view=health-monitor` | Deprecation candidate — covered by CommandCentreTab |
| ArcMobileWidget | main | command only | Keep (simulator only) |
| ArcWelcomeWidget | main | pref-gated (default OFF) | Invisible by default |
| ArcContextDrawer | none | **UNREACHABLE** | No contribution, no command |
| ArcRunTimelineWidget | (main) | **DEAD CODE** | No contribution file exists |

### Component library (15 shared components)

RunReceiptCard, FailureAutopsyCard, RunContractCard, EvidenceChip, VirtualizedEventList, BudgetGauge, NotificationBadge, DenialModal, ShortcutsModal, PolicyBypassBanner, ProgressBar, ToastContainer, ErrorBanner, CapabilityDiffViewer, WorkflowExecutionSection, WorkflowDetectionSection, TraceViewerSection, ExecutionSteps

### Swarmgraph components (orphaned from tab)

DagPlannerViz, ConsensusEvidenceCard, HitlApprovalPanel — exist in `browser/swarmgraph/` but are NOT used by SwarmGraphInsightTab (which has inline equivalents).

---

## 4. Command / Keybinding Inventory

### All 16 registered commands

| Command ID | Label | Category | Keybinding | Source |
|---|---|---|---|---|
| `arc.execute` | ARC: Execute Workflow | — | `Ctrl+E` **⚠️ CONFLICT** | arc-keybinding-contribution |
| `arc.scanWorkspace` | ARC: Scan Workspace | — | `Ctrl+Shift+S` **⚠️ CONFLICT** | arc-keybinding-contribution |
| `arc.showShortcuts` | ARC: Show Shortcuts | — | `Ctrl+H` **⚠️ CONFLICT** | arc-keybinding-contribution |
| `arc.open` | Open ARC Studio | — | none | arc-widget-contribution (legacy) |
| `arc-studio:open` | Open ARC Studio | — | none | arc-studio-widget-contribution |
| `arc:open-workflow-graph` | ARC: Open Workflow Graph | ARC | none | arc-workflow-contribution |
| `arc:open-run-timeline` | ARC: Open Run Timeline | ARC | none | arc-runs-contribution |
| `arc:open-adapters` | ARC: Open Adapters Status | ARC | none | arc-adapters-contribution |
| `arc:open-event-stream` | ARC: Open Event Stream | ARC | none | arc-event-stream-contribution |
| `arc:open-health-monitor` | ARC: Show Health Monitor | ARC | none | arc-health-contribution |
| `arc:open-simulation-panel` | ARC: Show IR Simulation Panel | ARC | none | arc-simulation-contribution |
| `arc:open-welcome` | ARC: Open Welcome | — | none | arc-welcome-contribution |
| `arc:open-mobile-runtime` | ARC: Open Mobile Runtime | ARC | none | arc-mobile-contribution |
| `arc.arena.nextCompletion` | ARC Arena: Next Completion | — | `Alt+]` | arena-contribution |
| `arc.arena.previousCompletion` | ARC Arena: Previous Completion | — | `Alt+[` | arena-contribution |
| `arc.arena.acceptInlineCompletion` | ARC Arena: Record Inline Acceptance | — | **none** | arena-contribution |

### Keybinding conflicts (critical)

| Keybinding | ARC command | Theia/VS Code default |
|---|---|---|
| `Ctrl+E` / `Cmd+E` | `arc.execute` | **Go to File (Quick Open)** |
| `Ctrl+Shift+S` / `Cmd+Shift+S` | `arc.scanWorkspace` | **Save All** |
| `Ctrl+H` / `Cmd+H` | `arc.showShortcuts` | **Find & Replace** |

### Other keybinding issues

| Issue | Detail |
|---|---|
| No `when` guards on any keybinding | All 5 fire globally; no focus/context gate |
| ArcKeybindingContribution drives legacy widget | `arc.execute` opens ArcWidget, not ArcStudioWidget |
| Duplicate label "Open ARC Studio" | `arc.open` and `arc-studio:open` are indistinguishable in command palette |
| Inconsistent namespace | `arc.` vs `arc:` vs `arc-studio:` — three styles across 16 commands |
| `arc:open-welcome` missing category | All peer commands have `category: 'ARC'`; welcome does not |
| ArcWelcomeContribution double-registers command | `OpenWelcomeCommand` registered by both AbstractViewContribution and an explicit override |

---

## 5. Architecture Risks

### Critical / High severity

| # | Severity | Issue | Location |
|---|---|---|---|
| 1 | **Critical** | `Ctrl+E`, `Ctrl+Shift+S`, `Ctrl+H` conflict with core Theia editor defaults | `arc-keybinding-contribution.ts` |
| 2 | **Critical** | `ArcRunTimelineWidget` has no contribution file — dead code, unreachable | `arc-run-timeline-widget.tsx` |
| 3 | **Critical** | `NotificationBackendService` has no env allowlist — passes full `process.env` (with API keys) to child process | `services/notification-service.ts` |
| 4 | **High** | `ArcContextDrawer` is DI-bound but has no `AbstractViewContribution`, no command, no area — unreachable | `arc-context-drawer.tsx`, frontend module |
| 5 | **High** | `ArcStatusBarContribution` bypasses DI by calling `createProxy` directly — creates second unmanaged WebSocket proxy | `arc-status-bar-contribution.ts` |
| 6 | **High** | `ArcKeybindingContribution` injects and delegates to legacy `ArcWidgetContribution`, not primary `ArcStudioWidgetContribution` | `arc-keybinding-contribution.ts` |
| 7 | **High** | `ConfigService` account methods bypass `DaemonDiscoveryService` loopback validation (read `process.env` directly) | `services/config-service.ts` |
| 8 | **High** | `ConfigService.getProviderCatalog()`, `setProviderKeyRef()`, `unsetProviderKeyRef()` have no `try/catch` — exceptions propagate unhandled through RPC layer | `services/config-service.ts` |
| 9 | **High** | `~/.arc/providers.json` has no advisory lock on concurrent writes in `ConfigService.updateProviderAccount()` | `services/config-service.ts` |
| 10 | **High** | `streamTrace`/`streamActiveTrace` methods return `AsyncIterable` — not serializable over Theia's JSON-RPC channel | `arc-protocol.ts` |

### Medium severity

| # | Issue | Location |
|---|---|---|
| 11 | `ArcBackendService` is nearly all `@deprecated` with no replacement wiring in backend module | `arc-backend-service.ts` |
| 12 | Health endpoint (`/api/health`) does not check Python daemon — reports `ok` even when daemon is dead | `health-endpoint.ts` |
| 13 | Health endpoint version hardcoded as `"0.6.0-alpha"` (project is at v0.8-r-ux2) | `health-endpoint.ts` |
| 14 | Metrics counters (`requests`, `executions`, `errors`) never incremented — always report zero | `metrics-endpoint.ts` |
| 15 | `arena-frontend-module.ts` is dead code — identical bindings are inlined in main module; if ever loaded separately, would produce duplicate bindings | `arena-frontend-module.ts` |
| 16 | `ArcStudioWidget` and `ArcWidget` both declare `LABEL = 'ARC Studio'` — two identically-labeled entries in View menu | Both widgets |
| 17 | `StudioTabId` union type only lists 8 of 12 tab IDs — TypeScript safety gap for 4 newer tabs | `arc-studio-widget.tsx` |
| 18 | `@theia/getting-started` not suppressed — Theia's default welcome page appears on fresh install | `applications/browser/package.json` |
| 19 | Protocol too large — 72-method god interface; split into ~9 sub-services recommended | `arc-protocol.ts` |
| 20 | No dynamic tab extension point — new tabs require modifying `arc-studio-widget.tsx` directly | `arc-studio-widget.tsx` |

### Low severity

| # | Issue |
|---|---|
| 21 | `ArcWelcomeWidget` default OFF (`arc.ui.showOnboarding: false`) — welcome is invisible on fresh install |
| 22 | No right/bottom panel contributions — all content crowds the `main` editor area |
| 23 | No custom layout defaults — fresh install shows pure Theia defaults, no ARC panel |
| 24 | `sanitizePrompt` rejects `$` (valid in natural language) — overly restrictive |
| 25 | `_sseConnected` flag set optimistically before stream proven reachable |
| 26 | DaemonDiscoveryService URL cache has no mutex — concurrent expiry fires redundant health probes |

---

## 6. Improved IDE Implementation Prompt

**Target:** Fix the 5 highest-severity issues: keybinding conflicts, dead widget cleanup, env allowlist, unreachable context drawer, duplicate proxy.

```
# Theia IDE Next Slice: Keybinding Hardening + Dead Code + Env Safety

## Context

ARC Studio Theia IDE v0.8-r-ux2. Five architecture gaps discovered:

1. Three keybindings (Ctrl+E, Ctrl+Shift+S, Ctrl+H) conflict with core
   Theia defaults (Go to File, Save All, Find & Replace). They have no
   `when` context guards, fire globally, and invoke the legacy ArcWidget
   rather than ArcStudioWidget.

2. ArcRunTimelineWidget has no contribution file — it is DI-bound but
   unreachable. ArcContextDrawer is similarly bound but has no
   AbstractViewContribution, no command, and no layout area.

3. NotificationBackendService calls spawn('arc', args) with no env argument,
   passing full process.env (including API keys/tokens) to the child
   process. All other CLI-bridge services use buildArcCliEnv().

4. ArcStatusBarContribution bypasses the DI-registered ArcService singleton
   by calling WebSocketConnectionProvider.createProxy() directly, creating
   a second unmanaged WebSocket proxy on the same path.

5. ConfigService.getProviderCatalog(), setProviderKeyRef(), and
   unsetProviderKeyRef() have no try/catch — exceptions propagate
   unhandled through the JSON-RPC layer to the frontend.

## Scope

### 1. Fix keybinding conflicts and wiring

File: packages/arc-extension/src/browser/arc-keybinding-contribution.ts

Replace conflicting bindings with ARC-safe keys:
```typescript
// BEFORE:
{ command: 'arc.execute',     keybinding: 'ctrlcmd+e' },       // conflicts Go to File
{ command: 'arc.scanWorkspace', keybinding: 'ctrlcmd+shift+s' }, // conflicts Save All
{ command: 'arc.showShortcuts', keybinding: 'ctrlcmd+h' },      // conflicts Find & Replace

// AFTER (safe alternatives, no conflict with Theia defaults):
{ command: 'arc.execute',       keybinding: 'ctrlcmd+shift+r', when: 'focusedView == arc-studio-widget' },
{ command: 'arc.scanWorkspace', keybinding: 'ctrlcmd+shift+w', when: 'focusedView == arc-studio-widget' },
{ command: 'arc.showShortcuts', keybinding: 'f1 arc.showShortcuts', when: 'false' }, // palette only
```

Also redirect `arc.execute` and `arc.scanWorkspace` to invoke
`ArcStudioWidgetContribution.openView()` rather than `ArcWidgetContribution`:

```typescript
// In ArcKeybindingContribution.registerCommands():
// Change @inject(ArcWidgetContribution) to @inject(ArcStudioWidgetContribution)
```

### 2. Remove dead widget ArcRunTimelineWidget

File: packages/arc-extension/src/browser/arc-extension-frontend-module.ts

Remove:
```typescript
// DELETE these 2 lines:
bind(ArcRunTimelineWidget).toSelf();
bind(WidgetFactory).toDynamicValue(ctx => ({
    id: 'arc:run-timeline',
    createWidget: () => ctx.container.get(ArcRunTimelineWidget)
})).inSingletonScope();
bindViewContribution(bind, ArcRunsContribution);
bind(FrontendApplicationContribution).toService(ArcRunsContribution);
```

File: packages/arc-extension/src/browser/arc-run-timeline-widget.tsx — DELETE file.

### 3. Fix ArcContextDrawer — make it reachable

File: packages/arc-extension/src/browser/arc-context-drawer.tsx

Add static ID/LABEL and extend AbstractViewContribution:

```typescript
// Add to arc-extension-frontend-module.ts:
bindViewContribution(bind, ArcContextDrawerContribution);
bind(FrontendApplicationContribution).toService(ArcContextDrawerContribution);
```

Create: packages/arc-extension/src/browser/arc-context-drawer-contribution.ts:
```typescript
@injectable()
export class ArcContextDrawerContribution
    extends AbstractViewContribution<ArcContextDrawer> {
    constructor() {
        super({
            widgetId: ArcContextDrawer.ID,
            widgetName: ArcContextDrawer.LABEL,
            defaultWidgetOptions: { area: 'right' },  // right panel
            toggleCommandId: 'arc-context:open',
        });
    }
}
```

### 4. Fix NotificationBackendService env allowlist

File: packages/arc-extension/src/node/services/notification-service.ts

```typescript
// Import the shared env builder:
import { buildArcCliEnv } from '../services/arc-cli-utils';

// In the spawn call, add the env argument:
const child = spawn('arc', ['events', 'summary', '--json'], {
    shell: false,
    env: buildArcCliEnv(),  // ← ADD THIS
    timeout: 5000,
});
```

### 5. Fix ArcStatusBarContribution DI bypass

File: packages/arc-extension/src/browser/arc-status-bar-contribution.ts

```typescript
// BEFORE:
constructor(
    @inject(WebSocketConnectionProvider) private connectionProvider: WebSocketConnectionProvider,
    ...
) {}

private async getService(): Promise<ArcService> {
    if (!this._service) {
        this._service = this.connectionProvider.createProxy<ArcService>(ArcServicePath);
    }
    return this._service;
}

// AFTER:
constructor(
    @inject(ArcService) private arcService: ArcService,  // use DI singleton
    ...
) {}
```

### 6. Add try/catch to ConfigService missing error handling

File: packages/arc-extension/src/node/services/config-service.ts

Wrap the three unguarded methods:
```typescript
async getProviderCatalog(): Promise<ProviderCatalogEntry[]> {
    try {
        const result = execFileSync(...);
        return JSON.parse(result);
    } catch (error) {
        this.logger.warn('getProviderCatalog failed', error);
        return [];  // graceful degradation
    }
}
// Same pattern for setProviderKeyRef and unsetProviderKeyRef
```

### 7. Fix health endpoint Python daemon check and version

File: packages/arc-extension/src/node/health-endpoint.ts

```typescript
// Add Python daemon check:
private async checkPythonDaemon(): Promise<{status: 'ok'|'degraded'|'error', details?: string}> {
    try {
        const resp = await fetch('http://127.0.0.1:7777/health', { signal: AbortSignal.timeout(2000) });
        return resp.ok ? { status: 'ok' } : { status: 'degraded', details: `HTTP ${resp.status}` };
    } catch {
        return { status: 'error', details: 'Python daemon not reachable' };
    }
}

// Replace hardcoded version:
// BEFORE: version: '0.6.0-alpha'
// AFTER: version: require('../../../package.json').version
```

### 8. Complete StudioTabId union type

File: packages/arc-extension/src/browser/arc-studio-widget.tsx

```typescript
// BEFORE (8 IDs):
export type StudioTabId = 'chat' | 'runs' | 'workflows' | 'assurance' |
    'swarmgraph-insight' | 'battle' | 'config' | 'command-centre';

// AFTER (all 12):
export type StudioTabId = 'chat' | 'runs' | 'workflows' | 'assurance' |
    'swarmgraph-insight' | 'battle' | 'config' | 'command-centre' |
    'mcp-workbench' | 'testbench' | 'edit-plans' | 'ci-guardrails';
```

## Do NOT do in this slice

- Protocol service split (9 sub-services) — major breaking change, separate slice
- Full accessibility test rewrite (separate a11y slice)
- Dynamic tab extension point
- Electron packaging
- McpWorkbenchTab decisions stream pane
- Legacy ArcWidget removal (requires staged deprecation)

## Non-negotiable constraints (AGENTS.md)

- Keybinding changes must not break existing user muscle memory silently
  — add a release note / deprecation warning if changing defaults
- NotificationBackendService fix MUST use buildArcCliEnv() — no exceptions
- ArcContextDrawer CLI proxy wiring remains stub (R-AUDIT16 follow-on)
- Run pnpm typecheck && pnpm build after all TypeScript changes
- Document failures honestly
```

---

## Appendix: Quick Reference

### Frontend module binding count

| Concern | Bindings |
|---|---|
| PreferenceContribution | 1 |
| ArcService proxy (canonical) | 1 |
| FrontendApplicationContribution | 11 |
| CommandContribution | 2 |
| KeybindingContribution | 2 |
| WidgetFactory | 11 |
| Widget (toSelf) | 11 |
| bindViewContribution | 10 (ArcContextDrawer excluded) |
| **Total** | **~53** |

### Backend service responsibilities

| Service | Responsibility |
|---|---|
| DaemonDiscoveryService | Loopback URL validation, 2s health probe, 30s TTL cache |
| arc-cli-utils | Shared env allowlist (10 vars), safe config key whitelist |
| ConfigService | Provider status/catalog/diagnostics/quota, isolation, workspace config |
| SessionBridgeService | Chat session read/write, write mutex, SSE push subscription |
| NotificationBackendService | Async CLI poll for event counts (**missing env allowlist**) |
| RunLifecycleService | Run start/preflight/active-trace |
| AuditBridgeService | Audit chain, run receipt, autopsy |
| BattleService | LM Arena battles/ELO |
| LocalTelemetryService | MCP workbench, workspace inventory, CI, sandbox inspect |
| EditPlanBridgeService | Edit plan metadata bridge |
| WorkflowExecutor | Workflow execution + cancellation |
| TraceParser | Trace file parsing + streaming |
| WorkflowDetector | Workspace workflow detection |
| FileManager | Trace file management |

### Status bar slots

| ID | Content | Priority | Alignment | Polling |
|---|---|---|---|---|
| `arc-backend-status` | `$(circle) ARC` (online/offline dot) | 10 | LEFT | 10s (no dirty-check) |
| `arc-profile-status` | `$(shield) Profile: <value>` | 9 | LEFT | 10s (not reactive to pref changes) |

### R-UX / IDE roadmap phases (all Baseline Complete)

R1 (streaming), R2 (runtime setup), R3 (provider UI), R4 (HITL), R5 (SwarmGraph), R8, R9, R10, R11, R12 (Electron spike), R44 (write bridge), R47, R48 (MCP workbench), R49 (testbench), R50 (Theia-native split), R51 (CI guardrails), R62 (edit plans), R71 (diff review), R79 (mobile), R-AUDIT12/16/21/23

### Remaining open IDE items

- ArcContextDrawer CLI proxy wiring (R-AUDIT16 follow-on)
- TestBenchTab Run button wiring
- McpWorkbenchTab MCP decisions stream pane (P1 gap, D-05)
- Legacy ArcWidget removal (staged deprecation)
- R50 broader backend service split
- Axe-core accessibility pass (deferred)
- Electron packaging (v0.2)
- LM Arena IDE tab productization (deferred)
