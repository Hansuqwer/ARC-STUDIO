# ARC Studio Accessibility, Performance & Reliability Audit — 2026-06-07

> **Scope:** Accessibility (WCAG 2.1 AA), keyboard navigation, screen reader support, reduced motion, high contrast, large trace rendering, event buffers, async cancellation, backend-degraded states, error boundaries  
> **Source:** Synthesized from UX, TUI, Theia IDE, runs/events, security, and CI audits

---

## 1. Accessibility Audit

### WCAG 2.1 AA failures (confirmed)

| Violation | Component | WCAG criterion | Fix |
|---|---|---|---|
| `critical` and `high` risk badges both map to CSS class `info` (blue) | McpWorkbenchTab `RISK_VARIANT` | **1.4.1 Use of Color** | Map critical→`danger` (red), add `aria-label="Risk level: critical"` |
| Keyboard navigation test suite: 3 describe blocks are `expect(true).toBe(true)` no-ops | `accessibility.test.tsx` | — | Replace with real renders + `axe()` + keyboard events |
| SandboxInspect input has no `<label>` or `aria-label` | CommandCentreTab | **1.3.1 Info and Relationships** | Add `aria-label="Command to inspect"` |
| Refresh buttons across all tabs have no `aria-label` | McpWorkbenchTab, TestBenchTab, CiGuardrailsTab | **4.1.2 Name, Role, Value** | Add descriptive `aria-label="Refresh MCP workbench status"` |
| Risk badge spans have no `aria-label` | McpWorkbenchTab decisions list | **4.1.2** | `aria-label={`Risk level: ${entry.riskScore}`}` |
| `Ctrl+O` TUI binding is a no-op (advertised but non-functional) | TUI ArcScreen | Honesty/discoverability | Either implement or remove from BINDINGS |
| `Ctrl+R` TUI history search silently dropped (no handler) | TUI InputArea | Honesty/discoverability | Implement or remove from KeycapHint |
| ToolCard "Ctrl+C to copy" hint is display text only — no clipboard action | TUI ToolCard expanded state | 4.1.2 | Implement copy or change hint to "select to copy" |
| HelpScreen is static text missing 12+ implemented features | TUI HelpScreen | Discoverability | Auto-generate from slash command registry |
| `tab` button `aria-controls` in ArcStudioWidget points to panel but focus ring may not be visible after keyboard nav | IDE ArcStudioWidget | **2.4.7 Focus Visible** | Add `:focus-visible` ring on `arc-studio-tab--active` after keyboard activation |

### Confirmed accessible ✅

| Feature | Component | Evidence |
|---|---|---|
| `role="tablist"` / `role="tab"` / `aria-selected` / `role="tabpanel"` | ArcStudioWidget | Verified in contract test |
| `aria-label="MCP Workbench"` on widget root | McpWorkbenchTab | Verified |
| Error states: `role="alert"` | McpWorkbenchTab | Verified |
| `*:focus-visible { outline: 2px solid var(--theia-focusBorder) }` | arc-studio-widget.css | Global rule |
| `@media (prefers-reduced-motion: reduce)` | arc-studio-widget.css | Suppresses transitions |
| `ARC_REDUCED_MOTION=1` → text spinner | TUI theme_extras.py | Tested |
| `NO_COLOR` env → mono theme → ASCII glyph substitutions | TUI theme.py | All 33 fallback entries tested |
| `high-contrast` theme: pure black/white, bright primaries | TUI theme.py | Test for background/foreground values |
| `role="status"` on ArcStudioWidget status strip | arc-studio-widget.tsx | Verified in contract test |
| `aria-label="Risk level: X"` (after proposed fix) | McpWorkbenchTab | Proposed above |
| 6 TUI themes including high-contrast and mono | TUI theme.py | All 6 tested |

### Accessibility test quality

The `accessibility.test.tsx` file:
- Uses **inline fake components**, not real production components
- Three describe blocks ("Keyboard Navigation", "Screen Reader", "Color Contrast") are **pure no-ops**: `expect(true).toBe(true)` with TODO comments
- Real axe scans are against fabricated JSX — provides zero protection for production component regressions

---

## 2. Performance Audit

### Large trace rendering

| Surface | Virtualized? | Bounded? | Risk |
|---|---|---|---|
| ArcEventStreamWidget | ✅ `VirtualizedEventList` | Display bounded; `liveEvents[]` array grows unbounded | Memory OOM on long-running streams |
| ArcRunTimelineWidget | ❌ raw array | ❌ unbounded | Dead code (no contribution file); OOM risk if ever enabled |
| TraceParser.streamTrace() | N/A | ❌ No per-line size limit | 100 MB trace file → OOM in Node backend |
| readActiveTraceStream() | N/A | ❌ Buffers entire stream | Collects all chunks before returning |
| AssuranceTab replay events | ❌ | ❌ | All events loaded into DOM |

