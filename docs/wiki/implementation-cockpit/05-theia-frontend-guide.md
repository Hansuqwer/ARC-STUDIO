# 05 — Theia Frontend Guide

## Current State

**Main widget:** `packages/arc-extension/src/browser/arc-widget.tsx` (554 lines) — single panel with sections
**Components:** 8 components in `packages/arc-extension/src/browser/components/`
**Registration:** Single widget registration via `ArcWidgetContribution`

## Target State

Single `ArcStudioWidget` with 4 tabs: Chat, Runs, Workflows, Config. Status bar shows runtime/model/mode.

## Implementation Slice 1: ArcStudioWidget Shell

**Create file:** `packages/arc-extension/src/browser/arc-studio-widget.tsx`

```typescript
@injectable()
export class ArcStudioWidget extends ReactWidget {
  static ID = 'arc-studio';
  static LABEL = 'ARC Studio';

  protected render(): React.ReactNode {
    return (
      <div className='arc-studio'>
        <Tabs tabs={TABS} activeId={this.state.activeTab} onChange={this.switchTab} />
        <div className='arc-studio-content'>
          {this.renderActiveTab()}
        </div>
        <StatusBar runtime={...} model={...} mode={...} />
      </div>
    );
  }
}
```

**Tab IDs:** `chat`, `runs`, `workflows`, `config`

**Widget registration** (modify `arc-extension-backend-module.ts` or create new contribution):
```typescript
bindViewContribution(bindings, ArcStudioContribution);
bind(ArcStudioWidget).toSelf();
bind(WidgetFactory).toDynamicValue(ctx => ({
  id: 'arc-studio',
  createWidget: () => ctx.container.get(ArcStudioWidget),
}));
```

**Keep old widget:** `arc-widget.tsx` remains registered for backward compatibility.

**Acceptance criteria:**
- Single widget with 4 tabs renders
- Tabs switch correctly
- Default tab is Chat
- Old widget still works

## Implementation Slice 2: ChatTab

**Create file:** `packages/arc-extension/src/browser/tabs/ChatTab.tsx`

**Key elements:**
- Chat message transcript (user/agent bubbles)
- Inline action buttons (Run workflow, Approve, Reject)
- Mode toggle (Plan/Build/Auto)
- Runtime dropdown and Model dropdown above input
- Multiline input with send button
- Slash command hints below input
- Streaming response rendering
- Real-time status indicators (thought timers, checkmarks)

**Interfaces (from UX spec):**
- `ChatMessageProps` — role, content, timestamp, actions, evidenceRefs
- `ChatInputProps` — value, placeholder, autocomplete, mentions, onSubmit
- `ModeToggleProps` — value, onChange, disabledModes

**Acceptance criteria:**
- Chat sends messages to backend
- Agent responses render as bubbles
- Run workflow inline buttons work
- Mode toggle cycles Plan/Build/Auto
- HITL approval card renders with Approve/Reject

## Implementation Slice 3: RunsTab

**Create file:** `packages/arc-extension/src/browser/tabs/RunsTab.tsx`

**Merge:** Merges functionality from `arc-run-timeline-widget` and `arc-event-stream-widget`

**Key elements:**
- Split view: list on left, detail on right
- Color-coded status chips
- Inline RunSummary and FailureCard expansion
- Filters: status chips, runtime, date range
- Export/Delete/Open Advanced Trace actions
- Receipt link and Failure Autopsy expansion

**Interfaces:**
- `RunSummary` — runId, sessionId, runtime, status, startedAt, durationMs, costUsd, failureNode, contractId, receiptId
- `RunListProps` — runs, filters, onSelect, onOpenAdvancedTrace
- `RunList` renders only summary, no event timeline or event JSON in v0.1

**Acceptance criteria:**
- Run list loads from SQLite index
- Click run → detail panel shows summary
- Failed runs show FailureCard with autopsy
- Filters work (status, runtime, date)
- Advanced trace opens editor with raw events

## Implementation Slice 4: WorkflowsTab

**Create file:** `packages/arc-extension/src/browser/tabs/WorkflowsTab.tsx`

**Merge:** Merges `arc-workflow-graph-widget` into tab

**Key elements:**
- Card per workflow with runtime badge
- Agent/node count
- File location
- Run/Inspect/Graph actions
- Scan button to re-detect

**Acceptance criteria:**
- Workflows load from `detectWorkflows()`
- Card shows runtime badge, node count, file path
- Run button executes workflow
- Graph button opens graph in editor area
- Scan button re-detects workflows

## Implementation Slice 5: ConfigTab

**Create file:** `packages/arc-extension/src/browser/tabs/ConfigTab.tsx`

**Key elements:**
- Runtime radio selection with detection status
- Model dropdown
- Provider key status with add/edit
- Mode toggle (Plan/Build/Auto)
- Workspace trust status
- Save button → persists `.arc/config.yaml`
- Tabs: Runtime, Model, Providers, Trust, Advanced

**Acceptance criteria:**
- Config form loads current config
- Runtime selection saves to config
- Provider key add/edit works (routes to keyring)
- Mode toggle persists
- Save button writes `.arc/config.yaml`

## Implementation Slice 6: Status Bar

**Modify existing** status bar in Theia to show:
- `Runtime: swarmgraph` (click → open Config)
- `Model: sonnet` (click → open Config)
- `Mode: Build` (Plan/Build/Auto chip)
- `Daemon: ●` (daemon status)
- `Cost: $0.00` (session cost)

**Interface:**
```typescript
interface StatusSegmentProps {
  id: string;
  label: string;
  value: string;
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'running';
  onPress?: () => void;
}
```

**Acceptance criteria:**
- Status bar shows runtime, model, mode, daemon, cost
- Clicking segments navigates to relevant tab
- Status updates on config change

## Component Implementations

| Component | Props Interface | Location | Status |
|-----------|----------------|----------|--------|
| `RunContractCard` | `RunContract`, `onAccept`, `onEdit`, `onCancel` | New | [MISSING] |
| `RunReceiptCard` | `RunReceipt`, `onExport`, `onVerify` | New | [MISSING] |
| `FailureCard` | `RunSummary`, `autopsy?`, `lastEvents[]`, `onRetry`, `onOpenDoctor` | New | [MISSING] |
| `EvidenceChip` | `EvidenceRef`, `onOpen` | New | [MISSING] |
| `CostMeter` | `provider`, `model`, `estimatedCeilingUsd`, `approvalState` | New | [MISSING] |
| `CostCeilingBadge` | `estimatedMinimumUsd`, `estimatedMaximumUsd`, `approvalState` | New | [MISSING] |
| `DaemonStatusBadge` | `state`, `version?`, `port?`, `recoveryAction?` | New | [MISSING] |
| `GraphNode` | `id`, `label`, `type`, `runtime`, `state`, `badges` | Refactor existing | [EXISTS] |
| `DiffHunk` | `filePath`, `hunkId`, `status`, `lines`, `onApprove`, `onReject` | New | [MISSING] |
| `WorkspaceTrustBanner` | `workspacePath`, `onTrust`, `onStayUntrusted`, `onLearnMore` | New | [MISSING] |

## Do Not Implement Yet

- Trace UI (event timeline, event JSON viewer) — v0.1 out-of-scope
- Replay scrubber — v0.1 out-of-scope
- Phase/Loop views in Tasks panel — v0.2 [RESERVED]
- Device panel and Frames panel — v0.2 HotLoop [RESERVED]
- Router suggestion card — v0.2 [RESERVED]
- Handoff card — v0.2 [RESERVED]
- Inline Cursor-style editor diffs — v0.2
- Image attachments — v0.2