**liveEvents array issue:** Both ArcEventStreamWidget and ArcRunTimelineWidget use `[...this.liveEvents, event]` — O(n) array copy on every event. At 10,000 events: 10,000 array copies, 10,000 TraceEvent objects in heap.

**Fix (priority):** Cap `liveEvents` at `MAX_LIVE_EVENTS = 2000`, keep most recent, show eviction banner.

### Event buffers

| Buffer | Bounded? | Overflow behavior |
|---|---|---|
| EventBroker.RingBuffer(1000) | ✅ | Drop-oldest when full |
| EventBroker subscriber queue (maxsize=1000) | ✅ | Drop-oldest (slow client policy) |
| ArcEventStreamWidget.liveEvents | ❌ | Unbounded array growth |
| TUI ActivityTray events | ✅ N_MAX=20 | Oldest evicted |
| NotificationBackendService output cap | ✅ 64KB | Hard cap on CLI output |

### Async/blocking performance

| Operation | Blocking? | Duration | Risk |
|---|---|---|---|
| `startRun()` in RunLifecycleService | ❌ Fixed | N/A | **FIXED**: use execFileAsync (see runs/events audit) |
| `listRuntimeCapabilities()` | ❌ Fixed | N/A | Should use execFileAsync |
| `saveConfig()` in ConfigService | ✅ execFileSync | 10s | Blocks Node backend |
| `getConfigStatus()` | ✅ 2× execFileSync sequential | 20s | Blocks Node backend |
| TUI shell escape `_run_coro_sync` | ✅ | Varies | Blocks Textual main thread |
| `asyncio.run(provider.execute(...))` in plan_apply | ✅ | Varies | Blocks CLI process per step |
| 4× git subprocess calls in workspace inventory | ✅ sequential | Max 20s | Blocks Python process |

### React performance

| Issue | Component | Detail |
|---|---|---|
| `setElement` every 10s without dirty check | TUI status bar | Re-renders unconditionally on timer |
| Profile item not reactive to pref changes | IDE status bar | Only refreshes every 10s |
| AssuranceTab 10s HITL interval destroyed on tab switch | ArcStudioWidget | Interval created/destroyed on every mode/tab change |
| `[...this.liveEvents, event]` O(n) copy | ArcEventStreamWidget | See liveEvents section above |

---

## 3. Reliability Audit

### Backend unavailable: does UI crash?

| Surface | Backend down behavior | Honest? |
|---|---|---|
| IDE ConfigTab | Returns degraded `ConfigStatus` with 3 hardcoded fallback providers | ✅ Shows "Backend unavailable" message |
| IDE status bar | `arc-backend-status` shows outline circle `○ ARC` | ✅ |
| McpWorkbenchTab | Shows loading/error/empty states | ✅ |
| TUI daemon poll | Sets `daemon_online=False`, shows `○` in status bar | ✅ |
| IDE ChatTab | `startRun()` throws → shows error in transcript | ⚠️ No "backend unavailable" specific message |
| TUI `_execute_run()` | Provider error → logged, session saved | ✅ |
| ArcEventStreamWidget live mode | → `state: 'disconnected'` terminal chunk + 5-retry backoff | ✅ |
| RunsTab artifact fetches | `.catch(() => null)` → **silent failure** | ❌ |
| AssuranceTab HITL | 10s poll → shows degraded state on error | ✅ |
| NotificationBackendService | On CLI fail → `{degraded: true, all counts: 0}` | ✅ |

### Empty / loading / error state consistency

**IDE CSS has 4 state banner variants:** `info`, `warning`, `error`, `success` — used consistently across AssuranceTab, McpWorkbenchTab, TestBenchTab, CiGuardrailsTab.

**Inconsistencies found:**
- RunsTab: `RunReceiptCard`, `FailureAutopsyCard`, `RunContractCard` silently absent when `.catch(() => null)` fires — no "Receipt unavailable" state shown
- TUI transcript: streaming broken at widget layer — `MarkdownBlock` not refreshed during streaming
- TUI SessionsView: advertises "Enter switch" but action is not implemented — no error shown

### Cancellation reliability

| Operation | Cancellable? | Reliable? | Notes |
|---|---|---|---|
| `cancelWorkflow()` | ✅ | ✅ SIGTERM → SIGKILL | WorkflowExecutor subprocess |
| `cancelActiveTraceStream()` | ✅ | ⚠️ async token | One in-flight chunk may arrive after cancel |
| ArcEventStreamWidget activeStreamToken | ✅ | ✅ | Increments on trace switch; stale streams detected |
| ArcRunTimelineWidget | ❌ | ❌ | No cancellation on trace switch |
| `startRun()` execFileSync | ❌ | ❌ | 120s block cannot be interrupted |
| TUI shell escape 30s timeout | ✅ | ⚠️ | `asyncio.TimeoutError` crashes proxy loop; no JSONRPC error returned |

### Duplicate submit prevention

| Surface | Duplicate submit possible? | Notes |
|---|---|---|
| ChatTab Send button | ⚠️ | `disabled` prop when `isRunning`; state may not be set fast enough on rapid double-click |
| ConfigTab Save button | ⚠️ | `execFileSync` blocks; second save impossible while first is blocking; but if async, no guard |
| ApprovalCard buttons | ✅ | Modal dismissed on first click; buttons unreachable after |
| TUI Enter key | ✅ | `is_streaming=True` gates submission |

### Error boundaries

**IDE:** No React `ErrorBoundary` components found in any tab or widget. A runtime React error in `ChatTab`, `RunsTab`, or any other tab will crash the entire `ArcStudioWidget` to a white screen. There is no per-tab error boundary.

**TUI:** Textual's built-in crash handler shows a stack trace overlay. TUI widgets use `try/except` around most operations — more resilient but no formal error boundary pattern.

---

## 4. Prioritized Bug List

### P0 — Breaks product function or causes data loss

| # | Bug | Surface | Fix |
|---|---|---|---|
| B1 | TUI streaming tokens invisible | TUI Transcript/MarkdownBlock | Poll loop must call `MarkdownBlock.update()` during `is_streaming` |
| B2 | `critical` and `high` risk indistinguishable | IDE McpWorkbenchTab | Map critical→danger CSS class + aria-label |
| B3 | RunReceiptCard/FailureAutopsyCard/RunContractCard silently absent | IDE RunsTab | Replace `.catch(() => null)` with explicit error state |
| B4 | Ctrl+Q exits TUI without session save | TUI ArcApp | Route through `_do_exit()` or add save in `on_quit` |

### P1 — Degrades UX significantly

| # | Bug | Surface | Fix |
|---|---|---|---|
| B5 | `liveEvents[]` grows unbounded in event stream | IDE ArcEventStreamWidget | Cap at 2000, show eviction banner |
| B6 | SessionsView "Enter switch" does nothing | TUI SessionsView | Implement switch or remove hint text |
| B7 | `Ctrl+O` no-op advertised in BINDINGS | TUI ArcScreen | Implement expand or remove binding |
| B8 | `Ctrl+R` history search silently dropped | TUI InputArea | Implement UI or remove hint |
| B9 | `saveConfig()` / `getConfigStatus()` block Node backend | IDE ConfigService | Convert to async (execFileAsync) |
| B10 | No React error boundaries in any tab | IDE ArcStudioWidget | Add per-tab ErrorBoundary wrapper |
| B11 | SettingsView theme/mode not persisted on Apply | TUI SettingsView | Wire theme/mode persistence in on_button_pressed |

### P2 — Accessibility / developer experience

| # | Bug | Surface | Fix |
|---|---|---|---|
| B12 | Accessibility tests are no-ops | `accessibility.test.tsx` | Render real components + jest-axe |
| B13 | SandboxInspect input missing aria-label | IDE CommandCentreTab | Add `aria-label="Command to inspect"` |
| B14 | Refresh buttons no aria-label | IDE multiple tabs | Add descriptive aria-labels |
| B15 | HelpScreen missing 12 documented features | TUI HelpScreen | Auto-generate from registry |
| B16 | `arch-studio-cli` entrypoint typo | Python pyproject.toml | Fix to `arc-studio-cli` |
| B17 | `protocol: "sse"` hardcoded lie in events summary | Python events CLI | Change to `protocol: "cli-poll"` |

---

## 5. Test Plan

### Immediate (fill critical zero-coverage gaps)

```typescript
// 1. Accessibility: render real components with jest-axe
import { render } from '@testing-library/react';
import { axe } from 'jest-axe';

it('McpWorkbenchTab has no axe violations', async () => {
    const { container } = render(<McpWorkbenchTab arcService={mockService} />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
});

// 2. Keyboard navigation: tab order in ArcStudioWidget
it('tab buttons are keyboard navigatable', async () => {
    render(<ArcStudioWidget ... />);
    userEvent.tab(); // should focus first tab button
    expect(screen.getByRole('tab', { name: 'Chat' })).toHaveFocus();
    userEvent.keyboard('{ArrowRight}');
    expect(screen.getByRole('tab', { name: 'Runs' })).toHaveFocus();
});

// 3. Error boundary: tab crash is isolated
it('ChatTab error does not crash RunsTab', () => {
    // Render with ChatTab throwing
    // Assert RunsTab still renders
});

// 4. liveEvents cap
it('liveEvents capped at 2000', async () => {
    // push 2500 events, assert liveEvents.length === 2000
    // assert eviction banner present
});
```

```python
# 5. TUI streaming update
def test_markdown_block_refreshes_during_streaming(screen):
    # Simulate append_to_last() during is_streaming
    # Assert MarkdownBlock.render() contains updated content

# 6. TUI Ctrl+Q saves session
def test_ctrl_q_saves_session(app_pilot):
    # Send Ctrl+Q
    # Assert session file exists at ~/.arc/sessions/{id}/session.json

# 7. SettingsView theme persists
async def test_settings_theme_persists_on_apply(app_pilot):
    # Mount SettingsView, select "mocha", press Apply
    # Assert app.theme_manager.current.name == "mocha"
```

### Contract test additions

```typescript
// In studio-tabs.contract.test.ts:
it('shows honest receipt missing state', () => {
    expect(source).toMatch(/Receipt unavailable/);
    expect(source).toMatch(/receiptError/);
});

it('all tabs wrapped in ErrorBoundary', () => {
    expect(source).toMatch(/ErrorBoundary/);
});
```

### Performance tests (new)

```typescript
it('liveEvents array does not grow beyond MAX_LIVE_EVENTS', () => {
    // Benchmark: push 10,000 events, measure heap delta
});

it('VirtualizedEventList renders only visible rows', () => {
    // Check that DOM contains only ~10 rows, not 10,000
});
```

---

## 6. Improved Implementation Prompt

**Target:** Four focused fixes addressing the P0/P1 gaps in the audit.

```
# A11y/Performance/Reliability Slice: Streaming + Error Boundaries + liveEvents Cap + Axe Tests

## Context

ARC Studio v0.8-r-ux2. Four gaps:

1. TUI streaming is visually broken. append_to_last() mutates DataStore
   but the already-mounted MarkdownBlock never re-renders.

2. No React ErrorBoundary wraps any tab. A runtime error in ChatTab
   crashes the entire ArcStudioWidget to a white screen with no fallback.

3. liveEvents arrays in ArcEventStreamWidget grow without bound using
   [...this.liveEvents, event]. At 10,000+ events this causes OOM.

4. accessibility.test.tsx tests fake components; three describe blocks
   are pure no-ops. No real component has an axe scan.

## Scope

### Fix 1: TUI streaming (python/tui/widgets/transcript.py)

In the 100ms polling loop, refresh the last MarkdownBlock during streaming:
```python
def _poll_entries(self) -> None:
    # ... existing new-entry mounting ...
    if self.data.is_streaming and self.data.entries:
        last = self.data.entries[-1]
        if last.role == "assistant":
            try:
                blocks = list(self.query(MarkdownBlock))
                if blocks:
                    blocks[-1].update(last.content)
            except Exception:
                pass  # never crash the poll loop
```

### Fix 2: Per-tab ErrorBoundary (arc-studio-widget.tsx)

```tsx
class TabErrorBoundary extends React.Component<
    { tabId: string; children: React.ReactNode },
    { hasError: boolean; errorMessage: string }
> {
    constructor(props) {
        super(props);
        this.state = { hasError: false, errorMessage: '' };
    }
    static getDerivedStateFromError(error: Error) {
        return { hasError: true, errorMessage: error.message };
    }
    render() {
        if (this.state.hasError) {
            return (
                <div role="alert" className="arc-studio-assurance__state-banner arc-studio-assurance__state-banner--error">
                    <span className="arc-studio-assurance__state-icon">✗</span>
                    <div className="arc-studio-assurance__state-body">
                        <div className="arc-studio-assurance__state-title">
                            {this.props.tabId} tab encountered an error
                        </div>
                        <div className="arc-studio-assurance__state-detail">
                            {this.state.errorMessage}
                        </div>
                        <button onClick={() => this.setState({ hasError: false, errorMessage: '' })}>
                            Retry
                        </button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}

// Wrap each tab panel:
<div role="tabpanel" hidden={activeTab !== tab.id}>
    <TabErrorBoundary tabId={tab.id}>
        {activeTab === tab.id && renderTab(tab.id)}
    </TabErrorBoundary>
</div>
```

### Fix 3: Cap liveEvents (arc-event-stream-widget.tsx)

```typescript
private readonly MAX_LIVE_EVENTS = 2000;
private liveEventsEvicted = 0;

// In runLiveStream():
const next = [...this.liveEvents, event];
if (next.length > this.MAX_LIVE_EVENTS) {
    this.liveEventsEvicted += next.length - this.MAX_LIVE_EVENTS;
    this.liveEvents = next.slice(-this.MAX_LIVE_EVENTS);
} else {
    this.liveEvents = next;
}
```

Add eviction banner in render():
```tsx
{this.liveEventsEvicted > 0 && (
    <div style={evictionBannerStyle} role="status">
        {this.liveEventsEvicted} earlier events dropped (buffer cap {this.MAX_LIVE_EVENTS}).
        {' '}<button onClick={() => { this.liveEventsEvicted = 0; this.update(); }}>Dismiss</button>
    </div>
)}
```

### Fix 4: Real axe coverage (accessibility.test.tsx)

Replace all 4 fake-component tests with real renders:
```tsx
import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

// Real component tests:
describe('McpWorkbenchTab accessibility', () => {
    it('has no axe violations', async () => {
        const mockService = createMockArcService();
        const { container } = render(
            <McpWorkbenchTab arcService={mockService} />
        );
        expect(await axe(container)).toHaveNoViolations();
    });

    it('risk badges have aria-labels', () => {
        const { getAllByRole } = render(<McpDecisionRow entry={highRiskDecision} />);
        const badges = getAllByRole('generic').filter(el => el.getAttribute('aria-label')?.startsWith('Risk level:'));
        expect(badges.length).toBeGreaterThan(0);
    });
});

describe('ArcStudioWidget keyboard navigation', () => {
    it('tab buttons are keyboard navigatable with arrow keys', async () => {
        const { getByRole } = render(<ArcStudioWidget arcService={mockService} />);
        const firstTab = getByRole('tab', { name: 'Chat' });
        firstTab.focus();
        expect(firstTab).toHaveFocus();
    });
});
```

Replace the 3 no-op describe blocks with:
```tsx
// REMOVE these:
describe('Keyboard Navigation', () => { it('handles keyboard correctly', () => { expect(true).toBe(true) }) });
describe('Screen Reader', () => { it('has screen reader support', () => { expect(true).toBe(true) }) });
describe('Color Contrast', () => { it('meets WCAG contrast requirements', () => { expect(true).toBe(true) }) });

// REPLACE with real tests above
```

## Do NOT do in this slice

- Full keyboard navigation implementation (separate a11y sprint)
- VirtualizedEventList for AssuranceTab
- Fix all empty states (separate empty state pass)
- Ctrl+O / Ctrl+R implementation

## Verification

```bash
# Python streaming fix
cd python && uv run pytest tests/tui/ -q

# TypeScript fixes
pnpm typecheck && pnpm build
pnpm --filter arc-extension test
```
```

---

## Appendix: Confirmed accessible vs gap summary

### IDE (Theia)

| Area | Status | Notes |
|---|---|---|
| Tab ARIA structure | ✅ | role=tablist/tab/tabpanel, aria-selected |
| Error state role="alert" | ✅ | McpWorkbenchTab, AssuranceTab |
| Focus ring (CSS) | ✅ | `*:focus-visible` global rule |
| Reduced motion (CSS) | ✅ | `@media (prefers-reduced-motion)` |
| React ErrorBoundary | ❌ | None anywhere |
| Risk badge color-only distinction | ❌ | critical=high=blue (WCAG 1.4.1 fail) |
| Refresh button labels | ❌ | No aria-label |
| Sandbox input label | ❌ | No label or aria-label |
| axe scan on real components | ❌ | Tests use fakes |

### TUI (Textual)

| Area | Status | Notes |
|---|---|---|
| NO_COLOR support | ✅ | All widgets, 33 fallback entries |
| High contrast theme | ✅ | Pure black/white + bright primaries |
| ARC_REDUCED_MOTION | ✅ | Text spinner fallback |
| Focus management | ⚠️ | Only InputArea auto-focused; no focus cycling |
| Keyboard bindings documented | ⚠️ | HelpScreen missing 12 bindings |
| Ctrl+O stub | ❌ | Advertised, non-functional |
| Ctrl+R stub | ❌ | Posts unhandled message |
| Streaming visible | ❌ | MarkdownBlock not refreshed |
